from abc import abstractmethod
from typing import List
from pathlib import Path

from src.core.interfaces import IAnalyzer
from src.core.project_index import ProjectIndex
from src.core.thresholds import QualityThresholds
from src.models.analysis_models import AnalysisResult, Severity


class BaseAnalyzer(IAnalyzer):
    def __init__(self, priority: int = 100):
        self._priority = priority
        self.thresholds = QualityThresholds()      # ProjectDoctor / ProjectService üzerinden geçersiz kılınabilir

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @property
    def category(self) -> str:
        return "general"

    def get_priority(self) -> int:
        return self._priority

    def _create_result(self, title: str, description: str, severity: Severity = Severity.INFO,
                      file_path: Path = None, size_impact: int = None,
                      recommendation: str = None, **metadata) -> AnalysisResult:
        return AnalysisResult(
            analyzer_name=self.name, category=self.category,
            severity=severity, title=title, description=description,
            file_path=file_path, size_impact=size_impact,
            recommendation=recommendation, metadata=metadata
        )

    @abstractmethod
    def analyze(self, index: ProjectIndex) -> List[AnalysisResult]:
        pass
