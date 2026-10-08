import math
from typing import Dict, Iterable, List

from src.core.interfaces import IHealthChecker
from src.models.analysis_models import ProjectAnalysis, AnalysisResult, Severity, HealthStatus


class HealthChecker(IHealthChecker):
    """Bulgulardan kategori bazlı ve genel sağlık skoru üretir.

    Her kategorinin cezası bulguların şiddet puanlarının toplamıdır.
    Alt skor = 100 * exp(-ceza / DECAY): ilk bulgular skoru hızlı düşürür,
    çok sayıda bulgu skoru sıfıra doğru yumuşakça yaklaştırır.
    """

    SEVERITY_PENALTY = {
        Severity.CRITICAL: 40,
        Severity.HIGH: 15,
        Severity.MEDIUM: 5,
        Severity.LOW: 1,
        Severity.INFO: 0,
    }
    # 'type' kategorisi yalnızca bilgi amaçlı olduğundan puanlanmaz.
    WEIGHTS = {
        'security': 0.20,
        'complexity': 0.16,
        'duplicate': 0.10,
        'size': 0.08,
        'structure': 0.08,
        'dependency': 0.08,
        'deadcode': 0.06,
        'architecture': 0.06,
        'reliability': 0.08,
        'testing': 0.06,
        'hygiene': 0.04,
    }
    DECAY = 60

    def calculate_category_scores(self, findings: Iterable[AnalysisResult],
                                  ran_categories: Iterable[str]) -> Dict[str, float]:
        """Çalışmış her puanlanabilir kategori için 0-100 arası alt skor döner."""
        penalties = {c: 0 for c in ran_categories if c in self.WEIGHTS}
        for finding in findings:
            if finding.category in penalties:
                penalties[finding.category] += self.SEVERITY_PENALTY.get(finding.severity, 0)
        return {c: 100 * math.exp(-p / self.DECAY) for c, p in penalties.items()}

    def calculate_score(self, analysis: ProjectAnalysis) -> float:
        scores = analysis.category_scores
        total_weight = sum(self.WEIGHTS[c] for c in scores)
        if total_weight == 0:
            return 0.0
        score = sum(s * self.WEIGHTS[c] for c, s in scores.items()) / total_weight
        return min(max(score, 0.0), 100.0)

    def get_health_status(self, score: float) -> HealthStatus:
        if score >= 95: return HealthStatus.EXCELLENT
        elif score >= 85: return HealthStatus.GOOD
        elif score >= 75: return HealthStatus.ABOVE_AVERAGE
        elif score >= 65: return HealthStatus.AVERAGE
        elif score >= 55: return HealthStatus.BELOW_AVERAGE
        elif score >= 45: return HealthStatus.POOR
        elif score >= 35: return HealthStatus.CRITICAL
        else: return HealthStatus.FAILING

    def get_critical_issues(self, analysis: ProjectAnalysis) -> List[AnalysisResult]:
        return [i for i in analysis.issues if i.severity in [Severity.HIGH, Severity.CRITICAL]]
