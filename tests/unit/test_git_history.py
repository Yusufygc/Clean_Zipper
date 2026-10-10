import shutil
import subprocess
from pathlib import Path

import pytest

from src.analyzers.git_history_analyzer import GitHistoryAnalyzer, secret_kind
from src.core.project_index import ProjectIndex
from src.models.analysis_models import Severity
from src.utils import git_info

needs_git = pytest.mark.skipif(shutil.which("git") is None, reason="git kurulu değil")

COMPLEX = "def hot(x):\n" + "".join(f"    if x == {i}:\n        return {i}\n" for i in range(12)) + "    return -1\n"


def git(repo, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                   cwd=repo, check=True, capture_output=True)


def commit(repo, files: dict, message="c"):
    for name, content in files.items():
        path = Path(repo) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    return root


def analyze(repo):
    return GitHistoryAnalyzer().analyze(ProjectIndex.build(repo))


def by_rule(results, rule):
    return [r for r in results if r.metadata.get("rule") == rule]


# ---- git_info ------------------------------------------------------------------------------------

@needs_git
def test_recent_commits_lists_files_newest_first_and_honors_limit(repo):
    commit(repo, {"a.py": "1\n"}, "bir")
    commit(repo, {"b.py": "1\n", "türkçe/c.py": "1\n"}, "iki")
    commits = git_info.recent_commits(repo)
    assert [set(c.files) for c in commits] == [{"b.py", "türkçe/c.py"}, {"a.py"}]
    assert all(len(c.sha) == 40 and c.time > 0 for c in commits)
    assert len(git_info.recent_commits(repo, limit=1)) == 1


@needs_git
def test_history_paths_finds_files_that_were_added_and_later_deleted(repo):
    commit(repo, {".env": "KEY=1\n", "keep.py": "1\n"})
    git(repo, "rm", "-q", ".env")
    git(repo, "commit", "-q", "-m", "sil")
    found = git_info.history_paths(repo, [":(glob)**/.env"])
    assert set(found) == {".env"} and found[".env"].time > 0


@needs_git
def test_history_paths_pathspec_covers_root_and_nested_files(repo):
    commit(repo, {".env": "1", "app/.env": "1", "app/other.txt": "1"})
    assert set(git_info.history_paths(repo, [":(glob)**/.env"])) == {".env", "app/.env"}


@needs_git
def test_history_from_a_subfolder_is_relative_to_it(repo):
    commit(repo, {"sub/x.py": "1\n", "top.py": "1\n"})
    assert set(git_info.recent_commits(repo / "sub")[0].files) == {"x.py"}


@needs_git
def test_history_helpers_return_none_outside_a_repository(tmp_path):
    assert git_info.recent_commits(tmp_path) is None and git_info.history_paths(tmp_path, ["x"]) is None


def test_history_helpers_return_none_without_git(tmp_path, monkeypatch):
    monkeypatch.setattr(git_info, "find_git", lambda: None)
    assert git_info.recent_commits(tmp_path) is None and git_info.history_paths(tmp_path, ["x"]) is None


