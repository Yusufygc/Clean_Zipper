"""Python için kullanım analizi (`ast`, kesin): kullanılmayan import, ulaşılamaz kod, kullanılmayan yerel değişken, sihirli sayı."""
import ast
import re
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Set, Tuple, Union

FunctionNode = Union[ast.FunctionDef, ast.AsyncFunctionDef]
_FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)
_SCOPES = _FUNCTIONS + (ast.Lambda, ast.ClassDef)
_TERMINATORS = (ast.Return, ast.Raise, ast.Break, ast.Continue)


@dataclass(frozen=True)
class UnusedImport:
    name: str       # bağlanan ad (`import a.b` -> 'a', `import x as y` -> 'y')
    line: int
    source: str     # kullanıcıya gösterilen ifade (`os.path`, `typing.List`)


@dataclass(frozen=True)
class UnreachableCode:
    line: int       # ulaşılamaz ilk ifadenin satırı
    after: str      # öncesindeki sonlandırıcı: return / raise / break / continue
    after_line: int


@dataclass(frozen=True)
class UnusedVariable:
    function: str
    name: str
    line: int


# ---- yardımcılar -----------------------------------------------------------------------

def _children(node: ast.AST) -> Iterator[ast.AST]:
    return ast.iter_child_nodes(node)


def _loaded_names(root: ast.AST) -> Set[str]:
    return {n.id for n in ast.walk(root) if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Load, ast.Del))}


def _annotation_roots(tree: ast.AST) -> Iterator[ast.AST]:
    for node in ast.walk(tree):
        if isinstance(node, _FUNCTIONS):
            args = node.args
            for arg in args.posonlyargs + args.args + args.kwonlyargs + [a for a in (args.vararg, args.kwarg) if a]:
                if arg.annotation is not None:
                    yield arg.annotation
            if node.returns is not None:
                yield node.returns
        elif isinstance(node, ast.AnnAssign):
            yield node.annotation


def _string_annotation_names(tree: ast.AST) -> Set[str]:
    """`x: "Foo"` / `List["Foo"]` gibi metin ek açıklamalarındaki adlar (TYPE_CHECKING importları için)."""
    names: Set[str] = set()
    for root in _annotation_roots(tree):
        for node in ast.walk(root):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                try:
                    names |= _loaded_names(ast.parse(node.value, mode='eval'))
                except (SyntaxError, ValueError):
                    continue
    return names


def _all_assignment(node: ast.AST) -> Optional[ast.expr]:
    """`__all__ = [...]` (veya `+=` / ek açıklamalı) atamasının değeri; başka düğümde None."""
    if isinstance(node, ast.Assign):
        targets, value = node.targets, node.value
    elif isinstance(node, (ast.AugAssign, ast.AnnAssign)):
        targets, value = [node.target], node.value
    else:
        return None
    named = any(isinstance(t, ast.Name) and t.id == '__all__' for t in targets)
    return value if named and isinstance(value, (ast.List, ast.Tuple, ast.Set)) else None


def _dunder_all(tree: ast.Module) -> Set[str]:
    names: Set[str] = set()
    for node in ast.walk(tree):
        value = _all_assignment(node)
        if value is not None:
            names |= {e.value for e in value.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)}
    return names


def _enclosing_functions(tree: ast.Module) -> Dict[ast.AST, Optional[ast.AST]]:
    """Her import düğümü için kapsayan fonksiyon (modül düzeyinde None)."""
    owner: Dict[ast.AST, Optional[ast.AST]] = {}

    def visit(node: ast.AST, function: Optional[ast.AST]):
        for child in _children(node):
            if isinstance(child, (ast.Import, ast.ImportFrom)):
                owner[child] = function
            visit(child, child if isinstance(child, _FUNCTIONS) else function)

    visit(tree, None)
    return owner


# ---- kullanılmayan import ------------------------------------------------------------------

_NOQA = re.compile(r'#\s*noqa\b(?!\s*:)|#\s*noqa\s*:[^#\n]*\bF401\b', re.IGNORECASE)


