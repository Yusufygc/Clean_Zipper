"""Dosya bağımlılık grafiği: içe aktarmaları proje dosyalarına çözümler, döngüleri (Tarjan SCC) bulur.

Python (mutlak + göreli) ve JS/TS (göreli + `@/`, `~/` takma adları) desteklenir. Projede karşılığı olmayan
(harici paket, standart kütüphane) içe aktarmalar grafiğe girmez.
"""
import posixpath
import sys
from collections import deque
from typing import Dict, Iterable, List, Optional, Set, Tuple

from src.languages.base import ImportRef

JS_EXTENSIONS = ('.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs', '.mts', '.cts')
_JS_SWAPS = {'.js': ('.ts', '.tsx'), '.jsx': ('.tsx',), '.mjs': ('.mts',), '.cjs': ('.cts',)}
_STDLIB = frozenset(getattr(sys, 'stdlib_module_names', ()))
Graph = Dict[str, Set[str]]
MAX_CYCLE_STARTS = 25            # çok büyük bileşenlerde en kısa döngü araması bu kadar düğümden başlar


def _directory(rel: str) -> str:
    return posixpath.dirname(rel)


# ---- Python -------------------------------------------------------------------------------------------

class PythonResolver:
    """`ImportRef` -> proje içi dosya yolları. Dosya `a/b.py` modül `a.b`, `a/b/__init__.py` paket `a.b`dir."""

    def __init__(self, files: Iterable[str]):
        self._files = set(files)
        self._by_tail: Dict[str, List[Tuple[str, str]]] = {}
        for rel in self._files:
            parts = self._module_parts(rel)
            for start in range(len(parts)):
                self._by_tail.setdefault('/'.join(parts[start:]), []).append(('/'.join(parts[:start]), rel))

    @staticmethod
    def _module_parts(rel: str) -> List[str]:
        parts = rel[:-3].split('/')
        return parts[:-1] if parts[-1] == '__init__' else parts

    def _exact(self, path: str) -> Optional[str]:
        """`path` yolundaki paket (`__init__.py`) veya modül (`.py`)."""
        for candidate in (f"{path}/__init__.py" if path else '__init__.py', f"{path}.py"):
            if candidate in self._files:
                return candidate
        return None

    def resolve(self, ref: ImportRef, importer: str) -> Set[str]:
        base = self._base(ref, importer)
        if base is None:
            return set()
        _, module_path = base
        module_file = self._exact(module_path)
        targets: Set[str] = set()
        for name in ref.names:
            submodule = self._exact(f"{module_path}/{name}" if module_path else name)
            if submodule:
                targets.add(submodule)
            elif module_file:
                targets.add(module_file)                                 # `name` bir öznitelik, modül yine de yüklenir
        if not ref.names and module_file:
            targets.add(module_file)
        targets.discard(importer)
        return targets

    def _base(self, ref: ImportRef, importer: str) -> Optional[Tuple[str, str]]:
        """(kaynak kök öneki, modülün kökten yolu) ya da çözülemezse None."""
        if ref.level > 0:
            return self._relative_base(ref, importer)
        return self._absolute_base(ref, importer) if ref.module else None

    @staticmethod
    def _relative_base(ref: ImportRef, importer: str) -> Optional[Tuple[str, str]]:
        directory = _directory(importer)
        for _ in range(ref.level - 1):
            if not directory:
                return None
            directory = _directory(directory)
        module = ref.module.replace('.', '/')
        return '', posixpath.join(directory, module) if module else directory

    def _absolute_base(self, ref: ImportRef, importer: str) -> Optional[Tuple[str, str]]:
        key = ref.module.replace('.', '/')
        importer_dir = _directory(importer)
        shadows_stdlib = ref.module.split('.')[0] in _STDLIB
        valid = [prefix for prefix, _ in self._by_tail.get(key, ())
                 if self._valid_prefix(prefix, importer_dir) and not (prefix and shadows_stdlib)]
        if not valid:
            return None
        prefix = min(valid)
        return prefix, f"{prefix}/{key}" if prefix else key

    @staticmethod
    def _valid_prefix(prefix: str, importer_dir: str) -> bool:
        """Kaynak kökü, içe aktaranın klasörü veya atasıdır (Python `sys.path[0]` anlambilimi)."""
        return prefix == '' or importer_dir == prefix or importer_dir.startswith(prefix + '/')


def python_graph(refs_by_file: Dict[str, List[ImportRef]]) -> Graph:
    resolver = PythonResolver(refs_by_file)
    graph: Graph = {rel: set() for rel in refs_by_file}
    for rel, refs in refs_by_file.items():
        for ref in refs:
            graph[rel] |= resolver.resolve(ref, rel)
    return graph


# ---- JS / TS --------------------------------------------------------------------------------------------

