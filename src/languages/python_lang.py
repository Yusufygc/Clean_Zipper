import ast
import io
import re
import tokenize
from typing import Iterator, List, Optional, Union

from src.languages.base import ClassInfo, FunctionInfo, ImportRef, LanguageSupport, SourceMetrics, StrippedSource

FunctionNode = Union[ast.FunctionDef, ast.AsyncFunctionDef]
_FUNCTION_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)
_LOOPS = (ast.For, ast.AsyncFor, ast.While)

# Sözdizimi hatalı dosyalarda içe aktarmaları yine de yakalamak için yedek.
_IMPORT_LINE = re.compile(r'^\s*import\s+([a-zA-Z0-9_.,\s]+)')
_FROM_LINE = re.compile(r'^\s*from\s+([a-zA-Z0-9_.]+)\s+import')


class CyclomaticComplexityVisitor(ast.NodeVisitor):
    """Siklomatik karmaşıklık; yaygın standart olan `radon` kurallarıyla uyumlu.

    +1: if/elif, üçlü ifade, for/while (+1 `else` varsa), her except (+1 try-`else` varsa), assert,
    kapsamlamanın her `for` ve `if`'i, her `case` (joker `_` hariç); mantıksal operatör: işlenen sayısı - 1.
    """
    def __init__(self):
        self.complexity = 1

    def visit_If(self, node):
        self.complexity += 1
        self.generic_visit(node)

    visit_IfExp = visit_If

    def visit_Assert(self, node):
        self.complexity += 1                          # radon gibi: assert içindeki ifadeler ayrıca sayılmaz

    def visit_For(self, node):
        self.complexity += 1 + bool(node.orelse)
        self.generic_visit(node)

    visit_AsyncFor = visit_While = visit_For

    def visit_Try(self, node):
        self.complexity += len(node.handlers) + bool(node.orelse)
        self.generic_visit(node)

    visit_TryStar = visit_Try

    def visit_comprehension(self, node):
        self.complexity += 1 + len(node.ifs)
        self.generic_visit(node)

    def visit_BoolOp(self, node):
        # Her 'and' veya 'or' ifadesi yeni bir karar noktası (dallanma) yaratır
        self.complexity += len(node.values) - 1
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        """İç içe fonksiyon / sınıf kendi bulgusunu üretir; üst fonksiyona katılmaz (çift sayım olmaz)."""

    visit_AsyncFunctionDef = visit_ClassDef = visit_FunctionDef

    def visit_Match(self, node):
        wildcard = any(isinstance(case.pattern, ast.MatchAs) and case.pattern.pattern is None
                       and case.pattern.name is None and case.guard is None for case in node.cases)
        self.complexity += max(0, len(node.cases) - wildcard)
        self.generic_visit(node)


