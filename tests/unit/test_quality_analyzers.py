import dataclasses
from pathlib import Path

from src.analyzers.clone_analyzer import CloneAnalyzer
from src.analyzers.code_complexity_analyzer import CodeComplexityAnalyzer
from src.analyzers.dead_code_analyzer import DeadCodeAnalyzer
from src.analyzers.magic_number_analyzer import MagicNumberAnalyzer
from src.core.path_rules import is_test_path
from src.core.project_index import ProjectIndex
from src.core.thresholds import QualityThresholds
from src.models.analysis_models import Severity
from src.services.project_service import ProjectService


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def run(analyzer, root: Path):
    return analyzer.analyze(ProjectIndex.build(root))


def by_rule(results, rule):
    return [r for r in results if r.metadata["rule"] == rule]


# ---- yol kuralları -----------------------------------------------------------------

def test_is_test_path_covers_folders_and_naming_conventions():
    positives = ["tests/a.py", "src/__tests__/x.js", "test_models.py", "pkg/models_test.go", "a/b.spec.ts",
                 "web/button.test.jsx", "UserServiceTests.cs", "e2e/login.py"]
    negatives = ["src/models.py", "latest.py", "contest/main.py", "src/attestation.py", "protest.js"]
    assert all(is_test_path(p) for p in positives)
    assert not any(is_test_path(p) for p in negatives)


# ---- DeadCodeAnalyzer ------------------------------------------------------------------

def test_dead_code_reports_unused_import_once_per_file_with_details(tmp_path):
    write(tmp_path / "a.py", "import os\nimport sys\n\nprint(sys.argv)\n")
    (result,) = run(DeadCodeAnalyzer(), tmp_path)
    assert result.metadata["rule"] == "unused-import" and result.severity == Severity.LOW
    assert result.category == "deadcode" and result.metadata["approximate"] is False
    assert result.metadata["imports"] == [{"name": "os", "line": 1, "source": "os"}]
    assert result.file_path.name == "a.py"


def test_dead_code_skips_package_init_and_unparsable_files(tmp_path):
    write(tmp_path / "pkg" / "__init__.py", "from .core import Thing\n")
    write(tmp_path / "broken.py", "import os\ndef (:\n")
    assert run(DeadCodeAnalyzer(), tmp_path) == []


def test_dead_code_unreachable_and_unused_variable(tmp_path):
    write(tmp_path / "m.py", "def f():\n    value = 1\n    return 2\n    print('x')\n")
    results = run(DeadCodeAnalyzer(), tmp_path)
    assert sorted(r.metadata["rule"] for r in results) == ["unreachable-code", "unused-variable"]
    unreachable = by_rule(results, "unreachable-code")[0]
    assert unreachable.severity == Severity.MEDIUM and unreachable.metadata["start_line"] == 4
    variable = by_rule(results, "unused-variable")[0]
    assert variable.metadata["function"] == "f" and variable.metadata["variables"] == [{"name": "value", "line": 2}]


def test_dead_code_javascript_is_marked_approximate(tmp_path):
    write(tmp_path / "app.js",
          "import { used, dead } from './mod';\nfunction f() {\n  return used();\n  cleanup();\n}\n")
    results = run(DeadCodeAnalyzer(), tmp_path)
    assert sorted(r.metadata["rule"] for r in results) == ["unreachable-code", "unused-import"]
    assert all(r.metadata["approximate"] and r.metadata["language"] == "javascript" for r in results)
    assert by_rule(results, "unreachable-code")[0].severity == Severity.LOW


def test_dead_code_ignores_unsupported_and_go_files(tmp_path):
    write(tmp_path / "main.go", 'package main\nimport "fmt"\nfunc f() int {\n  return 1\n  fmt.Println()\n}\n')
    write(tmp_path / "notes.txt", "import os\n")
    assert run(DeadCodeAnalyzer(), tmp_path) == []


# ---- MagicNumberAnalyzer ------------------------------------------------------------------

MAGIC_SOURCE = "def f(x):\n" + "".join(f"    x = x + {n}\n" for n in range(10, 22)) + "    return x\n"


