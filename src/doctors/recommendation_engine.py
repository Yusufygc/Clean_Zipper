"""Dashboard "Öneriler" kartı: bulguları kurala göre gruplayıp en önemli işleri öne çıkarır."""
from collections import defaultdict
from typing import Dict, List, Tuple

from src.core.interfaces import IRecommendationEngine
from src.models.analysis_models import AnalysisResult, ProjectAnalysis, Severity
from src.services.audit_catalog import RULE_LABELS, SEVERITY_LABELS   # salt veri modülü; servis mantığı içermez

# Öneriye girecek en düşük şiddet; DÜŞÜK ve BİLGİ bulguları öneri kartını boğmasın.
MIN_SEVERITY = Severity.MEDIUM
EXAMPLE_LIMIT = 2

Recommendation = Tuple[str, str, str]          # (başlık, açıklama, öncelik: 'KRİTİK' | 'YÜKSEK' | 'ORTA')


class RecommendationEngine(IRecommendationEngine):
    """Kural başına tek öneri: en yüksek şiddet, sonra bulgu sayısı. Sır bulgularının değeri metinde yer almaz
    (bulgu metinleri zaten değer içermez; yalnızca dosya adı ve analizörün düzeltme önerisi kullanılır)."""

    def generate_recommendations(self, analysis: ProjectAnalysis) -> List[Recommendation]:
        groups: Dict[str, List[AnalysisResult]] = defaultdict(list)
        for finding in analysis.all_findings:
            if finding.severity.value >= MIN_SEVERITY.value:
                groups[finding.metadata.get('rule') or finding.category].append(finding)
        ranked = self.prioritize_recommendations(groups.values())
        return [self._recommendation(rule_findings) for rule_findings in ranked]

    def prioritize_recommendations(self, groups) -> List[List[AnalysisResult]]:
        return sorted(groups, key=lambda g: (-max(f.severity.value for f in g), -len(g),
                                             g[0].metadata.get('rule') or g[0].category))

    def get_top_recommendations(self, analysis: ProjectAnalysis, count: int = 5) -> List[Recommendation]:
        return self.generate_recommendations(analysis)[:count]

    @staticmethod
    def _recommendation(findings: List[AnalysisResult]) -> Recommendation:
        top = max(findings, key=lambda f: f.severity.value)
        rule = top.metadata.get('rule', '')
        title = RULE_LABELS.get(rule, top.title)
        names = []
        for f in findings:
            if f.file_path is not None and f.file_path.name not in names:
                names.append(f.file_path.name)
        where = f" ({', '.join(names[:EXAMPLE_LIMIT])}{' …' if len(names) > EXAMPLE_LIMIT else ''})" if names else ""
        advice = next((f.recommendation for f in findings if f.recommendation), top.description)
        return title, f"{len(findings)} bulgu{where}. {advice}", SEVERITY_LABELS[top.severity][1]
