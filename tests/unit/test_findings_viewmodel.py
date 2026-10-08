"""FindingsViewModel ve FindingsListModel birim testi."""
import sys
from pathlib import Path
import pytest

from PySide6.QtWidgets import QApplication
from src.services.project_service import ProjectService
from src.models.analysis_models import AnalysisResult, Severity
from src.qml_ui.viewmodels.findings_viewmodel import FindingsViewModel, is_sensitive_finding, get_finding_effort


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_findings_viewmodel_initial_state(qapp):
    service = ProjectService()
    vm = FindingsViewModel(service)

    assert vm.isDiagnosing is False
    assert vm.totalCount == 0
    assert vm.criticalCount == 0
    assert vm.selectedSeverity == "ALL"
    assert vm.model.rowCount() == 0


def test_sensitive_finding_masking():
    # Sır sızıntısı olan bulgu
    secret_res = AnalysisResult(
        analyzer_name="SecurityLeakAnalyzer",
        category="security",
        severity=Severity.HIGH,
        title="Hardcoded API Key",
        description="API key bulundu: AKIAIOSFODNN7EXAMPLE",
        file_path=Path("config.py"),
        metadata={"rule": "hardcoded-secret", "line": 15}
    )
    assert is_sensitive_finding(secret_res) is True

    # .env dosyası
    env_res = AnalysisResult(
        analyzer_name="SecurityLeakAnalyzer",
        category="security",
        severity=Severity.CRITICAL,
        title="Environment File",
        description="Gizli dosya",
        file_path=Path(".env.production"),
        metadata={"rule": "env-file"}
    )
    assert is_sensitive_finding(env_res) is True

    # Standart kod kalitesi bulgusu
    clean_res = AnalysisResult(
        analyzer_name="ComplexityAnalyzer",
        category="complexity",
        severity=Severity.MEDIUM,
        title="Karmaşık fonksiyon",
        description="Siklomatik karmaşıklık yüksek",
        file_path=Path("utils.py"),
        metadata={"rule": "function-metrics", "line": 42}
    )
    assert is_sensitive_finding(clean_res) is False


def test_findings_model_filtering(qapp):
    service = ProjectService()
    vm = FindingsViewModel(service)

    f1 = AnalysisResult(
        analyzer_name="A1", category="security", severity=Severity.CRITICAL,
        title="Kritik Güvenlik Açığı", description="Açıklama 1",
        file_path=Path("sec.py"), metadata={"rule": "provider-secret"}
    )
    f2 = AnalysisResult(
        analyzer_name="A2", category="complexity", severity=Severity.MEDIUM,
        title="Uzun Fonksiyon", description="Açıklama 2",
        file_path=Path("calc.py"), metadata={"rule": "function-metrics"}
    )
    f3 = AnalysisResult(
        analyzer_name="A3", category="hygiene", severity=Severity.LOW,
        title="Gereksiz Yorum", description="Açıklama 3",
        file_path=Path("style.py"), metadata={"rule": "magic-numbers"}
    )

    vm._populate_findings([f1, f2, f3])
    assert vm.totalCount == 3
    assert vm.criticalCount == 1
    assert vm.mediumCount == 1
    assert vm.lowCount == 1
    assert vm.model.rowCount() == 3

    # Şiddet filtresi
    vm.setSeverityFilter("CRITICAL")
    assert vm.model.rowCount() == 1
    assert vm.model.data(vm.model.index(0, 0), vm.model.TitleRole) == "Kritik Güvenlik Açığı"

    # Tümüne dön
    vm.setSeverityFilter("ALL")
    assert vm.model.rowCount() == 3

    # Arama filtresi
    vm.setSearchQuery("calc")
    assert vm.model.rowCount() == 1
    assert vm.model.data(vm.model.index(0, 0), vm.model.FileNameRole) == "calc.py"

    vm.setSearchQuery("")
    assert vm.model.rowCount() == 3
