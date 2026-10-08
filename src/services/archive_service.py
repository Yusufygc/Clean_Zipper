import logging
import os
import zipfile
import shutil
from pathlib import Path
from typing import Optional, Callable, Dict, List, Mapping, Tuple

from src.core.exclusions import is_excluded_dir
from src.services.archive_profiles import ArchiveProfile, load_profiles
from src.utils.git_info import tracked_paths
from src.utils.gitignore_parser import GitignoreParser

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int], None]


class ArchiveService:
    """Profil tabanlı arşivleme servisi.

    Profiller `resources/profiles/*.json` (ve kullanıcının `~/.gitclean/profiles`) dosyalarından gelir,
    desenler gitignore sözdizimidir. Dışlanan klasörler (venv, node_modules, .next ...) her profilde atlanır.

    Sonuç sözlüğü: `success` çıktı üretildi mi, `complete` hiçbir dosya atlanmadan mı üretildi,
    `failed_files` eklenemeyen dosyalar (yol, hata), `error` ölümcül hata mesajı.
    """

    def __init__(self, parser: Optional[GitignoreParser] = None,
                 profiles: Optional[Mapping[str, ArchiveProfile]] = None):
        self.parser = parser
        self.profiles: Mapping[str, ArchiveProfile] = profiles if profiles is not None else load_profiles()

    @property
    def PROFILES(self) -> Dict[str, Dict]:
        """UI için {ad: {"excludes": desenler, "description": açıklama}} görünümü (profil sırasıyla)."""
        return {name: {"excludes": list(p.patterns), "description": p.description}
                for name, p in self.profiles.items()}

    def _refuse_if_gitignore_unreadable(self, result: Dict) -> bool:
        """Okunamayan .gitignore (kök ya da iç içe) ile arşivleme gizli dosyaları sızdırabilir; işlem reddedilir.

        İç içe dosyalar yürüyüş sırasında tembel yüklendiğinden bu kontrol toplamadan önce ve sonra yapılır.
        """
        errors = list(getattr(self.parser, 'load_errors', []) or [])
        if errors:
            result['error'] = f"{'; '.join(errors)}. Gizli dosyaların arşive sızmaması için işlem durduruldu."
            logger.error("Arşivleme reddedildi: %s", result['error'])
            return True
        return False

    def _resolve_profile(self, profile_name: str, result: Dict) -> Optional[ArchiveProfile]:
        """Bilinmeyen profil adı sessizce 'hiçbir şeyi eleme' olmaz: işlem hata ile durur."""
        profile = self.profiles.get(profile_name)
        if profile is None:
            result['error'] = f"Bilinmeyen arşiv profili: {profile_name!r}. Geçerli profiller: {', '.join(self.profiles)}"
            logger.error(result['error'])
        return profile

    def _collect_files(self, source_dir: Path, profile: ArchiveProfile, result: Dict,
                       skip_root_dir: Optional[str] = None,
                       skip_file: Optional[Path] = None) -> List[Tuple[Path, Path]]:
        """Kaynak ağacı gezer, .gitignore ve profil süzgecinden geçen (mutlak, göreli) yolları döner."""
        files: List[Tuple[Path, Path]] = []
        for root, dirs, filenames in os.walk(source_dir):
            root_path = Path(root)
            skipped_dir = skip_root_dir if root_path == source_dir else None
            dirs[:] = [d for d in dirs if self._enters_dir(root, d, dirs + filenames, skipped_dir)]
            for name in filenames:
                fp = root_path / name
                rp = fp.relative_to(source_dir)
                if self._is_filtered(fp, rp, profile, skip_file):
                    result['skipped_files'] += 1
                else:
                    files.append((fp, rp))
        return files

    def _enters_dir(self, root: str, name: str, sibling_names: List[str], skipped_dir: Optional[str]) -> bool:
        path = os.path.join(root, name)
        return not (is_excluded_dir(path, name, sibling_names) or (skipped_dir and name == skipped_dir)
                    or self._is_ignored_dir(path))

    def _is_filtered(self, path: Path, relative: Path, profile: ArchiveProfile, skip_file: Optional[Path]) -> bool:
        """Dosya arşive girmeyecek mi: hedef zip'in kendisi, .gitignore kuralı ya da profil deseni."""
        if skip_file is not None and path.resolve() == skip_file:
            return True                                           # hedef dosyanın kendisini (zip kaynak içindeyse) atla
        if self.parser and self.parser.should_ignore(str(path)):
            return True                                           # .gitignore kuralları
        return profile.matches(relative.as_posix())               # seçilen profilin desenleri

    def _refresh_tracked(self, source_dir: Path):
        """Arşiv anındaki git izleme durumunu al: izlenen dosyalar .gitignore'a uysa bile arşive girer."""
        setter = getattr(self.parser, 'set_tracked', None)
        if setter is not None:
            setter(tracked_paths(source_dir))

    def _is_ignored_dir(self, dir_path: str) -> bool:
        """.gitignore'lu klasöre hiç girilmez (git gibi içi geri eklenemez); büyük ignore'lu veri klasörlerinde hızlıdır."""
        checker = getattr(self.parser, 'is_dir_ignored', None)
        return bool(checker and checker(dir_path))

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
        profile = self._resolve_profile(profile_name, result)
        if profile is None or self._refuse_if_gitignore_unreadable(result):
            return result

        try:
            output_path.relative_to(source_dir)
            zip_inside_source = True
        except ValueError:
            zip_inside_source = False

        self._refresh_tracked(source_dir)
        files_to_add = self._collect_files(
            source_dir, profile, result, skip_file=output_path if zip_inside_source else None)
        if self._refuse_if_gitignore_unreadable(result):             # iç içe .gitignore yürüyüşte yüklendi
            return result
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
        profile = self._resolve_profile(profile_name, result)
        if profile is None or self._refuse_if_gitignore_unreadable(result):
            return result

        try:
            skip_root_dir = target_dir.relative_to(source_dir).parts[0]
        except (ValueError, IndexError):
            skip_root_dir = None

        self._refresh_tracked(source_dir)
        files_to_copy = self._collect_files(source_dir, profile, result, skip_root_dir=skip_root_dir)
        if self._refuse_if_gitignore_unreadable(result):
            return result
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
