import logging
import os
import zipfile
from pathlib import Path

import pytest

from src.services.archive_service import ArchiveService
from src.services.backup_service import BackupService
from src.utils.gitignore_parser import GitignoreParser


def write(path: Path, content="x", encoding="utf-8"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode(encoding) if isinstance(content, str) else content)
    return path


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "proj"
    write(root / "app.py", "print(1)")
    write(root / "src" / "mod.py", "x = 1")
    write(root / "secret.txt", "gizli")
    write(root / ".gitignore", "secret.txt\n*.log\n")
    write(root / "run.log", "log")
    write(root / "venv" / "lib.py")
    return root


def names(zip_path):
    with zipfile.ZipFile(zip_path) as zf:
        return sorted(zf.namelist())


# ---- .gitignore dayanıklılığı ----------------------------------------------------

def test_gitignore_with_bom_and_cp1254_is_read(tmp_path):
    root = tmp_path / "p"
    write(root / ".gitignore", b"\xef\xbb\xbfsecret.txt\n# \xfd\xfe\xf0 yorum\n*.tmp\n")      # BOM + cp1254 baytları
    parser = GitignoreParser(str(root))
    assert parser.load_error is None
    assert parser.should_ignore(str(root / "secret.txt")) and parser.should_ignore(str(root / "a.tmp"))
    assert not parser.should_ignore(str(root / "app.py"))


def test_unreadable_gitignore_sets_load_error_without_raising(tmp_path, monkeypatch, caplog):
    root = tmp_path / "p"
    write(root / ".gitignore", "x\n")
    real_open = open

    def deny(path, *args, **kwargs):
        if str(path).endswith(".gitignore"):
            raise PermissionError("erişim reddedildi")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", deny)
    with caplog.at_level(logging.ERROR):
        parser = GitignoreParser(str(root))
    assert parser.spec is None and "erişim reddedildi" in parser.load_error
    assert ".gitignore okunamadı" in caplog.text


def test_missing_gitignore_is_not_an_error(tmp_path):
    parser = GitignoreParser(str(tmp_path))
    assert parser.load_error is None and parser.spec is None


def test_archive_refuses_when_gitignore_is_unreadable(project, tmp_path):
    parser = GitignoreParser(str(project))
    parser.load_error = ".gitignore okunamadı: test"
    service = ArchiveService(parser)
    out = tmp_path / "out.zip"
    zip_result = service.create_zip(project, out)
    copy_result = service.copy_project(project, tmp_path / "copy")
    for result in (zip_result, copy_result):
        assert result["success"] is False and "gizli dosyaların" in result["error"].lower()
    assert not out.exists() and not (tmp_path / "copy").exists()


# ---- arşivleme (mevcut davranış korunur) ---------------------------------------------

def test_zip_applies_gitignore_and_excluded_dirs(project, tmp_path):
    service = ArchiveService(GitignoreParser(str(project)))
    out = tmp_path / "out.zip"
    result = service.create_zip(project, out)
    assert result["success"] and result["complete"] and result["failed_files"] == [] and result["error"] is None
    assert names(out) == [".gitignore", "app.py", "src/mod.py"]
    assert (result["total_files"], result["added_files"]) == (3, 3)
    assert result["skipped_files"] == 2                                  # secret.txt, run.log


def test_zip_inside_source_does_not_include_itself(project):
    service = ArchiveService(GitignoreParser(str(project)))
    out = project / "self.zip"
    assert service.create_zip(project, out)["success"]
    assert "self.zip" not in names(out)


def test_copy_skips_target_dir_inside_source(project):
    service = ArchiveService(GitignoreParser(str(project)))
    target = project / "export"
    result = service.copy_project(project, target)
    assert result["success"] and result["complete"]
    copied = sorted(p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file())
    assert copied == [".gitignore", "app.py", "src/mod.py"]               # export/ kendi içine kopyalanmaz


def test_progress_callback_reports_every_file(project, tmp_path):
    seen = []
    ArchiveService().create_zip(project, tmp_path / "o.zip", progress_callback=lambda d, t: seen.append((d, t)))
    assert seen and seen[-1][0] == seen[-1][1]


