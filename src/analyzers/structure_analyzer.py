from pathlib import Path
from typing import List
from src.core.base_analyzer import BaseAnalyzer
from src.models.analysis_models import AnalysisResult, Severity

class StructureAnalyzer(BaseAnalyzer):
    def __init__(self, priority: int = 50):
        super().__init__(priority)
    
    @property
    def name(self) -> str:
        return "Yapi Analizoru"
    
    @property
    def category(self) -> str:
        return "structure"
    
    def analyze(self, project_path: Path) -> List[AnalysisResult]:
        results = []
        max_depth = 0
        for root_path, dirs, _ in self._walk_project(project_path):
            depth = len(Path(root_path).relative_to(project_path).parts)
            if depth > max_depth:
                max_depth = depth
        if max_depth > 10:
            results.append(self._create_result(
                title=f"Derin klasor yapisi: {max_depth} seviye",
                description="Klasor yapisini basitlestirmeyi dusunun.",
                severity=Severity.MEDIUM
            ))
        return results
