from pathlib import Path
from typing import List
from collections import defaultdict
from src.core.base_analyzer import BaseAnalyzer
from src.models.analysis_models import AnalysisResult, Severity

class TypeAnalyzer(BaseAnalyzer):
    def __init__(self, priority: int = 20):
        super().__init__(priority)
    
    @property
    def name(self) -> str:
        return "Dosya Turu Analizoru"
    
    @property
    def category(self) -> str:
        return "type"
    
    def analyze(self, project_path: Path) -> List[AnalysisResult]:
        results = []
        ext_count = defaultdict(int)
        for root_path, dirs, filenames in self._walk_project(project_path):
            for filename in filenames:
                ext = Path(filename).suffix.lower()
                ext_count[ext] += 1
        
        for ext, count in sorted(ext_count.items(), key=lambda x: x[1], reverse=True)[:5]:
            results.append(self._create_result(
                title=f"Dosya turu: {ext or 'uzantisiz'}",
                description=f"{count} adet dosya",
                severity=Severity.INFO
            ))
        return results
