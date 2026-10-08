"""Fonksiyon başına parametre sayısı, iç içe derinlik ve bilişsel karmaşıklık.

Beklenen değerler SonarSource bilişsel karmaşıklık kurallarıyla elle hesaplanmıştır.
"""
import sys
import textwrap

import pytest

from src.languages import default_languages
from src.languages.python_lang import PythonLanguage

sys.path.insert(0, __file__.rsplit("test_metrics.py", 1)[0])
import test_languages as samples  # noqa: E402  (aynı örnek kodlar)


def py(source):
    metrics = PythonLanguage().analyze(textwrap.dedent(source))
    return {f.name: f for f in metrics.functions}


# ---- Python (kesin) ------------------------------------------------------------------

def test_sonar_reference_example():
    f = py('''
        def f(a, b, c):
            if a:                       # +1
                for x in a:             # +2
                    if x:               # +3
                        pass
            elif b:                     # +1
                pass
            else:                       # +1
                pass
            return a and b or c         # +2
    ''')["f"]
    assert (f.cognitive, f.max_nesting, f.params) == (10, 3, 3)


def test_ternary_boolean_sequences_and_lambda():
    r = py('''
        def ternary(a): return 1 if a else 2                    # +1
        def one_sequence(a, b, c): return a and b and c         # +1
        def two_sequences(a, b, c): return a and b or c         # +2
        def grouped(a, b, c): return a and (b and c)            # +1 (parantezli aynı operatör ayrı dizi değil)
        def with_lambda(a): return lambda x: 1 if x else 0      # lambda gövdesi bir seviye içte: 1 + 1
    ''')
    assert (r["ternary"].cognitive, r["one_sequence"].cognitive, r["two_sequences"].cognitive,
            r["grouped"].cognitive, r["with_lambda"].cognitive) == (1, 1, 2, 1, 2)


def test_elif_chain_and_loop_else():
    r = py('''
        def chain(a):
            if a == 1:      # +1
                pass
            elif a == 2:    # +1
                pass
            elif a == 3:    # +1
                pass
            else:           # +1
                pass
        def loops(a):
            while a:        # +1
                a -= 1
            else:           # içerik seviyesi (ek artış yok)
                pass
    ''')
    assert r["chain"].cognitive == 4 and r["chain"].max_nesting == 1
    assert r["loops"].cognitive == 1


def test_try_except_and_match():
    r = py('''
        def guarded(a):
            try:                    # derinlik 1, bilişsel artış yok
                run()
            except ValueError:      # +1
                if a:               # +2
                    pass
            finally:
                pass
        def matcher(x):
            match x:                # +1
                case 1:
                    if x:           # +1 +1 (iç içe)
                        pass
    ''')
    assert (r["guarded"].cognitive, r["guarded"].max_nesting) == (3, 2)
    assert (r["matcher"].cognitive, r["matcher"].max_nesting) == (3, 2)


def test_nested_function_adds_a_nesting_level_and_with_is_not_a_block():
    r = py('''
        def outer(a):
            def inner(b):
                if b:               # +1 +1 (iç içe fonksiyon)
                    return 1
            with open(a) as f:      # blok sayılmaz
                if f:               # +1
                    pass
    ''')
    assert r["outer"].cognitive == 2 + 1
    assert r["inner"].cognitive == 1 and r["inner"].max_nesting == 1
    assert r["outer"].max_nesting == 1


def test_recursion_adds_one_and_methods_use_self():
    r = py('''
        def fact(n): return 1 if n <= 1 else n * fact(n - 1)    # üçlü +1, özyineleme +1
        class A:
            def walk(self, n): return self.walk(n - 1) if n else 0   # üçlü +1, özyineleme +1
    ''')
    assert r["fact"].cognitive == 2 and r["walk"].cognitive == 2


@pytest.mark.parametrize("signature,expected", [
    ("def f(): pass", 0),
    ("def f(a, b, c): pass", 3),
    ("def f(a, /, b, *, c, **kw): pass", 4),
    ("def f(*args, **kwargs): pass", 2),
    ("def f(self, a, b): pass", 2),                 # self hariç
    ("def f(cls): pass", 0),
    ("async def f(a, b=1, *c): pass", 3),
])
def test_python_parameter_counts(signature, expected):
    assert next(iter(py(signature).values())).params == expected


# ---- Brace dilleri (yaklaşık, örnek kodlarda elle hesaplanmış) -----------------------------

def metrics(language_id, source):
    return {f.name: f for f in default_languages.get(language_id).analyze(source).functions}


