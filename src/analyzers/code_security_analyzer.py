import re
from bisect import bisect_right
from typing import Dict, Iterable, List, Optional

from src.core.base_analyzer import BaseAnalyzer
from src.core.path_rules import is_test_path
from src.core.project_index import FileEntry, ProjectIndex
from src.core.registry import register_analyzer
from src.core.security_rules import SecurityRule, load_security_rules
from src.languages import parse_file
from src.languages.registry import get_stripped
from src.models.analysis_models import AnalysisResult

MAX_LISTED_LINES = 10


@register_analyzer
class CodeSecurityAnalyzer(BaseAnalyzer):
    """SAST-lite: `resources/rules/*.json` kurallarını kaynak kodda arar (tehlikeli API ve kalıplar).

    Kural başına dosya başına tek bulgu; satırlar listelenir. Yorumlar ve (kurala göre) string içerikleri taramaya
    girmez. Test dosyaları atlanır. Regex tabanlıdır: Sonuçlar ipucudur (`approximate=True`;
    veri akışı bilinmez). `disabled_rules` ile kural kimliği bazında kapatılır.
    """

    def __init__(self, priority: int = 16, rules: Optional[List[SecurityRule]] = None,
                 disabled_rules: Iterable[str] = ()):
        super().__init__(priority)
        self._rules = rules if rules is not None else load_security_rules()
        self.disabled_rules = frozenset(disabled_rules)

    @property
    def name(self) -> str:
        return "Kod Güvenliği (SAST) Analizörü"

    @property
    def category(self) -> str:
        return "security"

    def analyze(self, index: ProjectIndex) -> List[AnalysisResult]:
        active = [r for r in self._rules if r.id not in self.disabled_rules]
        if not active:
            return []
        by_language: Dict[str, List[SecurityRule]] = {}
        results: List[AnalysisResult] = []
        for entry in index.files:
            if is_test_path(entry.rel):
                continue
            metrics = parse_file(index, entry)
            if metrics is None:
                continue
            rules = by_language.setdefault(
                metrics.language, [r for r in active if r.applies_to(metrics.language)])
            if rules:
                results.extend(self._scan(index, entry, metrics.language, rules))
        return results

    def _scan(self, index: ProjectIndex, entry: FileEntry, language: str,
              rules: List[SecurityRule]) -> List[AnalysisResult]:
        stripped = get_stripped(index, entry)
        if stripped is None:
            return []
        results = []
        line_starts: Optional[List[int]] = None
        for rule in rules:
            text = stripped.clean if rule.scope == 'code' else stripped.no_comments
            offsets = [m.start() for m in rule.pattern.finditer(text)]
            if not offsets:
                continue
            if line_starts is None:
                line_starts = [0] + [m.end() for m in re.finditer('\n', stripped.clean)]
            lines = sorted({bisect_right(line_starts, offset) for offset in offsets})
            results.append(self._finding(entry, rule, lines, language))
        return results

    def _finding(self, entry: FileEntry, rule: SecurityRule, lines: List[int], language: str) -> AnalysisResult:
        shown = ", ".join(str(n) for n in lines[:MAX_LISTED_LINES])
        more = f" ... (+{len(lines) - MAX_LISTED_LINES})" if len(lines) > MAX_LISTED_LINES else ""
        cwe = f" [{rule.cwe}]" if rule.cwe else ""
        return self._create_result(
            title=f"{rule.title}: {entry.path.name}",
            description=f"{rule.title}{cwe}. Satır: {shown}{more}.",
            severity=rule.severity, file_path=entry.path, recommendation=rule.advice,
            rule=rule.id, cwe=rule.cwe, lines=lines, count=len(lines), language=language,
            approximate=True)
