from pathlib import Path
from typing import List, Dict
from collections import defaultdict
import hashlib
from src.core.base_analyzer import BaseAnalyzer
from src.models.analysis_models import AnalysisResult, Severity

class DuplicateFinder(BaseAnalyzer):
    def __init__(self, min_file_size: int = 1024, priority: int = 30):
        super().__init__(priority)
        self.min_file_size = min_file_size
    
    @property
    def name(self) -> str:
        return "Cift Dosya Bulucu"
    
    @property
    def category(self) -> str:
        return "duplicate"
    
    def analyze(self, project_path: Path) -> List[AnalysisResult]:
        results = []
        duplicates = self._find_duplicates(project_path)
        if duplicates:
            for file_hash, file_list in duplicates.items():
                if len(file_list) > 1:
                    waste = sum(f.stat().st_size for f in file_list[1:])
                    results.append(self._create_result(
                        title=f"Cift dosyalar: {file_list[0].name}",
                        description=f"{len(file_list)-1} kopya, {waste/(1024*1024):.1f} MB gereksiz",
                        severity=Severity.HIGH, size_impact=waste,
                        file_path=file_list[0],
                        kind='duplicate_group', paths=list(file_list), reclaimable=True
                    ))
        return results
    
    def _find_duplicates(self, project_path: Path) -> Dict[str, List[Path]]:
        size_map = defaultdict(list)
        for root_path, dirs, filenames in self._walk_project(project_path):
            for filename in filenames:
                fp = Path(root_path) / filename
                try:
                    if fp.stat().st_size >= self.min_file_size:
                        size_map[fp.stat().st_size].append(fp)
                except (OSError, PermissionError):
                    continue
        
        duplicates = defaultdict(list)
        for size, files in size_map.items():
            if len(files) > 1:
                hash_map = defaultdict(list)
                for fp in files:
                    try:
                        with open(fp, 'rb') as f:
                            file_hash = hashlib.md5(f.read()).hexdigest()
                        hash_map[file_hash].append(fp)
                    except:
                        pass
                for h, fps in hash_map.items():
                    if len(fps) > 1:
                        duplicates[h] = fps
        return duplicates
