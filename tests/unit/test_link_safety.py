"""Bağ güvenliği: sembolik bağ ve Windows dizin birleşimi (junction) proje dışına ya da kendi üstüne işaret edebilir.

Analiz, temizlik, arşiv, kopya ve yedek bunların içine girmez; dosya bağlarının hedefi arşive / yedeğe konmaz.
Önceden: junction üzerinden proje dışındaki `__pycache__` temizlik adayıydı, dışarıdaki dosya paylaşılan zip'e
giriyordu, kendine işaret eden junction taramayı yol uzunluğu sınırına kadar özyinelettiriyordu.
"""
import os
import zipfile
from pathlib import Path

import pytest

from src.core.exclusions import is_link
from src.core.project_index import ProjectIndex
from src.services.archive_service import ArchiveService
from src.services.backup_service import BackupService
from src.services.cleanup_service import CleanupService
from src.utils.gitignore_parser import GitignoreParser


def write(path: Path, content: str = "x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def make_dir_link(link: Path, target: Path):
    """Windows'ta yetki gerektirmeyen junction, diğerlerinde dizin sembolik bağı."""
    if os.name == "nt":
        import _winapi
        _winapi.CreateJunction(str(target), str(link))
    else:
        os.symlink(target, link, target_is_directory=True)


@pytest.fixture
def linked(tmp_path):
    outside = tmp_path / "outside"
    write(outside / "secret.txt", "GIZLI")
    write(outside / "__pycache__" / "m.pyc")
    write(outside / "notes.tmp")
    project = tmp_path / "proj"
    write(project / "app.py", "x = 1\n")
    make_dir_link(project / "junc", outside)
    make_dir_link(project / "loop", project)                         # kendine işaret eden bağ (döngü)
    return project, outside


def test_directory_links_are_detected(linked):
    project, _ = linked
    assert is_link(project / "junc") and is_link(project / "loop")
    assert not is_link(project) and not is_link(project / "app.py") and not is_link(project / "yok")


def test_index_does_not_follow_links_or_loop(linked):
    project, _ = linked
    index = ProjectIndex.build(project, respect_gitignore=False)
    assert [f.rel for f in index.files] == ["app.py"] and index.max_depth <= 1


def test_cleanup_never_offers_or_trashes_outside_files(linked):
    project, outside = linked
    trashed = []
    service = CleanupService(trash_func=trashed.append)
    assert service.scan(project, ["python_cache", "temp_files"]) == []
    service.cleanup(project, ["python_cache", "temp_files"], dry_run=False)
    assert trashed == [] and (outside / "__pycache__" / "m.pyc").exists()


def test_cleanup_refuses_paths_outside_the_project_even_if_scanned(tmp_path, monkeypatch):
    """Son savunma: tarama bir gün dışarıdaki yolu döndürse bile çöpe gönderilmez."""
    from src.services import cleanup_service as module
    project, outside = tmp_path / "p", write(tmp_path / "dis" / "x.tmp")
    project.mkdir()
    monkeypatch.setattr(module.CleanupService, "scan",
                        lambda self, root, categories=None: [module.CleanupItem(outside, 1, "temp_files")])
    trashed = []
    result = module.CleanupService(trash_func=trashed.append).cleanup(project, dry_run=False)
    assert trashed == [] and result["failed"] == [(str(outside), "proje klasörünün dışında")]


def test_archive_copy_and_backup_skip_linked_directories(linked, tmp_path):
    project, _ = linked
    archive = ArchiveService(GitignoreParser(str(project)))
    archive.create_zip(project, tmp_path / "out.zip")
    with zipfile.ZipFile(tmp_path / "out.zip") as z:
        assert z.namelist() == ["app.py"]
    archive.copy_project(project, tmp_path / "kopya")
    assert sorted(p.name for p in (tmp_path / "kopya").rglob("*")) == ["app.py"]
    result = BackupService(tmp_path / "yedek").create_backup(project, "b")
    with zipfile.ZipFile(tmp_path / "yedek" / "b" / "b.zip") as z:
        assert z.namelist() == ["app.py"]
    assert {"junc", "loop"} <= set(result["excluded_dirs"])


def test_file_symlinks_are_not_archived_or_backed_up(tmp_path):
    project = tmp_path / "proj"
    write(project / "app.py")
    secret = write(tmp_path / "id_rsa", "PRIVATE")
    try:
        os.symlink(secret, project / "notes.txt")
    except (OSError, NotImplementedError):
        pytest.skip("dosya sembolik bağı oluşturma yetkisi yok (Windows'ta Geliştirici Modu / yönetici gerekir)")
    zip_result = ArchiveService(GitignoreParser(str(project))).create_zip(project, tmp_path / "out.zip")
    with zipfile.ZipFile(tmp_path / "out.zip") as z:
        assert z.namelist() == ["app.py"]
    assert zip_result["skipped_links"] == ["notes.txt"]
    backup = BackupService(tmp_path / "yedek").create_backup(project, "b")
    assert backup["skipped_links"] == ["notes.txt"]
