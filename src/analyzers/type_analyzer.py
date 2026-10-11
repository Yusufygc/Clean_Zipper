from typing import List
from src.core.base_analyzer import BaseAnalyzer
from src.core.project_index import ProjectIndex
from src.core.registry import register_analyzer
from src.models.analysis_models import AnalysisResult, Severity


@register_analyzer
class TypeAnalyzer(BaseAnalyzer):
    def __init__(self, priority: int = 20):
        super().__init__(priority)

    @property
    def name(self) -> str:
        return "Dosya Türü Analizörü"

    @property
    def category(self) -> str:
        return "type"

    def analyze(self, index: ProjectIndex) -> List[AnalysisResult]:
        results = []
        for ext, count in sorted(index.ext_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
            results.append(self._create_result(
                title=f"Dosya türü: {ext or 'uzantısız'}",
                description=f"{count} adet dosya",
                severity=Severity.INFO
            ))
        return results
