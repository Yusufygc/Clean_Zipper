"""
Temel interface'ler - SOLID prensipleri icin abstract base class'lar
"""
from abc import ABC, abstractmethod
from typing import List, Tuple
from pathlib import Path
from src.core.project_index import ProjectIndex
from src.models.analysis_models import AnalysisResult, ProjectAnalysis, HealthStatus


class IAnalyzer(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def category(self) -> str:
        pass
    
    @abstractmethod
    def analyze(self, index: ProjectIndex) -> List[AnalysisResult]:
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        pass
    
    def can_analyze(self, index: ProjectIndex) -> bool:
        return True


class IHealthChecker(ABC):
    @abstractmethod
    def calculate_score(self, analysis: ProjectAnalysis) -> float:
        pass
    
    @abstractmethod
    def get_health_status(self, score: float) -> HealthStatus:
        pass
    
    @abstractmethod
    def get_critical_issues(self, analysis: ProjectAnalysis) -> List[AnalysisResult]:
        pass


class IRecommendationEngine(ABC):
    @abstractmethod
    def generate_recommendations(self, analysis: ProjectAnalysis) -> List[Tuple[str, str, str]]:
        """(başlık, açıklama, öncelik etiketi) listesi, önemliden önemsize."""

    @abstractmethod
    def prioritize_recommendations(self, groups) -> list:
        """Öneri adaylarını önem sırasına dizer."""


class IReporter(ABC):
    @abstractmethod
    def generate_report(self, analysis: ProjectAnalysis) -> str:
        pass
    
    @abstractmethod
    def export_report(self, analysis: ProjectAnalysis, output_path: Path) -> bool:
        pass