class StructureMetricsVisitor:
    """Tek geçişte bilişsel karmaşıklık (SonarSource kuralları) ve iç içe blok derinliği.

    Bilişsel: if/üçlü/for/while/except/match +1 ve iç içe seviye kadar ek; `elif`/`else` +1 (ek yok);
    her mantıksal operatör dizisi +1; iç içe fonksiyon ve lambda iç içe seviyeyi artırır; özyineleme +1.
    Derinlik: if/for/while/try/match blokları (`elif` bir alt seviye sayılmaz, `with` sayılmaz).
    """

    def __init__(self, function: FunctionNode):
        self.function = function
        self.cognitive = 0
        self.max_nesting = 0

    def run(self) -> 'StructureMetricsVisitor':
        self._block(self.function.body, nesting=0, depth=0)
        if self._is_recursive():
            self.cognitive += 1
        return self

    # ---- ifadeler ------------------------------------------------------------

    def _block(self, statements, nesting: int, depth: int):
        for statement in statements:
            self._statement(statement, nesting, depth)

    def _statement(self, node: ast.stmt, nesting: int, depth: int):
        if isinstance(node, ast.If):
            self._if(node, nesting, depth, is_elif=False)
        elif isinstance(node, _LOOPS):
            self._loop(node, nesting, depth)
        elif isinstance(node, ast.Try) or type(node).__name__ == 'TryStar':
            self._try(node, nesting, depth)
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            self._with(node, nesting, depth)
        elif hasattr(ast, 'Match') and isinstance(node, ast.Match):
            self._match(node, nesting, depth)
        elif isinstance(node, _FUNCTION_NODES + (ast.ClassDef,)):
            self._block(node.body, nesting + 1, depth)               # iç içe fonksiyon/sınıf: seviye artar
        else:
            self._expression(node, nesting)

    def _loop(self, node, nesting: int, depth: int):
        self._structural(nesting, depth)
        self._expression(node.test if isinstance(node, ast.While) else node.iter, nesting)
        self._block(node.body, nesting + 1, depth + 1)
        self._block(node.orelse, nesting + 1, depth + 1)

    def _try(self, node, nesting: int, depth: int):
        self._touch(depth + 1)
        self._block(node.body, nesting, depth + 1)
        for handler in node.handlers:
            self.cognitive += 1 + nesting
            if handler.type is not None:
                self._expression(handler.type, nesting)
            self._block(handler.body, nesting + 1, depth + 1)
        self._block(node.orelse, nesting, depth + 1)
        self._block(node.finalbody, nesting, depth + 1)

    def _with(self, node, nesting: int, depth: int):
        for item in node.items:
            self._expression(item.context_expr, nesting)
        self._block(node.body, nesting, depth)

    def _match(self, node, nesting: int, depth: int):
        self._structural(nesting, depth)
        self._expression(node.subject, nesting)
        for case in node.cases:
            self._block(case.body, nesting + 1, depth + 1)

    def _if(self, node: ast.If, nesting: int, depth: int, is_elif: bool):
        if is_elif:
            self.cognitive += 1
            self._touch(depth + 1)
        else:
            self._structural(nesting, depth)
        self._expression(node.test, nesting)
        self._block(node.body, nesting + 1, depth + 1)
        orelse = node.orelse
        if len(orelse) == 1 and isinstance(orelse[0], ast.If):
            self._if(orelse[0], nesting, depth, is_elif=True)
        elif orelse:
            self.cognitive += 1
            self._block(orelse, nesting + 1, depth + 1)

    def _structural(self, nesting: int, depth: int):
        self.cognitive += 1 + nesting
        self._touch(depth + 1)

    def _touch(self, depth: int):
        self.max_nesting = max(self.max_nesting, depth)

    # ---- ifade ağaçları (üçlü, mantıksal operatör, lambda) -----------------------

    def _expression(self, node: ast.AST, nesting: int, parent_bool_op: Optional[ast.boolop] = None):
        if isinstance(node, ast.BoolOp):
            if type(node.op) is not type(parent_bool_op):            # parantezli aynı operatör ayrı dizi sayılmaz
                self.cognitive += 1
            for value in node.values:
                self._expression(value, nesting, node.op)
        elif isinstance(node, ast.IfExp):
            self.cognitive += 1 + nesting
            self._expression(node.test, nesting)
            self._expression(node.body, nesting + 1)
            self._expression(node.orelse, nesting + 1)
        elif isinstance(node, ast.Lambda):
            self._expression(node.body, nesting + 1)
        else:
            for child in self._expression_children(node):
                self._expression(child, nesting)

    @staticmethod
    def _expression_children(node: ast.AST) -> Iterator[ast.AST]:
        """İfade ağacında gezilecek çocuklar (deyimler hariç)."""
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.expr, ast.comprehension, ast.keyword, ast.arguments, ast.Starred)) \
                    or isinstance(child, ast.AST) and not isinstance(child, ast.stmt):
                yield child

    def _is_recursive(self) -> bool:
        name = self.function.name
        for node in ast.walk(self.function):
            if isinstance(node, ast.Call):
                target = node.func
                if isinstance(target, ast.Name) and target.id == name:
                    return True
                if isinstance(target, ast.Attribute) and target.attr == name \
                        and isinstance(target.value, ast.Name) and target.value.id in ('self', 'cls'):
                    return True
        return False


def count_parameters(function: FunctionNode) -> int:
    args = function.args
    names = [a.arg for a in args.posonlyargs + args.args + args.kwonlyargs]
    if args.vararg:
        names.append(args.vararg.arg)
    if args.kwarg:
        names.append(args.kwarg.arg)
    if names and names[0] in ('self', 'cls') and (args.posonlyargs + args.args):
        names = names[1:]
    return len(names)


def _is_type_checking(test: ast.expr) -> bool:
    return (isinstance(test, ast.Name) and test.id == 'TYPE_CHECKING')         or (isinstance(test, ast.Attribute) and test.attr == 'TYPE_CHECKING')


def _import_refs(node: ast.stmt) -> Iterator[ImportRef]:
    if isinstance(node, ast.Import):
        for alias in node.names:
            yield ImportRef(alias.name, 0, (), node.lineno)
    elif isinstance(node, ast.ImportFrom):
        names = tuple(alias.name for alias in node.names if alias.name != '*')
        yield ImportRef(node.module or '', node.level, names, node.lineno)


