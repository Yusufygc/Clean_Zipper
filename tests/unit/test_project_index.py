import os
import sys

import pytest

from src.core.project_index import ProjectIndex, PARTIAL_HASH_BYTES


def write(path, content="x", mode="w", **kw):
    path.parent.mkdir(parents=True, exist_ok=True)
    if "b" in mode:
        path.write_bytes(content)
    else:
        path.write_text(content, **kw)
    return path


@pytest.fixture
def tree(tmp_path):
    write(tmp_path / "main.py", "print(1)")
    write(tmp_path / "README")                       # uzantısız
    write(tmp_path / ".env", "A=1")                  # nokta dosyası
    write(tmp_path / "src" / "a.PY", "aa")
    write(tmp_path / "src" / "pkg" / "b.txt", "bbb")
    (tmp_path / "empty").mkdir()
    write(tmp_path / "onlyvenv" / "venv" / "lib.py")   # yalnızca dışlanan alt klasör
    write(tmp_path / "venv" / "lib" / "x.py")
    write(tmp_path / "node_modules" / "m" / "i.js")
    write(tmp_path / ".git" / "HEAD")
    return tmp_path


def rels(index):
    return sorted(f.rel for f in index.files)


def test_excluded_dirs_are_not_indexed(tree):
    index = ProjectIndex.build(tree)
    assert rels(index) == [".env", "README", "main.py", "src/a.PY", "src/pkg/b.txt"]
    assert index.total_files == 5


def test_totals_ext_counts_and_sizes(tree):
    index = ProjectIndex.build(tree)
    assert index.total_size == sum(f.size for f in index.files)
    assert index.ext_counts[".py"] == 2          # küçük harfe çevrilir
    assert index.ext_counts[""] == 2             # README ve .env
    assert index.ext_sizes[".txt"] == 3


def test_dir_entries_depth_and_empty_semantics(tree):
    index = ProjectIndex.build(tree)
    by_rel = {d.rel: d for d in index.dirs}
    assert by_rel["src"].depth == 1 and by_rel["src/pkg"].depth == 2
    assert index.max_depth == 2
    assert by_rel["empty"].file_count == 0 and by_rel["empty"].dir_count == 0
    # yalnızca dışlanan 'venv' içeren klasör boş sayılmaz
    assert by_rel["onlyvenv"].dir_count == 1
    assert "venv" not in by_rel and ".git" not in by_rel


def test_files_with_ext_is_case_insensitive(tree):
    index = ProjectIndex.build(tree)
    assert sorted(f.rel for f in index.files_with_ext(".py")) == ["main.py", "src/a.PY"]
    assert sorted(f.rel for f in index.files_with_ext(".PY", ".txt")) == ["main.py", "src/a.PY", "src/pkg/b.txt"]


def entry(index, rel):
    return next(f for f in index.files if f.rel == rel)


def test_read_text_encodings(tmp_path):
    write(tmp_path / "utf8.txt", "şğüıöç İ".encode("utf-8"), mode="wb")
    write(tmp_path / "bom.txt", b"\xef\xbb\xbfmerhaba", mode="wb")
    write(tmp_path / "cp1254.txt", "şğüıöç İ".encode("cp1254"), mode="wb")
    index = ProjectIndex.build(tmp_path)
    assert index.read_text(entry(index, "utf8.txt")) == "şğüıöç İ"
    assert index.read_text(entry(index, "bom.txt")) == "merhaba"      # BOM atılır
    assert index.read_text(entry(index, "cp1254.txt")) == "şğüıöç İ"  # eski kodda 'binary' sayılıyordu
    assert not index.is_binary(entry(index, "cp1254.txt"))


@pytest.mark.parametrize("encoding", ["utf-16", "utf-16-be", "utf-32"])
def test_bom_marked_utf16_and_utf32_are_text(tmp_path, encoding):
    """PowerShell `>` çıktısı UTF-16 LE BOM'ludur; NUL baytları yüzünden ikilik sayılıp analizden düşüyordu."""
    data = ("﻿" if encoding == "utf-16-be" else "") + "x = 'şğü'\n"
    write(tmp_path / "a.ps1", data.encode(encoding), mode="wb")
    index = ProjectIndex.build(tmp_path)
    e = entry(index, "a.ps1")
    assert not index.is_binary(e)
    assert index.read_text(e) == "x = 'şğü'\n"