# ---- dosya başına hata ve yarım çıktı temizliği --------------------------------------------

def test_zip_continues_after_a_file_error_and_reports_it(project, tmp_path, monkeypatch, caplog):
    real_write = zipfile.ZipFile.write

    def flaky(self, filename, arcname=None, *args, **kwargs):
        if str(filename).endswith("mod.py"):
            raise PermissionError("dosya kilitli")
        return real_write(self, filename, arcname, *args, **kwargs)

    monkeypatch.setattr(zipfile.ZipFile, "write", flaky)
    out = tmp_path / "out.zip"
    with caplog.at_level(logging.WARNING):
        result = ArchiveService().create_zip(project, out)
    assert result["success"] is True and result["complete"] is False
    assert [Path(p).name for p, _ in result["failed_files"]] == ["mod.py"]
    assert "dosya kilitli" in result["failed_files"][0][1] and "mod.py" in caplog.text
    assert "src/mod.py" not in names(out) and "app.py" in names(out)
    assert result["added_files"] == result["total_files"] - 1


def test_fatal_zip_error_removes_partial_output_and_logs_traceback(project, tmp_path, monkeypatch, caplog):
    def explode(self, *args, **kwargs):
        raise RuntimeError("disk dolu")                                    # OSError değil: dosya başına yakalayıcıdan geçer

    monkeypatch.setattr(zipfile.ZipFile, "write", explode)
    out = tmp_path / "out.zip"
    with caplog.at_level(logging.ERROR):
        result = ArchiveService().create_zip(project, out)
    assert result["success"] is False and "disk dolu" in result["error"]
    assert not out.exists()                                                # yarım zip bırakılmaz
    assert "Traceback" in caplog.text and "disk dolu" in caplog.text


def test_copy_continues_after_file_error(project, tmp_path, monkeypatch):
    import shutil
    real_copy = shutil.copy2

    def flaky(src, dst, *args, **kwargs):
        if str(src).endswith("app.py"):
            raise PermissionError("kilitli")
        return real_copy(src, dst, *args, **kwargs)

    monkeypatch.setattr("src.services.archive_service.shutil.copy2", flaky)
    result = ArchiveService().copy_project(project, tmp_path / "copy")
    assert result["success"] is True and result["complete"] is False
    assert [Path(p).name for p, _ in result["failed_files"]] == ["app.py"]
    assert (tmp_path / "copy" / "src" / "mod.py").exists()


# ---- yedek -----------------------------------------------------------------------------------

def test_backup_success_and_failed_files(project, tmp_path, monkeypatch):
    service = BackupService(tmp_path / "backups")
    result = service.create_backup(project, "b1")
    assert result["success"] and result["complete"] and result["size"] > 0 and result["error"] is None
    assert "app.py" in names(tmp_path / "backups" / "b1" / "b1.zip")

    real_write = zipfile.ZipFile.write

    def flaky(self, filename, arcname=None, *a, **k):
        if str(filename).endswith("app.py"):
            raise PermissionError("kilitli")
        return real_write(self, filename, arcname, *a, **k)

    monkeypatch.setattr(zipfile.ZipFile, "write", flaky)
    partial = service.create_backup(project, "b2")
    assert partial["success"] and not partial["complete"]
    assert [Path(p).name for p, _ in partial["failed_files"]] == ["app.py"]


def test_backup_fatal_error_removes_partial_zip_and_empty_dir(project, tmp_path, monkeypatch, caplog):
    def explode(self, *args, **kwargs):
        raise RuntimeError("disk dolu")

    monkeypatch.setattr(zipfile.ZipFile, "write", explode)
    service = BackupService(tmp_path / "backups")
    with caplog.at_level(logging.ERROR):
        result = service.create_backup(project, "b3")
    assert result["success"] is False and "disk dolu" in result["error"]
    assert not (tmp_path / "backups" / "b3").exists()
    assert "Traceback" in caplog.text


# ---- profiller: iç içe eşleşme, ortak dışlama, hatalı profil ------------------------------------