def find_unused_imports(tree: ast.Module, source_lines: Optional[List[str]] = None) -> List[UnusedImport]:
    """Hiçbir yerde okunmayan içe aktarmalar. Fonksiyon içi importlar yalnızca o fonksiyonda aranır.

    Atlananlar: `from __future__`, `*` importları, `import x as x` (açık yeniden dışa aktarım), `__all__` içindekiler
    ve satırında `# noqa` / `# noqa: F401` bulunanlar (`source_lines` verilirse). Ad tabanlıdır: aynı adlı bir
    yerel değişken/parametre kullanım sayılır, yani pyflakes'tan daha tutucudur (yanlış pozitif azdır).
    """
    exported = _dunder_all(tree)
    cache: Dict[ast.AST, Set[str]] = {}
    found: List[UnusedImport] = []
    for node, function in _enclosing_functions(tree).items():
        if not _is_ignored_import(node, source_lines):
            scope = function if function is not None else tree
            if scope not in cache:
                cache[scope] = _loaded_names(scope) | _string_annotation_names(scope) | exported
            found.extend(_unused_aliases(node, cache[scope]))
    return sorted(found, key=lambda item: item.line)


def _is_ignored_import(node: ast.AST, source_lines: Optional[List[str]]) -> bool:
    if isinstance(node, ast.ImportFrom) and (node.module == '__future__' or node.level == 0 and not node.module):
        return True
    return bool(source_lines and node.lineno <= len(source_lines) and _NOQA.search(source_lines[node.lineno - 1]))


def _unused_aliases(node: ast.AST, used: Set[str]) -> Iterator[UnusedImport]:
    module = ('.' * node.level + (node.module or '')) if isinstance(node, ast.ImportFrom) else ''
    separator = '' if module.endswith('.') or not module else '.'
    for alias in node.names:
        if alias.name == '*' or alias.asname == alias.name:              # `import x as x`: açık yeniden dışa aktarım
            continue
        bound = alias.asname or alias.name.split('.')[0]
        if bound not in used:
            yield UnusedImport(bound, node.lineno, f"{module}{separator}{alias.name}")


# ---- ulaşılamaz kod ----------------------------------------------------------------------------

def find_unreachable(tree: ast.Module) -> List[UnreachableCode]:
    """`return/raise/break/continue` sonrasında aynı blokta kalan ilk ifade (liste başına bir bulgu)."""
    found: List[UnreachableCode] = []
    for node in ast.walk(tree):
        for field in ('body', 'orelse', 'finalbody'):
            block = getattr(node, field, None)
            item = _first_unreachable(block) if isinstance(block, list) else None
            if item is not None:
                found.append(item)
    return sorted(found, key=lambda item: item.line)


def _first_unreachable(block: List[ast.stmt]) -> Optional[UnreachableCode]:
    for index, statement in enumerate(block[:-1]):
        if isinstance(statement, _TERMINATORS):
            following = block[index + 1]
            if _is_generator_marker(following):
                return None
            return UnreachableCode(following.lineno, type(statement).__name__.lower(), statement.lineno)
    return None


def _is_generator_marker(statement: ast.stmt) -> bool:
    """`raise X` / `return` sonrası `yield` fonksiyonu üreteç yapmak için kasıtlı bırakılır."""
    return isinstance(statement, ast.Expr) and isinstance(statement.value, (ast.Yield, ast.YieldFrom))


# ---- kullanılmayan yerel değişken -----------------------------------------------------------

def _own_statements(function: ast.AST) -> Iterator[ast.AST]:
    """Fonksiyonun kendi kapsamındaki düğümler (iç içe fonksiyon / sınıf / lambda gövdesine inilmez)."""
    stack = list(reversed(function.body))
    while stack:
        node = stack.pop()
        yield node
        if isinstance(node, _SCOPES):
            continue
        stack.extend(reversed(list(_children(node))))


def find_unused_variables(tree: ast.Module) -> List[UnusedVariable]:
    """`ad = değer`, `ad: T = değer`, `a, b = x, y`, `with ... as ad` ve `except E as ad` bağlamaları.

    Bilinmeyen uzunluklu açmalar (`a, b = f()`) ve `for` hedefleri kasıtlı atlanır (pyflakes ile aynı).
    """
    found: List[UnusedVariable] = []
    for function in ast.walk(tree):
        if isinstance(function, _FUNCTIONS):
            found.extend(_unused_in_function(function))
    return sorted(found, key=lambda item: item.line)


def _unused_in_function(function: FunctionNode) -> List[UnusedVariable]:
    used = _loaded_names(function)
    if 'locals' in used or 'vars' in used:
        return []
    skip = used | _declared_or_augmented(function)
    found: List[UnusedVariable] = []
    seen: Set[str] = set()
    for node in _own_statements(function):
        for name, line in _binding_names(node):
            if name not in seen and not name.startswith('_') and name not in skip:
                seen.add(name)
                found.append(UnusedVariable(function.name, name, line))
    return found