def resolve_js(spec: str, importer: str, files: Set[str]) -> Optional[str]:
    """Göreli (`./x`, `../y`) ve `@/`, `~/` belirteçlerini proje dosyasına çözer; harici paket veya yoksa None."""
    if spec.startswith('.'):
        bases = [posixpath.normpath(posixpath.join(_directory(importer), spec))]
    elif spec.startswith(('@/', '~/')):
        bases = [spec[2:], 'src/' + spec[2:]]
    else:
        return None
    for base in bases:
        if base.startswith('..'):
            continue
        found = _js_candidate(base, files)
        if found:
            return found
    return None


def _js_candidate(base: str, files: Set[str]) -> Optional[str]:
    root, ext = posixpath.splitext(base)
    candidates = [base] if ext in JS_EXTENSIONS else []
    candidates += [root + swap for swap in _JS_SWAPS.get(ext, ())]
    candidates += [base + e for e in JS_EXTENSIONS]
    candidates += [f"{base}/index{e}" for e in JS_EXTENSIONS]
    return next((c for c in candidates if c in files), None)


def js_graph(imports_by_file: Dict[str, Iterable[str]]) -> Graph:
    files = set(imports_by_file)
    graph: Graph = {rel: set() for rel in files}
    for rel, specs in imports_by_file.items():
        for spec in specs:
            target = resolve_js(spec, rel, files)
            if target and target != rel:
                graph[rel].add(target)
    return graph


# ---- döngüler ---------------------------------------------------------------------------------------------

class _Tarjan:
    """Yinelemeli Tarjan: derin zincirlerde özyineleme sınırına takılmaz."""

    def __init__(self, graph: Graph):
        self.graph = graph
        self.index_of: Dict[str, int] = {}
        self.low: Dict[str, int] = {}
        self.on_stack: Set[str] = set()
        self.stack: List[str] = []
        self.components: List[List[str]] = []

    def run(self) -> List[List[str]]:
        for root in sorted(self.graph):
            if root not in self.index_of:
                self._visit(root)
        return sorted(self.components, key=lambda c: (-len(c), c[0]))

    def _enter(self, node: str, work: list):
        self.index_of[node] = self.low[node] = len(self.index_of)
        self.stack.append(node)
        self.on_stack.add(node)
        work.append((node, iter(sorted(self.graph[node]))))

    def _visit(self, root: str):
        work: list = []
        self._enter(root, work)
        while work:
            node, neighbours = work[-1]
            if self._advance(node, neighbours, work):
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                self.low[parent] = min(self.low[parent], self.low[node])
            if self.low[node] == self.index_of[node]:
                self._close_component(node)

    def _advance(self, node: str, neighbours, work: list) -> bool:
        """Sıradaki ziyaret edilmemiş komşuya iner (True); komşular bittiyse False."""
        for neighbour in neighbours:
            if neighbour not in self.graph:
                continue
            if neighbour not in self.index_of:
                self._enter(neighbour, work)
                return True
            if neighbour in self.on_stack:
                self.low[node] = min(self.low[node], self.index_of[neighbour])
        return False

    def _close_component(self, node: str):
        component = []
        while True:
            member = self.stack.pop()
            self.on_stack.discard(member)
            component.append(member)
            if member == node:
                break
        if len(component) > 1:
            self.components.append(sorted(component))


def strongly_connected_components(graph: Graph) -> List[List[str]]:
    """Boyutu >= 2 olan güçlü bağlı bileşenler (döngü kümeleri); büyükten küçüğe, deterministik sıralı."""
    return _Tarjan(graph).run()


def _path_back(parents: Dict[str, str], last: str, start: str) -> List[str]:
    path = [last]
    while path[-1] != start:
        path.append(parents[path[-1]])
    return path[::-1]


def _cycle_through(graph: Graph, members: Set[str], start: str) -> Optional[List[str]]:
    """`start` düğümünden kendisine dönen en kısa yol (BFS); yoksa None."""
    parents: Dict[str, str] = {}
    queue = deque([start])
    while queue:
        node = queue.popleft()
        for neighbour in sorted(graph[node] & members):
            if neighbour == start:
                return _path_back(parents, node, start) + [start]
            if neighbour not in parents:
                parents[neighbour] = node
                queue.append(neighbour)
    return None


def shortest_cycle(graph: Graph, component: List[str]) -> List[str]:
    """Bileşendeki en kısa döngü (ilk ve son eleman aynı); çok büyük bileşenlerde ilk düğümlerden aranır."""
    members = set(component)
    best: List[str] = []
    for start in component[:MAX_CYCLE_STARTS]:
        cycle = _cycle_through(graph, members, start)
        if cycle and (not best or len(cycle) < len(best)):
            best = cycle
            if len(best) == 3:
                break
    return best
