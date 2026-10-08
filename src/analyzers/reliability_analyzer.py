import ast
from collections import Counter
from pathlib import Path
from typing import Dict, List

from src.core.base_analyzer import BaseAnalyzer
from src.core.path_rules import is_test_path
from src.core.project_index import FileEntry, ProjectIndex
from src.core.registry import register_analyzer
from src.languages import brace_reliability, parse_file, python_reliability
from src.languages.base import SourceMetrics
from src.languages.registry import get_stripped
from src.languages.todo_markers import TodoItem, find_todos
from src.models.analysis_models import AnalysisResult, Severity

MAX_LISTED_LINES = 10
MAX_TODO_ITEMS = 200
TOP_TODO_FILES = 5

# kural kimliği -> (başlık, öncelik, öneri)
RULES = {
    'bare-except': ("Çıplak except (tüm hataları ve KeyboardInterrupt'ı yakalar)", Severity.HIGH,
                    "Yakalanacak hata türünü belirtin (ör. `except ValueError`); gerçekten gerekiyorsa loglayıp `raise` ile yeniden fırlatın."),
    'swallowed-exception': ("Hata sessizce yutuluyor (except Exception: pass)", Severity.MEDIUM,
                            "Hatayı loglayın (`logger.exception`), daha dar bir tür yakalayın veya yeniden fırlatın."),
    'empty-catch': ("Boş catch bloğu: hata yutuluyor", Severity.MEDIUM,
                    "Hatayı loglayın veya işleyin; bilerek yutuyorsanız nedenini yorumla açıklayın."),
    'open-without-encoding': ("Metin dosyası kodlama belirtilmeden açılıyor", Severity.MEDIUM,
                              "`encoding='utf-8'` verin; yoksa Windows'ta sistem kodlamasına (cp1254/cp1252) bağımlı olur."),
    'naive-datetime': ("Saat dilimsiz datetime (now/utcnow/today)", Severity.LOW,
                       "`datetime.now(timezone.utc)` gibi saat dilimli değerler kullanın."),
    'debug-flag': ("Sabit DEBUG = True", Severity.MEDIUM,
                   "Hata ayıklama bayrağını ortam değişkeninden okuyun; üretimde kapalı olmalı."),
    'debugger-statement': ("debugger ifadesi bırakılmış", Severity.MEDIUM,
                           "`debugger;` satırlarını üretim koduna göndermeyin."),
    'print-density': ("Günlükleme yerine çok sayıda konsol çıktısı", Severity.LOW,
                      "Konsol çıktısını günlükleme kütüphanesiyle (logging / winston ...) ve seviyelerle değiştirin."),
}


