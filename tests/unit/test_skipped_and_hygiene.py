import ast
import logging
import os
from pathlib import Path

from src.analyzers.duplicate_finder import DuplicateFinder
from src.core.project_index import ProjectIndex
from src.languages import parse_file
from src.languages.base import LanguageSupport
from src.languages.registry import LanguageRegistry
from src.services.cleanup_service import CleanupService
from src.services.project_service import ProjectService

SRC = Path(__file__).resolve().parents[2] / "src"


def write(path: Path, content="x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
    return path


def entry_of(index, rel):
    return next(f for f in index.files if f.rel == rel)


# ---- atlanan dosyalar görünür -------------------------------------------------------

def test_too_large_file_is_marked_skipped(tmp_path):
    write(tmp_path / "big.py", "x = 1\n" * 10)
    index = ProjectIndex.build(tmp_path)
    assert index.read_text(entry_of(index, "big.py"), max_bytes=10) is None
    assert index.skipped == {"big.py": "too_large"}


def test_unreadable_file_is_marked_skipped(tmp_path, monkeypatch):
    write(tmp_path / "a.py", "x = 1\n")
    index = ProjectIndex.build(tmp_path)
    real_open = open

    def deny(path, *args, **kwargs):
        if str(path).endswith("a.py"):
            raise PermissionError("kilitli")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", deny)
    assert index.read_text(entry_of(index, "a.py")) is None
    assert index.skipped == {"a.py": "unreadable"}


def test_binary_file_is_not_reported_as_skipped(tmp_path):
    write(tmp_path / "blob.bin", b"\x00\x01\x02")
    index = ProjectIndex.build(tmp_path)
    assert index.read_text(entry_of(index, "blob.bin")) is None
    assert index.skipped == {}                          # ikilik dosya beklenen durum


def test_first_skip_reason_is_kept(tmp_path):
    write(tmp_path / "a.py", "x")
    index = ProjectIndex.build(tmp_path)
    entry = entry_of(index, "a.py")
    index.mark_skipped(entry, "too_large")
    index.mark_skipped(entry, "unreadable")
    assert index.skipped == {"a.py": "too_large"}


def test_parse_crash_and_minified_files_are_marked_skipped(tmp_path):
    class Boom(LanguageSupport):
        id, display_name, extensions = "boom", "Boom", (".boom",)

        def analyze(self, text):
            raise RuntimeError("patladı")

    registry = LanguageRegistry()
    registry.register(Boom())
    write(tmp_path / "a.boom", "x")
    index = ProjectIndex.build(tmp_path)
    assert parse_file(index, index.files[0], registry) is None
    assert index.skipped == {"a.boom": "parse_error"}

    write(tmp_path / "chunk.py", "x=1;" * 3000)       # tek satır, 12 KB: küçültülmüş sayılır
    index = ProjectIndex.build(tmp_path)
    assert parse_file(index, entry_of(index, "chunk.py")) is None
    assert index.skipped["chunk.py"] == "minified"


def test_duplicate_finder_marks_unhashable_files(tmp_path, monkeypatch):
    write(tmp_path / "a.bin", b"A" * 2048)
    write(tmp_path / "b.bin", b"A" * 2048)
    index = ProjectIndex.build(tmp_path)

    def broken(entry, partial=False):
        raise PermissionError("kilitli")

    monkeypatch.setattr(index, "hash_file", broken)
    assert DuplicateFinder().analyze(index) == []
    assert index.skipped == {"a.bin": "unreadable", "b.bin": "unreadable"}


def test_analysis_reports_skipped_counts_and_unreadable_dirs(tmp_path, monkeypatch, caplog):
    write(tmp_path / "big.py", "x = 1\n" * 10)
    write(tmp_path / "ok.py", "y = 2\n")
    (tmp_path / "locked").mkdir()
    real_scandir = os.scandir

    def fake(path):
        if str(path).endswith("locked"):
            raise PermissionError("erişim reddedildi")
        return real_scandir(path)

    monkeypatch.setattr(os, "scandir", fake)
    monkeypatch.setattr("src.core.project_index.DEFAULT_MAX_TEXT_BYTES", 20)
    monkeypatch.setattr(ProjectIndex.read_text, "__defaults__", (20,))
    service = ProjectService()
    service.set_project(tmp_path)
    with caplog.at_level(logging.INFO):
        result = service.analyze_project()
    assert result["skipped_files"].get("unreadable_dir") == 1
    assert result["skipped_files"].get("too_large", 0) >= 1
    assert "Analize girmeyen öğeler" in caplog.text


def test_clean_project_has_no_skipped_files(tmp_path):
    write(tmp_path / "ok.py", "x = 1\n")
    service = ProjectService()
    service.set_project(tmp_path)
    assert service.analyze_project()["skipped_files"] == {}


# ---- temizlik loglaması ---------------------------------------------------------------------

def test_cleanup_failure_is_logged_as_warning(tmp_path, caplog):
    write(tmp_path / "a.tmp", "x")

    def deny(path):
        raise OSError("kilitli")

    with caplog.at_level(logging.WARNING):
        result = CleanupService(trash_func=deny).cleanup(tmp_path, dry_run=False)
    assert not result["success"]
    assert "a.tmp" in caplog.text and "kilitli" in caplog.text


# ---- gerileme koruması: sessiz hata yutma yasak ---------------------------------------------------

def _python_files():
    yield from SRC.rglob("*.py")                       # arayüz (`qml_ui`) dahil, istisna yok


def _handler_logs(handler: ast.ExceptHandler) -> bool:
    for node in ast.walk(ast.Module(body=handler.body, type_ignores=[])):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and isinstance(node.func.value, ast.Name) and node.func.value.id in ("logger", "logging"):
            return True
        if isinstance(node, ast.Raise):
            return True
    return False


def test_no_bare_except_and_no_silent_broad_except():
    offenders = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8-sig"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ExceptHandler):
                continue
            where = f"{path.relative_to(SRC.parent)}:{node.lineno}"
            if node.type is None:
                offenders.append(f"{where} çıplak except")
                continue
            broad = isinstance(node.type, ast.Name) and node.type.id in ("Exception", "BaseException")
            if broad and not _handler_logs(node):
                offenders.append(f"{where} geniş except loglamıyor ve yeniden fırlatmıyor")
    assert offenders == []
