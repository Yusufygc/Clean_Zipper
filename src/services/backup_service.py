import os, zipfile
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

class BackupService:
    def __init__(self, backup_root: Optional[Path] = None):
        self._backup_root = backup_root or Path.home() / '.gitclean_backups'
        self._backup_root.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, project_path: Path, backup_name: Optional[str] = None) -> Dict:
        if not backup_name:
            backup_name = f"{project_path.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_dir = self._backup_root / backup_name
        backup_dir.mkdir(parents=True, exist_ok=True)
        zip_path = backup_dir / f"{backup_name}.zip"
        result = {'success': False, 'backup_name': backup_name, 'size': 0}
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(project_path):
                    if '.git' in dirs: dirs.remove('.git')
                    for file in files:
                        fp = Path(root) / file
                        zf.write(fp, str(fp.relative_to(project_path)))
            result['size'] = zip_path.stat().st_size
            result['success'] = True
        except Exception as e:
            result['error'] = str(e)
        return result
    
    def list_backups(self) -> List[Dict]:
        backups = []
        if self._backup_root.exists():
            for d in self._backup_root.iterdir():
                if d.is_dir():
                    backups.append({'name': d.name, 'created': datetime.fromtimestamp(d.stat().st_ctime).isoformat()})
        return sorted(backups, key=lambda x: x['created'], reverse=True)
