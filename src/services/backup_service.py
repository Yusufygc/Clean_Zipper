import json
import logging
import os
import zipfile
from pathlib import Path
from typing import Callable, Iterator, List, Dict, Optional
from datetime import datetime

from send2trash import send2trash

from src.core.exclusions import is_excluded_dir

logger = logging.getLogger(__name__)

MAX_REPORTED_EXCLUDED = 100         # sonuçta ayrıntısı listelenen dışlanan klasör sayısı (toplam sayı her zaman verilir)
DEFAULT_MAX_BACKUPS = 5             # proje başına saklanan otomatik yedek; 0 = sınırsız
MARKER_NAME = 'backup.json'         # yedek klasöründeki kimlik: hangi projenin, ne zaman, otomatik adlı mı


def default_backup_root() -> Path:
    return Path.home() / '.gitclean_backups'


class BackupService:
    """Zip yedekleri ve rotasyon.

    Rotasyon: başarılı ve tam bir otomatik adlı yedekten sonra aynı projenin en yeni `max_backups` otomatik yedeği
    kalır, eskiler Geri Dönüşüm Kutusu'na taşınır (kalıcı silme yok). Elle adlandırılmış yedeklere ve kimlik dosyası
    (`backup.json`) olmayan eski yedeklere hiç dokunulmaz: hangi projeye ait oldukları bilinemez.
    """

    def __init__(self, backup_root: Optional[Path] = None, max_backups: int = DEFAULT_MAX_BACKUPS,
                 trash_func: Callable[[str], None] = send2trash):
        self._backup_root = backup_root or default_backup_root()
        self._backup_root.mkdir(parents=True, exist_ok=True)
        self.max_backups = max_backups
        self._trash = trash_func

    def create_backup(self, project_path: Path, backup_name: Optional[str] = None) -> Dict:
        """Projeyi zip olarak yedekler. `complete` False ise bazı dosyalar eklenemedi (`failed_files`).

        Yedek felaket kurtarma içindir: `.gitignore`'a BAKMAZ, çünkü `.env`, yerel veritabanları, modeller gibi git'te
        olmayan ve geri getirilemeyen dosyalar çoğunlukla ignore'dadır. Yalnızca yeniden üretilebilir klasörler
        (`.git`, `venv`, `node_modules`, `__pycache__`, `dist`, `build`, önbellekler) dışarıda kalır; hangileri
        olduğu sonuçta `excluded_dirs` (en çok 100) ve `excluded_dir_count` olarak bildirilir.
        """
        automatic = not backup_name
        created = datetime.now().astimezone()       # yerel saat, dilim bilgisiyle
        if automatic:
            backup_name = self._free_name(f"{project_path.name}_{created.strftime('%Y%m%d_%H%M%S')}")
        backup_dir = self._backup_root / backup_name
        zip_path = backup_dir / f"{backup_name}.zip"
        result = {'success': False, 'complete': False, 'backup_name': backup_name, 'size': 0,
                  'failed_files': [], 'error': None, 'excluded_dirs': [], 'excluded_dir_count': 0,
                  'removed_backups': [], 'rotation_errors': []}
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                excluded: List[str] = []
                for fp in self._backup_files(Path(project_path), zip_path, excluded):
                    try:
                        zf.write(fp, str(fp.relative_to(project_path)))
                    except OSError as e:
                        result['failed_files'].append((str(fp), str(e)))
                        logger.warning("Yedeğe eklenemedi: %s (%s)", fp, e)
                result['excluded_dir_count'] = len(excluded)
                result['excluded_dirs'] = excluded[:MAX_REPORTED_EXCLUDED]
            result['size'] = zip_path.stat().st_size
            result['success'] = True
            result['complete'] = not result['failed_files']
            self._write_marker(backup_dir, project_path, created, automatic, result['complete'])
        except Exception as e:
            logger.exception("Yedek oluşturulamadı: %s", zip_path)
            result['error'] = str(e)
            self._cleanup_partial(zip_path, backup_dir)
            return result
        if automatic and result['complete']:
            self._rotate(project_path, result)
        return result

    def _free_name(self, base: str) -> str:
        """Aynı saniyede alınan ikinci otomatik yedek öncekinin üzerine yazmasın: `ad_2`, `ad_3` ..."""
        name, n = base, 1
        while (self._backup_root / name).exists():
            n += 1
            name = f"{base}_{n}"
        return name

    @staticmethod
    def _project_key(project_path: Path) -> str:
        return os.path.normcase(str(Path(project_path).resolve()))

    def _write_marker(self, backup_dir: Path, project_path: Path, created: datetime, automatic: bool, complete: bool):
        marker = {'project': str(Path(project_path).resolve()), 'created': created.isoformat(timespec='microseconds'),
                  'automatic': automatic, 'complete': complete}
        try:
            (backup_dir / MARKER_NAME).write_text(json.dumps(marker, ensure_ascii=False, indent=1), encoding='utf-8')
        except OSError:
            logger.warning("Yedek kimlik dosyası yazılamadı (rotasyona girmez): %s", backup_dir, exc_info=True)

    def _read_marker(self, backup_dir: Path) -> Optional[Dict]:
        try:
            data = json.loads((backup_dir / MARKER_NAME).read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    def _rotate(self, project_path: Path, result: Dict):
        """Aynı projenin tam, otomatik yedeklerinden en yeni `max_backups` tanesi kalır; fazlası çöpe."""
        if self.max_backups <= 0:
            return
        key = self._project_key(project_path)
        own = []
        for d in self._backup_root.iterdir():
            marker = self._read_marker(d) if d.is_dir() else None
            if (marker and marker.get('automatic') is True and marker.get('complete') is True
                    and self._project_key(Path(str(marker.get('project', '')))) == key):
                own.append((str(marker.get('created', '')), d.name, d))
        own.sort(reverse=True)
        for _, name, d in own[self.max_backups:]:
            try:
                self._trash(str(d))
                result['removed_backups'].append(name)
            except OSError as e:
                logger.warning("Eski yedek çöpe taşınamadı: %s (%s)", d, e)
                result['rotation_errors'].append((name, str(e)))

    @staticmethod
    def _backup_files(project_path: Path, zip_path: Path, excluded: List[str]) -> Iterator[Path]:
        """Yedeğe girecek dosyalar. Girilmeyen klasörlerin proje köküne göre yolu `excluded`a eklenir.
        Yedek zip'inin kendisi (yedek klasörü proje içindeyse) atlanır."""
        own_zip = zip_path.resolve()
        for root, dirs, files in os.walk(project_path):
            siblings = dirs + files
            kept = []
            for name in dirs:
                if is_excluded_dir(os.path.join(root, name), name, siblings):
                    excluded.append((Path(root) / name).relative_to(project_path).as_posix())
                else:
                    kept.append(name)
            dirs[:] = kept
            for name in files:
                path = Path(root) / name
                if path.resolve() != own_zip:
                    yield path

    @staticmethod
    def _cleanup_partial(zip_path: Path, backup_dir: Path):
        try:
            zip_path.unlink(missing_ok=True)
            backup_dir.rmdir()                       # yalnızca boşsa silinir
        except OSError:
            logger.warning("Yarım kalan yedek temizlenemedi: %s", backup_dir, exc_info=True)

    @property
    def backup_root(self) -> Path:
        return self._backup_root

    def list_backups(self) -> List[Dict]:
        backups = []
        if self._backup_root.exists():
            for d in self._backup_root.iterdir():
                if d.is_dir():
                    backups.append({'name': d.name, 'created': datetime.fromtimestamp(d.stat().st_ctime).isoformat()})
        return sorted(backups, key=lambda x: x['created'], reverse=True)
