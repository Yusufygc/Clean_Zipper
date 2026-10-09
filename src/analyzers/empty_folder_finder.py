from typing import Dict, List, Set
from src.core.base_analyzer import BaseAnalyzer
from src.core.project_index import DirEntry, ProjectIndex
from src.core.registry import register_analyzer
from src.models.analysis_models import AnalysisResult, Severity


@register_analyzer
class EmptyFolderFinder(BaseAnalyzer):
    """Boş klasörler: hiç dosyası olmayan ve alt klasörlerinin hepsi de boş olan klasörler.

    Yalnızca en üstteki boş klasör raporlanır (`a/b/c` boşsa `a`); onu silmek içini de temizler. Dışlanan
    (`venv`, `node_modules` ...) ya da `.gitignore`'lu alt klasör içeren klasör boş sayılmaz: diskte boş değildir.
    """

    def __init__(self, priority: int = 40):
        super().__init__(priority)

    @property
    def name(self) -> str:
        return "Bos Klasor Bulucu"

    @property
    def category(self) -> str:
        return "structure"

    def analyze(self, index: ProjectIndex) -> List[AnalysisResult]:
        empty = self._empty_rels(index.dirs)
        results = []
        for d in index.dirs:
            parent = d.rel.rsplit('/', 1)[0] if '/' in d.rel else ''
            if d.rel not in empty or parent in empty:
                continue
            nested = sum(1 for rel in empty if rel.startswith(d.rel + '/'))
            results.append(self._create_result(
                title=f"Boş klasör: {d.path.name}",
                description=f"Bu klasör ve içindeki {nested} alt klasör boş." if nested else "Bu klasör boş.",
                severity=Severity.LOW,
                file_path=d.path,
                rule='empty-folder', kind='empty_dir', nested_empty=nested,
            ))
        return results

    @staticmethod
    def _empty_rels(dirs: List[DirEntry]) -> Set[str]:
        """Alttan üste: dosyasız ve tüm alt klasörleri boş olan klasörler (indekse girmeyen alt klasör boş sayılmaz)."""
        empty_children: Dict[str, int] = {}
        empty: Set[str] = set()
        for d in sorted(dirs, key=lambda e: -e.depth):
            if d.file_count == 0 and empty_children.get(d.rel, 0) == d.dir_count:
                empty.add(d.rel)
                if '/' in d.rel:
                    parent = d.rel.rsplit('/', 1)[0]
                    empty_children[parent] = empty_children.get(parent, 0) + 1
        return empty