def test_magic_numbers_reported_above_threshold_with_top_values(tmp_path):
    write(tmp_path / "calc.py", MAGIC_SOURCE)
    (result,) = run(MagicNumberAnalyzer(), tmp_path)
    assert result.metadata["rule"] == "magic-numbers" and result.severity == Severity.LOW
    assert result.metadata["count"] == 12 and result.metadata["first_lines"][0] == 2
    assert len(result.metadata["top_values"]) == 5


def test_magic_numbers_threshold_is_configurable_and_boundary_is_exclusive(tmp_path):
    write(tmp_path / "calc.py", MAGIC_SOURCE)
    analyzer = MagicNumberAnalyzer()
    analyzer.thresholds = QualityThresholds(magic_numbers=12)
    assert run(analyzer, tmp_path) == []
    analyzer.thresholds = QualityThresholds(magic_numbers=11)
    assert len(run(analyzer, tmp_path)) == 1


def test_magic_numbers_skip_test_files(tmp_path):
    write(tmp_path / "tests" / "test_calc.py", MAGIC_SOURCE)
    write(tmp_path / "calc_test.py", MAGIC_SOURCE)
    assert run(MagicNumberAnalyzer(), tmp_path) == []


def test_magic_numbers_in_javascript_files(tmp_path):
    body = "".join(f"  total = total + {n};\n" for n in range(10, 22))
    write(tmp_path / "calc.js", "function f(total) {\n" + body + "  return total;\n}\n")
    (result,) = run(MagicNumberAnalyzer(), tmp_path)
    assert result.metadata["language"] == "javascript" and result.metadata["approximate"] is True
    assert result.metadata["count"] == 12


# ---- CloneAnalyzer -------------------------------------------------------------------------

def block(prefix: str, count: int) -> str:
    return "".join(f"    value_{prefix}_{i} = compute_something(argument_{i}, constant_value_{i})\n" for i in range(count))


SHARED = block("shared", 10)


def test_clone_analyzer_reports_group_and_summary(tmp_path):
    write(tmp_path / "a.py", "def a():\n    first_unique_a = 1\n" + SHARED + "    return first_unique_a\n")
    write(tmp_path / "b.py", "def b():\n    first_unique_b = 2\n" + SHARED + "    return first_unique_b\n")
    results = run(CloneAnalyzer(), tmp_path)
    (clone,) = by_rule(results, "code-clone")
    assert clone.category == "duplicate" and clone.severity == Severity.LOW      # 10 satır < 20
    assert clone.metadata["lines"] == 10 and clone.metadata["copies"] == 2
    assert [(loc["path"], loc["start_line"], loc["end_line"]) for loc in clone.metadata["locations"]] == [
        ("a.py", 3, 12), ("b.py", 3, 12)]
    (summary,) = by_rule(results, "clone-summary")
    assert summary.severity == Severity.INFO and summary.metadata["groups"] == 1
    assert summary.metadata["duplicated_lines"] == 10


def test_long_clone_is_medium_severity(tmp_path):
    shared = block("long", 24)
    write(tmp_path / "a.py", "def a():\n    unique_a = 1\n" + shared + "    return unique_a\n")
    write(tmp_path / "b.py", "def b():\n    unique_b = 2\n" + shared + "    return unique_b\n")
    (clone,) = by_rule(run(CloneAnalyzer(), tmp_path), "code-clone")
    assert clone.severity == Severity.MEDIUM and clone.metadata["lines"] == 24


def test_clone_analyzer_ignores_comment_only_differences_but_not_value_differences(tmp_path):
    commented = SHARED.replace("    value_shared_0", "    # kopya\n    value_shared_0")
    write(tmp_path / "a.py", "def a():\n    unique_a = 1\n" + SHARED + "    return unique_a\n")
    write(tmp_path / "b.py", "def b():\n    unique_b = 2\n" + commented + "    return unique_b\n")
    assert len(by_rule(run(CloneAnalyzer(), tmp_path), "code-clone")) == 1
    changed = SHARED.replace("constant_value_5", "constant_value_X")
    write(tmp_path / "b.py", "def b():\n    unique_b = 2\n" + changed + "    return unique_b\n")
    assert by_rule(run(CloneAnalyzer(), tmp_path), "code-clone") == []


