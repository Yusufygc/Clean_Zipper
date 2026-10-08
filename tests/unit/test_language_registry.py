import logging
from pathlib import Path

from src.core.project_index import ProjectIndex
from src.languages import default_languages, parse_file
from src.languages.base import LanguageSupport, SourceMetrics
from src.languages.python_lang import PythonLanguage
from src.languages.registry import LanguageRegistry, is_generated


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def metrics_for(tmp_path, name, content):
    write(tmp_path / name, content)
    index = ProjectIndex.build(tmp_path)
    entry = next(f for f in index.files if f.rel == name)
    return parse_file(index, entry)


# ---- Python ----------------------------------------------------------------

def test_python_functions_classes_and_lines(tmp_path):
    src = (
        "# başlık\n"
        "\n"
        "class A:\n"
        "    def one(self):\n"
        "        if True:\n"
        "            return 1\n"
        "    async def two(self):\n"
        "        for _ in []:\n"
        "            pass\n"
        "\n"
        "def top(x):\n"
        "    return x and 1 or 2\n"
    )
    m = metrics_for(tmp_path, "m.py", src)
    assert (m.language, m.approximate, m.parse_ok) == ("python", False, True)
    assert (m.total_lines, m.blank_lines, m.comment_lines, m.code_lines) == (12, 2, 1, 9)
    assert [(c.name, c.method_count, c.start_line, c.end_line) for c in m.classes] == [("A", 2, 3, 9)]
    complexity = {f.name: f.complexity for f in m.functions}
    assert complexity == {"one": 2, "two": 2, "top": 3}     # async metot artık sayılıyor
    assert {f.name: f.lines for f in m.functions}["one"] == 3


def test_python_imports_come_from_ast_not_comments_or_strings(tmp_path):
    src = (
        "import os, sys.path\n"
        "from a.b import c\n"
        "from . import local\n"
        "# import commented\n"
        'text = """\nimport inside_string\n"""\n'
        "def f():\n"
        "    import lazy\n"
    )
    m = metrics_for(tmp_path, "m.py", src)
    assert sorted(m.imports) == ["a.b", "lazy", "os", "sys.path"]


def test_python_syntax_error_keeps_line_counts_and_regex_imports(tmp_path):
    m = metrics_for(tmp_path, "bad.py", "import numpy\nfrom pandas import x\ndef (:\n")
    assert m.parse_ok is False
    assert m.functions == [] and m.classes == []
    assert sorted(m.imports) == ["numpy", "pandas"]
    assert m.total_lines == 3


# ---- Registry / parse_file ----------------------------------------------------

def test_unknown_extension_and_binary_return_none(tmp_path):
    write(tmp_path / "notes.txt", "x")
    (tmp_path / "bin.py").write_bytes(b"\x00\x01\x02")
    index = ProjectIndex.build(tmp_path)
    assert all(parse_file(index, e) is None for e in index.files)


def test_generated_files_are_skipped(tmp_path):
    for name in ("app.min.py", "x_pb2.py", "form_ui.py", "res_rc.py"):
        write(tmp_path / name, "def f():\n    pass\n")
    index = ProjectIndex.build(tmp_path)
    assert all(parse_file(index, e) is None for e in index.files)
    assert is_generated("Foo.Designer.cs") and is_generated("types.D.TS") and not is_generated("main.py")


class CountingLanguage(LanguageSupport):
    id = "counting"
    display_name = "Counting"
    extensions = (".cnt",)

    def __init__(self):
        self.calls = 0

    def analyze(self, text):
        self.calls += 1
        return SourceMetrics("counting", 1, 1, 0, 0)


def test_parse_file_is_memoized_per_index(tmp_path):
    write(tmp_path / "a.cnt", "x")
    registry = LanguageRegistry()
    lang = registry.register(CountingLanguage())
    index = ProjectIndex.build(tmp_path)
    entry = index.files[0]
    first = parse_file(index, entry, registry)
    second = parse_file(index, entry, registry)
    assert first is second and lang.calls == 1
    assert parse_file(ProjectIndex.build(tmp_path), entry, registry) is not first   # yeni indeks, yeni önbellek


def test_analyzer_crash_is_isolated_and_logged(tmp_path, caplog):
    class Boom(CountingLanguage):
        def analyze(self, text):
            raise RuntimeError("patladı")

    write(tmp_path / "a.cnt", "x")
    registry = LanguageRegistry()
    registry.register(Boom())
    index = ProjectIndex.build(tmp_path)
    with caplog.at_level(logging.WARNING):
        assert parse_file(index, index.files[0], registry) is None
    assert "a.cnt" in caplog.text


def test_refine_can_redirect_to_another_language(tmp_path):
    class Redirect(CountingLanguage):
        id, extensions = "first", (".dual",)

        def refine(self, text):
            return "second"

    registry = LanguageRegistry()
    registry.register(Redirect())
    second = CountingLanguage()
    second.id = "second"
    second.extensions = ()
    registry.register(second)
    write(tmp_path / "a.dual", "x")
    index = ProjectIndex.build(tmp_path)
    parse_file(index, index.files[0], registry)
    assert second.calls == 1


def test_default_registry_has_python():
    assert isinstance(default_languages.for_extension(".PY"), PythonLanguage)


def test_minified_bundles_are_skipped_by_line_shape(tmp_path):
    from src.languages.registry import looks_minified
    bundle = "function a(){" + "if(x){y()}" * 800 + "}"          # tek satır, 8 KB+
    write(tmp_path / "chunk.js", bundle)
    write(tmp_path / "normal.js", "function a() {\n  if (x) { y(); }\n}\n" * 200)
    index = ProjectIndex.build(tmp_path)
    results = {e.rel: parse_file(index, e) for e in index.files}
    assert results["chunk.js"] is None and results["normal.js"] is not None
    assert looks_minified(bundle) and not looks_minified("kısa\nmetin\n")


def test_build_output_dirs_are_not_indexed(tmp_path):
    write(tmp_path / ".next" / "server" / "a.js", "x")
    write(tmp_path / "coverage" / "lcov.js", "x")
    write(tmp_path / "src" / "a.js", "x")
    assert [f.rel for f in ProjectIndex.build(tmp_path).files] == ["src/a.js"]
