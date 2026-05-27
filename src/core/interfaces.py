"""
Temel interface'ler - SOLID prensipleri icin abstract base class'lar
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
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
    def analyze(self, project_path: Path) -> List[AnalysisResult]:
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        pass
    
    def can_analyze(self, project_path: Path) -> bool:
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
    def generate_recommendations(self, analysis: ProjectAnalysis) -> List[Tuple[str, str, int]]:
        pass
    
    @abstractmethod
    def prioritize_recommendations(self, recommendations) -> List[Tuple[str, str, int]]:
        pass


class IReporter(ABC):
    @abstractmethod
    def generate_report(self, analysis: ProjectAnalysis) -> str:
        pass
    
    @abstractmethod
    def export_report(self, analysis: ProjectAnalysis, output_path: Path) -> bool:
        pass