@pytest.mark.parametrize("encoding", ["utf-16-le", "utf-16-be"])
def test_bomless_utf16_text_is_text(tmp_path, encoding):
    """Bazı Windows araçları (ODBC, yerelleştirme, `Out-File -Encoding Unicode` olmadan yazan betikler) BOM yazmaz."""
    text = "[2026-08-31] gecelik iş başladı\r\nadım 2\r\n" * 3
    write(tmp_path / "a.log", text.encode(encoding), mode="wb")
    index = ProjectIndex.build(tmp_path)
    e = entry(index, "a.log")
    assert not index.is_binary(e)
    assert index.read_text(e) == text


def test_binary_with_nul_pattern_stays_binary(tmp_path):
    write(tmp_path / "x.bin", bytes([1, 0, 2, 0, 0, 0, 3, 0]) * 64 + b"\x00\x05" * 32, mode="wb")   # çift konumda NUL var
    write(tmp_path / "y.bin", b"\x01\x00" * 10 + bytes(range(256)) * 4, mode="wb")                 # NUL oranı düşük
    index = ProjectIndex.build(tmp_path)
    assert index.is_binary(entry(index, "x.bin")) and index.is_binary(entry(index, "y.bin"))


def test_binary_and_oversize_return_none(tmp_path):
    write(tmp_path / "img.bin", b"\x89PNG\x00\x00data", mode="wb")
    write(tmp_path / "big.txt", "a" * 100)
    index = ProjectIndex.build(tmp_path)
    assert index.is_binary(entry(index, "img.bin"))
    assert index.read_text(entry(index, "img.bin")) is None
    assert index.read_text(entry(index, "big.txt"), max_bytes=50) is None
    assert index.read_text(entry(index, "big.txt")) == "a" * 100


def test_read_text_is_cached(tmp_path):
    f = write(tmp_path / "a.py", "v1")
    index = ProjectIndex.build(tmp_path)
    e = entry(index, "a.py")
    assert index.read_text(e) == "v1"
    f.write_text("v2")
    assert index.read_text(e) == "v1"        # ikinci okuma diskten gelmez


def test_empty_file_text_is_empty_string_not_none(tmp_path):
    write(tmp_path / "e.txt", "")
    index = ProjectIndex.build(tmp_path)
    assert index.read_text(entry(index, "e.txt")) == ""


def test_hash_full_and_partial(tmp_path):
    head = b"A" * PARTIAL_HASH_BYTES
    write(tmp_path / "one.bin", head + b"1", mode="wb")
    write(tmp_path / "two.bin", head + b"2", mode="wb")
    write(tmp_path / "three.bin", head + b"1", mode="wb")
    index = ProjectIndex.build(tmp_path)
    one, two, three = (entry(index, n) for n in ("one.bin", "two.bin", "three.bin"))
    assert index.hash_file(one, partial=True) == index.hash_file(two, partial=True)
    assert index.hash_file(one) != index.hash_file(two)
    assert index.hash_file(one) == index.hash_file(three)


def test_unreadable_directory_is_recorded(tmp_path, monkeypatch):
    write(tmp_path / "ok" / "a.txt")
    (tmp_path / "locked").mkdir()
    real = os.scandir

    def fake(path):
        if str(path).endswith("locked"):
            raise PermissionError("erişim reddedildi")
        return real(path)

    monkeypatch.setattr(os, "scandir", fake)
    index = ProjectIndex.build(tmp_path)
    assert [p.name for p, _ in index.errors] == ["locked"]
    assert rels(index) == ["ok/a.txt"]


@pytest.mark.skipif(sys.platform == "win32", reason="symlink oluşturma Windows'ta yetki ister")
def test_symlinks_are_skipped(tmp_path):
    write(tmp_path / "real.txt")
    os.symlink(tmp_path / "real.txt", tmp_path / "link.txt")
    index = ProjectIndex.build(tmp_path)
    assert rels(index) == ["real.txt"]


def test_progress_callback_reports_file_counts(tmp_path, monkeypatch):
    monkeypatch.setattr("src.core.project_index.PROGRESS_EVERY_FILES", 3)
    for i in range(7):
        write(tmp_path / f"f{i}.txt")
    seen = []
    ProjectIndex.build(tmp_path, progress=seen.append)
    assert seen and seen[-1] <= 7 and seen == sorted(seen)


def test_target_is_excluded_only_next_to_a_build_manifest(tmp_path):
    write(tmp_path / "rust" / "Cargo.toml", "[package]")
    write(tmp_path / "rust" / "target" / "debug" / "a.rlib")
    write(tmp_path / "rust" / "src" / "main.rs")
    write(tmp_path / "plain" / "target" / "notes.txt")               # manifest yok: kaynak olabilir
    write(tmp_path / "maven" / "pom.xml", "<project/>")
    write(tmp_path / "maven" / "target" / "x.class")
    assert rels(ProjectIndex.build(tmp_path)) == [
        "maven/pom.xml", "plain/target/notes.txt", "rust/Cargo.toml", "rust/src/main.rs"]


