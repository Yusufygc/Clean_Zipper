import ast
from collections import Counter
from typing import List, Tuple

from src.core.base_analyzer import BaseAnalyzer
from src.core.path_rules import is_test_path
from src.core.project_index import FileEntry, ProjectIndex
from src.core.registry import register_analyzer
from src.languages import brace_usage, parse_file, python_usage
from src.languages.base import SourceMetrics
from src.languages.registry import get_stripped
from src.models.analysis_models import AnalysisResult, Severity

TOP_VALUES = 5


@register_analyzer
class MagicNumberAnalyzer(BaseAnalyzer):
    """Fonksiyon gövdelerindeki adsız sayısal sabitler (sihirli sayı); dosya başına en fazla bir bulgu.

    {0, 1, 2, -1, 0.5}, adlandırılmış atamalar (`retries = 3`, `const`/`final`), adlı argümanlar, indeksler ve sabit veri
    tabloları sayılmaz. Test dosyaları atlanır. Eşik `thresholds.magic_numbers` (varsayılan 10).
    """

    def __init__(self, priority: int = 16):
        super().__init__(priority)

    @property
    def name(self) -> str:
        return "Sihirli Sayı Analizörü"

    @property
    def category(self) -> str:
        return "deadcode"

    def analyze(self, index: ProjectIndex) -> List[AnalysisResult]:
        results: List[AnalysisResult] = []
        for entry in index.files:
            if is_test_path(entry.rel):
                continue
            metrics = parse_file(index, entry)
            if metrics is None:
                continue
            numbers = self._find(index, entry, metrics)
            if len(numbers) > self.thresholds.magic_numbers:
                results.append(self._finding(entry, metrics, numbers))
        return results

    @staticmethod
    def _find(index: ProjectIndex, entry: FileEntry, metrics: SourceMetrics) -> List[python_usage.MagicNumber]:
        if metrics.language == 'python':
            if not metrics.parse_ok:
                return []
            try:
                return python_usage.find_magic_numbers(ast.parse(index.read_text(entry) or ''))
            except (SyntaxError, ValueError, RecursionError):
                return []
        stripped = get_stripped(index, entry)
        if stripped is None:
            return []
        ranges = [(f.start_line, f.end_line) for f in metrics.functions]
        return brace_usage.find_magic_numbers(stripped.clean, ranges)

    def _finding(self, entry: FileEntry, metrics: SourceMetrics,
                 numbers: List[python_usage.MagicNumber]) -> AnalysisResult:
        top: List[Tuple[float, int]] = Counter(n.value for n in numbers).most_common(TOP_VALUES)
        listed = ", ".join(f"{value:g} ({count}x)" for value, count in top)
        return self._create_result(
            title=f"Sihirli Sayılar: {entry.path.name}",
            description=(f"Fonksiyon gövdelerinde {len(numbers)} adsız sayısal sabit var "
                         f"(Limit: {self.thresholds.magic_numbers}); en sık geçenler: {listed}."),
            severity=Severity.LOW, file_path=entry.path,
            recommendation="Anlamlı sabitleri adlandırılmış sabitlere (BÜYÜK_HARF / const) taşıyın.",
            rule='magic-numbers', count=len(numbers), top_values=top, first_lines=[n.line for n in numbers[:10]],
            language=metrics.language, approximate=metrics.approximate)
