from pathlib import Path

from src.analyzers.code_complexity_analyzer import CodeComplexityAnalyzer
from src.analyzers.dead_weight_analyzer import DeadWeightAnalyzer
from src.analyzers.duplicate_finder import DuplicateFinder
from src.analyzers.empty_folder_finder import EmptyFolderFinder
from src.analyzers.security_analyzer import SecurityLeakAnalyzer
from src.analyzers.size_analyzer import SizeAnalyzer
from src.analyzers.structure_analyzer import StructureAnalyzer
from src.analyzers.type_analyzer import TypeAnalyzer
from src.core.project_index import ProjectIndex
from src.models.analysis_models import Severity


def write(path: Path, content="x", encoding="utf-8"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode(encoding) if isinstance(content, str) else content)
    return path


def titles(results):
    return sorted(r.title for r in results)


# ---- Size / Type / Structure / Empty -----------------------------------

def test_size_analyzer_reports_total_without_reclaimable_and_large_files(tmp_path):
    write(tmp_path / "big.bin", b"a" * 2048)
    write(tmp_path / "small.txt", "hi")
    results = SizeAnalyzer(large_file_threshold_mb=1 / 1024).analyze(ProjectIndex.build(tmp_path))
    total = next(r for r in results if r.metadata["kind"] == "total_size")
    assert total.size_impact is None and total.metadata["total_bytes"] == 2050
    large = [r for r in results if r.metadata["kind"] == "large_file"]
    assert [r.file_path.name for r in large] == ["big.bin"]


def test_type_analyzer_top_five_by_count(tmp_path):
    for ext, n in [(".py", 3), (".txt", 2), (".md", 1), (".js", 1), (".c", 1), (".h", 1)]:
        for i in range(n):
            write(tmp_path / f"f{i}{ext}")
    results = TypeAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert len(results) == 5
    assert results[0].title == "Dosya turu: .py" and results[0].description == "3 adet dosya"


def test_structure_analyzer_flags_only_deeper_than_ten(tmp_path):
    write(tmp_path.joinpath(*["d"] * 10) / "f.txt")
    assert StructureAnalyzer().analyze(ProjectIndex.build(tmp_path)) == []
    write(tmp_path.joinpath(*["d"] * 11) / "f.txt")
    results = StructureAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert titles(results) == ["Derin klasor yapisi: 11 seviye"]


def test_empty_folder_finder(tmp_path):
    (tmp_path / "empty").mkdir()
    write(tmp_path / "full" / "a.txt")
    write(tmp_path / "wrapper" / "venv" / "x.py")
    results = EmptyFolderFinder().analyze(ProjectIndex.build(tmp_path))
    assert titles(results) == ["Bos klasor: empty"]
    assert results[0].metadata["kind"] == "empty_dir"


# ---- Duplicates -------------------------------------------------------------

def test_duplicate_finder_groups_identical_content(tmp_path):
    write(tmp_path / "a" / "one.bin", b"Z" * 2048)
    write(tmp_path / "b" / "two.bin", b"Z" * 2048)
    results = DuplicateFinder().analyze(ProjectIndex.build(tmp_path))
    assert len(results) == 1
    r = results[0]
    assert r.size_impact == 2048 and r.metadata["reclaimable"] is True
    assert [p.name for p in r.metadata["paths"]] == ["one.bin", "two.bin"]
    assert r.file_path.name == "one.bin"


def test_duplicate_finder_ignores_same_size_different_content(tmp_path):
    write(tmp_path / "one.bin", b"A" * 2048)
    write(tmp_path / "two.bin", b"B" * 2048)
    assert DuplicateFinder().analyze(ProjectIndex.build(tmp_path)) == []


def test_duplicate_finder_separates_files_that_differ_after_first_64kb(tmp_path):
    head = b"H" * (64 * 1024)
    write(tmp_path / "x1.bin", head + b"tail-1")
    write(tmp_path / "x2.bin", head + b"tail-2")
    write(tmp_path / "x3.bin", head + b"tail-1")
    results = DuplicateFinder().analyze(ProjectIndex.build(tmp_path))
    assert len(results) == 1
    assert [p.name for p in results[0].metadata["paths"]] == ["x1.bin", "x3.bin"]


def test_duplicate_finder_skips_small_files(tmp_path):
    write(tmp_path / "a.txt", "same")
    write(tmp_path / "b.txt", "same")
    assert DuplicateFinder().analyze(ProjectIndex.build(tmp_path)) == []


# ---- Security -------------------------------------------------------------------

# Kaynak satırının kendisi sızıntı olarak işaretlenmesin diye parçalanmış.
LEAK = 'api_' + 'key = "ABC' + 'DEFGH12345678"\n'


def test_security_flags_sensitive_file_names_as_critical(tmp_path):
    write(tmp_path / ".env", "SECRET=1")
    results = SecurityLeakAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert [(r.severity, r.file_path.name) for r in results] == [(Severity.CRITICAL, ".env")]


