"""ArchiveViewModel birim testi."""
import sys
import pytest

from PySide6.QtWidgets import QApplication
from src.services.project_service import ProjectService
from src.qml_ui.viewmodels.archive_viewmodel import ArchiveViewModel


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_archive_viewmodel_initial_state(qapp):
    service = ProjectService()
    vm = ArchiveViewModel(service)

    assert vm.isProcessing is False
    assert len(vm.profiles) >= 3
    assert vm.selectedProfile != ""


def test_archive_viewmodel_creates_zip(qapp, tmp_path):
    project_dir = tmp_path / "proj"
    project_dir.mkdir()
    (project_dir / "app.py").write_text("print('test')\n", encoding="utf-8")
    (project_dir / "temp.log").write_text("log data\n", encoding="utf-8")

    service = ProjectService()
    service.set_project(project_dir)
    vm = ArchiveViewModel(service)

    output_zip = tmp_path / "output.zip"
    vm.selectProfile(vm.profiles[0]["name"])
    vm.startZipArchive(str(output_zip))

    assert vm._worker is not None
    vm._worker.wait(10000)
    qapp.processEvents()

    assert vm.isProcessing is False
    assert output_zip.exists()
    assert vm.lastResult.get("success") is True
    assert vm.lastResult.get("addedFiles") >= 1


def test_archive_viewmodel_creates_clean_copy(qapp, tmp_path):
    project_dir = tmp_path / "proj_copy"
    project_dir.mkdir()
    (project_dir / "index.js").write_text("console.log('hi');\n", encoding="utf-8")

    service = ProjectService()
    service.set_project(project_dir)
    vm = ArchiveViewModel(service)

    output_dir = tmp_path / "exported_copy"
    vm.startCleanCopy(str(output_dir))

    assert vm._worker is not None
    vm._worker.wait(10000)
    qapp.processEvents()

    assert vm.isProcessing is False
    assert output_dir.exists()
    assert (output_dir / "index.js").exists()
    assert vm.lastResult.get("success") is True


def test_archive_viewmodel_creates_backup(qapp, tmp_path):
    project_dir = tmp_path / "proj_backup"
    project_dir.mkdir()
    (project_dir / "data.py").write_text("DATA = 1\n", encoding="utf-8")

    service = ProjectService()
    service.set_project(project_dir)
    vm = ArchiveViewModel(service)

    vm.startBackup("test_backup_qml")

    assert vm._worker is not None
    vm._worker.wait(10000)
    qapp.processEvents()

    assert vm.isProcessing is False
    assert vm.lastResult.get("success") is True
    assert vm.lastResult.get("mode") == "backup"
