import ast
from pathlib import Path
from typing import List

from src.core.base_analyzer import BaseAnalyzer
from src.core.project_index import FileEntry, ProjectIndex
from src.core.registry import register_analyzer
from src.languages import parse_file
from src.languages import brace_usage, python_usage
from src.languages.base import SourceMetrics
from src.languages.registry import get_stripped
from src.models.analysis_models import AnalysisResult, Severity

MAX_LISTED = 10


def _listing(items: List[str]) -> str:
    shown = ", ".join(items[:MAX_LISTED])
    return shown + (f" ... (+{len(items) - MAX_LISTED})" if len(items) > MAX_LISTED else "")


@register_analyzer
class DeadCodeAnalyzer(BaseAnalyzer):
    """Ölü kod: kullanılmayan import, ulaşılamaz kod ve (yalnızca Python) kullanılmayan yerel değişken.

    Python `ast` ile kesindir. JS/TS/Java importları ve C/C++/Java/C#/JS/TS ulaşılamaz kodu sözcük tabanlıdır
    (`approximate=True`). Go ve Rust derleyici tarafından zaten reddettiği için atlanır.
    """

    def __init__(self, priority: int = 14):
        super().__init__(priority)

    @property
    def name(self) -> str:
        return "Ölü Kod Analizörü"

    @property
    def category(self) -> str:
        return "deadcode"

    def analyze(self, index: ProjectIndex) -> List[AnalysisResult]:
        results: List[AnalysisResult] = []
        for entry in index.files:
            metrics = parse_file(index, entry)
            if metrics is None:
                continue
            if metrics.language == 'python':
                results.extend(self._python(index, entry, metrics))
            else:
                results.extend(self._brace(index, entry, metrics))
        return results

    # ---- Python (ast, kesin) -------------------------------------------------------------

    def _python(self, index: ProjectIndex, entry: FileEntry, metrics: SourceMetrics) -> List[AnalysisResult]:
        if not metrics.parse_ok:
            return []
        text = index.read_text(entry)
        try:
            tree = ast.parse(text or '')
        except (SyntaxError, ValueError, RecursionError):
            return []
        extra = {'language': 'python', 'approximate': False}
        results: List[AnalysisResult] = []
        if entry.path.name != '__init__.py':                       # paket girişleri yeniden dışa aktarım için import eder
            unused = python_usage.find_unused_imports(tree, text.splitlines())
            results.extend(self._unused_imports(entry.path, unused, extra))
        for item in python_usage.find_unreachable(tree):
            results.append(self._unreachable(entry.path, item, Severity.MEDIUM, extra))
        results.extend(self._unused_variables(entry.path, python_usage.find_unused_variables(tree), extra))
        return results

    # ---- süslü parantezli diller (sözcük tabanlı, yaklaşık) -------------------------------

    def _brace(self, index: ProjectIndex, entry: FileEntry, metrics: SourceMetrics) -> List[AnalysisResult]:
        language = metrics.language
        wants_imports = language in brace_usage.UNUSED_IMPORT_LANGUAGES
        wants_unreachable = language in brace_usage.UNREACHABLE_LANGUAGES
        if not (wants_imports or wants_unreachable):
            return []
        stripped = get_stripped(index, entry)
        if stripped is None:
            return []
        extra = {'language': language, 'approximate': True}
        results: List[AnalysisResult] = []
        if wants_imports:
            raw = index.read_text(entry) or ''
            unused = brace_usage.find_unused_imports(language, stripped.no_comments, raw)
            results.extend(self._unused_imports(entry.path, unused, extra))
        if wants_unreachable:
            for item in brace_usage.find_unreachable(stripped.clean, stripped.no_comments):
                results.append(self._unreachable(entry.path, item, Severity.LOW, extra))
        return results

    # ---- bulgu üretimi -----------------------------------------------------------------------

    def _unused_imports(self, path: Path, unused: List[python_usage.UnusedImport], extra: dict) -> List[AnalysisResult]:
        if not unused:
            return []
        names = [f"{item.name} (satır {item.line})" for item in unused]
        return [self._create_result(
            title=f"Kullanılmayan Import: {path.name}",
            description=f"{len(unused)} içe aktarma dosyada hiç kullanılmıyor: {_listing(names)}.",
            severity=Severity.LOW, file_path=path,
            recommendation="Kullanılmayan importları silin; yan etkisi olan modüller için nedenini bir yorumla belirtin.",
            rule='unused-import', count=len(unused),
            imports=[{'name': i.name, 'line': i.line, 'source': i.source} for i in unused], **extra)]

    def _unreachable(self, path: Path, item: python_usage.UnreachableCode, severity: Severity,
                     extra: dict) -> AnalysisResult:
        return self._create_result(
            title=f"Ulaşılamaz Kod: {path.name}:{item.line}",
            description=f"Satır {item.after_line} içindeki '{item.after}' sonrasında kalan kod hiçbir zaman çalışmaz (satır {item.line}).",
            severity=severity, file_path=path,
            recommendation="Ulaşılamaz kodu silin; kasıtlıysa sonlandırıcı ifadeyi koşula bağlayın.",
            rule='unreachable-code', start_line=item.line, after=item.after, **extra)

    def _unused_variables(self, path: Path, unused: List[python_usage.UnusedVariable], extra: dict) -> List[AnalysisResult]:
        by_function = {}
        for item in unused:
            by_function.setdefault(item.function, []).append(item)
        results = []
        for function, items in by_function.items():
            names = [f"{i.name} (satır {i.line})" for i in items]
            results.append(self._create_result(
                title=f"Kullanılmayan Yerel Değişken: {function}()",
                description=f"{function}() içinde atanıp hiç okunmayan {len(items)} değişken: {_listing(names)}.",
                severity=Severity.LOW, file_path=path,
                recommendation="Değişkeni silin; yalnızca yan etki için çağrılıyorsa dönüş değerini atamayın veya '_' önekini kullanın.",
                rule='unused-variable', function=function, start_line=items[0].line,
                variables=[{'name': i.name, 'line': i.line} for i in items], **extra))
        return results
