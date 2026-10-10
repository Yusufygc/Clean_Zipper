from pathlib import Path

import pytest

from src.services.cleanup_service import CleanupService


class FakeTrash:
    def __init__(self, fail_on=()):
        self.moved = []
        self.fail_on = set(fail_on)

    def __call__(self, path):
        if Path(path).name in self.fail_on:
            raise OSError("erişim reddedildi")
        self.moved.append(Path(path))


def write(path: Path, content: str = "x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def project(tmp_path):
    write(tmp_path / "src" / "app.py")
    write(tmp_path / "src" / "__pycache__" / "app.cpython-310.pyc", "abc")
    write(tmp_path / "src" / "__pycache__" / "b.pyc", "abcd")
    write(tmp_path / "notes.tmp", "12")
    write(tmp_path / "run.log", "log")
    write(tmp_path / "old.bak", "bak")
    write(tmp_path / "venv" / "lib" / "x.pyc")
    write(tmp_path / "venv" / "lib" / "__pycache__" / "y.pyc")
    write(tmp_path / "node_modules" / "pkg" / "a.log")
    write(tmp_path / ".git" / "objects" / "z.tmp")
    return tmp_path


def paths(items, root):
    return {i.path.relative_to(root).as_posix() for i in items}


def test_excluded_dirs_are_never_scanned(project):
    items = CleanupService(FakeTrash()).scan(project, ["python_cache", "temp_files", "logs", "backups"])
    found = paths(items, project)
    assert not any(p.startswith(("venv", "node_modules", ".git")) for p in found)



def test_virtualenv_with_any_name_and_build_outputs_are_never_scanned(tmp_path):
    """Analizle aynı dışlama kuralı (`is_excluded_dir`): adı ne olursa olsun sanal ortam, bağlamsal derleme klasörü."""
    write(tmp_path / "myenv" / "pyvenv.cfg", "home = x")
    write(tmp_path / "myenv" / "Lib" / "site-packages" / "__pycache__" / "m.pyc")
    write(tmp_path / "rs" / "Cargo.toml", "[package]")
    write(tmp_path / "rs" / "target" / "debug" / "build.log")
    write(tmp_path / "plain" / "target" / "keep.log")
    found = paths(CleanupService(FakeTrash()).scan(tmp_path, ["python_cache", "logs"]), tmp_path)
    assert found == {"plain/target/keep.log"}

def test_pycache_dir_is_single_item_with_totals(project):
    items = CleanupService(FakeTrash()).scan(project, ["python_cache"])
    assert len(items) == 1
    item = items[0]
    assert item.is_dir and item.path.name == "__pycache__"
    assert item.file_count == 2
    assert item.size == 7


def test_default_categories_skip_logs_and_backups(project):
    found = paths(CleanupService(FakeTrash()).scan(project), project)
    assert "notes.tmp" in found
    assert "run.log" not in found
    assert "old.bak" not in found


def test_category_selection_is_applied(project):
    found = paths(CleanupService(FakeTrash()).scan(project, ["logs"]), project)
    assert found == {"run.log"}


def test_empty_category_list_selects_nothing(project):
    assert CleanupService(FakeTrash()).scan(project, []) == []


def test_preview_keeps_legacy_keys(project):
    preview = CleanupService(FakeTrash()).preview_cleanup(project, ["python_cache", "temp_files"])
    assert preview["total_files"] == 3
    assert preview["total_size"] == 9
    assert {f["category"] for f in preview["files"]} == {"python_cache", "temp_files"}


def test_dry_run_touches_nothing(project):
    trash = FakeTrash()
    result = CleanupService(trash).cleanup(project, dry_run=True)
    assert result["success"] and result["dry_run"]
    assert result["cleaned_files"] == 0
    assert trash.moved == []


def test_cleanup_moves_items_to_trash(project):
    trash = FakeTrash()
    result = CleanupService(trash).cleanup(project, ["python_cache", "temp_files"], dry_run=False)
    assert result["success"]
    assert result["cleaned_files"] == 3
    assert {p.name for p in trash.moved} == {"__pycache__", "notes.tmp"}


def test_failure_is_reported_and_others_continue(project):
    trash = FakeTrash(fail_on={"__pycache__"})
    result = CleanupService(trash).cleanup(project, ["python_cache", "temp_files"], dry_run=False)
    assert not result["success"]
    assert [Path(p).name for p, _ in result["failed"]] == ["__pycache__"]
    assert result["cleaned_files"] == 1
    assert [p.name for p in trash.moved] == ["notes.tmp"]
