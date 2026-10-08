import json
import logging
import sys
import warnings
from pathlib import Path

import pytest

from src.services import archive_profiles
from src.services.archive_profiles import (
    DEFAULT_PROFILE_NAME, ArchiveProfile, bundled_profiles_dir, load_profiles)
from src.utils.gitignore_parser import make_pathspec

STANDART = "Geliştirici (Standart)"
TEMIZ = "Müşteri Teslimi (Temiz)"
MINIMAL = "Yayınlama / Dağıtım (Minimal)"


def write_profile(directory: Path, file_name: str, data):
    directory.mkdir(parents=True, exist_ok=True)
    text = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    (directory / file_name).write_text(text, encoding="utf-8")


# ---- paketli profiller ---------------------------------------------------------------

def test_bundled_profiles_load_in_file_order_with_descriptions():
    profiles = load_profiles([bundled_profiles_dir()])
    assert list(profiles) == [STANDART, TEMIZ, MINIMAL]
    assert all(p.description for p in profiles.values())
    assert profiles[STANDART].patterns == []
    assert set(profiles[TEMIZ].patterns) <= set(profiles[MINIMAL].patterns)       # Minimal, Temiz'i genişletir


@pytest.mark.parametrize("path,temiz,minimal", [
    ("app.py", False, False),
    ("tests/a.py", True, True),
    ("src/tests/a.py", True, True),                  # eski regex: sızıyordu
    ("pkg/test/b.py", True, True),                   # eski regex: sızıyordu
    ("test_x.py", True, True),
    ("src/test_x.py", True, True),                   # eski regex: sızıyordu
    ("src/x_test.py", True, True),
    ("src/web/app.test.ts", True, True),
    ("conftest.py", True, True),
    ("docs/a.md", True, True),
    ("pkg/docs/a.md", False, False),                 # docs yalnızca kökte
    (".github/ci.yml", True, True),
    ("src/.github/x", False, False),
    ("README.md", False, True),
    ("README_old.txt", False, True),
    ("pkg/README.md", False, False),                 # README/LICENSE/pytest.ini yalnızca kökte
    ("LICENSE", False, True),
    ("pkg/LICENSE", False, False),
    ("pytest.ini", False, True),
    ("sub/pytest.ini", False, False),
    (".env", True, True),                            # gizli dosya müşteriye de gitmez
    ("backend/.env", True, True),                    # eski regex: gizli dosya sızıyordu
    ("backend/.env.local", True, True),
])
def test_bundled_profile_matching(path, temiz, minimal):
    profiles = load_profiles([bundled_profiles_dir()])
    assert profiles[STANDART].matches(path) is False
    assert profiles[TEMIZ].matches(path) is temiz
    assert profiles[MINIMAL].matches(path) is minimal


def test_windows_separators_are_normalised():
    assert load_profiles([bundled_profiles_dir()])[TEMIZ].matches("src\\tests\\a.py")


# ---- yükleme kuralları ----------------------------------------------------------------------

def test_extends_prepends_parent_patterns(tmp_path):
    write_profile(tmp_path, "a.json", {"name": "A", "exclude": ["a/"]})
    write_profile(tmp_path, "b.json", {"name": "B", "extends": "A", "exclude": ["b/"]})
    write_profile(tmp_path, "c.json", {"name": "C", "extends": "B", "exclude": ["c/"]})
    profiles = load_profiles([tmp_path])
    assert profiles["C"].patterns == ["a/", "b/", "c/"]
    assert profiles["C"].matches("x/a/f") and profiles["A"].matches("b/f") is False


