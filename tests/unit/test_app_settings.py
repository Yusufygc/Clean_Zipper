import json
from pathlib import Path

import pytest

from src.core.thresholds import QualityThresholds
from src.services import app_settings
from src.services.app_settings import (AppSettings, THRESHOLD_LIMITS, default_thresholds, load_settings, save_settings,
                                       settings_from_dict)


def test_defaults_come_from_quality_thresholds_single_source():
    defaults = default_thresholds()
    assert set(defaults) == set(THRESHOLD_LIMITS) and len(defaults) == 9
    assert defaults["cyclomatic"] == QualityThresholds().cyclomatic == 10
    assert AppSettings().quality_thresholds() == QualityThresholds()


def test_save_and_load_round_trip(tmp_path):
    path = tmp_path / "s.json"
    settings = AppSettings(respect_gitignore=False, disabled_analyzers=["CloneAnalyzer"], disabled_rules=["magic-numbers"],
                           agent_batch_size=30, agent_output_dir="D:/cikti")
    settings.set_threshold("cyclomatic", 18)
    settings.set_threshold("parameters", 7)
    assert save_settings(settings, path) is True
    loaded = load_settings(path)
    assert loaded == settings and loaded.quality_thresholds().parameters == 7
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == 1


def test_missing_or_corrupt_file_gives_defaults(tmp_path, caplog):
    assert load_settings(tmp_path / "yok.json") == AppSettings()
    broken = tmp_path / "b.json"
    broken.write_text("{ bozuk", encoding="utf-8")
    assert load_settings(broken) == AppSettings()
    assert "okunamadı" in caplog.text


@pytest.mark.parametrize("raw", [[], "metin", 5, None])
def test_non_object_json_gives_defaults(raw):
    assert settings_from_dict(raw) == AppSettings()


def test_invalid_values_are_cleaned_or_clamped():
    data = {"respect_gitignore": "evet", "disabled_analyzers": ["A", "A", 5, "", None, "B"], "disabled_rules": "x",
            "thresholds": {"cyclomatic": -4, "cognitive": "yüksek", "bilinmeyen": 9, "file_lines": 10, "nesting": True},
            "agent_batch_size": 9999, "agent_output_dir": 7, "ekstra": 1}
    cleaned = settings_from_dict(data)
    assert cleaned.respect_gitignore is True                     # yalnızca açıkça False olan kapatır
    assert cleaned.disabled_analyzers == ["A", "B"] and cleaned.disabled_rules == []
    assert cleaned.thresholds["cyclomatic"] == 1 and cleaned.thresholds["cognitive"] == 15
    assert cleaned.thresholds["file_lines"] == 50 and cleaned.thresholds["nesting"] == 4 and "bilinmeyen" not in cleaned.thresholds
    assert cleaned.agent_batch_size == 200 and cleaned.agent_output_dir == ""


def test_set_threshold_enforces_the_minimum_and_rejects_unknown_names():
    settings = AppSettings()
    assert settings.set_threshold("function_lines", 1) == 5
    assert settings.set_threshold("class_methods", 30) == 30
    with pytest.raises(KeyError):
        settings.set_threshold("yok", 1)


def test_failed_write_returns_false_and_leaves_no_temp_file(tmp_path, monkeypatch, caplog):
    path = tmp_path / "s.json"

    def boom(*args, **kwargs):
        raise OSError("disk dolu")

    monkeypatch.setattr(app_settings.os, "replace", boom)
    assert save_settings(AppSettings(), path) is False
    assert not path.exists() and not list(tmp_path.glob("*.tmp")) and "kaydedilemedi" in caplog.text


def test_default_agent_dir_is_outside_the_project_and_sanitised(monkeypatch):
    monkeypatch.undo()                                           # conftest'in test klasörü yönlendirmesini kaldır
    from src.services.app_settings import default_agent_dir
    project = Path("C:/projeler/Benim Proje:1")
    target = default_agent_dir(project)
    assert target.parent.name == "agent-tasks" and target.name == "Benim_Proje_1"
    assert project not in target.parents
    assert default_agent_dir(None).name == "proje"


def test_max_backups_is_clamped_and_defaults_on_bad_values():
    assert AppSettings().max_backups == 5
    assert settings_from_dict({"max_backups": 999}).max_backups == app_settings.MAX_KEPT_BACKUPS
    assert settings_from_dict({"max_backups": -1}).max_backups == 0
    assert settings_from_dict({"max_backups": "3"}).max_backups == 5
