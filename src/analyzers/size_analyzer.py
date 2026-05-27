from pathlib import Path
from typing import List, Dict
from collections import defaultdict
from src.core.base_analyzer import BaseAnalyzer
from src.models.analysis_models import AnalysisResult, Severity

class SizeAnalyzer(BaseAnalyzer):
    def __init__(self, large_file_threshold_mb: float = 10, priority: int = 10):
        super().__init__(priority)
        self.large_file_threshold = large_file_threshold_mb * 1024 * 1024
    
    @property
    def name(self) -> str:
        return "Boyut Analizoru"
    
    @property
    def category(self) -> str:
        return "size"
    
    def analyze(self, project_path: Path) -> List[AnalysisResult]:
        results = []
        total_size = 0
        large_files = []
        for root_path, dirs, filenames in self._walk_project(project_path):
            root = Path(root_path)
            for filename in filenames:
                file_path = root / filename
                try:
                    size = file_path.stat().st_size
                    total_size += size
                    if size > self.large_file_threshold:
                        large_files.append(self._get_file_info(file_path))
                except (OSError, PermissionError):
                    continue
        
        total_mb = total_size / (1024 * 1024)
        severity = Severity.HIGH if total_mb > 500 else Severity.MEDIUM if total_mb > 200 else Severity.INFO
        results.append(self._create_result(
            title=f"Toplam proje boyutu: {total_mb:.1f} MB",
            description=f"Proje {total_mb:.1f} MB disk alani kapliyor.",
            severity=severity, size_impact=total_size
        ))
        
        for file_info in sorted(large_files, key=lambda x: x.size_bytes, reverse=True)[:10]:
            results.append(self._create_result(
                title=f"Buyuk dosya: {file_info.path.name}",
                description=f"{file_info.size_mb:.1f} MB",
                severity=Severity.HIGH if file_info.size_mb > 50 else Severity.MEDIUM,
                file_path=file_info.path, size_impact=file_info.size_bytes
            ))
        return results