def triple(f):
    return (f.cognitive, f.max_nesting, f.params)


def test_csharp_java_c_cpp_samples():
    cs = metrics("csharp", samples.CSHARP)
    assert triple(cs["Process"]) == (7, 2, 2)          # if +1, && +1, foreach +2, else-if +1, || +1, ?: +1
    java = metrics("java", samples.JAVA)
    assert triple(java["run"]) == (5, 2, 1)            # for +1, if +2, switch +1, catch +1; `<? extends U>` tek parametre
    c = metrics("c", samples.C_SOURCE)
    assert triple(c["make"]) == (2, 1, 1) and triple(c["count"]) == (3, 1, 1)
    cpp = metrics("cpp", samples.CPP)
    assert triple(cpp["helper"]) == (3, 2, 1) and triple(cpp["set"]) == (1, 1, 1)


def test_javascript_typescript_samples():
    js = metrics("javascript", samples.JAVASCRIPT)
    assert triple(js["plain"]) == (3, 1, 2) and triple(js["arrow"]) == (3, 2, 1)
    ts = metrics("typescript", samples.TYPESCRIPT)
    assert triple(ts["f"]) == (1, 0, 2) and ts["onResize"].params == 1


def test_go_headers_with_semicolons_are_control_blocks():
    go = metrics("go", samples.GO)
    assert triple(go["Start"]) == (7, 3, 1)            # if +1, && +1, for +2, select +3
    extra = metrics("go", '''package main
func g(items []int) error {
	if err := load(); err != nil {
		return err
	}
	for i := 0; i < len(items); i++ {
		switch items[i] {
		case 1:
			if items[i] > 0 && ok {
			}
		}
	}
	return nil
}
''')
    assert triple(extra["g"]) == (1 + 1 + 2 + 3 + 1, 3, 1)


def test_rust_samples():
    rust = metrics("rust", samples.RUST)
    assert triple(rust["tick"]) == (4, 1, 0)           # if +1, && +1, || +1, else +1; &mut self sayılmaz
    assert triple(rust["go"]) == (1, 1, 1)             # match +1; `<'a>` jenerik, &self hariç
    assert rust["new"].params == 1


@pytest.mark.parametrize("language_id,source,expected", [
    ("csharp", "class A { void F(Dictionary<string, int> map, int x) { } }", 2),
    ("java", "class A { void f(Map<String, List<Integer>> a, int b) { } }", 2),
    ("c", "int f(void) { return 0; }", 0),
    ("c", "int f() { return 0; }", 0),
    ("javascript", "function f({a, b}, c) { }", 2),
    ("javascript", "function f(a = [1, 2], b) { }", 2),
    ("javascript", "const f = x => { return x; };", 1),
    ("javascript", "const f = () => { return 1; };", 0),
    ("go", "package p\nfunc f(a, b int, c string) {}", 3),
    ("rust", "fn f<F: Fn(i32)>(&self, x: F, y: u8) {}", 2),
    ("typescript", "function f(this: Window, a: number) { }", 1),
])
def test_parameter_counts_across_languages(language_id, source, expected):
    [function] = default_languages.get(language_id).analyze(source).functions
    assert function.params == expected


def test_control_flow_without_braces_is_counted_but_not_nested():
    f = metrics("c", "int f(int a) {\n  if (a) return 1;\n  for (;;) break;\n  return 0;\n}\n")["f"]
    assert f.cognitive == 2 and f.max_nesting == 0     # süslü parantezsiz yapılar iç içe sayılamaz (bilinen sınır)


# ---- stripped() ----------------------------------------------------------------------------

def test_python_stripped_blanks_comments_and_strings_keeping_length_and_lines():
    source = 'x = "a#b"  # note\ny = 2  \'\'\'multi\nline\'\'\'\n'
    stripped = PythonLanguage().stripped(source)
    assert len(stripped.clean) == len(stripped.no_comments) == len(source)
    assert '"a#b"' in stripped.no_comments and "note" not in stripped.no_comments
    assert "a#b" not in stripped.clean and "multi" not in stripped.clean
    assert stripped.clean.count("\n") == source.count("\n")


def test_python_stripped_returns_none_for_untokenizable_source():
    assert PythonLanguage().stripped("x = (1,\n") is None


def test_brace_stripped_normalises_newlines_and_hides_preprocessor():
    stripped = default_languages.get("c").stripped('#define X { \\\n 1 }\r\nint a = "s{"; // c\r\n')
    assert "\r" not in stripped.clean and "{" not in stripped.clean
    assert "s{" in stripped.no_comments and "// c" not in stripped.no_comments
