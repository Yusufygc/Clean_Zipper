import logging
import os
import zipfile
import shutil
import re
from pathlib import Path
from typing import Optional, Callable, Dict, List, Tuple

from src.utils.gitignore_parser import GitignoreParser

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int], None]


class ArchiveService:
    """Farklı sıkıştırma profillerini destekleyen kurumsal arşivleme servisi.

    Sonuç sözlüğü: `success` çıktı üretildi mi, `complete` hiçbir dosya atlanmadan mı üretildi,
    `failed_files` eklenemeyen dosyalar (yol, hata), `error` ölümcül hata mesajı.
    """

    # Arşivleme Profillerinin Tanımları ve Filtre Kuralları (Düzenli İfadeler)
    PROFILES = {
        "Geliştirici (Standart)": {
            "excludes": [],
            "description": "Sadece .gitignore kurallarını uygular. Geliştirici araçları ve testler korunur."
        },
        "Müşteri Teslimi (Temiz)": {
            "excludes": [
                r"tests?/.*", r"test_.*\.py", r"docs?/.*", r"\.pytest_cache/.*",
                r"\.coverage", r"htmlcov/.*", r"benchmarks?/.*", r"\.github/.*",
                r"venv/.*", r"\.venv/.*"
            ],
            "description": "Testler, dökümanlar ve CI/CD ayarları elenerek sadece temiz teslimat kodu kalır."
        },
        "Yayınlama / Dağıtım (Minimal)": {
            "excludes": [
                r"tests?/.*", r"test_.*\.py", r"docs?/.*", r"\.pytest_cache/.*",
                r"\.coverage", r"htmlcov/.*", r"benchmarks?/.*", r"\.github/.*",
                r"requirements-dev\.txt", r"\.env.*", r"pytest\.ini", r"tox\.ini",
                r"\.gitattributes", r"CONTRIBUTING.*", r"LICENSE.*", r"README.*",
                r"venv/.*", r"\.venv/.*"
            ],
            "description": "Sadece çalışması için gerekli kaynak dosyalar kalır. Geliştirme bağımlılıkları ve konfigürasyonları elenir."
        }
    }

    def __init__(self, parser: Optional[GitignoreParser] = None):
        self.parser = parser
        # Genel olarak her koşulda atlanacak kritik sistem klasörleri
        self._excluded_dirs = {'.git', '__pycache__', 'venv', 'node_modules', '.idea', '.vs', 'dist', 'build'}

    def _should_exclude_by_profile(self, relative_path_str: str, profile_name: str) -> bool:
        """Dosyanın seçilen profile göre elenmesi gerekip gerekmediğini doğrular."""
        profile = self.PROFILES.get(profile_name)
        if not profile:
            return False

        # Path seperator'ları standardizasyon için '/' yapıyoruz
        rp_normalized = relative_path_str.replace('\\', '/')

        for pattern in profile["excludes"]:
            if re.match(pattern, rp_normalized, re.IGNORECASE):
                return True
        return False

    def _refuse_if_gitignore_unreadable(self, result: Dict) -> bool:
        """Okunamayan .gitignore ile arşivleme gizli dosyaları sızdırabilir; işlem reddedilir."""
        if self.parser is not None and self.parser.load_error:
            result['error'] = f"{self.parser.load_error}. Gizli dosyaların arşive sızmaması için işlem durduruldu."
            logger.error("Arşivleme reddedildi: %s", result['error'])
            return True
        return False

    def _collect_files(self, source_dir: Path, profile_name: str, result: Dict,
                       skip_root_dir: Optional[str] = None,
                       skip_file: Optional[Path] = None) -> List[Tuple[Path, Path]]:
        """Kaynak ağacı gezer, .gitignore ve profil süzgecinden geçen (mutlak, göreli) yolları döner."""
        files: List[Tuple[Path, Path]] = []
        for root, dirs, filenames in os.walk(source_dir):
            root_path = Path(root)
            dirs[:] = [d for d in dirs
                       if d not in self._excluded_dirs
                       and not (skip_root_dir and root_path == source_dir and d == skip_root_dir)]
            for name in filenames:
                fp = root_path / name
                rp = fp.relative_to(source_dir)

                # Hedef dosyanın kendisini (zip kaynak içindeyse) atla
                if skip_file is not None and fp.resolve() == skip_file:
                    result['skipped_files'] += 1
                    continue
                # 1. .gitignore Kurallarını Uygula
                if self.parser and self.parser.should_ignore(str(fp)):
                    result['skipped_files'] += 1
                    continue
                # 2. Seçilen Sıkıştırma Profil Filtrelerini Uygula
                if self._should_exclude_by_profile(str(rp), profile_name):
                    result['skipped_files'] += 1
                    continue
                files.append((fp, rp))
        return files

    @staticmethod
    def _record_failure(result: Dict, path: Path, error: Exception):
        result['failed_files'].append((str(path), str(error)))
        logger.warning("Dosya işlenemedi: %s (%s)", path, error)

    @staticmethod
    def _remove_partial(path: Path):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            logger.warning("Yarım kalan çıktı silinemedi: %s", path, exc_info=True)

    def create_zip(self, source_dir: Path, output_path: Path,
                   profile_name: str = "Geliştirici (Standart)",
                   progress_callback: Optional[ProgressCallback] = None) -> Dict:
        source_dir = Path(source_dir).resolve()
        output_path = Path(output_path).resolve()

        result = {'success': False, 'complete': False, 'total_files': 0, 'added_files': 0,
                  'skipped_files': 0, 'failed_files': [], 'error': None}
        if self._refuse_if_gitignore_unreadable(result):
            return result

        try:
            output_path.relative_to(source_dir)
            zip_inside_source = True
        except ValueError:
            zip_inside_source = False

        files_to_add = self._collect_files(
            source_dir, profile_name, result, skip_file=output_path if zip_inside_source else None)
        result['total_files'] = len(files_to_add)

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for i, (fp, rp) in enumerate(files_to_add):
                    try:
                        zf.write(fp, str(rp))
                        result['added_files'] += 1
                    except OSError as e:
                        self._record_failure(result, fp, e)
                    if progress_callback:
                        progress_callback(i + 1, result['total_files'])
            result['success'] = True
            result['complete'] = not result['failed_files']
        except Exception as e:
            logger.exception("Arşiv oluşturulamadı: %s", output_path)
            result['error'] = str(e)
            self._remove_partial(output_path)

        return result

    def copy_project(self, source_dir: Path, target_dir: Path,
                     profile_name: str = "Geliştirici (Standart)",
                     progress_callback: Optional[ProgressCallback] = None) -> Dict:
        source_dir = Path(source_dir).resolve()
        target_dir = Path(target_dir).resolve()

        result = {'success': False, 'complete': False, 'copied_files': 0,
                  'skipped_files': 0, 'failed_files': [], 'error': None}
        if self._refuse_if_gitignore_unreadable(result):
            return result

        try:
            skip_root_dir = target_dir.relative_to(source_dir).parts[0]
        except (ValueError, IndexError):
            skip_root_dir = None

        files_to_copy = self._collect_files(source_dir, profile_name, result, skip_root_dir=skip_root_dir)
        total = len(files_to_copy)

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            for i, (fp, rp) in enumerate(files_to_copy):
                dest = target_dir / rp
                try:
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(fp, dest)
                    result['copied_files'] += 1
                except OSError as e:
                    self._record_failure(result, fp, e)
                if progress_callback:
                    progress_callback(i + 1, total)
            result['success'] = True
            result['complete'] = not result['failed_files']
        except Exception as e:
            logger.exception("Proje kopyalanamadı: %s", target_dir)
            result['error'] = str(e)

        return result
