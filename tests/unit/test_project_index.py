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
