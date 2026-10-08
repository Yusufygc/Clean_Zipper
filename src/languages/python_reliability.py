"""Python için hata yönetimi ve üretim hijyeni taraması (`ast`, kesin).

Bulgular: çıplak / sessiz `except`, kodlamasız metin modunda dosya açma, saat dilimsiz `datetime`, sabit `DEBUG = True`
ve `print` çağrıları (`if __name__ == "__main__":` bloğu hariç).
"""
import ast
from dataclasses import dataclass, field
from typing import AbstractSet, List, Optional

_BROAD = frozenset({'Exception', 'BaseException'})
_SILENT = (ast.Pass, ast.Continue, ast.Break)


@dataclass
class PythonReliability:
    bare_excepts: List[int] = field(default_factory=list)          # çıplak `except:` (yeniden fırlatmayan)
    swallowed: List[int] = field(default_factory=list)             # `except Exception: pass` benzeri
    open_without_encoding: List[int] = field(default_factory=list)
    naive_datetimes: List[int] = field(default_factory=list)
    debug_flags: List[int] = field(default_factory=list)
    prints: List[int] = field(default_factory=list)


def analyze(tree: ast.Module, comment_lines: AbstractSet[int] = frozenset()) -> PythonReliability:
    """`comment_lines`: yorum içeren satır numaraları. Yorumla gerekçelendirilmiş sessiz `except` bulgu sayılmaz."""
    facts = PythonReliability()
    main_ranges = _main_block_ranges(tree)
    localized: set = set()                        # `datetime.now().astimezone()` saat dilimi ekler: naif sayılmaz
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            _check_handler(node, facts, comment_lines)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute) and node.func.attr == 'astimezone':
                localized.add(id(node.func.value))
            _check_call(node, facts, main_ranges, localized)
    facts.debug_flags = _debug_flags(tree)
    for values in vars(facts).values():
        values.sort()
    return facts


# ---- except -----------------------------------------------------------------------------------

def _is_broad(handler: ast.ExceptHandler) -> bool:
    kind = handler.type
    if isinstance(kind, ast.Name):
        return kind.id in _BROAD
    if isinstance(kind, ast.Tuple):
        return any(isinstance(e, ast.Name) and e.id in _BROAD for e in kind.elts)
    return False


def _is_silent_statement(statement: ast.stmt) -> bool:
    if isinstance(statement, _SILENT):
        return True
    if isinstance(statement, ast.Expr):
        return isinstance(statement.value, ast.Constant)               # `...` veya belge metni
    if isinstance(statement, ast.Return):
        return statement.value is None or (isinstance(statement.value, ast.Constant) and statement.value.value is None)
    return False                                  # `return False` / `return 0` bir geri dönüş değeri verir: yutma sayılmaz


def _reraises(handler: ast.ExceptHandler) -> bool:
    return any(isinstance(n, ast.Raise) for n in ast.walk(ast.Module(body=handler.body, type_ignores=[])))


def _check_handler(handler: ast.ExceptHandler, facts: PythonReliability, comment_lines: AbstractSet[int]):
    silent = all(_is_silent_statement(s) for s in handler.body)
    if handler.type is None:
        if not _reraises(handler):
            facts.bare_excepts.append(handler.lineno)
    elif _is_broad(handler) and silent:
        span = range(handler.lineno, (handler.end_lineno or handler.lineno) + 1)
        if not any(number in comment_lines for number in span):          # yorumla açıklanmış yutma bilinçlidir
            facts.swallowed.append(handler.lineno)


# ---- çağrılar ------------------------------------------------------------------------------------

def _check_call(call: ast.Call, facts: PythonReliability, main_ranges: List[range], localized: set):
    target = call.func
    if isinstance(target, ast.Name):
        _check_builtin_call(call, target.id, facts, main_ranges)
    elif isinstance(target, ast.Attribute):
        _check_method_call(call, target, facts, localized)


def _check_builtin_call(call: ast.Call, name: str, facts: PythonReliability, main_ranges: List[range]):
    if name == 'open' and _opens_text_without_encoding(call):
        facts.open_without_encoding.append(call.lineno)
    elif name == 'print' and not any(call.lineno in r for r in main_ranges):
        facts.prints.append(call.lineno)


def _check_method_call(call: ast.Call, target: ast.Attribute, facts: PythonReliability, localized: set):
    if target.attr in ('read_text', 'write_text'):
        if _text_io_without_encoding(call, target.attr):
            facts.open_without_encoding.append(call.lineno)
    elif id(call) not in localized and _is_naive_datetime(call, target):
        facts.naive_datetimes.append(call.lineno)


def _has_keyword(call: ast.Call, name: str) -> bool:
    return any(k.arg == name for k in call.keywords)


def _has_double_star(call: ast.Call) -> bool:
    return any(k.arg is None for k in call.keywords) or any(isinstance(a, ast.Starred) for a in call.args)


def _opens_text_without_encoding(call: ast.Call) -> bool:
    """`open(...)` metin kipinde ve kodlamasız. Kip bilinmiyorsa (değişken) veya `**kwargs` varsa False."""
    if _has_double_star(call) or _has_keyword(call, 'encoding') or len(call.args) >= 4:
        return False
    mode: Optional[ast.expr] = call.args[1] if len(call.args) > 1 else None
    for keyword in call.keywords:
        if keyword.arg == 'mode':
            mode = keyword.value
    if mode is None:
        return True
    return isinstance(mode, ast.Constant) and isinstance(mode.value, str) and 'b' not in mode.value


def _text_io_without_encoding(call: ast.Call, method: str) -> bool:
    if _has_double_star(call) or _has_keyword(call, 'encoding'):
        return False
    return len(call.args) < (1 if method == 'read_text' else 2)


def _is_naive_datetime(call: ast.Call, target: ast.Attribute) -> bool:
    """`datetime.now()` (saat dilimsiz), `datetime.utcnow()`, `datetime.today()`."""
    owner = target.value
    is_datetime = (isinstance(owner, ast.Name) and owner.id == 'datetime') \
        or (isinstance(owner, ast.Attribute) and owner.attr == 'datetime')
    if not is_datetime:
        return False
    if target.attr in ('utcnow', 'today'):
        return True
    return target.attr == 'now' and not call.args and not call.keywords


# ---- DEBUG bayrağı ve __main__ bloğu ----------------------------------------------------------------

def _debug_flags(tree: ast.Module) -> List[int]:
    found = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and node.value.value is True \
                and any(isinstance(t, ast.Name) and t.id == 'DEBUG' for t in node.targets):
            found.append(node.lineno)
    return found


def _main_block_ranges(tree: ast.Module) -> List[range]:
    ranges = []
    for node in tree.body:
        if isinstance(node, ast.If) and _is_main_guard(node.test):
            ranges.append(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    return ranges


def _is_main_guard(test: ast.expr) -> bool:
    if not (isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(test.ops[0], ast.Eq)):
        return False
    sides = [test.left] + test.comparators
    return any(isinstance(s, ast.Name) and s.id == '__name__' for s in sides) \
        and any(isinstance(s, ast.Constant) and s.value == '__main__' for s in sides)
