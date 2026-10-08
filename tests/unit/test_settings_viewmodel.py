"""SettingsViewModel için birim testleri."""
from pathlib import Path
import pytest
from PySide6.QtWidgets import QApplication

from src.services.project_service import ProjectService
from src.qml_ui.viewmodels.settings_viewmodel import SettingsViewModel


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_settings_viewmodel_defaults(qapp):
    service = ProjectService()
    vm = SettingsViewModel(service)

    assert vm.respectGitignore is True
    assert vm.cyclomatic == 10
    assert vm.cognitive == 15
    assert vm.functionLines == 50
    assert vm.classLines == 300
    assert vm.fileLines == 500
    assert vm.agentBatchSize == 15

    analyzers = vm.analyzersList
    assert len(analyzers) == 18
    assert all(a["enabled"] for a in analyzers)
    # Türkçeleştirilmiş meta verileri doğrula
    first = analyzers[0]
    assert "name" in first
    assert "description" in first
    assert "id" in first


def test_settings_viewmodel_setters_and_clamping(qapp):
    service = ProjectService()
    vm = SettingsViewModel(service)

    signal_received = []
    vm.settingsChanged.connect(lambda: signal_received.append(True))

    vm.setRespectGitignore(False)
    assert vm.respectGitignore is False

    vm.setCyclomatic(25)
    assert vm.cyclomatic == 25
    vm.setCyclomatic(-5)
    assert vm.cyclomatic == 1  # max(val, 1)

    vm.setCognitive(30)
    assert vm.cognitive == 30
    vm.setCognitive(0)
    assert vm.cognitive == 1

    vm.setFunctionLines(120)
    assert vm.functionLines == 120
    vm.setFunctionLines(1)
    assert vm.functionLines == 5

    vm.setClassLines(500)
    assert vm.classLines == 500
    vm.setClassLines(5)
    assert vm.classLines == 20

    vm.setFileLines(1200)
    assert vm.fileLines == 1200
    vm.setFileLines(10)
    assert vm.fileLines == 50

    vm.setAgentBatchSize(30)
    assert vm.agentBatchSize == 30
    vm.setAgentBatchSize(0)
    assert vm.agentBatchSize == 1

    assert len(signal_received) >= 8


def test_settings_analyzer_toggles(qapp):
    service = ProjectService()
    vm = SettingsViewModel(service)

    # CloneAnalyzer kapat
    vm.toggleAnalyzer("CloneAnalyzer", False)
    analyzers = {a["id"]: a["enabled"] for a in vm.analyzersList}
    assert analyzers["CloneAnalyzer"] is False
    assert analyzers["ArchitectureAnalyzer"] is True

    # Tümünü kapat
    vm.disableAllAnalyzers()
    analyzers = {a["id"]: a["enabled"] for a in vm.analyzersList}
    assert all(not val for val in analyzers.values())

    # Tümünü aç
    vm.enableAllAnalyzers()
    analyzers = {a["id"]: a["enabled"] for a in vm.analyzersList}
    assert all(val for val in analyzers.values())


def test_settings_apply_and_reset(qapp):
    service = ProjectService()
    vm = SettingsViewModel(service)

    vm.setCyclomatic(18)
    vm.setRespectGitignore(False)
    vm.toggleAnalyzer("DeadCodeAnalyzer", False)
    vm.applySettings()

    doctor = service.doctor
    assert doctor.respect_gitignore is False
    assert doctor.thresholds.cyclomatic == 18
    # DeadCodeAnalyzer oluşturulmamış olmalı
    analyzer_names = [type(a).__name__ for a in doctor._analyzers]
    assert "DeadCodeAnalyzer" not in analyzer_names
    assert "ArchitectureAnalyzer" in analyzer_names

    # Varsayılanlara dön
    vm.resetToDefaults()
    assert vm.cyclomatic == 10
    assert vm.respectGitignore is True
    assert "DeadCodeAnalyzer" in [type(a).__name__ for a in service.doctor._analyzers]


def test_agent_task_export_and_verify(qapp, tmp_path):
    service = ProjectService()
    vm = SettingsViewModel(service)

    # 1. Proje seçilmeden hata testi
    errors = []
    vm.taskExportError.connect(lambda err: errors.append(err))
    vm.exportAgentTasks(str(tmp_path))
    assert len(errors) == 1

    # 2. Proje seçilip dışa aktarım testi
    project_dir = tmp_path / "mock_project"
    project_dir.mkdir()
    py_file = project_dir / "app.py"
    py_file.write_text("x = 1\n", encoding="utf-8")

    service.set_project(project_dir)
    export_dir = tmp_path / "tasks_output"

    results = []
    vm.taskExportFinished.connect(lambda res: results.append(res))
    vm.exportAgentTasks(str(export_dir))

    assert len(results) == 1
    assert results[0]["success"] is True
    assert (export_dir / "tasks.json").exists()
    assert (export_dir / "README.md").exists()

    # 3. Doğrulama testi
    vm.verifyAgentTasks(str(export_dir))
    assert len(results) == 2
    assert results[1]["verified"] is True
