"""CleanupViewModel birim testi."""
import sys
from pathlib import Path
import pytest

from PySide6.QtWidgets import QApplication
from src.services.project_service import ProjectService
from src.qml_ui.viewmodels.cleanup_viewmodel import CleanupViewModel


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_cleanup_viewmodel_initial_state(qapp):
    service = ProjectService()
    vm = CleanupViewModel(service)

    assert vm.isProcessing is False
    assert vm.categoryPythonCache is True
    assert vm.categoryTempFiles is True
    assert vm.categoryLogs is False
    assert vm.categoryBackups is False
    assert vm.previewCount == 0


def test_cleanup_viewmodel_category_toggling(qapp):
    service = ProjectService()
    vm = CleanupViewModel(service)

    vm.setCategory("logs", True)
    assert vm.categoryLogs is True
    vm.setCategory("logs", False)
    assert vm.categoryLogs is False


def test_cleanup_viewmodel_preview(qapp, tmp_path):
    project_dir = tmp_path / "proj_clean"
    project_dir.mkdir()
    pycache = project_dir / "__pycache__"
    pycache.mkdir()
    (pycache / "module.cpython-310.pyc").write_text("bytecode", encoding="utf-8")
    (project_dir / "temp.tmp").write_text("temporary", encoding="utf-8")

    service = ProjectService()
    service.set_project(project_dir)
    vm = CleanupViewModel(service)

    vm.startPreview()
    assert vm._worker is not None
    vm._worker.wait(10000)
    qapp.processEvents()

    assert vm.isProcessing is False
    assert vm.previewCount >= 2
    assert len(vm.previewFiles) >= 2


def test_cleanup_viewmodel_execution(qapp, tmp_path, monkeypatch):
    project_dir = tmp_path / "proj_exec"
    project_dir.mkdir()
    (project_dir / "trash.tmp").write_text("trash me", encoding="utf-8")

    trashed_paths = []
    def fake_trash(path):
        trashed_paths.append(path)

    service = ProjectService()
    service.set_project(project_dir)
    service.cleanup_service._trash = fake_trash
    vm = CleanupViewModel(service)

    vm.startCleanup()
    assert vm._worker is not None
    vm._worker.wait(10000)
    qapp.processEvents()

    assert vm.isProcessing is False
    assert vm.lastResult.get("success") is True
    assert vm.lastResult.get("cleanedFiles") >= 1
    assert len(trashed_paths) >= 1
