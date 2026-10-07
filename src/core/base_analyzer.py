"""
Temel analizor siniflari
"""
from abc import abstractmethod
from typing import List, Set
from pathlib import Path
import os
from datetime import datetime

from src.core.constants import EXCLUDED_DIRS
from src.core.interfaces import IAnalyzer
from src.models.analysis_models import AnalysisResult, Severity, FileInfo


class BaseAnalyzer(IAnalyzer):
    def __init__(self, priority: int = 100):
        self._priority = priority
        self._excluded_dirs: Set[str] = set(EXCLUDED_DIRS)
    
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
    
    def _get_file_info(self, file_path: Path) -> FileInfo:
        stat = file_path.stat()
        return FileInfo(
            path=file_path, size_bytes=stat.st_size,
            extension=file_path.suffix.lower(),
            last_modified=datetime.fromtimestamp(stat.st_mtime)
        )
    
    def _is_binary(self, file_path: Path) -> bool:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                f.read(1024)
            return False
        except (UnicodeDecodeError, IOError):
            return True
    
    def _walk_project(self, project_path: Path):
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in self._excluded_dirs]
            yield Path(root), dirs, files
    
    @abstractmethod
    def analyze(self, project_path: Path) -> List[AnalysisResult]:
        pass