def test_dotnet_bin_and_obj_are_excluded_only_with_a_project_file(tmp_path):
    write(tmp_path / "app" / "App.csproj", "<Project/>")
    write(tmp_path / "app" / "bin" / "Debug" / "app.dll")
    write(tmp_path / "app" / "obj" / "x.cache")
    write(tmp_path / "app" / "Program.cs")
    write(tmp_path / "scripts" / "bin" / "run.sh")                   # .csproj yok: gerçek betik klasörü
    assert rels(ProjectIndex.build(tmp_path)) == ["app/App.csproj", "app/Program.cs", "scripts/bin/run.sh"]


def test_virtualenv_is_detected_by_pyvenv_cfg_whatever_its_name(tmp_path):
    write(tmp_path / "myenv" / "pyvenv.cfg", "home = x")
    write(tmp_path / "myenv" / "Lib" / "site-packages" / "dep.py")
    write(tmp_path / "app.py")
    assert rels(ProjectIndex.build(tmp_path)) == ["app.py"]


# ---- .gitignore duyarlılığı ------------------------------------------------------------------

def gitignore_tree(tmp_path):
    write(tmp_path / ".gitignore", "*.log\ngen/\n/local.cfg\n")
    write(tmp_path / "app.py", "x")
    write(tmp_path / "run.log", "log")
    write(tmp_path / "local.cfg", "cfg")
    write(tmp_path / "gen" / "out.py", "generated")
    write(tmp_path / "sub" / "local.cfg", "kök kuralı buna uymaz")
    write(tmp_path / "sub" / ".gitignore", "*.cache\n")
    write(tmp_path / "sub" / "a.cache", "x")
    write(tmp_path / "sub" / "keep.py", "x")
    return tmp_path


def test_gitignored_files_and_dirs_are_left_out_and_counted(tmp_path):
    index = ProjectIndex.build(gitignore_tree(tmp_path))
    assert rels(index) == [".gitignore", "app.py", "sub/.gitignore", "sub/keep.py", "sub/local.cfg"]
    assert index.gitignore_applied is True
    assert index.gitignored == {"files": 3, "dirs": 1}          # run.log, local.cfg, sub/a.cache; gen/ (içi sayılmaz)


def test_respect_gitignore_can_be_disabled(tmp_path):
    index = ProjectIndex.build(gitignore_tree(tmp_path), respect_gitignore=False)
    assert "gen/out.py" in rels(index) and "run.log" in rels(index)
    assert index.gitignore_applied is False and index.gitignored == {"files": 0, "dirs": 0}


def test_directory_with_only_ignored_files_is_not_reported_empty(tmp_path):
    write(tmp_path / ".gitignore", "*.log\n")
    write(tmp_path / "logs" / "a.log", "x")
    (tmp_path / "truly_empty").mkdir()
    index = ProjectIndex.build(tmp_path)
    by_rel = {d.rel: d for d in index.dirs}
    assert by_rel["logs"].file_count == 1                         # git boş klasörü izlemez; içi dolu klasör "boş" sayılmaz
    assert by_rel["truly_empty"].file_count == 0 and by_rel["truly_empty"].dir_count == 0


def test_unreadable_gitignore_is_reported_in_index_errors(tmp_path, monkeypatch):
    import builtins
    write(tmp_path / ".gitignore", "x\n")
    write(tmp_path / "a.py", "x")
    real_open = builtins.open

    def deny(path, *args, **kwargs):
        if str(path).endswith(".gitignore"):
            raise PermissionError("kilitli")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", deny)
    index = ProjectIndex.build(tmp_path)
    assert "a.py" in rels(index)                                  # analiz ignore'suz sürer
    assert any("kilitli" in message for _, message in index.errors)


@pytest.mark.skipif(__import__("shutil").which("git") is None, reason="git kurulu değil")
def test_tracked_file_matching_a_gitignore_rule_stays_in_the_index(tmp_path):
    import subprocess
    write(tmp_path / ".gitignore", ".gitignore\n*.txt\n")
    write(tmp_path / "forced.txt", "x")
    write(tmp_path / "notes.txt", "x")
    write(tmp_path / "app.py", "x")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-f", ".gitignore", "forced.txt", "app.py"], cwd=tmp_path, check=True)
    index = ProjectIndex.build(tmp_path)
    assert rels(index) == [".gitignore", "app.py", "forced.txt"]
    assert index.gitignored == {"files": 1, "dirs": 0}                  # yalnızca notes.txt
