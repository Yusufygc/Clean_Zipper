import logging
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from src.utils.gitignore_parser import GitignoreMatcher, GitignoreParser

HAS_GIT = shutil.which("git") is not None


def write(path: Path, content="x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
    return path


def build(root: Path, files: dict):
    for rel, content in files.items():
        write(root / rel, content)
    return GitignoreMatcher(str(root))


# ---- temel semantik --------------------------------------------------------------------

def test_root_patterns_basic(tmp_path):
    m = build(tmp_path, {".gitignore": "*.log\nbuild/\n/secret.txt\n", "a.log": "", "src/b.log": "", "secret.txt": "",
                         "sub/secret.txt": "", "build/x.o": "", "src/build/y.o": "", "app.py": ""})
    ignored = {rel: m.is_ignored(tmp_path / rel) for rel in
               ["a.log", "src/b.log", "secret.txt", "sub/secret.txt", "build/x.o", "src/build/y.o", "app.py"]}
    assert ignored == {"a.log": True, "src/b.log": True, "secret.txt": True, "sub/secret.txt": False,
                       "build/x.o": True, "src/build/y.o": True, "app.py": False}


def test_nested_gitignore_applies_only_to_its_subtree(tmp_path):
    m = build(tmp_path, {"backend/.gitignore": ".env\n*.sqlite\n", "backend/.env": "", "backend/db/a.sqlite": "",
                         "frontend/.env": "", "frontend/a.sqlite": ""})
    assert m.is_ignored(tmp_path / "backend/.env") and m.is_ignored(tmp_path / "backend/db/a.sqlite")
    assert not m.is_ignored(tmp_path / "frontend/.env") and not m.is_ignored(tmp_path / "frontend/a.sqlite")


def test_nested_negation_overrides_parent_rule(tmp_path):
    m = build(tmp_path, {".gitignore": "*.log\n", "logs/.gitignore": "!keep.log\n", "logs/keep.log": "", "logs/drop.log": ""})
    assert not m.is_ignored(tmp_path / "logs/keep.log")
    assert m.is_ignored(tmp_path / "logs/drop.log")


def test_negation_cannot_reinclude_inside_an_ignored_directory(tmp_path):
    m = build(tmp_path, {".gitignore": "vendor/\n!vendor/keep.txt\n", "vendor/keep.txt": "", "vendor/other.txt": ""})
    assert m.is_ignored(tmp_path / "vendor", is_dir=True)
    assert m.is_ignored(tmp_path / "vendor/keep.txt")                 # git: üst klasör ignore ise içi geri eklenemez


def test_directory_queries_use_trailing_slash_semantics(tmp_path):
    m = build(tmp_path, {".gitignore": "cache/\nfile_or_dir\n", "cache/a": "", "src/cache/b": ""})
    assert m.is_ignored(tmp_path / "cache", is_dir=True) and m.is_ignored(tmp_path / "src/cache", is_dir=True)
    assert not m.is_ignored(tmp_path / "cache")                      # `cache/` kuralı aynı adlı DOSYAYA uymaz
    assert m.is_ignored(tmp_path / "file_or_dir") and m.is_ignored(tmp_path / "x/file_or_dir", is_dir=True)


def test_git_info_exclude_has_lower_priority_than_gitignore(tmp_path):
    m = build(tmp_path, {".git/info/exclude": "*.tmp\nlocal.txt\n", ".gitignore": "!local.txt\n", "a.tmp": "", "local.txt": ""})
    assert m.is_ignored(tmp_path / "a.tmp")
    assert not m.is_ignored(tmp_path / "local.txt")


def test_paths_outside_root_and_no_gitignore_are_never_ignored(tmp_path):
    (tmp_path / "proj").mkdir()
    write(tmp_path / "other" / ".gitignore", "*\n")
    m = GitignoreMatcher(str(tmp_path / "proj"))
    assert not m.is_ignored(tmp_path / "proj" / "a.py")
    assert not m.is_ignored(tmp_path / "other" / "a.py")
    assert m.load_errors == []


def test_encodings_and_line_endings(tmp_path):
    content = b"\xef\xbb\xbfsecret.txt\r\n# \xfd\xfe\xf0 yorum\r\n*.tmp\r\n"
    m = build(tmp_path, {".gitignore": content, "secret.txt": "", "a.tmp": "", "app.py": ""})
    assert m.is_ignored(tmp_path / "secret.txt") and m.is_ignored(tmp_path / "a.tmp") and not m.is_ignored(tmp_path / "app.py")


def test_unreadable_nested_gitignore_is_recorded_not_raised(tmp_path, monkeypatch, caplog):
    write(tmp_path / "sub" / ".gitignore", "x\n")
    real_open = open

    def deny(path, *args, **kwargs):
        if str(path).endswith(os.path.join("sub", ".gitignore")):
            raise PermissionError("erişim reddedildi")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", deny)
    m = GitignoreMatcher(str(tmp_path))
    with caplog.at_level(logging.ERROR):
        assert m.is_ignored(tmp_path / "sub" / "a.txt") is False
    assert len(m.load_errors) == 1 and "erişim reddedildi" in m.load_errors[0] and ".gitignore okunamadı" in m.load_errors[0]
    assert "erişim reddedildi" in caplog.text
    m.is_ignored(tmp_path / "sub" / "b.txt")
    assert len(m.load_errors) == 1                                    # aynı dosya için tekrar kaydedilmez


def test_parser_compat_wrapper(tmp_path):
    write(tmp_path / ".gitignore", "secret.txt\n")
    write(tmp_path / "pkg" / ".gitignore", "*.cache\n")
    parser = GitignoreParser(str(tmp_path))
    assert parser.should_ignore(str(tmp_path / "secret.txt")) and parser.should_ignore(str(tmp_path / "pkg" / "a.cache"))
    assert parser.spec is not None and parser.load_error is None
    parser.load_error = "elle"
    assert parser.load_errors == ["elle"]
    parser.load_error = None
    assert parser.load_errors == []


# ---- gerçek git ile çapraz doğrulama -----------------------------------------------------------

CROSS_CHECK_FILES = [
    "app.py", "a.log", "keep.log", "src/b.log", "src/keep.log", "logs/keep.log", "logs/drop.log", "logs/deep/x.log",
    "build/x.o", "src/build/y.o", "vendor/keep.txt", "vendor/other.txt", "secret.txt", "sub/secret.txt",
    "backend/.env", "backend/db/a.sqlite", "frontend/.env", "frontend/a.sqlite", "docs/tmp.md", "docs/sub/tmp.md",
    "docs/readme.md", "a b/space file.txt", "dir.d/x", "node/file_or_dir", "x/file_or_dir/inner.txt",
]
CROSS_CHECK_RULES = {
    ".gitignore": "*.log\n!keep.log\nbuild/\n/secret.txt\nvendor/\n!vendor/keep.txt\ndocs/*\n!docs/readme.md\n"
                  "file_or_dir\n*.d/\n**/sub/*.tmp\n",
    "logs/.gitignore": "!keep.log\n",
    "backend/.gitignore": ".env\n*.sqlite\n",
    "docs/sub/.gitignore": "!tmp.md\n",
}


@pytest.mark.skipif(not HAS_GIT, reason="git kurulu değil")
def test_matcher_agrees_with_real_git_check_ignore(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    for rel, content in CROSS_CHECK_RULES.items():
        write(repo / rel, content)
    for rel in CROSS_CHECK_FILES:
        write(repo / rel, "x")

    matcher = GitignoreMatcher(str(repo))
    disagreements = []
    for rel in CROSS_CHECK_FILES:
        git_says = subprocess.run(["git", "check-ignore", "-q", rel], cwd=repo).returncode == 0
        ours = matcher.is_ignored(repo / rel)
        if git_says != ours:
            disagreements.append((rel, "git", git_says, "biz", ours))
    assert disagreements == []


# ---- izlenen dosyalar: git semantiği ---------------------------------------------------------------

def test_tracked_files_are_never_ignored_even_if_a_rule_matches(tmp_path):
    m = build(tmp_path, {".gitignore": ".gitignore\n*.txt\nbuild/\n", "notes.txt": "", "forced.txt": "", "build/keep.cfg": "",
                         "build/x.o": ""})
    m.set_tracked({".gitignore", "forced.txt", "build/keep.cfg"})
    assert not m.is_ignored(tmp_path / ".gitignore")                      # kendi adını içeren .gitignore (gerçek vaka)
    assert not m.is_ignored(tmp_path / "forced.txt") and m.is_ignored(tmp_path / "notes.txt")
    assert not m.is_ignored(tmp_path / "build/keep.cfg") and m.is_ignored(tmp_path / "build/x.o")


def test_directory_with_tracked_files_is_not_pruned_but_siblings_stay_ignored(tmp_path):
    m = build(tmp_path, {".gitignore": "build/\n", "build/keep.cfg": "", "build/deep/x.o": "", "other/a": ""})
    assert m.is_dir_ignored(tmp_path / "build")                            # izleme bilgisi yokken budanır
    m.set_tracked({"build/keep.cfg"})
    assert not m.is_dir_ignored(tmp_path / "build")                        # içinde izlenen dosya var
    assert m.is_dir_ignored(tmp_path / "build" / "deep")                   # izlenen dosyası olmayan alt klasör yine budanır
    m.set_tracked(None)
    assert m.is_dir_ignored(tmp_path / "build")                            # önbellek temizlenir


@pytest.mark.skipif(not HAS_GIT, reason="git kurulu değil")
def test_matcher_with_tracked_set_agrees_with_git_ls_files_oracle(tmp_path):
    from src.utils.git_info import tracked_paths
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    write(repo / ".gitignore", ".gitignore\n*.txt\nbuild/\nsecret.cfg\n")
    for rel in ["app.py", "notes.txt", "forced.txt", "build/keep.cfg", "build/x.o", "secret.cfg", "src/mod.py", "src/extra.txt"]:
        write(repo / rel, "x")
    subprocess.run(["git", "add", "-f", ".gitignore", "forced.txt", "build/keep.cfg", "app.py", "src/mod.py"], cwd=repo, check=True)

    matcher = GitignoreMatcher(str(repo), tracked=tracked_paths(repo))
    oracle = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=repo,
                            capture_output=True).stdout.split(b"\0")
    expected = {p.decode() for p in oracle if p}
    kept = set()
    for root, dirs, files in os.walk(repo):
        if ".git" in dirs:
            dirs.remove(".git")
        dirs[:] = [d for d in dirs if not matcher.is_dir_ignored(os.path.join(root, d))]
        for name in files:
            full = os.path.join(root, name)
            if not matcher.is_ignored(full):
                kept.add(os.path.relpath(full, repo).replace(os.sep, "/"))
    assert kept == expected