def _declared_or_augmented(function: FunctionNode) -> Set[str]:
    """`global`/`nonlocal` ile bildirilen ve `+=` ile okunan adlar (kullanılmış sayılır)."""
    names: Set[str] = set()
    for node in ast.walk(function):
        if isinstance(node, (ast.Global, ast.Nonlocal)):
            names.update(node.names)
        elif isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _is_literal_unpacking(target: ast.AST, value: ast.AST) -> bool:
    return isinstance(target, ast.Tuple) and isinstance(value, ast.Tuple) and len(target.elts) == len(value.elts)


def _assign_names(node: ast.Assign) -> Iterator[Tuple[str, int]]:
    for target in node.targets:
        if isinstance(target, ast.Name):
            yield target.id, target.lineno
        elif _is_literal_unpacking(target, node.value):                  # `a, b = x, y`
            for element in target.elts:
                if isinstance(element, ast.Name):
                    yield element.id, element.lineno


def _binding_names(node: ast.AST) -> Iterator[Tuple[str, int]]:
    if isinstance(node, ast.Assign):
        yield from _assign_names(node)
    elif isinstance(node, (ast.With, ast.AsyncWith)):
        for item in node.items:
            if isinstance(item.optional_vars, ast.Name):
                yield item.optional_vars.id, item.optional_vars.lineno
    elif isinstance(node, ast.AnnAssign) and node.value is not None and isinstance(node.target, ast.Name):
        yield node.target.id, node.lineno
    elif isinstance(node, ast.ExceptHandler) and node.name:
        yield node.name, node.lineno


# ---- sihirli sayı ---------------------------------------------------------------------------------

ALLOWED_NUMBERS = frozenset({0, 1, 2, -1, 0.0, 1.0, 0.5})


@dataclass(frozen=True)
class MagicNumber:
    value: float
    line: int


def find_magic_numbers(tree: ast.Module) -> List[MagicNumber]:
    """Fonksiyon gövdelerindeki adsız sayısal sabitler.

    Sayılmayanlar: {0, 1, 2, -1, 0.5}; `ad = 30` (adlandırılmış) ve `f(zaman_asimi=30)` (adlı argüman);
    indeks / dilim; liste, demet, küme, sözlük sabit verisi.
    """
    found: List[MagicNumber] = []
    for function in ast.walk(tree):
        if isinstance(function, _FUNCTIONS):
            for statement in function.body:
                _collect_magic(statement, found)
    unique = {(item.value, item.line): item for item in found}           # iç içe fonksiyonlar aynı sabiti iki kez görür
    return sorted(unique.values(), key=lambda item: item.line)


def _numeric(node: ast.AST) -> Optional[float]:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        inner = _numeric(node.operand)
        if inner is not None:
            return -inner if isinstance(node.op, ast.USub) else inner
    return None


def _magic_in_assignment(node: ast.AST, found: List[MagicNumber]):
    if node.value is not None and _numeric(node.value) is None:          # `ad = 30` adlandırılmış sabittir
        _collect_magic(node.value, found)


def _magic_in_subscript(node: ast.Subscript, found: List[MagicNumber]):
    _collect_magic(node.value, found)                                    # indeks / dilim sabitleri sayılmaz


def _magic_in_collection(node: ast.AST, found: List[MagicNumber]):
    for child in _children(node):                                        # sabit veri tabloları sayılmaz
        if _numeric(child) is None:
            _collect_magic(child, found)


def _magic_in_call(node: ast.Call, found: List[MagicNumber]):
    _collect_magic(node.func, found)
    for argument in node.args:
        _collect_magic(argument, found)
    for keyword in node.keywords:                                        # `f(zaman_asimi=30)` adlı argüman
        if _numeric(keyword.value) is None:
            _collect_magic(keyword.value, found)


_MAGIC_HANDLERS = (
    ((ast.Assign, ast.AnnAssign), _magic_in_assignment),
    ((ast.Subscript,), _magic_in_subscript),
    ((ast.List, ast.Tuple, ast.Set, ast.Dict), _magic_in_collection),
    ((ast.Call,), _magic_in_call),
)


def _collect_magic(node: ast.AST, found: List[MagicNumber]):
    value = _numeric(node)
    if value is not None:
        if value not in ALLOWED_NUMBERS:
            found.append(MagicNumber(value, node.lineno))
        return
    if isinstance(node, _SCOPES):
        return                                                           # iç içe fonksiyonu dış `walk` ayrıca ziyaret eder
    for types, handler in _MAGIC_HANDLERS:
        if isinstance(node, types):
            handler(node, found)
            return
    for child in _children(node):
        _collect_magic(child, found)
