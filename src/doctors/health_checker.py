from typing import List
from src.models.analysis_models import ProjectAnalysis, AnalysisResult, Severity, HealthStatus

class HealthChecker:
    WEIGHTS = {'size': 0.25, 'structure': 0.20, 'quality': 0.20, 'duplicates': 0.15, 'types': 0.10, 'empty': 0.05, 'organization': 0.05}
    
    def calculate_score(self, analysis: ProjectAnalysis) -> float:
        scores = {
            'size': self._calc_size(analysis),
            'structure': self._calc_structure(analysis),
            'quality': self._calc_quality(analysis),
            'duplicates': self._calc_duplicates(analysis),
            'types': 80,
            'empty': 90 if len(analysis.empty_dirs) < 5 else 70,
            'organization': 85
        }
        return min(max(sum(scores[k] * self.WEIGHTS[k] for k in self.WEIGHTS), 0), 100)
    
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
    
    def _calc_size(self, a): return 100 if a.total_size_mb < 10 else max(0, 100 - a.total_size_mb / 10)
    def _calc_structure(self, a): return max(0, 100 - len(a.empty_dirs) * 3)
    def _calc_quality(self, a): return max(0, 100 - len(a.issues) * 10)
    def _calc_duplicates(self, a): return 100 if not a.duplicate_files else max(0, 100 - len(a.duplicate_files) * 15)