@register_analyzer
class ReliabilityAnalyzer(BaseAnalyzer):
    """Hata yönetimi ve üretim hijyeni: yutulan hatalar, kodlamasız dosya açma, saat dilimsiz tarih, DEBUG, konsol çıktısı.

    Python `ast` ile kesindir; diğer diller sözcük tabanlıdır (`approximate`). Kural başına dosya başına tek bulgu.
    Test dosyaları kurallara girmez. Ayrıca projede tek bir BİLGİ bulgusu olarak TODO/FIXME/HACK/XXX envanteri çıkar.
    """

    def __init__(self, priority: int = 35):
        super().__init__(priority)

    @property
    def name(self) -> str:
        return "Güvenilirlik ve Üretim Hijyeni Analizörü"

    @property
    def category(self) -> str:
        return "reliability"

    def analyze(self, index: ProjectIndex) -> List[AnalysisResult]:
        results: List[AnalysisResult] = []
        todos: Dict[str, List[TodoItem]] = {}
        for entry in index.files:
            metrics = parse_file(index, entry)
            if metrics is None:
                continue
            stripped = get_stripped(index, entry)
            if stripped is None:
                continue
            raw = index.read_text(entry) or ''
            if len(raw) != len(stripped.no_comments):
                raw = raw.replace('\r\n', '\n').replace('\r', '\n')       # brace dilleri satır sonunu normalleştirir
            found = find_todos(raw, stripped.no_comments)
            if found:
                todos[entry.rel] = found
            if not is_test_path(entry.rel):
                facts = self._facts(index, entry, metrics, stripped, raw)
                results.extend(self._findings(entry.path, metrics, facts))
        if todos:
            results.append(self._todo_summary(todos))
        return results

    # ---- olgular: kural kimliği -> satırlar ----------------------------------------------------------

    def _facts(self, index: ProjectIndex, entry: FileEntry, metrics: SourceMetrics, stripped,
               raw: str) -> Dict[str, List[int]]:
        if metrics.language == 'python':
            return self._python_facts(raw, metrics, stripped.no_comments)
        clean = stripped.clean
        return {
            'empty-catch': brace_reliability.find_empty_catches(metrics.language, clean, raw),
            'debugger-statement': brace_reliability.find_debugger(metrics.language, clean),
            'print-density': brace_reliability.find_prints(metrics.language, clean),
        }

    @staticmethod
    def _python_facts(raw: str, metrics: SourceMetrics, no_comments: str) -> Dict[str, List[int]]:
        if not metrics.parse_ok:
            return {}
        try:
            tree = ast.parse(raw)
        except (SyntaxError, ValueError, RecursionError):
            return {}
        commented = {number for number, (before, after)
                     in enumerate(zip(raw.split('\n'), no_comments.split('\n')), start=1) if before != after}
        facts = python_reliability.analyze(tree, commented)
        return {
            'bare-except': facts.bare_excepts, 'swallowed-exception': facts.swallowed,
            'open-without-encoding': facts.open_without_encoding, 'naive-datetime': facts.naive_datetimes,
            'debug-flag': facts.debug_flags, 'print-density': facts.prints,
        }

    # ---- bulgu üretimi ---------------------------------------------------------------------------------

    def _findings(self, path: Path, metrics: SourceMetrics, facts: Dict[str, List[int]]) -> List[AnalysisResult]:
        results = []
        for rule, lines in facts.items():
            if rule == 'print-density' and len(lines) <= self.thresholds.print_calls:
                continue
            if lines:
                results.append(self._finding(path, metrics, rule, lines))
        return results

    def _finding(self, path: Path, metrics: SourceMetrics, rule: str, lines: List[int]) -> AnalysisResult:
        title, severity, advice = RULES[rule]
        shown = ", ".join(str(n) for n in lines[:MAX_LISTED_LINES])
        more = f" ... (+{len(lines) - MAX_LISTED_LINES})" if len(lines) > MAX_LISTED_LINES else ""
        limit = f" (Limit: {self.thresholds.print_calls})" if rule == 'print-density' else ""
        return self._create_result(
            title=f"{title}: {path.name}",
            description=f"{title}{limit}. {len(lines)} yerde, satır: {shown}{more}.",
            severity=severity, file_path=path, recommendation=advice,
            rule=rule, lines=lines, count=len(lines), language=metrics.language, approximate=metrics.approximate)

    def _todo_summary(self, todos: Dict[str, List[TodoItem]]) -> AnalysisResult:
        counts = Counter(item.marker for items in todos.values() for item in items)
        total = sum(counts.values())
        top = sorted(((rel, len(items)) for rel, items in todos.items()), key=lambda x: (-x[1], x[0]))[:TOP_TODO_FILES]
        items = [{'path': rel, 'line': i.line, 'marker': i.marker, 'text': i.text}
                 for rel, found in sorted(todos.items()) for i in found][:MAX_TODO_ITEMS]
        by_marker = ", ".join(f"{marker} {n}" for marker, n in counts.most_common())
        return self._create_result(
            title=f"TODO/FIXME Envanteri: {total} işaret",
            description=f"{len(todos)} dosyada {total} işaret ({by_marker}). En çok: "
                        + ", ".join(f"{rel} ({n})" for rel, n in top) + ".",
            severity=Severity.INFO,
            rule='todo-inventory', total=total, by_marker=dict(counts), files=len(todos), top_files=top,
            items=items, truncated=total > MAX_TODO_ITEMS, approximate=False)
