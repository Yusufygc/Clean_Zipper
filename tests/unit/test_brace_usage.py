import textwrap

from src.languages import brace_usage as bu
from src.languages.catalog import default_languages


def stripped(language: str, code: str):
    text = textwrap.dedent(code)
    return text, default_languages.get(language).stripped(text)


def unused(language: str, code: str):
    text, source = stripped(language, code)
    return [(i.name, i.line) for i in bu.find_unused_imports(language, source.no_comments, text)]


def unreachable(language: str, code: str):
    text, source = stripped(language, code)
    return [(u.line, u.after) for u in bu.find_unreachable(source.clean, source.no_comments)]


# ---- JS / TS importları ---------------------------------------------------------------

def test_js_imports_default_named_alias_namespace():
    code = """
        import Foo from './foo';
        import { a, b as c, d } from './mod';
        import * as ns from 'ns';
        import Other, { e } from 'other';
        import './side-effect';
        console.log(Foo, a, c, ns, e);
    """
    assert unused('javascript', code) == [('d', 3), ('Other', 5)]


def test_js_multiline_named_import_and_property_access_is_not_use():
    code = """
        import {
          used,
          dead,
        } from './mod';
        const x = obj.dead;
        used();
    """
    assert unused('javascript', code) == [('dead', 2)]


def test_ts_type_import_and_react_jsx_are_handled():
    code = """
        import type { Props } from './types';
        import React from 'react';
        import { Button } from './button';
        export const A = (p: Props) => <Button />;
    """
    assert unused('typescript', code) == []


def test_js_name_used_only_inside_template_literal_counts():
    code = """
        import { fmt } from './fmt';
        const s = `value: ${fmt(1)}`;
    """
    assert unused('javascript', code) == []


def test_js_commented_import_is_ignored():
    code = """
        // import Gone from './gone';
        import Kept from './kept';
        Kept();
    """
    assert unused('javascript', code) == []


# ---- Java --------------------------------------------------------------------------------

def test_java_unused_import_wildcard_skipped_and_javadoc_use_counts():
    code = """
        import java.util.List;
        import java.util.Map;
        import java.io.*;
        import static java.lang.Math.max;
        import java.util.Set;

        /** Bkz. {@link Set} */
        class A {
            List<String> names;
            int m(int a, int b) { return max(a, b); }
        }
    """
    assert unused('java', code) == [('Map', 3)]


def test_unsupported_language_returns_nothing():
    assert bu.find_unused_imports('go', 'import "fmt"', 'import "fmt"') == []


# ---- ulaşılamaz kod -------------------------------------------------------------------------

def test_js_statement_after_return_is_unreachable():
    code = """
        function f() {
          return 1;
          console.log('never');
        }
    """
    assert unreachable('javascript', code) == [(4, 'return')]


def test_conditional_return_and_closing_brace_are_reachable():
    code = """
        function f(a) {
          if (a) return 1;
          doWork();
          if (a) {
            return 2;
          }
          switch (a) {
            case 1: return 3;
            case 2: break;
            default: return 4;
          }
          for (;;) { break; }
          return 5;
        }
    """
    assert unreachable('javascript', code) == []


def test_c_preprocessor_branches_are_not_unreachable():
    code = """
        int f(void) {
        #if A
          return 1;
        #else
          return 2;
        #endif
        }
    """
    assert unreachable('c', code) == []


def test_java_break_then_statement_and_throw():
    code = """
        class A {
          void m(int[] xs) {
            for (int x : xs) {
              break;
              use(x);
            }
            throw new RuntimeException();
            cleanup();
          }
        }
    """
    assert unreachable('java', code) == [(6, 'break'), (9, 'throw')]


def test_jsx_return_with_entity_semicolon_is_not_a_false_positive():
    code = """
        export default function Page() {
          return (
            <div>
              <p>CV&apos;ler</p>
            </div>
          );
        }
        export const other = 1;
    """
    assert unreachable('typescript', code) == []


def test_hoisted_function_declaration_after_return_is_reachable():
    code = """
        function f() {
          return helper();
          function helper() { return 1; }
        }
    """
    assert unreachable('javascript', code) == []


# ---- sihirli sayı -----------------------------------------------------------------------------

def magic(language: str, code: str, ranges):
    _, source = stripped(language, code)
    return [m.value for m in bu.find_magic_numbers(source.clean, ranges)]


def test_brace_magic_numbers_skip_declarations_indexes_and_lists():
    code = """
        function f(x) {
          const LIMIT = 500;
          let retries = 3;
          const a = x[5];
          const t = [10, 20, 30, 40];
          call({ wait: 15 });
          if (x > 30) return x * 7;
          return x + 0.25;
        }
    """
    assert magic('javascript', code, [(1, 9)]) == [30, 7, 0.25]


def test_brace_magic_numbers_ignore_lines_outside_functions_and_allowed_values():
    code = """
        const TOP = 99;
        function f(x) {
          return x + 1 + 2 - 1 + 0;
        }
    """
    assert magic('javascript', code, [(2, 4)]) == []


def test_hex_and_suffixed_numbers_are_parsed():
    code = """
        int f(int x) {
          return x & 0xFF + 1000L + 2.5f;
        }
    """
    assert magic('java', code, [(1, 3)]) == [255, 1000, 2.5]
