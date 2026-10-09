import json
import textwrap
from pathlib import Path

from src.analyzers.project_hygiene_analyzer import ProjectHygieneAnalyzer
from src.analyzers.testing_analyzer import TestingAnalyzer
from src.core.path_rules import is_neutral_module, module_key, module_keys
from src.core.project_index import ProjectIndex
from src.core.thresholds import QualityThresholds
from src.languages import testing_patterns as tp
from src.languages.catalog import default_languages
from src.models.analysis_models import Severity
from src.services.project_service import ProjectService


def write(path: Path, content: str = "x = 1\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def lines(count: int, prefix: str = "value") -> str:
    return "".join(f"{prefix}_{i} = compute({i})\n" for i in range(count))


def by_rule(results):
    return {r.metadata["rule"]: r for r in results}


# ---- yol yardımcıları ----------------------------------------------------------------------------

def test_module_key_matches_source_and_test_names():
    assert module_key("src/foo_bar.py", False) == "foobar"
    assert module_key("tests/test_foo_bar.py", True) == "foobar"
    assert module_key("FooBarTests.cs", True) == "foobar"
    assert module_key("a/foo.test.ts", True) == "foo"
    assert module_key("pkg/foo_test.go", True) == "foo"
    assert module_key("src/latest.py", False) == "latest"          # kaynak dosyada 'test' soneki atılmaz
    assert module_key("tests/test.py", True) == "test"


def test_neutral_modules():
    assert all(is_neutral_module(p) for p in ("pkg/__init__.py", "tests/conftest.py", "src/index.ts"))
    assert not is_neutral_module("src/service.py")


# ---- dil kalıpları ----------------------------------------------------------------------------------

def stripped(language: str, code: str):
    return default_languages.get(language).stripped(textwrap.dedent(code))


def test_count_tests_per_language():
    js = stripped("javascript", "it('a', () => {});\ntest.skip('b', f);\ndescribe('x', () => {});\nobj.it('no');\n")
    assert tp.count_tests("javascript", js.clean, js.no_comments) == 2
    java = stripped("java", "@Test void a() {}\n@ParameterizedTest void b() {}\n@Override void c() {}\n")
    assert tp.count_tests("java", java.clean, java.no_comments) == 2
    cs = stripped("csharp", "[Fact] public void A() {}\n[Theory] public void B() {}\n[Obsolete] void C() {}\n")
    assert tp.count_tests("csharp", cs.clean, cs.no_comments) == 2
    go = stripped("go", "func TestA(t *testing.T) {}\nfunc helper() {}\nfunc BenchmarkB(b *testing.B) {}\n")
    assert tp.count_tests("go", go.clean, go.no_comments) == 2
    rust = stripped("rust", "#[test]\nfn a() {}\n#[tokio::test]\nasync fn b() {}\n")
    assert tp.count_tests("rust", rust.clean, rust.no_comments) == 2
    assert tp.count_tests("python", "", "", python_test_functions=7) == 7


def test_network_call_inside_a_string_literal_is_not_a_call():
    source = "DATA = \"requests.get('https://api.real.io/x')\"\n" + "requests.get('https://api.real.io/y')\n"
    py = stripped("python", source)
    assert tp.find_network_calls("python", py.no_comments, py.clean) == [2]


def test_skipped_sleep_and_network_detection():
    py = stripped("python", "@pytest.mark.skip\ndef t(): pass\ntime.sleep(1)\nrequests.get('http://localhost:8000')\n"
                            "requests.get('https://example.org/x')\nrequests.get('https://api.real.io/x')\n")
    assert tp.find_skipped("python", py.clean) == 1
    assert tp.find_sleeps("python", py.clean) == [3]
    assert tp.find_network_calls("python", py.no_comments, py.clean) == [6]
    js = stripped("javascript", "it.skip('a', f);\nxit('b', f);\nawait sleep(100);\nfetch('https://api.real.io');\n"
                               "fetch('http://localhost:3000');\n")
    assert tp.find_skipped("javascript", js.clean) == 2
    assert tp.find_sleeps("javascript", js.clean) == [3]
    assert tp.find_network_calls("javascript", js.no_comments, js.clean) == [4]


# ---- TestingAnalyzer -----------------------------------------------------------------------------------

def run_tests(root: Path, analyzer=None):
    return (analyzer or TestingAnalyzer()).analyze(ProjectIndex.build(root))


def test_no_tests_is_medium_and_high_for_large_sources(tmp_path):
    write(tmp_path / "app.py", lines(150))
    (finding,) = run_tests(tmp_path)
    assert finding.metadata["rule"] == "no-tests" and finding.severity == Severity.MEDIUM
    assert finding.category == "testing"
    write(tmp_path / "big.py", lines(400, "other"))
    (finding,) = run_tests(tmp_path)
    assert finding.severity == Severity.HIGH


def test_small_projects_without_tests_are_not_reported(tmp_path):
    write(tmp_path / "app.py", lines(20))
    assert run_tests(tmp_path) == []


def test_ratio_findings_follow_thresholds(tmp_path):
    write(tmp_path / "app.py", lines(300))
    write(tmp_path / "tests" / "test_app.py", "def test_a():\n    assert True\n" + lines(10, "t"))
    found = by_rule(run_tests(tmp_path))
    assert found["low-test-ratio"].severity == Severity.MEDIUM            # 12/300 = 0.04 < 0.1
    write(tmp_path / "tests" / "test_app.py", "def test_a():\n    assert True\n" + lines(60, "t"))
    assert by_rule(run_tests(tmp_path))["low-test-ratio"].severity == Severity.LOW    # ~0.21 < 0.3
    write(tmp_path / "tests" / "test_app.py", "def test_a():\n    assert True\n" + lines(120, "t"))
    assert "low-test-ratio" not in by_rule(run_tests(tmp_path))
    analyzer = TestingAnalyzer()
    analyzer.thresholds = QualityThresholds(test_ratio_low=0.5)
    assert "low-test-ratio" in by_rule(run_tests(tmp_path, analyzer))


def test_summary_counts_functions_files_and_skips(tmp_path):
    write(tmp_path / "app.py", lines(40))
    write(tmp_path / "tests" / "__init__.py", "")
    write(tmp_path / "tests" / "conftest.py", "import pytest\n")
    write(tmp_path / "tests" / "test_app.py",
          "import pytest\n\n\n@pytest.mark.skip\ndef test_a():\n    pass\n\n\ndef test_b():\n    pass\n\n\n"
          "class TestX:\n    def test_c(self):\n        pass\n    def helper(self):\n        pass\n")
    summary = by_rule(run_tests(tmp_path))["test-summary"]
    assert summary.severity == Severity.INFO
    assert summary.metadata["test_functions"] == 3 and summary.metadata["test_files"] == 1
    assert summary.metadata["skipped"] == 1


def test_untested_modules_are_matched_by_name(tmp_path):
    write(tmp_path / "src" / "billing.py", lines(60))
    write(tmp_path / "src" / "orders.py", lines(80, "o"))
    write(tmp_path / "src" / "tiny.py", lines(5, "t"))
    write(tmp_path / "src" / "__init__.py", lines(40, "i"))
    write(tmp_path / "tests" / "test_billing.py", "def test_a():\n    pass\n")
    found = by_rule(run_tests(tmp_path))
    untested = found["untested-modules"]
    assert [m["path"] for m in untested.metadata["modules"]] == ["src/orders.py"]
    assert untested.severity == Severity.INFO


def test_module_keys_include_parent_directory():
    assert module_keys("app/auth/service.py", False) == {"service", "authservice"}
    assert module_keys("tests/test_auth_service.py", True) == {"authservice"}
    assert module_keys("tests/auth/test_service.py", True) == {"service", "authservice"}
    assert module_keys("service.py", False) == {"service"}


def test_same_named_modules_in_packages_match_package_qualified_tests(tmp_path):
    """Önceden yalnızca ad eşleniyordu: `test_auth_service.py` `auth/service.py`'yi karşılamıyordu."""
    write(tmp_path / "app" / "auth" / "service.py", lines(60))
    write(tmp_path / "app" / "payment" / "service.py", lines(60, "p"))
    write(tmp_path / "tests" / "test_auth_service.py", "def test_a():\n    pass\n")
    untested = by_rule(run_tests(tmp_path))["untested-modules"]
    assert [m["path"] for m in untested.metadata["modules"]] == ["app/payment/service.py"]


def test_flaky_signals_in_test_files_only(tmp_path):
    write(tmp_path / "src" / "app.py", "import time\n\n\ndef wait():\n    time.sleep(1)\n" + lines(10))
    write(tmp_path / "tests" / "test_app.py",
          "import time\nimport requests\n\n\ndef test_a():\n    time.sleep(2)\n    requests.get('https://real.io/x')\n")
    found = by_rule(run_tests(tmp_path))
    assert found["test-sleep"].metadata["lines"] == [6] and found["test-sleep"].severity == Severity.LOW
    assert found["test-real-network"].metadata["lines"] == [7]
    assert found["test-sleep"].file_path.name == "test_app.py"


def test_rust_inline_tests_count_as_tests(tmp_path):
    write(tmp_path / "src" / "lib.rs", "pub fn a() -> i32 { 1 }\n" + "// pad\n" * 5 +
          "#[cfg(test)]\nmod tests {\n    #[test]\n    fn t() {}\n    #[test]\n    fn u() {}\n}\n")
    found = by_rule(run_tests(tmp_path))
    assert "no-tests" not in found and found["test-summary"].metadata["test_functions"] == 2


def test_javascript_tests_are_counted(tmp_path):
    write(tmp_path / "src" / "app.js", "export const a = 1;\n")
    write(tmp_path / "src" / "app.test.js", "it('works', () => {});\ntest('also', () => {});\n")
    summary = by_rule(run_tests(tmp_path))["test-summary"]
    assert summary.metadata["test_functions"] == 2 and summary.metadata["test_files"] == 1


def test_no_source_and_no_tests_gives_nothing(tmp_path):
    write(tmp_path / "notes.txt", "hi")
    assert run_tests(tmp_path) == []


# ---- ProjectHygieneAnalyzer ------------------------------------------------------------------------------------

def run_hygiene(root: Path):
    return ProjectHygieneAnalyzer().analyze(ProjectIndex.build(root))


def rules(results):
    return {r.metadata["rule"] for r in results}


def make_project(root: Path):
    write(root / "app.py", lines(150))


def test_missing_basics_are_reported_for_real_projects(tmp_path):
    make_project(tmp_path)
    (tmp_path / ".git").mkdir()
    results = run_hygiene(tmp_path)
    assert rules(results) == {"missing-readme", "missing-license", "missing-gitignore", "hygiene-summary"}
    assert all(r.severity == Severity.LOW for r in results if r.metadata["rule"].startswith("missing"))
    assert all(r.category == "hygiene" for r in results)


def test_present_basics_become_good_practices(tmp_path):
    make_project(tmp_path)
    (tmp_path / ".git").mkdir()
    write(tmp_path / "README.md", "# x")
    write(tmp_path / "LICENSE", "MIT")
    write(tmp_path / ".gitignore", "venv/\n")
    write(tmp_path / "Dockerfile", "FROM python")
    summary = by_rule(run_hygiene(tmp_path))["hygiene-summary"]
    assert set(summary.metadata["present"]) == {"readme", "license", "gitignore", "dockerfile"}
    assert summary.metadata["missing"] == [] and "4/4" in summary.title


def test_small_projects_and_non_git_dirs_skip_checks(tmp_path):
    write(tmp_path / "tiny.py", lines(5))
    assert run_hygiene(tmp_path) == []


def test_ci_only_required_when_tests_exist_and_recognizes_providers(tmp_path):
    make_project(tmp_path)
    assert "missing-ci" not in rules(run_hygiene(tmp_path))
    write(tmp_path / "tests" / "test_app.py", "def test_a():\n    pass\n")
    assert "missing-ci" in rules(run_hygiene(tmp_path))
    write(tmp_path / ".github" / "workflows" / "ci.yml", "name: ci\n")
    assert "missing-ci" not in rules(run_hygiene(tmp_path))
    (tmp_path / ".github" / "workflows" / "ci.yml").unlink()
    write(tmp_path / ".gitlab-ci.yml", "stages: []\n")
    assert "missing-ci" not in rules(run_hygiene(tmp_path))


def test_lockfile_checks_per_ecosystem(tmp_path):
    write(tmp_path / "web" / "package.json", json.dumps({"dependencies": {"react": "^18"}}))
    write(tmp_path / "empty" / "package.json", json.dumps({"name": "no-deps"}))
    write(tmp_path / "svc" / "go.mod", "module x\nrequire github.com/a/b v1.0.0\n")
    write(tmp_path / "bin" / "Cargo.toml", "[package]\nname='b'\n[dependencies]\nserde = '1'\n")
    write(tmp_path / "bin" / "src" / "main.rs", "fn main() {}\n")
    write(tmp_path / "lib" / "Cargo.toml", "[package]\nname='l'\n[dependencies]\nserde = '1'\n")
    write(tmp_path / "lib" / "src" / "lib.rs", "pub fn a() {}\n")
    manifests = {r.metadata["manifest"] for r in run_hygiene(tmp_path) if r.metadata["rule"] == "missing-lockfile"}
    assert manifests == {"web/package.json", "svc/go.mod", "bin/Cargo.toml"}
    write(tmp_path / "web" / "package-lock.json", "{}")
    write(tmp_path / "svc" / "go.sum", "")
    write(tmp_path / "bin" / "Cargo.lock", "")
    assert [r for r in run_hygiene(tmp_path) if r.metadata["rule"] == "missing-lockfile"] == []
    assert "lockfile" in by_rule(run_hygiene(tmp_path))["hygiene-summary"].metadata["present"]


def test_monorepo_root_lockfile_counts_and_pyproject_needs_locking_tool(tmp_path):
    write(tmp_path / "package-lock.json", "{}")
    write(tmp_path / "packages" / "a" / "package.json", json.dumps({"dependencies": {"x": "1"}}))
    write(tmp_path / "plain" / "pyproject.toml", "[project]\nname='p'\ndependencies=['requests']\n")
    write(tmp_path / "poetry_app" / "pyproject.toml", "[tool.poetry]\nname='p'\n")
    missing = {r.metadata["manifest"] for r in run_hygiene(tmp_path) if r.metadata["rule"] == "missing-lockfile"}
    assert missing == {"poetry_app/pyproject.toml"}


def test_env_example_required_when_env_exists(tmp_path):
    write(tmp_path / ".env", "KEY=1\n")
    assert "missing-env-example" in rules(run_hygiene(tmp_path))
    write(tmp_path / ".env.example", "KEY=\n")
    results = run_hygiene(tmp_path)
    assert "missing-env-example" not in rules(results)
    assert "env-example" in by_rule(results)["hygiene-summary"].metadata["present"]


def test_service_scores_testing_and_hygiene_categories(tmp_path):
    make_project(tmp_path)
    analysis = ProjectService().doctor.diagnose(tmp_path)
    assert analysis.category_scores["testing"] < 100 and analysis.category_scores["hygiene"] < 100
    assert not analysis.failed_analyzers
