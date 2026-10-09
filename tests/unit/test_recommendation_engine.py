from datetime import datetime
from pathlib import Path

from src.doctors.recommendation_engine import RecommendationEngine
from src.models.analysis_models import AnalysisResult, ProjectAnalysis, Severity


def finding(rule, severity, name="a.py", recommendation="Düzeltin."):
    return AnalysisResult(analyzer_name="t", category="security", severity=severity, title=f"{rule} başlık",
                          description="açıklama", file_path=Path("/p") / name, recommendation=recommendation,
                          metadata={"rule": rule})


def analysis(*findings):
    result = ProjectAnalysis(project_path=Path("/p"), analysis_time=datetime(2026, 10, 10))
    result.issues.extend(findings)          # öneri motoru şiddete göre değil, tüm bulgulara bakar
    return result


def test_critical_findings_come_first_then_by_count_and_low_findings_are_left_out():
    recs = RecommendationEngine().get_top_recommendations(analysis(
        finding("bare-except", Severity.HIGH, "x.py"),
        finding("unused-import", Severity.LOW),
        finding("file-length", Severity.MEDIUM, "big.py"),
        finding("bare-except", Severity.HIGH, "y.py"),
        finding("provider-secret", Severity.CRITICAL, "cfg.py", "Anahtarı yenileyin."),
        finding("import-cycle", Severity.HIGH, "m.py"),
    ))
    assert [(title, prio) for title, _, prio in recs] == [
        ("Bilinen sağlayıcı anahtarı", "KRİTİK"), ("Çıplak except", "YÜKSEK"),
        ("Döngüsel bağımlılık", "YÜKSEK"), ("Aşırı uzun dosyalar", "ORTA")]
    assert recs[0][1] == "1 bulgu (cfg.py). Anahtarı yenileyin."
    assert recs[1][1].startswith("2 bulgu (x.py, y.py).")


def test_examples_are_capped_and_list_is_limited_to_count():
    findings = [finding("bare-except", Severity.HIGH, f"f{i}.py") for i in range(4)]
    findings += [finding(f"rule-{i}", Severity.MEDIUM) for i in range(6)]
    recs = RecommendationEngine().get_top_recommendations(analysis(*findings))
    assert len(recs) == 5 and recs[0][1].startswith("4 bulgu (f0.py, f1.py …).")


def test_clean_project_has_no_recommendations():
    assert RecommendationEngine().get_top_recommendations(analysis(finding("unused-import", Severity.LOW))) == []