def test_security_finds_secret_with_line_number(tmp_path):
    write(tmp_path / "cfg.py", "x = 1\n" + LEAK)
    results = SecurityLeakAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert len(results) == 1 and "Satır 2" in results[0].description
    assert results[0].severity == Severity.HIGH


def test_security_scans_cp1254_files_that_used_to_be_skipped_as_binary(tmp_path):
    write(tmp_path / "ayar.py", "# şifre ayarları: öğrenci çalışması\n" + LEAK, encoding="cp1254")
    results = SecurityLeakAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert len(results) == 1


def test_security_skips_binary_files(tmp_path):
    write(tmp_path / "blob.dat", b"\x00\x01" + LEAK.encode())
    assert SecurityLeakAnalyzer().analyze(ProjectIndex.build(tmp_path)) == []


def test_security_detects_database_urls(tmp_path):
    write(tmp_path / "db.py", 'URL = "post' + 'gres://user:pw@host/db"\n')
    results = SecurityLeakAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert len(results) == 1 and "Veritabanı" in results[0].description


# ---- Dead weight -------------------------------------------------------------------

def test_dead_weight_reports_unused_requirement(tmp_path):
    write(tmp_path / "requirements.txt", "pathspec>=0.11\nnumpy==1.0\nPillow\n")
    write(tmp_path / "app.py", "import pathspec\nfrom PIL import Image\n")
    results = DeadWeightAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert titles(results) == ["Kullanılmayan Kütüphane Tespit Edildi: numpy"]


def test_dead_weight_without_requirements_gives_info(tmp_path):
    write(tmp_path / "app.py", "import os\n")
    results = DeadWeightAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert [r.severity for r in results] == [Severity.INFO]


def test_dead_weight_ignores_imports_in_excluded_dirs(tmp_path):
    write(tmp_path / "requirements.txt", "numpy\n")
    write(tmp_path / "app.py", "x = 1\n")
    write(tmp_path / "venv" / "lib.py", "import numpy\n")
    results = DeadWeightAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert len(results) == 1


# ---- Complexity -----------------------------------------------------------------------

def branchy(n):
    body = "\n".join(f"    if x == {i}:\n        y = {i}" for i in range(n))
    return f"def f(x):\n    y = 0\n{body}\n    return y\n"


def test_complexity_flags_function_over_limit_only(tmp_path):
    write(tmp_path / "ok.py", branchy(9))        # 1 + 9 = 10 -> limit içinde
    write(tmp_path / "bad.py", branchy(10))      # 1 + 10 = 11
    results = CodeComplexityAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert [(r.file_path.name, r.severity) for r in results] == [("bad.py", Severity.MEDIUM)]
    assert "11" in results[0].description


def test_complexity_flags_god_class_and_bloated_file(tmp_path):
    methods = "".join(f"    def m{i}(self):\n        pass\n" for i in range(13))
    write(tmp_path / "god.py", f"class God:\n{methods}")
    write(tmp_path / "long.py", "x = 1\n" * 401)
    results = CodeComplexityAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert sorted((r.file_path.name, r.severity) for r in results) == [
        ("god.py", Severity.HIGH), ("long.py", Severity.HIGH)]


def test_complexity_skips_broken_python(tmp_path):
    write(tmp_path / "broken.py", "def (:\n")
    assert CodeComplexityAnalyzer().analyze(ProjectIndex.build(tmp_path)) == []


def test_complexity_reads_utf8_bom_files(tmp_path):
    write(tmp_path / "bom.py", b"\xef\xbb\xbf" + branchy(10).encode())
    results = CodeComplexityAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert len(results) == 1


# ---- Dil istatistikleri -------------------------------------------------------------------

def test_language_stats_aggregates_per_language_sorted_by_code_lines(tmp_path):
    from src.analyzers.language_stats_analyzer import LanguageStatsAnalyzer
    write(tmp_path / "a.py", "# yorum\nx = 1\n\ny = 2\n")
    write(tmp_path / "b.py", "z = 3\n")
    write(tmp_path / "Main.java", "class A {\n  // c\n  void m() {}\n  int x;\n}\n")
    write(tmp_path / "notes.txt", "yok sayılır\n")
    write(tmp_path / "app.min.js", "var a=1;")
    results = LanguageStatsAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert [(r.title, r.severity) for r in results] == [("Dil: Java", Severity.INFO), ("Dil: Python", Severity.INFO)]
    by_lang = {r.metadata["language"]: r.metadata for r in results}
    assert set(by_lang) == {"python", "java"}                       # .txt ve .min.js sayılmaz
    py = by_lang["python"]
    assert (py["files"], py["total_lines"], py["code_lines"], py["comment_lines"], py["blank_lines"]) == (2, 5, 3, 1, 1)
    assert by_lang["java"]["approximate"] is True and by_lang["python"]["approximate"] is False
    codes = [r.metadata["code_lines"] for r in results]
    assert codes == sorted(codes, reverse=True)
