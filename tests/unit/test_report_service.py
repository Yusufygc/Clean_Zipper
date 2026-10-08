from datetime import datetime
from pathlib import Path

from src.models.analysis_models import AnalysisResult, ProjectAnalysis, Severity
from src.services.report_service import ReportService

PAYLOAD = '<img src=x onerror="alert(1)"><script>alert(2)</script>&\'"'


def analysis_with(finding, project_path=Path("proj")):
    analysis = ProjectAnalysis(project_path=project_path, analysis_time=datetime(2026, 10, 8, 12, 0, 0))
    analysis.issues.append(finding)
    return analysis


def hostile_finding():
    return AnalysisResult(
        analyzer_name="t", category="security", severity=Severity.HIGH,
        title=f"Başlık {PAYLOAD}", description=f"Açıklama {PAYLOAD}",
        file_path=Path(f"dir/{PAYLOAD.replace('/', '_')}.py"),
        recommendation=f"Öneri {PAYLOAD}",
    )


def test_untrusted_text_is_escaped_everywhere():
    report = ReportService().generate_report(analysis_with(hostile_finding(), Path(f"C:/x/{PAYLOAD}")))
    assert "<script>alert(2)</script>" not in report
    assert "<img src=x" not in report
    assert 'onerror="alert(1)"' not in report
    assert "&lt;script&gt;alert(2)&lt;/script&gt;" in report


def test_report_declares_restrictive_content_security_policy():
    report = ReportService().generate_report(analysis_with(hostile_finding()))
    assert 'http-equiv="Content-Security-Policy"' in report
    assert "default-src 'none'" in report


def test_turkish_characters_survive_escaping():
    finding = AnalysisResult(
        analyzer_name="t", category="size", severity=Severity.MEDIUM,
        title="Büyük dosya: çalışma_şığ.txt", description="İğdır & Ölçü", recommendation="Gözden geçirin",
    )
    analysis = ProjectAnalysis(project_path=Path("proje"), analysis_time=datetime(2026, 10, 8))
    analysis.warnings.append(finding)
    report = ReportService().generate_report(analysis)
    assert "Büyük dosya: çalışma_şığ.txt" in report
    assert "İğdır &amp; Ölçü" in report


def test_export_writes_utf8_file(tmp_path):
    out = tmp_path / "rapor.html"
    assert ReportService().export_report(analysis_with(hostile_finding()), out) is True
    assert "Sağlık" in out.read_text(encoding="utf-8")


def test_export_failure_returns_false_and_is_logged(tmp_path, caplog):
    missing_dir = tmp_path / "yok" / "rapor.html"
    with caplog.at_level("ERROR"):
        assert ReportService().export_report(analysis_with(hostile_finding()), missing_dir) is False
    assert "Rapor" in caplog.text
