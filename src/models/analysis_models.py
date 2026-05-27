"""
Veri modelleri - Tum analiz sonuclari icin dataclass'lar
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from enum import Enum, auto
from datetime import datetime
from pathlib import Path


class Severity(Enum):
    INFO = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


class HealthStatus(Enum):
    EXCELLENT = "A+"
    GOOD = "A"
    ABOVE_AVERAGE = "B+"
    AVERAGE = "B"
    BELOW_AVERAGE = "C+"
    POOR = "C"
    CRITICAL = "D"
    FAILING = "F"


@dataclass
class FileInfo:
    path: Path
    size_bytes: int
    extension: str
    last_modified: datetime
    is_binary: bool = False
    line_count: Optional[int] = None
    
    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)
    
    @property
    def size_kb(self) -> float:
        return self.size_bytes / 1024


@dataclass
class AnalysisResult:
    analyzer_name: str
    category: str
    severity: Severity
    title: str
    description: str
    file_path: Optional[Path] = None
    size_impact: Optional[int] = None
    recommendation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def size_impact_mb(self) -> Optional[float]:
        if self.size_impact:
            return self.size_impact / (1024 * 1024)
        return None


@dataclass
class ProjectAnalysis:
    project_path: Path
    analysis_time: datetime
    total_files: int = 0
    total_dirs: int = 0
    total_size: int = 0
    file_type_distribution: Dict[str, int] = field(default_factory=dict)
    file_type_sizes: Dict[str, int] = field(default_factory=dict)
    largest_files: List[FileInfo] = field(default_factory=list)
    empty_dirs: List[Path] = field(default_factory=list)
    duplicate_files: List[List[Path]] = field(default_factory=list)
    issues: List[AnalysisResult] = field(default_factory=list)
    warnings: List[AnalysisResult] = field(default_factory=list)
    suggestions: List[AnalysisResult] = field(default_factory=list)
    health_score: float = 0.0
    health_status: HealthStatus = HealthStatus.FAILING
    
    @property
    def total_size_mb(self) -> float:
        return self.total_size / (1024 * 1024)
    
    @property
    def potential_savings_bytes(self) -> int:
        savings = 0
        for issue in self.issues + self.warnings:
            if issue.size_impact:
                savings += issue.size_impact
        return savings
    
    @property
    def potential_savings_mb(self) -> float:
        return self.potential_savings_bytes / (1024 * 1024)
