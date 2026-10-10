"""ScanViewModel ve Dashboard veri köprüsü birim testi."""
import sys
import pytest

from PySide6.QtWidgets import QApplication
from src.services.project_service import ProjectService
from src.qml_ui.viewmodels.scan_viewmodel import ScanViewModel


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_scan_viewmodel_initial_state(qapp):
    service = ProjectService()
    vm = ScanViewModel(service)

    assert vm.isScanning is False
    assert vm.healthScore == 0
    assert vm.healthStatus == "—"
    assert vm.totalFiles == 0
    assert vm.issuesCount == 0
    assert vm.failedAnalyzers == []
    assert vm.topRecommendations == []


def test_scan_viewmodel_runs_quick_scan(qapp, tmp_path):
    # Geçici test projesi oluştur
    (tmp_path / "main.py").write_text("print('hello world')\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("*.tmp\n", encoding="utf-8")

    service = ProjectService()
    service.set_project(tmp_path)
    vm = ScanViewModel(service)

    # Worker başlat ve bitmesini bekle
    vm.startQuickScan()
    assert vm._worker is not None
    vm._worker.wait(10000)
    qapp.processEvents()

    assert vm.isScanning is False
    assert vm.totalFiles >= 1
    assert vm.healthScore > 0
    assert vm.healthStatus in ("A+", "A", "B", "C", "D", "E", "F")
    assert isinstance(vm.categoryScores, dict)
    assert len(vm.categoryScores) > 0


def test_scan_viewmodel_report_exports(qapp, tmp_path):
    (tmp_path / "sample.py").write_text("x = 1\n", encoding="utf-8")
    service = ProjectService()
    service.set_project(tmp_path)
    vm = ScanViewModel(service)

    html_out = tmp_path / "report.html"
    success_html = vm.exportHtmlReport(str(html_out))
    assert success_html is True
    assert html_out.exists()
    assert html_out.stat().st_size > 0

    md_out = tmp_path / "audit.md"
    success_md = vm.exportAuditReport(str(md_out))
    assert success_md is True
    assert md_out.exists()
    assert md_out.stat().st_size > 0
