import ast
import textwrap

from src.languages import python_usage as pu


def tree(code: str) -> ast.Module:
    return ast.parse(textwrap.dedent(code))


def unused(code: str):
    source = textwrap.dedent(code)
    return [(i.name, i.line) for i in pu.find_unused_imports(ast.parse(source), source.splitlines())]


# ---- kullanılmayan import ---------------------------------------------------

def test_unused_import_basic_and_attribute_use():
    code = """
        import os
        import sys
        from pathlib import Path, PurePath
        print(sys.argv, Path('.'))
    """
    assert unused(code) == [('os', 2), ('PurePath', 4)]


def test_dotted_import_binds_first_part_and_alias_binds_alias():
    code = """
        import os.path
        import numpy as np
        import json as j
        os.path.join('a')
        j.dumps(1)
    """
    assert unused(code) == [('np', 3)]


def test_future_star_all_and_explicit_reexport_are_skipped():
    code = """
        from __future__ import annotations
        from m import *
        from a import b as b
        import c as c
        from d import used_in_all
        from e import unused_one
        __all__ = ['used_in_all']
    """
    assert unused(code) == [('unused_one', 7)]


def test_string_annotation_counts_as_use():
    code = """
        from typing import TYPE_CHECKING
        if TYPE_CHECKING:
            from models import User
            from models import Order
        def f(u: "User") -> None:
            return None
    """
    assert unused(code) == [('Order', 5)]


def test_noqa_comment_suppresses_only_matching_codes():
    code = """
        import a  # noqa
        import b  # noqa: F401
        import c  # noqa: E501
        import d
    """
    assert unused(code) == [('c', 4), ('d', 5)]


def test_function_level_import_is_checked_inside_that_function_only():
    code = """
        import os
        def f():
            import json
            return 1
        def g():
            return json
    """
    assert unused(code) == [('os', 2), ('json', 4)]


def test_import_used_only_in_decorator_or_default_counts():
    code = """
        import functools
        import time
        @functools.lru_cache
        def f(t=time.time):
            return 1
    """
    assert unused(code) == []


# ---- ulaşılamaz kod -----------------------------------------------------------

def unreachable(code: str):
    return [(u.line, u.after) for u in pu.find_unreachable(tree(code))]


def test_unreachable_after_return_raise_break_continue():
    code = """
        def f():
            return 1
            x = 2
        def g():
            raise ValueError()
            y = 3
        def h(items):
            for i in items:
                break
                z = 4
            for i in items:
                continue
                w = 5
    """
    assert unreachable(code) == [(4, 'return'), (7, 'raise'), (11, 'break'), (14, 'continue')]


def test_reachable_code_and_generator_marker_are_not_reported():
    code = """
        def f(a):
            if a:
                return 1
            x = 2
            return x
        def gen():
            raise RuntimeError()
            yield
    """
    assert unreachable(code) == []


def test_unreachable_in_else_and_finally_blocks():
    code = """
        def f(a):
            try:
                pass
            finally:
                return 1
                print('x')
    """
    assert unreachable(code) == [(7, 'return')]


# ---- kullanılmayan yerel değişken -------------------------------------------------

def variables(code: str):
    return [(v.function, v.name, v.line) for v in pu.find_unused_variables(tree(code))]


def test_unused_local_variable_and_used_variable():
    code = """
        def f():
            used = 1
            unused = 2
            return used
    """
    assert variables(code) == [('f', 'unused', 4)]


def test_unused_tuple_literal_with_and_except_bindings():
    code = """
        def f(path):
            a, b = 1, 2
            with open(path) as handle:
                pass
            try:
                pass
            except ValueError as error:
                pass
            return a
    """
    assert variables(code) == [('f', 'b', 3), ('f', 'handle', 4), ('f', 'error', 8)]


def test_variables_that_are_not_reported():
    code = """
        def f(items):
            _ignored = 1
            counter = 0
            counter += 1
            captured = 5
            def inner():
                return captured
            first, second = items          # bilinmeyen uzunluklu açma
            for index in items:
                pass
            global shared
            shared = 3
            return inner
        def g():
            value = 1
            return locals()
    """
    assert variables(code) == []


# ---- sihirli sayı ---------------------------------------------------------------------

def magic(code: str):
    return [m.value for m in pu.find_magic_numbers(tree(code))]


def test_magic_numbers_flagged_in_function_bodies_only():
    code = """
        LIMIT = 500
        def f(x, y=42):
            if x > 30:
                return x * 7
            return x + 0.25
    """
    assert magic(code) == [30, 7, 0.25]


def test_allowed_named_indexed_and_data_constants_are_not_magic():
    code = """
        def f(items):
            retries = 3
            timeout: int = 60
            a = items[5]
            b = items[1:9]
            table = [10, 20, 30]
            mapping = {1: 100, 2: 200}
            call(wait=15)
            x = len(items) % 2 + 1 - 1 + 0
            neg = -1
            return x
    """
    assert magic(code) == []


def test_positional_call_arguments_and_negative_numbers_are_magic():
    code = """
        def f():
            sleep(12)
            return -45
    """
    assert magic(code) == [12, -45]


def test_magic_number_in_nested_function_is_counted_once():
    code = """
        def outer():
            def inner():
                return 99
            return inner
    """
    assert magic(code) == [99]
