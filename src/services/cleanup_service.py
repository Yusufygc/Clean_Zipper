import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

from send2trash import send2trash

from src.core.exclusions import is_excluded_dir

logger = logging.getLogger(__name__)


@dataclass
class CleanupItem:
    path: Path
    size: int
    category: str
    is_dir: bool = False
    file_count: int = 1


class CleanupService:
    """Geçici dosya ve önbellekleri Geri Dönüşüm Kutusu'na taşıyan temizlik servisi."""

    CLEANUP_CATEGORIES = {
        'python_cache': {
            'label': 'Python önbelleği (__pycache__, .pyc, .pyo)',
            'extensions': ['.pyc', '.pyo'],
            'directories': ['__pycache__'],
            'default_enabled': True,
        },
        'temp_files': {
            'label': 'Geçici dosyalar (.tmp)',
            'extensions': ['.tmp'],
            'directories': [],
            'default_enabled': True,
        },
        # Kullanıcı verisi içerebilir, varsayılan kapalı.
        'logs': {
            'label': 'Log dosyaları (.log)',
            'extensions': ['.log'],
            'directories': [],
            'default_enabled': False,
        },
        'backups': {
            'label': 'Yedek dosyalar (.bak)',
            'extensions': ['.bak'],
            'directories': [],
            'default_enabled': False,
        },
    }

    def __init__(self, trash_func: Callable[[str], None] = send2trash):
        self._trash = trash_func

    @classmethod
    def default_categories(cls) -> List[str]:
        return [name for name, spec in cls.CLEANUP_CATEGORIES.items() if spec['default_enabled']]

    def scan(self, project_path: Path, categories: Optional[List[str]] = None) -> List[CleanupItem]:
        if categories is None:
            categories = self.default_categories()
        selected = {name: self.CLEANUP_CATEGORIES[name] for name in categories if name in self.CLEANUP_CATEGORIES}

        ext_map = {ext: name for name, spec in selected.items() for ext in spec['extensions']}
        dir_map = {d: name for name, spec in selected.items() for d in spec['directories']}

        items: List[CleanupItem] = []
        for root, dirs, files in os.walk(project_path):
            dirs[:] = self._collect_dirs(Path(root), dirs, dirs + files, dir_map, items)
            self._collect_files(Path(root), files, ext_map, items)
        return items

    def _collect_dirs(self, root: Path, dirs: List[str], siblings: List[str], dir_map: Dict[str, str],
                      items: List[CleanupItem]) -> List[str]:
        """Temizlenecek klasörleri `items`e ekler; `os.walk`ın içine gireceği klasörleri döndürür.

        Girilmeyecek klasörler analizle aynı kuraldır (`is_excluded_dir`): `pyvenv.cfg` içeren sanal ortamlar ve
        derleme dosyası yanındaki `target` / `bin` / `obj` dahil. `siblings`: aynı klasördeki tüm girdi adları.
        """
        kept = []
        for name in dirs:
            full = root / name
            if name in dir_map and not full.is_symlink():
                size, count = self._dir_stats(full)
                items.append(CleanupItem(full, size, dir_map[name], is_dir=True, file_count=count))
            elif not is_excluded_dir(str(full), name, siblings):
                kept.append(name)
        return kept

    @staticmethod
    def _collect_files(root: Path, files: List[str], ext_map: Dict[str, str], items: List[CleanupItem]) -> None:
        for name in files:
            path = root / name
            category = ext_map.get(path.suffix.lower())
            if category is None or path.is_symlink():
                continue
            try:
                items.append(CleanupItem(path, path.stat().st_size, category))
            except OSError as e:
                logger.debug("Dosya boyutu okunamadı: %s (%s)", path, e)

    def preview_cleanup(self, project_path: Path, categories: Optional[List[str]] = None) -> Dict:
        items = self.scan(project_path, categories)
        return {
            'total_files': sum(i.file_count for i in items),
            'total_size': sum(i.size for i in items),
            'files': [
                {'path': str(i.path), 'size': i.size, 'category': i.category, 'is_dir': i.is_dir}
                for i in items
            ],
        }

    def cleanup(self, project_path: Path, categories: Optional[List[str]] = None,
                dry_run: bool = True) -> Dict:
        items = self.scan(project_path, categories)
        result = {
            'success': True, 'dry_run': dry_run,
            'cleaned_files': 0, 'cleaned_size': 0, 'failed': [],
        }
        if dry_run:
            return result

        for item in items:
            try:
                self._trash(os.path.abspath(item.path))
            except Exception as e:
                logger.warning("Geri Dönüşüm Kutusu'na taşınamadı: %s (%s)", item.path, e)
                result['failed'].append((str(item.path), str(e)))
                continue
            result['cleaned_files'] += item.file_count
            result['cleaned_size'] += item.size
        result['success'] = not result['failed']
        return result

    @staticmethod
    def _dir_stats(directory: Path):
        size, count = 0, 0
        for root, _, files in os.walk(directory):
            for file in files:
                try:
                    size += (Path(root) / file).stat().st_size
                    count += 1
                except OSError as e:
                    logger.debug("Dosya boyutu okunamadı: %s (%s)", file, e)
                    continue
        return size, count
