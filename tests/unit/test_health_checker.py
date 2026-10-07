import pytest

from src.doctors.health_checker import HealthChecker
from src.models.analysis_models import AnalysisResult, HealthStatus, ProjectAnalysis, Severity
from datetime import datetime
from pathlib import Path


def finding(category, severity, **metadata):
    return AnalysisResult(
        analyzer_name="t", category=category, severity=severity,
        title="t", description="d", metadata=metadata,
    )


def scored(findings, ran):
    checker = HealthChecker()
    analysis = ProjectAnalysis(project_path=Path("."), analysis_time=datetime.now())
    analysis.category_scores = checker.calculate_category_scores(findings, ran)
    return checker.calculate_score(analysis), analysis.category_scores


ALL = list(HealthChecker.WEIGHTS)


def test_no_findings_scores_100():
    score, _ = scored([], ALL)
    assert score == 100


def test_critical_security_hurts_more_than_low():
    crit, _ = scored([finding("security", Severity.CRITICAL)], ALL)
    low, _ = scored([finding("security", Severity.LOW)], ALL)
    assert crit < low < 100


def test_duplicates_and_empty_structure_now_lower_the_score():
    clean, _ = scored([], ALL)
    dup, scores = scored([finding("duplicate", Severity.HIGH)], ALL)
    assert dup < clean
    assert scores["duplicate"] < 100
    struct, _ = scored([finding("structure", Severity.LOW)] * 5, ALL)
    assert struct < clean


def test_info_findings_cost_nothing():
    score, _ = scored([finding("size", Severity.INFO)] * 10, ALL)
    assert score == 100


def test_type_category_is_not_scored():
    _, scores = scored([finding("type", Severity.HIGH)], ALL + ["type"])
    assert "type" not in scores


def test_category_that_did_not_run_is_excluded_from_weights():
    findings = [finding("security", Severity.CRITICAL)]
    full, _ = scored(findings, ALL)
    partial, scores = scored(findings, ["complexity"])
    assert "security" not in scores
    assert partial == 100
    assert full < partial


def test_nothing_ran_scores_zero():
    score, scores = scored([], [])
    assert scores == {} and score == 0


def test_many_findings_saturate_but_never_negative():
    score, scores = scored([finding("security", Severity.CRITICAL)] * 50, ALL)
    assert 0 <= scores["security"] < 1
    assert score >= 0


@pytest.mark.parametrize("score,status", [
    (100, HealthStatus.EXCELLENT), (95, HealthStatus.EXCELLENT), (94.9, HealthStatus.GOOD),
    (85, HealthStatus.GOOD), (84.9, HealthStatus.ABOVE_AVERAGE), (75, HealthStatus.ABOVE_AVERAGE),
    (65, HealthStatus.AVERAGE), (55, HealthStatus.BELOW_AVERAGE), (45, HealthStatus.POOR),
    (35, HealthStatus.CRITICAL), (34.9, HealthStatus.FAILING), (0, HealthStatus.FAILING),
])
def test_status_thresholds(score, status):
    assert HealthChecker().get_health_status(score) == status


def test_potential_savings_ignores_total_size_and_counts_reclaimable_only():
    analysis = ProjectAnalysis(project_path=Path("."), analysis_time=datetime.now())
    big = finding("size", Severity.HIGH, kind="total_size")
    big.size_impact = 10_000
    dup = finding("duplicate", Severity.HIGH, reclaimable=True)
    dup.size_impact = 500
    analysis.issues = [big, dup]
    assert analysis.potential_savings_bytes == 500