def test_history_commands_are_read_only(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(git_info, "find_git", lambda: "git")

    class Done:
        returncode, stdout, stderr = 0, b"", b""

    monkeypatch.setattr(git_info.subprocess, "run", lambda command, **kw: seen.append(command) or Done())
    git_info.recent_commits(tmp_path)
    git_info.history_paths(tmp_path, ["x"])
    assert [c[c.index("log")] for c in seen] == ["log", "log"]
    assert all("core.fsmonitor=false" in c and "--all" not in c for c in seen)      # --all stash'i de gezerdi


# ---- hassas dosya adı ------------------------------------------------------------------------------------

@pytest.mark.parametrize("rel,kind", [
    (".env", "env"), ("config/.env", "env"), (".env.production", "env"), ("Credentials.json", "credentials"),
    ("secrets.yaml", "credentials"), ("deploy/id_rsa", "private-key"), ("tls/server.pem", "private-key"),
    ("a/b.key", "private-key"), ("store.jks", "private-key")])
def test_secret_kind_recognises_sensitive_names(rel, kind):
    assert secret_kind(rel) == kind


@pytest.mark.parametrize("rel", [".env.example", ".env.sample", ".env.template", "id_rsa.pub", "keys.py", "env.txt",
                                 "monkey.txt", "README.md"])
def test_secret_kind_ignores_public_templates_and_lookalikes(rel):
    assert secret_kind(rel) is None


# ---- geçmişteki sırlar ---------------------------------------------------------------------------------------

@needs_git
def test_deleted_env_file_is_reported_high_under_security_category(repo):
    commit(repo, {".env": "TOKEN=abc\n", "app.py": "x = 1\n"})
    git(repo, "rm", "-q", ".env")
    git(repo, "commit", "-q", "-m", "env sil")
    [finding] = by_rule(analyze(repo), "secret-in-history")
    assert finding.severity == Severity.HIGH and finding.category == "security"
    assert finding.metadata["kind"] == "env" and len(finding.metadata["commit"]) >= 7
    assert ".env" in finding.title and "rotate" in finding.recommendation


@needs_git
def test_untracked_but_committed_secret_counts_as_removed(repo):
    commit(repo, {"id_rsa": "KEY\n", "app.py": "x = 1\n"})
    git(repo, "rm", "-q", "--cached", "id_rsa")
    git(repo, "commit", "-q", "-m", "izlemeyi bırak")
    (repo / ".gitignore").write_text("id_rsa\n", encoding="utf-8")
    assert [r.metadata["kind"] for r in by_rule(analyze(repo), "secret-in-history")] == ["private-key"]


@needs_git
def test_still_tracked_secret_is_left_to_the_leak_analyzer(repo):
    commit(repo, {".env": "TOKEN=abc\n", "app.py": "x = 1\n"})
    assert by_rule(analyze(repo), "secret-in-history") == []


@needs_git
def test_public_templates_in_history_are_not_reported(repo):
    commit(repo, {".env.example": "TOKEN=\n", "app.py": "x = 1\n"})
    git(repo, "rm", "-q", ".env.example")
    git(repo, "commit", "-q", "-m", "sil")
    assert by_rule(analyze(repo), "secret-in-history") == []


@needs_git
def test_secret_in_test_fixture_is_medium_and_pem_is_approximate(repo):
    commit(repo, {"tests/fixtures/dev.pem": "CERT\n", "app.py": "x = 1\n"})
    git(repo, "rm", "-q", "tests/fixtures/dev.pem")
    git(repo, "commit", "-q", "-m", "sil")
    [finding] = by_rule(analyze(repo), "secret-in-history")
    assert finding.severity == Severity.MEDIUM and finding.metadata["in_tests"] and finding.metadata["approximate"]


@needs_git
def test_secret_added_on_another_branch_is_found(repo):
    commit(repo, {"app.py": "x = 1\n"})
    git(repo, "checkout", "-q", "-b", "feature")
    commit(repo, {"credentials.json": "{}\n"})
    git(repo, "checkout", "-q", "-")
    assert len(by_rule(analyze(repo), "secret-in-history")) == 1


# ---- sıcak noktalar ------------------------------------------------------------------------------------------

@pytest.fixture(scope="module")
def busy_repo(tmp_path_factory):                              # salt-okunur kullanılır, bu yüzden modül başına bir kez kurulur
    repo = tmp_path_factory.mktemp("busy")
    git(repo, "init", "-q")
    commit(repo, {"hot.py": COMPLEX, "cold.py": "def f():\n    return 1\n", "other.py": "y = 1\n"})
    for number in range(24):
        commit(repo, {"hot.py": COMPLEX + f"# {number}\n"}, f"hot {number}")
    return repo


@needs_git
def test_frequently_changed_complex_file_is_a_low_hotspot(busy_repo):
    hotspots = by_rule(analyze(busy_repo), "hotspot")
    assert [h.metadata["changes"] for h in hotspots] == [25] and hotspots[0].file_path.name == "hot.py"
    assert hotspots[0].severity == Severity.LOW and hotspots[0].metadata["max_complexity"] == 13


@needs_git
def test_rarely_changed_files_are_not_hotspots(busy_repo):
    assert all(h.file_path.name == "hot.py" for h in by_rule(analyze(busy_repo), "hotspot"))


@needs_git
def test_hotspot_is_info_when_no_function_exceeds_the_threshold(repo):
    commit(repo, {"calm.py": "def f():\n    return 1\n"})
    for number in range(24):
        commit(repo, {"calm.py": f"def f():\n    return {number}\n"})
    [hotspot] = by_rule(analyze(repo), "hotspot")
    assert hotspot.severity == Severity.INFO and hotspot.recommendation is None


@needs_git
def test_short_history_gives_no_hotspots_or_co_changes(repo):
    for number in range(8):
        commit(repo, {"a.py": f"x = {number}\n", "b.py": f"y = {number}\n"})
    results = analyze(repo)
    assert by_rule(results, "hotspot") == [] and by_rule(results, "co-change") == []


@needs_git
def test_bulk_commits_are_ignored_for_hotspots(repo):
    commit(repo, {"hot.py": COMPLEX})
    for number in range(24):                                  # her commit 40 dosya: toplu değişiklik
        commit(repo, {"hot.py": COMPLEX + f"# {number}\n", **{f"bulk{number}_{i}.txt": "x" for i in range(40)}})
    assert by_rule(analyze(repo), "hotspot") == []


# ---- birlikte değişim ----------------------------------------------------------------------------------------

@needs_git
def test_files_that_always_change_together_are_reported(repo):
    commit(repo, {"api/handler.py": "a = 0\n", "ui/view.py": "b = 0\n", "solo.py": "c = 0\n"})
    for number in range(1, 8):
        commit(repo, {"api/handler.py": f"a = {number}\n", "ui/view.py": f"b = {number}\n"})
    for number in range(1, 16):
        commit(repo, {"solo.py": f"c = {number}\n"})
    [pair] = by_rule(analyze(repo), "co-change")
    assert pair.metadata["files"] == ["api/handler.py", "ui/view.py"] and pair.metadata["shared_commits"] == 8
    assert pair.metadata["confidence"] == 1.0 and pair.metadata["same_directory"] is False
    assert pair.severity == Severity.INFO


@needs_git
def test_source_and_its_own_test_are_not_a_co_change(repo):
    commit(repo, {"core.py": "a = 0\n", "tests/test_core.py": "b = 0\n", "x.py": "c = 0\n"})
    for number in range(1, 8):
        commit(repo, {"core.py": f"a = {number}\n", "tests/test_core.py": f"b = {number}\n"})
    for number in range(1, 15):
        commit(repo, {"x.py": f"c = {number}\n"})
    assert by_rule(analyze(repo), "co-change") == []


@needs_git
def test_weak_correlation_is_not_reported(repo):
    commit(repo, {"a.py": "a = 0\n", "b.py": "b = 0\n"})
    for number in range(1, 6):
        commit(repo, {"a.py": f"a = {number}\n", "b.py": f"b = {number}\n"})
    for number in range(1, 20):                               # a ve b ayrı ayrı çok değişir: güven < 0.6
        commit(repo, {"a.py": f"a = {number + 10}\n"})
        commit(repo, {"b.py": f"b = {number + 10}\n"})
    assert by_rule(analyze(repo), "co-change") == []


# ---- genel -------------------------------------------------------------------------------------------------------

@needs_git
def test_non_repository_gives_no_findings(tmp_path):
    (tmp_path / "a.py").write_text("x = 1\n", encoding="utf-8")
    assert GitHistoryAnalyzer().analyze(ProjectIndex.build(tmp_path)) == []


@needs_git
def test_repository_without_commits_gives_no_findings(repo):
    (repo / "a.py").write_text("x = 1\n", encoding="utf-8")
    assert analyze(repo) == []


@needs_git
def test_deleted_files_are_not_hotspots(repo):
    commit(repo, {"gone.py": COMPLEX, "keep.py": "x = 1\n"})
    for number in range(24):
        commit(repo, {"gone.py": COMPLEX + f"# {number}\n"})
    git(repo, "rm", "-q", "gone.py")
    git(repo, "commit", "-q", "-m", "sil")
    assert by_rule(analyze(repo), "hotspot") == []


def test_health_scoring_counts_secret_but_not_informational_git_findings():
    from src.doctors.health_checker import HealthChecker
    assert "git" not in HealthChecker.WEIGHTS and "security" in HealthChecker.WEIGHTS