def _nested_blocks(node: ast.stmt) -> Iterator[List[ast.stmt]]:
    """Modül yüklenirken çalışabilecek iç ifade blokları (`if`/`try`/`with`/`for`/sınıf gövdeleri)."""
    if isinstance(node, ast.If) and _is_type_checking(node.test):
        yield node.orelse
        return
    for field_name in ('body', 'orelse', 'finalbody'):
        block = getattr(node, field_name, None)
        if isinstance(block, list):
            yield block
    for handler in getattr(node, 'handlers', ()):
        yield handler.body


def runtime_imports(statements: List[ast.stmt]) -> Iterator[ImportRef]:
    """Modül yüklenirken çalışan içe aktarmalar: fonksiyon gövdeleri ve `if TYPE_CHECKING:` blokları hariç."""
    for node in statements:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            yield from _import_refs(node)
        elif not isinstance(node, _FUNCTION_NODES):
            for block in _nested_blocks(node):
                yield from runtime_imports(block)


def _import_names(node: ast.AST) -> List[str]:
    """`import a.b` -> ['a.b']; `from x import y` -> ['x'] (göreli içe aktarmalar bu listeye girmez)."""
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
        return [node.module]
    return []


def _blank_span(text: str, start: int, end: int, targets) -> None:
    """`text[start:end]` aralığını (satır sonları hariç) her hedef listede boşlukla değiştirir."""
    for index in range(start, end):
        if text[index] != '\n':
            for target in targets:
                target[index] = ' '


class PythonLanguage(LanguageSupport):
    id = 'python'
    display_name = 'Python'
    extensions = ('.py',)
    approximate = False

    def analyze(self, text: str) -> SourceMetrics:
        lines = text.splitlines()
        blank = sum(1 for line in lines if not line.strip())
        comment = sum(1 for line in lines if line.strip().startswith('#'))
        metrics = SourceMetrics(
            language=self.id, total_lines=len(lines),
            code_lines=len(lines) - blank - comment, comment_lines=comment, blank_lines=blank,
        )
        try:
            tree = ast.parse(text)
        except (SyntaxError, ValueError, RecursionError):
            metrics.parse_ok = False
            metrics.imports = self._imports_from_lines(lines)
            return metrics

        metrics.import_refs = list(runtime_imports(tree.body))
        for node in ast.walk(tree):
            self._collect(metrics, node)
        return metrics

    def _collect(self, metrics: SourceMetrics, node: ast.AST) -> None:
        """Bir ast düğümünden işlev / sınıf / içe aktarma ölçümünü `metrics`e ekler."""
        if isinstance(node, _FUNCTION_NODES):
            metrics.functions.append(self._function_info(node))
        elif isinstance(node, ast.ClassDef):
            methods = sum(1 for item in node.body if isinstance(item, _FUNCTION_NODES))
            metrics.classes.append(ClassInfo(node.name, node.lineno, node.end_lineno or node.lineno, methods))
        else:
            metrics.imports.extend(_import_names(node))

    @staticmethod
    def _function_info(node: FunctionNode) -> FunctionInfo:
        cyclomatic = CyclomaticComplexityVisitor()
        for statement in node.body:
            cyclomatic.visit(statement)
        structure = StructureMetricsVisitor(node).run()
        return FunctionInfo(
            node.name, node.lineno, node.end_lineno or node.lineno, cyclomatic.complexity,
            params=count_parameters(node), max_nesting=structure.max_nesting, cognitive=structure.cognitive)

    def stripped(self, text: str) -> Optional[StrippedSource]:
        """`tokenize` ile: COMMENT jetonları (no_comments) ve COMMENT + STRING jetonları (clean) boşlukla değişir."""
        line_starts = [0] + [match.end() for match in re.finditer('\n', text)]
        no_comments = list(text)
        clean = list(text)
        try:
            for token in tokenize.generate_tokens(io.StringIO(text).readline):
                if token.type not in (tokenize.COMMENT, tokenize.STRING):
                    continue
                start = line_starts[token.start[0] - 1] + token.start[1]
                end = line_starts[token.end[0] - 1] + token.end[1]
                _blank_span(text, start, end, (no_comments, clean) if token.type == tokenize.COMMENT else (clean,))
        except (tokenize.TokenError, IndentationError, SyntaxError, IndexError):
            return None                                              # bozuk dosya: çağıran ham metinle devam eder
        return StrippedSource(''.join(no_comments), ''.join(clean))

    @staticmethod
    def _imports_from_lines(lines: List[str]) -> List[str]:
        found = []
        for line in lines:
            match = _IMPORT_LINE.match(line)
            if match:
                found.extend(part.strip().split(' ')[0] for part in match.group(1).split(',') if part.strip())
                continue
            match = _FROM_LINE.match(line)
            if match:
                found.append(match.group(1))
        return found
