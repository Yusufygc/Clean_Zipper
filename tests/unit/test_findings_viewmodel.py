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

    vm._populate_findings([f1, f2, f3], Path.cwd())
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


def make_finding(tmp_path, **metadata):
    source = tmp_path / "pkg" / "mod.py"
    source.parent.mkdir(exist_ok=True)
    source.write_text("a = 1\nb = 2\nc = 3\nd = 4\n", encoding="utf-8")
    return source, AnalysisResult("A", "complexity", Severity.MEDIUM, "Başlık", "Açıklama", file_path=source,
                                  recommendation="Öneri", metadata=metadata)


def test_line_comes_from_any_location_metadata_and_relative_path_is_provided(qapp, tmp_path):
    vm = FindingsViewModel(ProjectService())
    _, by_start = make_finding(tmp_path, rule="function-metrics", start_line=3)
    _, by_lines = make_finding(tmp_path, rule="magic-numbers", lines=[2, 4])
    _, plain = make_finding(tmp_path, rule="x", line=1)
    vm._populate_findings([by_start, by_lines, plain], tmp_path)
    model = vm.model
    lines = [model.data(model.index(row, 0), model.LineRole) for row in range(3)]
    assert lines == [3, 2, 1]                                         # yalnızca `line` değil, start_line ve lines[0] da
    assert model.data(model.index(0, 0), model.RelPathRole) == "pkg/mod.py"


def test_rule_is_shown_with_a_turkish_label_and_unknown_rules_fall_back_to_the_id(qapp, tmp_path):
    vm = FindingsViewModel(ProjectService())
    _, known = make_finding(tmp_path, rule="class-size", line=1)
    _, unknown = make_finding(tmp_path, rule="bilinmeyen-kural", line=1)
    vm._populate_findings([known, unknown], tmp_path)
    model = vm.model
    labels = [model.data(model.index(row, 0), model.RuleLabelRole) for row in range(2)]
    assert labels == ["Aşırı büyük sınıflar", "bilinmeyen-kural"]


def test_secret_findings_hide_the_line_and_never_return_code(qapp, tmp_path):
    vm = FindingsViewModel(ProjectService())
    source, secret = make_finding(tmp_path, rule="hardcoded-secret", line=2)
    vm._populate_findings([secret], tmp_path)
    assert vm.model.data(vm.model.index(0, 0), vm.model.LineRole) == 0
    assert vm.evidenceFor(str(source), 2, True) == ""                 # sır bayrağı: kaynak satırı asla dönmez


def test_evidence_is_read_lazily_and_limited(qapp, tmp_path):
    vm = FindingsViewModel(ProjectService())
    source, _ = make_finding(tmp_path, rule="x")
    assert vm.evidenceFor(str(source), 2, False) == "2: b = 2\n3: c = 3\n4: d = 4"
    assert vm.evidenceFor(str(source), 0, False) == "" and vm.evidenceFor("", 1, False) == ""
    assert vm.evidenceFor("goreli/yol.py", 1, False) == "" and vm.evidenceFor(str(tmp_path / "yok.py"), 1, False) == ""


def test_category_list_counts_and_filter(qapp, tmp_path):
    vm = FindingsViewModel(ProjectService())
    findings = [AnalysisResult("A", cat, Severity.LOW, f"B{i}", "x", file_path=tmp_path / f"{i}.py", metadata={"rule": "r"})
                for i, cat in enumerate(["security", "security", "security", "complexity", "deadcode", "deadcode"])]
    vm._populate_findings(findings, tmp_path)
    assert [(c["key"], c["count"]) for c in vm.categories] == [("security", 3), ("deadcode", 2), ("complexity", 1)]
    assert vm.categories[0]["name"] == "Güvenlik"
    vm.setCategoryFilter("deadcode")
    assert vm.selectedCategory == "deadcode" and vm.model.rowCount() == 2
    vm.setSeverityFilter("HIGH")                                      # süzgeçler birlikte çalışır
    assert vm.model.rowCount() == 0
    vm.setSeverityFilter("ALL")
    vm.setCategoryFilter("ALL")
    assert vm.model.rowCount() == 6
