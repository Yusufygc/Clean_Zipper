from pathlib import Path
from typing import List
from src.core.base_analyzer import BaseAnalyzer
from src.models.analysis_models import AnalysisResult, Severity

class EmptyFolderFinder(BaseAnalyzer):
    def __init__(self, priority: int = 40):
        super().__init__(priority)
    
    @property
    def name(self) -> str:
        return "Bos Klasor Bulucu"
    
    @property
    def category(self) -> str:
        return "structure"
    
    def analyze(self, project_path: Path) -> List[AnalysisResult]:
        results = []
        for root_path, dirs, filenames in self._walk_project(project_path):
            if not dirs and not filenames:
                results.append(self._create_result(
                    title=f"Bos klasor: {Path(root_path).name}",
                    description="Bu klasor bos.",
                    severity=Severity.LOW,
                    file_path=Path(root_path)
                ))
        return results
