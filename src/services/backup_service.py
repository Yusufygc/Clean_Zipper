import logging
import os
import zipfile
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class BackupService:
    def __init__(self, backup_root: Optional[Path] = None):
        self._backup_root = backup_root or Path.home() / '.gitclean_backups'
        self._backup_root.mkdir(parents=True, exist_ok=True)

    def create_backup(self, project_path: Path, backup_name: Optional[str] = None) -> Dict:
        """Projeyi zip olarak yedekler. `complete` False ise bazı dosyalar eklenemedi (`failed_files`)."""
        if not backup_name:
            backup_name = f"{project_path.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir = self._backup_root / backup_name
        zip_path = backup_dir / f"{backup_name}.zip"
        result = {'success': False, 'complete': False, 'backup_name': backup_name, 'size': 0,
                  'failed_files': [], 'error': None}
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(project_path):
                    if '.git' in dirs: dirs.remove('.git')
                    for file in files:
                        fp = Path(root) / file
                        try:
                            zf.write(fp, str(fp.relative_to(project_path)))
                        except OSError as e:
                            result['failed_files'].append((str(fp), str(e)))
                            logger.warning("Yedeğe eklenemedi: %s (%s)", fp, e)
            result['size'] = zip_path.stat().st_size
            result['success'] = True
            result['complete'] = not result['failed_files']
        except Exception as e:
            logger.exception("Yedek oluşturulamadı: %s", zip_path)
            result['error'] = str(e)
            self._cleanup_partial(zip_path, backup_dir)
        return result

    @staticmethod
    def _cleanup_partial(zip_path: Path, backup_dir: Path):
        try:
            zip_path.unlink(missing_ok=True)
            backup_dir.rmdir()                       # yalnızca boşsa silinir
        except OSError:
            logger.warning("Yarım kalan yedek temizlenemedi: %s", backup_dir, exc_info=True)

    def list_backups(self) -> List[Dict]:
        backups = []
        if self._backup_root.exists():
            for d in self._backup_root.iterdir():
                if d.is_dir():
                    backups.append({'name': d.name, 'created': datetime.fromtimestamp(d.stat().st_ctime).isoformat()})
        return sorted(backups, key=lambda x: x['created'], reverse=True)