@pytest.fixture
def nested(tmp_path):
    root = tmp_path / "nested"
    for rel in ["app.py", "src/tests/a.py", "pkg/test/b.py", "src/test_x.py", "docs/guide.md", "pkg/docs/api.md",
                "README.md", "pkg/README.md", ".env", "backend/.env", "backend/.env.local",
                "LICENSE", "pkg/LICENSE", ".venv/lib/a.py", "myenv/pyvenv.cfg", "myenv/Lib/x.py",
                "rust/Cargo.toml", "rust/target/debug/a.rlib", "rust/src/main.rs", ".next/server/a.js"]:
        write(root / rel, "home = x" if rel.endswith("pyvenv.cfg") else "x")
    return root


def zipped(service, root, tmp_path, profile):
    out = tmp_path / f"{abs(hash(profile))}.zip"
    result = service.create_zip(root, out, profile_name=profile)
    assert result["success"], result["error"]
    return set(names(out))


def test_standard_profile_still_skips_virtualenvs_and_build_dirs(nested, tmp_path):
    included = zipped(ArchiveService(), nested, tmp_path, "Geliştirici (Standart)")
    assert not any(p.startswith((".venv/", "myenv/", "rust/target/", ".next/")) for p in included)   # eskiden .venv/myenv giriyordu
    assert {"src/tests/a.py", "backend/.env", "README.md", "rust/src/main.rs"} <= included              # Standart hiçbir şeyi elemez


def test_clean_profile_removes_nested_tests_but_keeps_nested_docs_and_readme(nested, tmp_path):
    included = zipped(ArchiveService(), nested, tmp_path, "Müşteri Teslimi (Temiz)")
    assert not any("test" in p for p in included)
    assert "docs/guide.md" not in included
    assert {"app.py", "pkg/docs/api.md", "README.md", "pkg/README.md"} <= included
    assert not any(p.split("/")[-1].startswith(".env") for p in included)            # Temiz profil de gizli dosya taşımaz


def test_minimal_profile_never_ships_env_files_at_any_depth(nested, tmp_path):
    included = zipped(ArchiveService(), nested, tmp_path, "Yayınlama / Dağıtım (Minimal)")
    assert not any(p.split("/")[-1].startswith(".env") for p in included)
    assert "README.md" not in included and "LICENSE" not in included          # kök dosyaları elenir
    assert {"pkg/README.md", "pkg/LICENSE", "pkg/docs/api.md", "app.py"} <= included


def test_copy_project_uses_the_same_profile_rules(nested, tmp_path):
    target = tmp_path / "kopya"
    result = ArchiveService().copy_project(nested, target, profile_name="Yayınlama / Dağıtım (Minimal)")
    assert result["success"]
    copied = {p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()}
    assert "backend/.env" not in copied and "src/tests/a.py" not in copied and "app.py" in copied


def test_unknown_profile_is_an_error_not_a_silent_no_filter(nested, tmp_path, caplog):
    out = tmp_path / "o.zip"
    with caplog.at_level(logging.ERROR):
        zip_result = ArchiveService().create_zip(nested, out, profile_name="Müşteri Teslimi (Temız)")   # yazım hatası
        copy_result = ArchiveService().copy_project(nested, tmp_path / "c", profile_name="yok")
    for result in (zip_result, copy_result):
        assert result["success"] is False and "Bilinmeyen arşiv profili" in result["error"]
        assert "Geçerli profiller" in result["error"]
    assert not out.exists() and not (tmp_path / "c").exists()
    assert "Bilinmeyen arşiv profili" in caplog.text


def test_profiles_view_keeps_the_ui_dictionary_shape(tmp_path):
    view = ArchiveService().PROFILES
    assert list(view) == ["Geliştirici (Standart)", "Müşteri Teslimi (Temiz)", "Yayınlama / Dağıtım (Minimal)"]
    for entry in view.values():
        assert set(entry) == {"excludes", "description"} and entry["description"] and isinstance(entry["excludes"], list)


def test_custom_profiles_can_be_injected(nested, tmp_path):
    from src.services.archive_profiles import ArchiveProfile
    service = ArchiveService(profiles={"Özel": ArchiveProfile("Özel", "yalnız logo", ["*.md"])})
    included = zipped(service, nested, tmp_path, "Özel")
    assert "app.py" in included and not any(p.endswith(".md") for p in included)


