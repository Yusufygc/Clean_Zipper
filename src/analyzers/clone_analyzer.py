from typing import List

from src.core.base_analyzer import BaseAnalyzer
from src.core.project_index import ProjectIndex
from src.core.registry import register_analyzer
from src.languages import parse_file
from src.languages.clones import CloneFinder, CloneGroup, normalize
from src.languages.registry import get_stripped
from src.models.analysis_models import AnalysisResult, Severity

MAX_GROUPS = 50                 # raporlanan en büyük klon grubu sayısı
MAX_LISTED_LOCATIONS = 10
MAX_FILE_LINES = 20_000         # bundan uzun (büyük olasılıkla üretilmiş / veri) dosyalar klon taramasına girmez


@register_analyzer
class CloneAnalyzer(BaseAnalyzer):
    """Kod klonları (copy-paste): dosyalar arası ve dosya içi, en az `thresholds.clone_lines` ardışık anlamlı satır.

    Yalnızca yorum ve boşluk farkları yok sayılır (string / sayı değerleri birebir aynı olmalı). Tamamen aynı dosyalar `DuplicateFinder`'a bırakılır.
    En çok tekrar eden `MAX_GROUPS` grup ayrı bulgu olur; ayrıca tek bir özet (INFO) bulgusu üretilir.
    """

    def __init__(self, priority: int = 18):
        super().__init__(priority)

    @property
    def name(self) -> str:
        return "Kod Klonu Analizörü"

    @property
    def category(self) -> str:
        return "duplicate"

    def analyze(self, index: ProjectIndex) -> List[AnalysisResult]:
        finder = CloneFinder(window=self.thresholds.clone_lines)
        for entry in index.files:
            if parse_file(index, entry) is None:
                continue
            stripped = get_stripped(index, entry)
            if stripped is None:
                continue
            lines, numbers = normalize(stripped.no_comments)
            if len(lines) <= MAX_FILE_LINES:
                finder.add_file(entry.rel, lines, numbers)
        groups = finder.find()
        if not groups:
            return []
        root = index.root
        results = [self._group_result(root, group) for group in groups[:MAX_GROUPS]]
        results.append(self._summary(groups, finder))
        return results

    def _group_result(self, root, group: CloneGroup) -> AnalysisResult:
        first = group.locations[0]
        severity = Severity.MEDIUM if group.lines >= self.thresholds.clone_severe_lines else Severity.LOW
        shown = [f"{loc.key}:{loc.start_line}-{loc.end_line}" for loc in group.locations[:MAX_LISTED_LOCATIONS]]
        more = group.copies - len(shown)
        where = ", ".join(shown) + (f" ... (+{more})" if more > 0 else "")
        return self._create_result(
            title=f"Kod Klonu: {first.key.rsplit('/', 1)[-1]}:{first.start_line} ({group.lines} satır, {group.copies} kopya)",
            description=f"Aynı {group.lines} satırlık blok {group.copies} yerde tekrarlanıyor: {where}.",
            severity=severity, file_path=root / first.key,
            recommendation="Ortak bloğu tek bir fonksiyona / sınıfa çıkarın (Extract Method) ve kopyaların yerine çağırın.",
            rule='code-clone', lines=group.lines, copies=group.copies, duplicated_lines=group.duplicated_lines,
            locations=[{'path': loc.key, 'start_line': loc.start_line, 'end_line': loc.end_line}
                       for loc in group.locations],
            approximate=False)

    def _summary(self, groups: List[CloneGroup], finder: CloneFinder) -> AnalysisResult:
        duplicated = sum(g.duplicated_lines for g in groups)
        ratio = duplicated / finder.total_lines if finder.total_lines else 0.0
        return self._create_result(
            title=f"Kod Klonu Özeti: {len(groups)} grup",
            description=(f"{len(groups)} klon grubunda yaklaşık {duplicated} tekrarlanan anlamlı satır "
                         f"(taranan {finder.total_lines} satırın %{ratio * 100:.1f}'i). "
                         f"En büyük {min(len(groups), MAX_GROUPS)} grup ayrı bulgu olarak listelendi."),
            severity=Severity.INFO,
            rule='clone-summary', groups=len(groups), duplicated_lines=duplicated, scanned_lines=finder.total_lines,
            ratio=ratio, identical_files=len(finder.identical_files), approximate=False)
