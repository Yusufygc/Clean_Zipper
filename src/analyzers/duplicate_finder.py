import logging
from collections import defaultdict
from typing import Dict, List
from src.core.base_analyzer import BaseAnalyzer
from src.core.project_index import FileEntry, ProjectIndex
from src.core.registry import register_analyzer
from src.models.analysis_models import AnalysisResult, Severity

logger = logging.getLogger(__name__)


@register_analyzer
class DuplicateFinder(BaseAnalyzer):
    def __init__(self, min_file_size: int = 1024, priority: int = 30):
        super().__init__(priority)
        self.min_file_size = min_file_size

    @property
    def name(self) -> str:
        return "Çift Dosya Bulucu"

    @property
    def category(self) -> str:
        return "duplicate"

    def analyze(self, index: ProjectIndex) -> List[AnalysisResult]:
        results = []
        for group in self._find_duplicate_groups(index):
            waste = sum(f.size for f in group[1:])
            results.append(self._create_result(
                title=f"Çift dosyalar: {group[0].path.name}",
                description=f"{len(group)-1} kopya, {waste/(1024*1024):.1f} MB gereksiz",
                severity=Severity.HIGH, size_impact=waste,
                file_path=group[0].path,
                rule='duplicate-files', kind='duplicate_group', paths=[f.path for f in group], reclaimable=True
            ))
        return results

    def _find_duplicate_groups(self, index: ProjectIndex) -> List[List[FileEntry]]:
        """Boyut, ilk 64 KB özeti, tam özet sırasıyla eleyerek aynı içerikli dosya gruplarını bulur."""
        by_size: Dict[int, List[FileEntry]] = defaultdict(list)
        for entry in index.files:
            if entry.size >= self.min_file_size:
                by_size[entry.size].append(entry)

        groups = []
        for same_size in by_size.values():
            if len(same_size) < 2:
                continue
            for candidates in self._split_by_hash(index, same_size, partial=True):
                for group in self._split_by_hash(index, candidates, partial=False):
                    groups.append(sorted(group, key=lambda f: f.rel))
        return sorted(groups, key=lambda g: g[0].rel)

    @staticmethod
    def _split_by_hash(index: ProjectIndex, entries: List[FileEntry], partial: bool) -> List[List[FileEntry]]:
        buckets: Dict[str, List[FileEntry]] = defaultdict(list)
        for entry in entries:
            try:
                buckets[index.hash_file(entry, partial=partial)].append(entry)
            except OSError as e:
                logger.debug("Özet hesaplanamadı: %s (%s)", entry.rel, e)
                index.mark_skipped(entry, 'unreadable')
                continue
        return [b for b in buckets.values() if len(b) > 1]
