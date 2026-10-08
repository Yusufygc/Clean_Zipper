"""QML Arayüzünün Temel Yüklenme ve Bileşen Duman Testi (Smoke Test)."""
import sys
from pathlib import Path
import pytest

from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QUrl
from src.qml_ui.viewmodels.app_viewmodel import AppViewModel
from src.qml_ui.viewmodels.scan_viewmodel import ScanViewModel
from src.qml_ui.viewmodels.findings_viewmodel import FindingsViewModel
from src.qml_ui.viewmodels.archive_viewmodel import ArchiveViewModel
from src.qml_ui.viewmodels.cleanup_viewmodel import CleanupViewModel


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_qml_shell_loads_cleanly(qapp):
    engine = QQmlApplicationEngine()
    warnings = []
    engine.warnings.connect(lambda ws: warnings.extend([w.toString() for w in ws]))

    qml_dir = Path(__file__).resolve().parents[2] / "src" / "qml_ui" / "qml"
    engine.addImportPath(str(qml_dir))
    engine.addImportPath(str(qml_dir / "singletons"))
    engine.addImportPath(str(qml_dir / "components"))
    engine.addImportPath(str(qml_dir / "views"))

    app_vm = AppViewModel()
    scan_vm = ScanViewModel(app_vm.service)
    findings_vm = FindingsViewModel(app_vm.service)
    archive_vm = ArchiveViewModel(app_vm.service)
    cleanup_vm = CleanupViewModel(app_vm.service)
    engine.rootContext().setContextProperty("appVM", app_vm)
    engine.rootContext().setContextProperty("scanVM", scan_vm)
    engine.rootContext().setContextProperty("findingsVM", findings_vm)
    engine.rootContext().setContextProperty("archiveVM", archive_vm)
    engine.rootContext().setContextProperty("cleanupVM", cleanup_vm)

    main_qml = qml_dir / "MainView.qml"
    engine.load(QUrl.fromLocalFile(str(main_qml)))

    assert len(engine.rootObjects()) == 1, f"MainView yüklenemedi! Uyarılar: {warnings}"
    root = engine.rootObjects()[0]
    assert root is not None

    # Tab değişimi testi
    assert root.property("currentTab") == 0
    root.setProperty("currentTab", 1)
    assert root.property("currentTab") == 1
    root.setProperty("currentTab", 0)

    # Proje yolu testi
    test_dir = Path(__file__).resolve().parents[2]
    success = app_vm.setProjectPath(str(test_dir))
    assert success is True
    assert app_vm.hasProject is True
    assert app_vm.projectName == test_dir.name
