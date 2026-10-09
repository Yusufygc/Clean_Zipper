from typing import List
from src.core.base_analyzer import BaseAnalyzer
from src.core.project_index import ProjectIndex
from src.core.registry import register_analyzer
from src.models.analysis_models import AnalysisResult, Severity

MB = 1024 * 1024


@register_analyzer
class SizeAnalyzer(BaseAnalyzer):
    def __init__(self, large_file_threshold_mb: float = 10, priority: int = 10):
        super().__init__(priority)
        self.large_file_threshold = large_file_threshold_mb * MB

    @property
    def name(self) -> str:
        return "Boyut Analizoru"

    @property
    def category(self) -> str:
        return "size"

    def analyze(self, index: ProjectIndex) -> List[AnalysisResult]:
        results = []
        total_mb = index.total_size / MB
        severity = Severity.HIGH if total_mb > 500 else Severity.MEDIUM if total_mb > 200 else Severity.INFO
        results.append(self._create_result(
            title=f"Toplam proje boyutu: {total_mb:.1f} MB",
            description=f"Proje {total_mb:.1f} MB disk alanı kaplıyor.",
            severity=severity, kind='total_size', total_bytes=index.total_size
        ))

        large_files = [f for f in index.files if f.size > self.large_file_threshold]
        for entry in sorted(large_files, key=lambda f: f.size, reverse=True)[:10]:
            size_mb = entry.size / MB
            results.append(self._create_result(
                title=f"Buyuk dosya: {entry.path.name}",
                description=f"{size_mb:.1f} MB",
                severity=Severity.HIGH if size_mb > 50 else Severity.MEDIUM,
                file_path=entry.path, size_impact=entry.size,
                kind='large_file'
            ))
        return results
