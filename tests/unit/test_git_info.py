import logging
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from src.core.project_index import ProjectIndex
from src.utils import git_info
from src.utils.git_info import tracked_paths

HAS_GIT = shutil.which("git") is not None
needs_git = pytest.mark.skipif(not HAS_GIT, reason="git kurulu değil")


def git(repo, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                   cwd=repo, check=True, capture_output=True)


def write(path: Path, content="x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    git(root, "init", "-q")
    write(root / "tracked.py")
    write(root / "src" / "inner.py")
    write(root / "türkçe dosya.txt")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "ilk")
    write(root / "untracked.py")
    return root


@needs_git
def test_tracked_paths_lists_only_committed_files(repo):
    assert tracked_paths(repo) == {"tracked.py", "src/inner.py", "türkçe dosya.txt"}


@needs_git
def test_subfolder_root_returns_paths_relative_to_it(repo):
    assert tracked_paths(repo / "src") == {"inner.py"}


@needs_git
def test_tracked_file_stays_tracked_even_if_later_gitignored(repo):
    write(repo / ".gitignore", "tracked.py\n")
    assert "tracked.py" in tracked_paths(repo)                      # .gitignore geçmişi/izlemeyi silmez


@needs_git
def test_non_repository_returns_none(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    assert tracked_paths(plain) is None


def test_missing_git_returns_none_and_logs(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(git_info, "find_git", lambda: None)
    with caplog.at_level(logging.INFO):
        assert tracked_paths(tmp_path) is None
    assert "git bulunamadı" in caplog.text


def test_timeout_and_os_errors_return_none_and_log(tmp_path, monkeypatch, caplog):
    monkeypatch.setattr(git_info, "find_git", lambda: "git")

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("git", 1)

    monkeypatch.setattr(git_info.subprocess, "run", timeout)
    with caplog.at_level(logging.WARNING):
        assert tracked_paths(tmp_path) is None
    assert "çalıştırılamadı" in caplog.text


def test_command_is_read_only_and_non_interactive(tmp_path, monkeypatch):
    captured = {}
    monkeypatch.setattr(git_info, "find_git", lambda: "git")

    class Done:
        returncode, stdout, stderr = 0, b"a.py\0", b""

    def fake_run(command, **kwargs):
        captured.update(command=command, env=kwargs["env"])
        return Done()

    monkeypatch.setattr(git_info.subprocess, "run", fake_run)
    assert tracked_paths(tmp_path) == {"a.py"}
    assert "core.fsmonitor=false" in captured["command"] and "ls-files" in captured["command"]
    assert captured["env"]["GIT_OPTIONAL_LOCKS"] == "0" and captured["env"]["GIT_TERMINAL_PROMPT"] == "0"


@needs_git
def test_index_asks_git_once_and_shares_the_result(repo, monkeypatch):
    calls = []
    real = git_info.tracked_paths

    def counting(root):
        calls.append(root)
        return real(root)

    monkeypatch.setattr("src.core.project_index.tracked_paths", counting)
    index = ProjectIndex.build(repo)                                # .gitignore duyarlı: izlenen dosyalar kurala karşı korunur
    assert len(calls) == 1
    assert "tracked.py" in index.git_tracked and "untracked.py" not in index.git_tracked
    index.git_tracked
    assert len(calls) == 1                                          # güvenlik analizörü aynı listeyi kullanır


@needs_git
def test_index_without_gitignore_support_loads_git_tracked_lazily(repo, monkeypatch):
    calls = []
    real = git_info.tracked_paths
    monkeypatch.setattr("src.core.project_index.tracked_paths", lambda root: calls.append(root) or real(root))
    index = ProjectIndex.build(repo, respect_gitignore=False)
    assert calls == []
    assert "tracked.py" in index.git_tracked and len(calls) == 1


def test_find_git_searches_only_absolute_path_entries(tmp_path, monkeypatch):
    """Analiz edilen projedeki sahte `git` (geçerli klasör ya da göreli PATH girdisi) çalıştırılmamalı."""
    fake_dir = tmp_path / "proje"
    fake_dir.mkdir()
    name = "git.exe" if os.name == "nt" else "git"
    fake = fake_dir / name
    fake.write_text("sahte", encoding="utf-8")
    fake.chmod(0o755)
    monkeypatch.chdir(fake_dir)
    monkeypatch.setenv("PATH", "." + os.pathsep + "proje")
    assert git_info.find_git() is None
    monkeypatch.setenv("PATH", str(fake_dir))                         # açıkça PATH'e konmuşsa kullanıcının seçimi
    assert os.path.normcase(git_info.find_git()) == os.path.normcase(str(fake))


@pytest.mark.skipif(not HAS_GIT, reason="git kurulu değil")
def test_find_git_returns_an_absolute_path():
    found = git_info.find_git()
    assert found is not None and os.path.isabs(found)