# ---- iç içe .gitignore ------------------------------------------------------------------------

@pytest.fixture
def nested_ignore(tmp_path):
    root = tmp_path / "ni"
    write(root / ".gitignore", "*.log\n")
    write(root / "app.py", "x")
    write(root / "backend" / ".gitignore", ".env\nuploads/\n!keep.log\n")
    write(root / "backend" / "server.py", "x")
    write(root / "backend" / ".env", "SECRET=1")
    write(root / "backend" / "uploads" / "big.bin", "x")
    write(root / "backend" / "keep.log", "x")
    write(root / "backend" / "other.log", "x")
    write(root / "frontend" / ".env", "SECRET=2")
    return root


def test_nested_gitignore_is_applied_to_archive_and_copy(nested_ignore, tmp_path):
    service = ArchiveService(GitignoreParser(str(nested_ignore)))
    out = tmp_path / "o.zip"
    result = service.create_zip(nested_ignore, out)
    assert result["success"]
    assert names(out) == [".gitignore", "app.py", "backend/.gitignore", "backend/keep.log", "backend/server.py", "frontend/.env"]
    # backend/.env ve uploads/ elendi; backend/keep.log iç içe `!` ile geri geldi; frontend/.env'i backend kuralı etkilemez
    copy = service.copy_project(nested_ignore, tmp_path / "copy")
    copied = sorted(p.relative_to(tmp_path / "copy").as_posix() for p in (tmp_path / "copy").rglob("*") if p.is_file())
    assert copy["success"] and copied == names(out)


def test_ignored_directories_are_pruned_not_walked(nested_ignore, tmp_path, monkeypatch):
    import os
    visited = []
    real_walk = os.walk

    def spy(top, *args, **kwargs):
        for root, dirs, files in real_walk(top, *args, **kwargs):
            visited.append(Path(root).name)
            yield root, dirs, files

    monkeypatch.setattr("src.services.archive_service.os.walk", spy)
    ArchiveService(GitignoreParser(str(nested_ignore))).create_zip(nested_ignore, tmp_path / "o.zip")
    assert "uploads" not in visited


def test_unreadable_nested_gitignore_makes_archive_refuse(nested_ignore, tmp_path, monkeypatch):
    import builtins
    real_open = builtins.open

    def deny(path, *args, **kwargs):
        if str(path).endswith(os.path.join("backend", ".gitignore")):
            raise PermissionError("kilitli")
        return real_open(path, *args, **kwargs)

    parser = GitignoreParser(str(nested_ignore))                       # kök dosya sorunsuz yüklenir
    assert parser.load_error is None
    monkeypatch.setattr(builtins, "open", deny)
    service = ArchiveService(parser)
    out = tmp_path / "o.zip"
    zip_result = service.create_zip(nested_ignore, out)
    monkeypatch.setattr(builtins, "open", real_open)
    assert zip_result["success"] is False and "kilitli" in zip_result["error"]
    assert "Gizli dosyaların" in zip_result["error"] and not out.exists()


@pytest.mark.skipif(__import__("shutil").which("git") is None, reason="git kurulu değil")
def test_archive_keeps_tracked_files_even_when_gitignore_matches_them(tmp_path):
    """Gerçek vaka: `.gitignore` kendi adını içeriyor ve izleniyor; `git add -f` ile eklenenler de depodadır."""
    import subprocess
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    write(repo / ".gitignore", ".gitignore\n*.txt\n")
    for rel in ["app.py", "forced.txt", "notes.txt"]:
        write(repo / rel, "x")
    subprocess.run(["git", "add", "-f", ".gitignore", "forced.txt", "app.py"], cwd=repo, check=True)

    out = tmp_path / "o.zip"
    result = ArchiveService(GitignoreParser(str(repo))).create_zip(repo, out)
    assert result["success"]
    assert names(out) == [".gitignore", "app.py", "forced.txt"]        # notes.txt izlenmiyor + ignore'lu: arşivde yok
