import ast
import textwrap

from src.languages.base import ImportRef
from src.languages.import_graph import (PythonResolver, js_graph, python_graph, resolve_js, shortest_cycle,
                                        strongly_connected_components)
from src.languages.python_lang import runtime_imports


def refs(code: str):
    return list(runtime_imports(ast.parse(textwrap.dedent(code)).body))


# ---- çalışma zamanı importları -----------------------------------------------------------

def test_runtime_imports_skip_function_bodies_and_type_checking():
    code = """
        import os
        from typing import TYPE_CHECKING
        from . import sibling
        from ..pkg.mod import a, b
        if TYPE_CHECKING:
            from models import Hidden
        else:
            import fallback
        def f():
            import lazy
        try:
            import optional
        except ImportError:
            optional = None
        class C:
            import in_class
    """
    got = {(r.module, r.level, r.names) for r in refs(code)}
    assert got == {('os', 0, ()), ('typing', 0, ('TYPE_CHECKING',)), ('', 1, ('sibling',)),
                   ('pkg.mod', 2, ('a', 'b')), ('fallback', 0, ()), ('optional', 0, ()), ('in_class', 0, ())}


# ---- Python çözümleme -----------------------------------------------------------------------

FILES = ['main.py', 'pkg/__init__.py', 'pkg/a.py', 'pkg/b.py', 'pkg/sub/__init__.py', 'pkg/sub/c.py',
         'src/core/x.py', 'src/core/y.py', 'utils/logging.py']


def resolve(ref, importer):
    return PythonResolver(FILES).resolve(ref, importer)


def test_absolute_import_of_module_and_package():
    assert resolve(ImportRef('pkg.a', 0, (), 1), 'main.py') == {'pkg/a.py'}
    assert resolve(ImportRef('pkg', 0, (), 1), 'main.py') == {'pkg/__init__.py'}


def test_from_import_prefers_submodule_over_package_attribute():
    assert resolve(ImportRef('pkg', 0, ('a', 'Thing'), 1), 'main.py') == {'pkg/a.py', 'pkg/__init__.py'}
    assert resolve(ImportRef('pkg.sub', 0, ('c',), 1), 'main.py') == {'pkg/sub/c.py'}


def test_relative_imports():
    assert resolve(ImportRef('', 1, ('b',), 1), 'pkg/a.py') == {'pkg/b.py'}
    assert resolve(ImportRef('a', 1, ('X',), 1), 'pkg/b.py') == {'pkg/a.py'}
    assert resolve(ImportRef('a', 2, ('X',), 1), 'pkg/sub/c.py') == {'pkg/a.py'}
    assert resolve(ImportRef('', 3, ('x',), 1), 'pkg/a.py') == set()


def test_source_root_prefix_must_be_ancestor_of_importer():
    assert resolve(ImportRef('core.y', 0, (), 1), 'src/core/x.py') == {'src/core/y.py'}
    assert resolve(ImportRef('core.y', 0, (), 1), 'main.py') == set()


def test_stdlib_name_is_not_resolved_to_nested_project_file():
    assert resolve(ImportRef('logging', 0, (), 1), 'utils/other.py') == set()
    assert PythonResolver(FILES + ['logging.py']).resolve(ImportRef('logging', 0, (), 1), 'main.py') == {'logging.py'}


def test_external_import_and_self_import_are_ignored():
    assert resolve(ImportRef('numpy', 0, (), 1), 'main.py') == set()
    assert resolve(ImportRef('pkg.a', 0, (), 1), 'pkg/a.py') == set()


# ---- döngüler ------------------------------------------------------------------------------------

def test_python_graph_and_scc():
    graph = python_graph({
        'pkg/__init__.py': [], 'pkg/a.py': [ImportRef('', 1, ('b',), 1)], 'pkg/b.py': [ImportRef('', 1, ('c',), 1)],
        'pkg/c.py': [ImportRef('', 1, ('a',), 1)], 'pkg/d.py': [ImportRef('', 1, ('a',), 1)],
    })
    assert strongly_connected_components(graph) == [['pkg/a.py', 'pkg/b.py', 'pkg/c.py']]
    assert shortest_cycle(graph, ['pkg/a.py', 'pkg/b.py', 'pkg/c.py']) == [
        'pkg/a.py', 'pkg/b.py', 'pkg/c.py', 'pkg/a.py']


def test_scc_ignores_dag_and_returns_largest_first():
    graph = {'a': {'b'}, 'b': {'a'}, 'c': {'d'}, 'd': {'e'}, 'e': {'c'}, 'f': {'a'}, 'g': set()}
    assert strongly_connected_components(graph) == [['c', 'd', 'e'], ['a', 'b']]


def test_shortest_cycle_prefers_two_node_cycle():
    graph = {'a': {'b', 'c'}, 'b': {'a'}, 'c': {'d'}, 'd': {'a'}}
    assert shortest_cycle(graph, ['a', 'b', 'c', 'd']) == ['a', 'b', 'a']


def test_deep_chain_does_not_hit_recursion_limit():
    graph = {f"n{i}": {f"n{i + 1}"} for i in range(5000)}
    graph['n5000'] = {'n0'}
    (component,) = strongly_connected_components(graph)
    assert len(component) == 5001


# ---- JS / TS ----------------------------------------------------------------------------------------

JS_FILES = {'src/a.ts', 'src/b.tsx', 'src/lib/index.ts', 'src/util.js', 'lib/x.ts', 'components/Button.tsx'}


def test_resolve_js_relative_extension_and_index():
    assert resolve_js('./b', 'src/a.ts', JS_FILES) == 'src/b.tsx'
    assert resolve_js('./lib', 'src/a.ts', JS_FILES) == 'src/lib/index.ts'
    assert resolve_js('../lib/x', 'src/a.ts', JS_FILES) == 'lib/x.ts'
    assert resolve_js('./util.js', 'src/a.ts', JS_FILES) == 'src/util.js'


def test_resolve_js_typescript_js_extension_swap_and_aliases():
    assert resolve_js('./a.js', 'src/b.tsx', JS_FILES) == 'src/a.ts'
    assert resolve_js('@/components/Button', 'src/a.ts', JS_FILES) == 'components/Button.tsx'
    assert resolve_js('@/lib/x', 'src/a.ts', JS_FILES) == 'lib/x.ts'
    assert resolve_js('@/util', 'src/a.ts', JS_FILES) == 'src/util.js'


def test_resolve_js_external_and_escaping_paths_are_none():
    assert resolve_js('react', 'src/a.ts', JS_FILES) is None
    assert resolve_js('../../outside', 'src/a.ts', JS_FILES) is None
    assert resolve_js('./missing', 'src/a.ts', JS_FILES) is None


def test_js_graph_builds_cycle():
    graph = js_graph({'a.ts': ['./b'], 'b.ts': ['./a', 'react'], 'c.ts': ['./a']})
    assert strongly_connected_components(graph) == [['a.ts', 'b.ts']]