def test_identical_files_are_left_to_duplicate_finder(tmp_path):
    content = "def a():\n    unique_a = 1\n" + SHARED + "    return unique_a\n"
    write(tmp_path / "a.py", content)
    write(tmp_path / "b.py", content)
    assert run(CloneAnalyzer(), tmp_path) == []


def test_clone_window_is_configurable(tmp_path):
    short = block("tiny", 5)
    write(tmp_path / "a.py", "def a():\n    unique_a = 1\n" + short + "    return unique_a\n")
    write(tmp_path / "b.py", "def b():\n    unique_b = 2\n" + short + "    return unique_b\n")
    assert run(CloneAnalyzer(), tmp_path) == []
    analyzer = CloneAnalyzer()
    analyzer.thresholds = QualityThresholds(clone_lines=5)
    assert len(by_rule(run(analyzer, tmp_path), "code-clone")) == 1


def test_clone_across_languages_files_is_found_in_javascript(tmp_path):
    shared = "".join(f"  const value{i} = computeSomething(argument{i}, constantValue{i});\n" for i in range(10))
    write(tmp_path / "a.js", "function a() {\n  const uniqueA = 1;\n" + shared + "  return uniqueA;\n}\n")
    write(tmp_path / "b.js", "function b() {\n  const uniqueB = 2;\n" + shared + "  return uniqueB;\n}\n")
    (clone,) = by_rule(run(CloneAnalyzer(), tmp_path), "code-clone")
    assert clone.metadata["lines"] == 10


# ---- Entegrasyon -----------------------------------------------------------------------------

def test_service_runs_new_analyzers_and_scores_their_categories(tmp_path):
    write(tmp_path / "a.py", "import os\n\n\ndef f():\n    return 1\n    x = 2\n")
    service = ProjectService()
    service.set_project(tmp_path)
    analysis = service.doctor.diagnose(tmp_path)
    assert "deadcode" in analysis.category_scores and "duplicate" in analysis.category_scores
    assert analysis.category_scores["deadcode"] < 100
    assert not analysis.failed_analyzers


def test_thresholds_dataclass_has_new_fields():
    fields = {f.name for f in dataclasses.fields(QualityThresholds)}
    assert {"magic_numbers", "clone_lines", "clone_severe_lines"} <= fields


# ---- sınıf ve dosya boyutu metinleri ----------------------------------------------------------

def test_class_size_fires_on_either_metric_and_names_it(tmp_path):
    """Denetimde iddia edildi: `and` yüzünden tek ölçüyü aşan sınıf kaçar. Kaçmıyor; iki yön de sınanır."""
    long_body = "".join(f"        x{i} = {i}\n" for i in range(320))
    write(tmp_path / "long_cls.py", f"class Long:\n    def a(self):\n{long_body}")                       # 1 metot, 322 satır
    write(tmp_path / "many.py", "class Many:\n" + "".join(f"    def m{i}(self):\n        pass\n" for i in range(21)))
    results = {r.metadata["class_name"]: r.description for r in run(CodeComplexityAnalyzer(), tmp_path)
               if r.metadata["rule"] == "class-size"}
    assert set(results) == {"Long", "Many"}
    assert "satır (eşik 300)" in results["Long"] and "metot (eşik" not in results["Long"]
    assert "21 metot (eşik 20)" in results["Many"] and "satır (eşik" not in results["Many"]


def test_file_length_text_separates_total_and_code_lines(tmp_path):
    write(tmp_path / "long.py", "# yorum\n\n" * 200 + "x = 1\n" * 150)          # 550 toplam, 150 kod
    [result] = run(CodeComplexityAnalyzer(), tmp_path)
    assert "toplam 550 satır" in result.description and "150 kod satırı" in result.description
