"""SettingsViewModel: kalıcı ayarlar, eşikler, kural kapatma ve ajan görevleri köprüsü."""
import json
from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication

from src.qml_ui.viewmodels.settings_viewmodel import SettingsViewModel
from src.services import app_settings
from src.services.project_service import ProjectService


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def make(qapp):
    service = ProjectService()
    return service, SettingsViewModel(service)


def thresholds(vm):
    return {t["key"]: t for t in vm.thresholds}


def test_defaults(qapp):
    _, vm = make(qapp)
    assert vm.respectGitignore is True and vm.agentBatchSize == 15
    values = thresholds(vm)
    assert len(values) == 9 and values["cyclomatic"]["value"] == 10 and values["parameters"]["default"] == 5
    assert len(vm.analyzersList) == 18 and all(a["enabled"] for a in vm.analyzersList)
    assert vm.disabledRules == [] and vm.lastAgentResult == {}
    first = vm.analyzersList[0]
    assert {"id", "name", "description", "enabled"} <= set(first)


def test_every_threshold_can_be_adjusted_and_is_clamped(qapp):
    _, vm = make(qapp)
    vm.adjustThreshold("cyclomatic", 5)
    vm.adjustThreshold("function_lines", -100)
    vm.adjustThreshold("nesting", -50)
    vm.adjustThreshold("yok", 3)                                 # bilinmeyen anahtar yok sayılır
    values = thresholds(vm)
    assert values["cyclomatic"]["value"] == 15
    assert values["function_lines"]["value"] == 5 and values["nesting"]["value"] == 1       # alt sınır
    assert set(values) == set(app_settings.THRESHOLD_LIMITS)


def test_apply_reaches_the_doctor_with_all_nine_thresholds_and_gitignore(qapp):
    service, vm = make(qapp)
    vm.setRespectGitignore(False)
    vm.adjustThreshold("parameters", 3)
    vm.adjustThreshold("module_imports", 10)
    vm.toggleAnalyzer("DeadCodeAnalyzer", False)
    messages = []
    vm.settingsApplied.connect(messages.append)
    vm.applySettings()
    doctor = service.doctor
    assert doctor.respect_gitignore is False
    assert doctor.thresholds.parameters == 8 and doctor.thresholds.module_imports == 35
    assert "DeadCodeAnalyzer" not in [type(a).__name__ for a in doctor._analyzers]
    assert messages and "kaydedildi" in messages[0]


def test_settings_are_persisted_and_restored_on_the_next_start(qapp):
    _, vm = make(qapp)
    vm.adjustThreshold("cognitive", 5)
    vm.toggleAnalyzer("CloneAnalyzer", False)
    vm.disableRule("magic-numbers")
    vm.adjustAgentBatchSize(10)
    saved = json.loads(app_settings.settings_path().read_text(encoding="utf-8"))
    assert saved["thresholds"]["cognitive"] == 20 and saved["disabled_rules"] == ["magic-numbers"]

    service, again = make(qapp)                                  # uygulama yeniden açılıyor
    assert thresholds(again)["cognitive"]["value"] == 20
    assert again.agentBatchSize == 15                            # batch yalnızca uygulayınca kaydedilir: bu testte disableRule kaydetti
    assert [a["enabled"] for a in again.analyzersList if a["id"] == "CloneAnalyzer"] == [False]
    assert service.doctor.thresholds.cognitive == 20             # kayıtlı ayar açılışta doctor'a da uygulandı
    assert "CloneAnalyzer" not in [type(a).__name__ for a in service.doctor._analyzers]
    assert service.doctor.disabled_rules == frozenset({"magic-numbers"})


def test_analyzer_enable_disable_all(qapp):
    _, vm = make(qapp)
    vm.toggleAnalyzer("CloneAnalyzer", False)
    assert {a["id"]: a["enabled"] for a in vm.analyzersList}["CloneAnalyzer"] is False
    vm.disableAllAnalyzers()
    assert not any(a["enabled"] for a in vm.analyzersList)
    vm.enableAllAnalyzers()
    assert all(a["enabled"] for a in vm.analyzersList)


def test_disable_and_enable_rule_apply_immediately_and_signal_a_refresh(qapp):
    service, vm = make(qapp)
    refreshes = []
    vm.rulesChanged.connect(lambda: refreshes.append(True))
    vm.disableRule("unused-import")
    vm.disableRule("unused-import")                              # ikinci kez etkisiz
    assert service.doctor.disabled_rules == frozenset({"unused-import"}) and len(refreshes) == 1
    assert vm.disabledRules == [{"id": "unused-import", "title": "Kullanılmayan import"}]
    vm.enableRule("unused-import")
    assert service.doctor.disabled_rules == frozenset() and len(refreshes) == 2 and vm.disabledRules == []


