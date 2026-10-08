from typing import List
from src.core.base_analyzer import BaseAnalyzer
from src.core.project_index import ProjectIndex
from src.core.registry import register_analyzer
from src.models.analysis_models import AnalysisResult, Severity


@register_analyzer
class StructureAnalyzer(BaseAnalyzer):
    MAX_DEPTH = 10

    def __init__(self, priority: int = 50):
        super().__init__(priority)

    @property
    def name(self) -> str:
        return "Yapi Analizoru"

    @property
    def category(self) -> str:
        return "structure"

    def analyze(self, index: ProjectIndex) -> List[AnalysisResult]:
        if index.max_depth <= self.MAX_DEPTH:
            return []
        return [self._create_result(
            title=f"Derin klasor yapisi: {index.max_depth} seviye",
            description="Klasor yapisini basitlestirmeyi dusunun.",
            severity=Severity.MEDIUM
        )]