def test_user_directory_overrides_bundled_profile_and_adds_new_ones(tmp_path):
    bundled, user = tmp_path / "bundled", tmp_path / "user"
    write_profile(bundled, "01.json", {"name": "Temiz", "description": "paketli", "exclude": ["tests/"]})
    write_profile(bundled, "02.json", {"name": "Diğer", "exclude": []})
    write_profile(user, "x.json", {"name": "Temiz", "description": "kullanıcı", "exclude": ["tests/", "docs/"]})
    write_profile(user, "y.json", {"name": "Benim", "exclude": ["*.bak"]})
    profiles = load_profiles([bundled, user])
    assert list(profiles) == ["Temiz", "Diğer", "Benim"]                # geçersiz kılınan profil yerini korur
    assert profiles["Temiz"].description == "kullanıcı" and profiles["Temiz"].matches("docs/a")


def test_negation_pattern_reincludes_a_file(tmp_path):
    write_profile(tmp_path, "a.json", {"name": "A", "exclude": ["tests/*", "!tests/keep.py"]})
    profile = load_profiles([tmp_path])["A"]
    assert profile.matches("tests/a.py") and not profile.matches("tests/keep.py")


@pytest.mark.parametrize("content", [
    "{ bozuk json",
    "[1, 2]",
    {"description": "ad yok", "exclude": []},
    {"name": "A", "exclude": "tests/"},
    {"name": "A", "exclude": [1, 2]},
    {"name": "  ", "exclude": []},
])
def test_invalid_profile_files_are_skipped_and_logged(tmp_path, caplog, content):
    write_profile(tmp_path, "bad.json", content)
    write_profile(tmp_path, "good.json", {"name": "İyi", "exclude": ["x/"]})
    with caplog.at_level(logging.WARNING):
        profiles = load_profiles([tmp_path])
    assert list(profiles) == ["İyi"]
    assert "bad.json" in caplog.text


def test_unknown_extends_and_cycles_skip_only_the_affected_profiles(tmp_path, caplog):
    write_profile(tmp_path, "1.json", {"name": "Tamam", "exclude": []})
    write_profile(tmp_path, "2.json", {"name": "Yetim", "extends": "Yok", "exclude": []})
    write_profile(tmp_path, "3.json", {"name": "X", "extends": "Y", "exclude": []})
    write_profile(tmp_path, "4.json", {"name": "Y", "extends": "X", "exclude": []})
    write_profile(tmp_path, "5.json", {"name": "Çocuk", "extends": "X", "exclude": []})
    with caplog.at_level(logging.WARNING):
        profiles = load_profiles([tmp_path])
    assert list(profiles) == ["Tamam"]
    assert "Yok" in caplog.text and "döngü" in caplog.text


def test_missing_directories_fall_back_to_a_do_nothing_default(tmp_path, caplog):
    with caplog.at_level(logging.ERROR):
        profiles = load_profiles([tmp_path / "yok"])
    assert list(profiles) == [DEFAULT_PROFILE_NAME] and profiles[DEFAULT_PROFILE_NAME].patterns == []
    assert "Hiç arşiv profili yüklenemedi" in caplog.text


def test_frozen_app_reads_profiles_from_meipass(tmp_path, monkeypatch):
    write_profile(tmp_path / "resources" / "profiles", "01.json", {"name": "Paketli", "exclude": []})
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert bundled_profiles_dir() == tmp_path / "resources" / "profiles"
    assert list(load_profiles([bundled_profiles_dir()])) == ["Paketli"]


def test_user_profile_dir_default_location(monkeypatch):
    monkeypatch.undo()                                # conftest'teki yalıtımı kaldır: gerçek varsayılanı doğrula
    assert archive_profiles.user_profiles_dir() == Path.home() / ".gitclean" / "profiles"


# ---- pathspec uyumu -------------------------------------------------------------------------------

def test_make_pathspec_emits_no_deprecation_warning():
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        spec = make_pathspec(["tests/", "/README*"])
    assert spec.match_file("a/tests/x.py") and spec.match_file("README.md") and not spec.match_file("a/README.md")


def test_empty_profile_matches_nothing():
    assert ArchiveProfile("Boş", "", []).matches("tests/a.py") is False
