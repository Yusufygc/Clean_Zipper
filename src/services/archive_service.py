import os
import zipfile
import shutil
import re
from pathlib import Path
from typing import Optional, Callable, Dict, List

from src.utils.gitignore_parser import GitignoreParser


class ArchiveService:
    """Farklı sıkıştırma profillerini destekleyen kurumsal arşivleme servisi."""

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

    def create_zip(self, source_dir: Path, output_path: Path,
                   profile_name: str = "Geliştirici (Standart)",
                   progress_callback: Optional[Callable[[int, int], None]] = None) -> Dict:
        source_dir = Path(source_dir).resolve()
        output_path = Path(output_path).resolve()

        result = {'success': False, 'total_files': 0, 'added_files': 0, 'skipped_files': 0, 'error': None}

        # Hedef zip dosyası kaynak içindeyse hariç tut
        try:
            output_path.relative_to(source_dir)
            zip_inside_source = True
        except ValueError:
            zip_inside_source = False

        output_path.parent.mkdir(parents=True, exist_ok=True)

        files_to_add = []
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if d not in self._excluded_dirs]
            for file in files:
                fp = Path(root) / file
                fp = fp.resolve()

                # Hedef zip dosyasının kendisini atla
                if zip_inside_source and fp == output_path:
                    result['skipped_files'] += 1
                    continue

                rp = fp.relative_to(source_dir)
                rp_str = str(rp)

                # 1. .gitignore Kurallarını Uygula
                if self.parser and self.parser.should_ignore(str(fp)):
                    result['skipped_files'] += 1
                    continue
                
                # 2. Seçilen Sıkıştırma Profil Filtrelerini Uygula
                if self._should_exclude_by_profile(rp_str, profile_name):
                    result['skipped_files'] += 1
                    continue

                files_to_add.append((fp, rp))

        result['total_files'] = len(files_to_add)

        try:
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for i, (fp, rp) in enumerate(files_to_add):
                    zf.write(fp, str(rp))
                    result['added_files'] += 1
                    if progress_callback:
                        progress_callback(i + 1, result['total_files'])
            result['success'] = True
        except Exception as e:
            result['error'] = str(e)

        return result

    def copy_project(self, source_dir: Path, target_dir: Path,
                     profile_name: str = "Geliştirici (Standart)",
                     progress_callback: Optional[Callable[[int, int], None]] = None) -> Dict:
        source_dir = Path(source_dir).resolve()
        target_dir = Path(target_dir).resolve()

        result = {'success': False, 'copied_files': 0, 'skipped_files': 0, 'error': None}

        try:
            target_dir.relative_to(source_dir)
            target_inside_source = True
            target_dir_name = target_dir.relative_to(source_dir).parts[0]
        except ValueError:
            target_inside_source = False
            target_dir_name = None

        target_dir.mkdir(parents=True, exist_ok=True)

        files_to_copy = []
        for root, dirs, files in os.walk(source_dir):
            root_path = Path(root).resolve()

            if target_inside_source:
                dirs[:] = [d for d in dirs
                           if d not in self._excluded_dirs
                           and not (root_path == source_dir and d == target_dir_name)]
            else:
                dirs[:] = [d for d in dirs if d not in self._excluded_dirs]

            for file in files:
                fp = root_path / file
                rp = fp.relative_to(source_dir)
                rp_str = str(rp)

                # 1. .gitignore Kurallarını Uygula
                if self.parser and self.parser.should_ignore(str(fp)):
                    result['skipped_files'] += 1
                    continue

                # 2. Seçilen Sıkıştırma Profil Filtrelerini Uygula
                if self._should_exclude_by_profile(rp_str, profile_name):
                    result['skipped_files'] += 1
                    continue

                files_to_copy.append((fp, rp))

        total = len(files_to_copy)
        try:
            for i, (fp, rp) in enumerate(files_to_copy):
                dest = target_dir / rp
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(fp, dest)
                result['copied_files'] += 1
                if progress_callback:
                    progress_callback(i + 1, total)
            result['success'] = True
        except Exception as e:
            result['error'] = str(e)

        return result