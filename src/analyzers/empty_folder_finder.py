from typing import List
from src.core.base_analyzer import BaseAnalyzer
from src.core.project_index import ProjectIndex
from src.core.registry import register_analyzer
from src.models.analysis_models import AnalysisResult, Severity


@register_analyzer
class EmptyFolderFinder(BaseAnalyzer):
    def __init__(self, priority: int = 40):
        super().__init__(priority)

    @property
    def name(self) -> str:
        return "Bos Klasor Bulucu"

    @property
    def category(self) -> str:
        return "structure"

    def analyze(self, index: ProjectIndex) -> List[AnalysisResult]:
        return [
            self._create_result(
                title=f"Boş klasör: {d.path.name}",
                description="Bu klasör boş.",
                severity=Severity.LOW,
                file_path=d.path,
                rule='empty-folder', kind='empty_dir'
            )
            for d in index.dirs if d.file_count == 0 and d.dir_count == 0
        ]