def test_a_disabled_rule_really_disappears_from_the_analysis(qapp, tmp_path):
    (tmp_path / "a.py").write_text("import os\nx = 1\n", encoding="utf-8")
    service, vm = make(qapp)
    service.set_project(tmp_path)
    rules = lambda: {f.metadata.get("rule") for f in service.doctor.diagnose(tmp_path).all_findings}
    assert "unused-import" in rules()
    vm.disableRule("unused-import")
    assert "unused-import" not in rules()


def test_reset_restores_everything_and_persists_defaults(qapp):
    service, vm = make(qapp)
    vm.adjustThreshold("cyclomatic", 9)
    vm.disableRule("magic-numbers")
    vm.setRespectGitignore(False)
    vm.resetToDefaults()
    assert thresholds(vm)["cyclomatic"]["value"] == 10 and vm.respectGitignore is True and vm.disabledRules == []
    assert service.doctor.thresholds.cyclomatic == 10 and service.doctor.respect_gitignore is True
    assert json.loads(app_settings.settings_path().read_text(encoding="utf-8"))["disabled_rules"] == []


def test_default_agent_dir_is_outside_the_project_and_follows_the_project(qapp, tmp_path):
    service, vm = make(qapp)
    project = tmp_path / "benim_proje"
    project.mkdir()
    service.set_project(project)
    changes = []
    vm.settingsChanged.connect(lambda: changes.append(True))
    vm.onProjectChanged()
    assert changes and vm.agentOutputDirIsCustom is False
    assert Path(vm.agentOutputDir).name == "benim_proje" and project.resolve() not in Path(vm.agentOutputDir).parents
    vm.setAgentOutputDir("file:///" + str(tmp_path / "ozel").replace("\\", "/"))
    assert vm.agentOutputDirIsCustom is True and Path(vm.agentOutputDir) == tmp_path / "ozel"
    vm.setAgentOutputDir("")
    assert vm.agentOutputDirIsCustom is False


def test_batch_size_is_bounded(qapp):
    _, vm = make(qapp)
    vm.adjustAgentBatchSize(-100)
    assert vm.agentBatchSize == 1
    vm.adjustAgentBatchSize(10_000)
    assert vm.agentBatchSize == app_settings.MAX_BATCH_SIZE


def test_agent_tasks_require_a_project(qapp):
    _, vm = make(qapp)
    errors = []
    vm.taskExportError.connect(errors.append)
    vm.exportAgentTasks()
    vm.verifyAgentTasks()
    assert len(errors) == 2


def test_export_then_verify_reports_real_counts(qapp, tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    (project / "a.py").write_text("import os\nimport sys\nx = 1\n", encoding="utf-8")
    service, vm = make(qapp)
    service.set_project(project)
    vm.setAgentOutputDir(str(tmp_path / "gorevler"))
    results = []
    vm.taskExportFinished.connect(results.append)

    vm.exportAgentTasks()
    export = results[0]
    assert export["kind"] == "export" and export["totalItems"] == 2 and export["totalTasks"] == 1
    assert (tmp_path / "gorevler" / "tasks.json").is_file() and export["waves"][0]["wave"] == 3

    (project / "a.py").write_text("x = 1\n", encoding="utf-8")   # iki import silindi
    vm.verifyAgentTasks()
    verify = results[1]
    assert verify["kind"] == "verify" and verify["closed"] == 2 and verify["open"] == 0 and verify["total"] == 2
    assert verify["newCount"] == 0 and vm.lastAgentResult == verify


def test_verify_without_exported_tasks_reports_an_error(qapp, tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    (project / "a.py").write_text("x = 1\n", encoding="utf-8")
    service, vm = make(qapp)
    service.set_project(project)
    vm.setAgentOutputDir(str(tmp_path / "yok"))
    errors = []
    vm.taskExportError.connect(errors.append)
    vm.verifyAgentTasks()
    assert errors and "Doğrulama yapılamadı" in errors[0]


def test_max_backups_is_applied_to_backup_service_and_saved_at_once(qapp):
    service, vm = make(qapp)
    assert vm.maxBackups == 5 and service.backup_service.max_backups == 5
    vm.adjustMaxBackups(-10)
    assert vm.maxBackups == 0 and service.backup_service.max_backups == 0          # 0 = sınırsız, altı yok
    vm.adjustMaxBackups(3)
    saved = json.loads(app_settings.settings_path().read_text(encoding="utf-8"))
    assert saved["max_backups"] == 3
    service2, vm2 = make(qapp)
    assert vm2.maxBackups == 3 and service2.backup_service.max_backups == 3
