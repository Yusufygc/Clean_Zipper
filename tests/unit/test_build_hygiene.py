import shutil
import subprocess
from pathlib import Path

import pytest

from src.analyzers.dead_weight_analyzer import DeadWeightAnalyzer
from src.analyzers.project_hygiene_analyzer import ProjectHygieneAnalyzer
from src.core.path_rules import artifact_root
from src.core.project_index import ProjectIndex
from src.models.analysis_models import Severity

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git kurulu değil")
ROOT = Path(__file__).resolve().parents[2]


def write(path: Path, content: str = "x = 1\n"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def git(repo, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                   cwd=repo, check=True, capture_output=True)


def commit_all(repo, files: dict):
    git(repo, "init", "-q")
    for name, content in files.items():
        write(repo / name, content)
    git(repo, "add", "-A", "-f")                    # .gitignore'a bakmadan: izlenen üretilmiş içeriği taklit eder
    git(repo, "commit", "-q", "-m", "c")


def rules(results, rule):
    return [r for r in results if r.metadata.get("rule") == rule]


# ---- yol tanıma ----------------------------------------------------------------------------------------

@pytest.mark.parametrize("rel,expected", [
    ("node_modules/left-pad/index.js", ("node_modules", "dependencies")),
    ("web/node_modules/a/b.js", ("web/node_modules", "dependencies")),
    ("venv/Lib/site.py", ("venv", "dependencies")),
    ("src/__pycache__/a.cpython-310.pyc", ("src/__pycache__", "cache")),
    (".next/cache/x", (".next", "cache")),
    ("dist/app.js", ("dist", "build")),
    ("pkg/build/out.o", ("pkg/build", "build")),
    ("src/old.pyc", ("src/*.pyc", "bytecode")),
    ("top.pyc", ("*.pyc", "bytecode")),
    ("a\\node_modules\\x.js", ("a/node_modules", "dependencies")),
    ("lib/pkg/node_modules/x.js", ("lib/pkg/node_modules", "dependencies"))])           # bağımlılık klasörü satıcı klasöründe de sayılır
def test_artifact_root_recognises_generated_content(rel, expected):
    assert artifact_root(rel) == expected


@pytest.mark.parametrize("rel", ["wwwroot/lib/bootstrap/dist/css/b.css", "vendor/pkg/build/x.js", "third_party/a/dist/y.js",
                                 "src/main.py", "build.gradle", "docs/build_notes.md", "src/distribution/a.py",
                                 "node_modules.txt", "builder/x.py", "env/config.py"])
def test_artifact_root_ignores_normal_source(rel):
    assert artifact_root(rel) is None


# ---- tracked-artifacts ----------------------------------------------------------------------------------

@needs_git
def test_tracked_dependency_cache_and_build_folders_are_reported(tmp_path):
    commit_all(tmp_path, {"app.py": "x = 1\n", "node_modules/a/i.js": "1", "node_modules/b/i.js": "1",
                          "pkg/__pycache__/m.pyc": "1", "dist/app.js": "1"})
    found = {r.metadata["root"]: r for r in rules(ProjectHygieneAnalyzer().analyze(ProjectIndex.build(tmp_path)), "tracked-artifacts")}
    assert set(found) == {"node_modules", "pkg/__pycache__", "dist"}
    assert found["node_modules"].severity == Severity.MEDIUM and found["node_modules"].metadata["tracked_files"] == 2
    assert found["pkg/__pycache__"].severity == Severity.LOW and found["dist"].metadata["approximate"] is True
    assert found["node_modules"].metadata["approximate"] is False
    assert "git rm -r --cached node_modules" in found["node_modules"].recommendation


@needs_git
def test_untracked_or_gitignored_artifacts_are_not_reported(tmp_path):
    tmp_path.joinpath(".gitignore").write_text("node_modules/\n__pycache__/\n", encoding="utf-8")
    git(tmp_path, "init", "-q")
    write(tmp_path / "app.py")
    write(tmp_path / "node_modules" / "a.js", "1")
    write(tmp_path / "__pycache__" / "a.pyc", "1")
    git(tmp_path, "add", "-A")
    git(tmp_path, "commit", "-q", "-m", "c")
    results = ProjectHygieneAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert rules(results, "tracked-artifacts") == []
    summary = rules(results, "hygiene-summary")[0]
    assert "clean-repo" in summary.metadata["present"] and "clean-repo" not in summary.metadata["missing"]


@needs_git
def test_artifact_findings_do_not_pollute_the_missing_list(tmp_path):
    commit_all(tmp_path, {"app.py": "x = 1\n", "dist/a.js": "1"})
    summary = rules(ProjectHygieneAnalyzer().analyze(ProjectIndex.build(tmp_path)), "hygiene-summary")[0]
    assert "tracked-artifacts" not in summary.metadata["missing"] and "clean-repo" not in summary.metadata["present"]
    assert all(not item.startswith("tracked") for item in summary.metadata["missing"])


@needs_git
def test_findings_are_capped_and_largest_first(tmp_path):
    files = {f"p{i}/node_modules/a.js": "1" for i in range(14)}
    files.update({"big/node_modules/a.js": "1", "big/node_modules/b.js": "1", "app.py": "x = 1\n"})
    commit_all(tmp_path, files)
    found = rules(ProjectHygieneAnalyzer().analyze(ProjectIndex.build(tmp_path)), "tracked-artifacts")
    assert len(found) == 10 and found[0].metadata["root"] == "big/node_modules"


def test_non_repository_has_no_artifact_findings(tmp_path):
    write(tmp_path / "node_modules" / "a.js", "1")
    write(tmp_path / "app.py")
    results = ProjectHygieneAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert rules(results, "tracked-artifacts") == []
    assert all("clean-repo" not in r.metadata.get("present", []) for r in results)


# ---- dev-dependency-in-runtime ----------------------------------------------------------------------------

def run_dependencies(root: Path):
    return DeadWeightAnalyzer().analyze(ProjectIndex.build(root))


def test_test_and_packaging_tools_in_requirements_txt_are_flagged_once(tmp_path):
    write(tmp_path / "requirements.txt", "requests==2.0\npytest==7.0\npyinstaller==6.0\n")
    write(tmp_path / "app.py", "import requests\n")
    [finding] = rules(run_dependencies(tmp_path), "dev-dependency-in-runtime")
    assert finding.severity == Severity.LOW and finding.metadata["dependencies"] == ["pytest", "pyinstaller"]
    assert "requirements-dev.txt" in finding.recommendation and finding.file_path.name == "requirements.txt"


def test_clean_runtime_list_has_no_dev_finding(tmp_path):
    write(tmp_path / "requirements.txt", "requests==2.0\n")
    write(tmp_path / "app.py", "import requests\n")
    assert rules(run_dependencies(tmp_path), "dev-dependency-in-runtime") == []


@pytest.mark.parametrize("name", ["requirements-dev.txt", "requirements_test.txt", "requirements-build.txt"])
def test_dev_named_manifests_may_hold_tools(name):
    assert DeadWeightAnalyzer._is_runtime_manifest(name) is False


def test_plain_requirements_name_is_runtime():
    assert DeadWeightAnalyzer._is_runtime_manifest("requirements.txt") is True


# ---- bu repo kendi kurallarına uyuyor -----------------------------------------------------------------------------

def test_this_repository_follows_its_own_build_hygiene_rules():
    runtime = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert "pytest" not in runtime.lower() and "pyinstaller" not in runtime.lower() and "pillow" not in runtime.lower()
    for name in ("requirements-dev.txt", "requirements-build.txt"):
        assert "-r requirements.txt" in (ROOT / name).read_text(encoding="utf-8")
    assert (ROOT / ".gitattributes").is_file() and (ROOT / ".editorconfig").is_file()
    results = DeadWeightAnalyzer().analyze(ProjectIndex.build(ROOT))
    assert rules(results, "unpinned-dependencies") == [] and rules(results, "dev-dependency-in-runtime") == []
    assert rules(results, "unused-dependency") == []


def test_source_files_have_no_utf8_bom():
    offenders = [str(p.relative_to(ROOT)) for p in list((ROOT / "src").rglob("*.py")) + [ROOT / "main.py"]
                 if p.read_bytes().startswith(b"\xef\xbb\xbf")]
    assert offenders == []


# ---- test dosyalarındaki sahte gizli değerler ----------------------------------------------------------------

def leaks(root: Path):
    from src.analyzers.security_analyzer import SecurityLeakAnalyzer
    return [r for r in SecurityLeakAnalyzer().analyze(ProjectIndex.build(root)) if r.metadata.get("rule") == "hardcoded-secret"]


def test_hardcoded_secret_in_source_is_high_but_in_tests_is_low(tmp_path):
    write(tmp_path / "config.py", "PASSWORD = 'hunter2hunter2'\n")
    write(tmp_path / "tests" / "test_config.py", "SECRET = 'fakefakefakefake'\n")
    by_name = {r.file_path.name: r for r in leaks(tmp_path)}
    assert by_name["config.py"].severity == Severity.HIGH and by_name["config.py"].metadata["in_tests"] is False
    assert by_name["test_config.py"].severity == Severity.LOW and by_name["test_config.py"].metadata["in_tests"] is True


def test_provider_shaped_keys_keep_their_priority_inside_tests(tmp_path):
    from src.analyzers.security_analyzer import SecurityLeakAnalyzer
    write(tmp_path / "tests" / "test_a.py", "KEY = 'ghp_" + "a1B2c3D4e5F6g7H8i9J0k1L2m3N4o5P6q7R8'\n")
    found = [r for r in SecurityLeakAnalyzer().analyze(ProjectIndex.build(tmp_path)) if r.metadata.get("rule") == "provider-secret"]
    assert found and all(r.severity.value >= Severity.HIGH.value for r in found)
