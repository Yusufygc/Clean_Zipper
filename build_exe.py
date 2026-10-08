import os
import sys
import shutil
import subprocess
from pathlib import Path


def pyinstaller_requirement(root_dir: Path):
    """pip argümanları: sürümü sabitlenmiş requirements-build.txt varsa o, yoksa sürümsüz paket adı."""
    requirements = root_dir / "requirements-build.txt"
    return ["-r", str(requirements)] if requirements.exists() else ["pyinstaller"]


def ensure_pyinstaller(root_dir: Path):
    """PyInstaller yoksa pip ile kurar; kurulamazsa çıkar."""
    try:
        import PyInstaller
        print("[OK] PyInstaller is ready.")
    except ImportError:
        print("[!] PyInstaller not found. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *pyinstaller_requirement(root_dir)])
            print("[OK] PyInstaller successfully installed.")
        except Exception as e:
            print(f"[X] PyInstaller installation failed! Error: {e}")
            sys.exit(1)


def clean_build_artifacts(root_dir: Path):
    """Eski build / dist klasörlerini ve .spec dosyasını siler."""
    build_dir = root_dir / "build"
    dist_dir = root_dir / "dist"
    spec_file = root_dir / "GitCleanArchiverPro.spec"

    print("\n[*] Cleaning old build directories...")
    for path in [build_dir, dist_dir]:
        if path.exists():
            try:
                shutil.rmtree(path)
                print(f"  - Cleaned directory: {path.name}")
            except Exception as e:
                print(f"  - Warning cleaning {path.name}: {e}")
    if spec_file.exists():
        try:
            spec_file.unlink()
            print("  - Cleaned old .spec file.")
        except Exception as e:
            print(f"  - Warning cleaning .spec file: {e}")


def data_file_args(root_dir: Path):
    """Pakete eklenecek stil dosyası ve resources klasörü için --add-data argümanları."""
    sep = os.pathsep
    style_qss_source = root_dir / "src" / "ui" / "themes" / "style.qss"
    style_qss_dest = "src/ui/themes"

    add_data_args = []
    if style_qss_source.exists():
        add_data_args.extend(["--add-data", f"{style_qss_source}{sep}{style_qss_dest}"])
        print(f"[OK] Added stylesheet to package: {style_qss_source.name}")
    else:
        print("[!] WARNING: style.qss not found! Styles may be missing in built app.")

    resources_source = root_dir / "resources"
    if resources_source.exists():
        add_data_args.extend(["--add-data", f"{resources_source}{sep}resources"])
        print(f"[OK] Added resources directory to package.")
    return add_data_args


def icon_args(root_dir: Path):
    icon_path = root_dir / "resources" / "icons" / "app_icon.ico"
    if icon_path.exists():
        print(f"[OK] Added app icon: {icon_path}")
        return ["--icon", str(icon_path)]
    print(f"[!] Info: '{icon_path}' not found. Building with default system icon.")
    return []


def pyinstaller_arguments(root_dir: Path, entry_point: Path):
    """PyInstaller komut satırı argümanları."""
    version_info_path = root_dir / "version_info.txt"
    arguments = [
        str(entry_point),
        "--name=GitCleanArchiverPro",
        "--onefile",           # Tek dosya (dist klasörüne bağımlılığı kaldırır)
        "--windowed",          # Konsol penceresini gizle
        "--clean",             # Önbelleği temizle
        "--noconfirm",         # Onay sorma
        "--noupx",             # UPX sıkıştırmasını kapat (Virüs uyarısı riskini ciddi oranda düşürür)
        "--collect-submodules=src.analyzers",  # Analizörler pkgutil ile dinamik yüklenir
    ]

    if version_info_path.exists():
        arguments.append(f"--version-file={version_info_path}")

    arguments.extend(data_file_args(root_dir))
    arguments.extend(icon_args(root_dir))
    return arguments


def run_pyinstaller(arguments, dist_dir: Path):
    print("\n[*] Compiling executable, this may take a moment...")
    print(f"    Command: pyinstaller {' '.join(arguments[1:])}\n")

    try:
        import PyInstaller.__main__
        PyInstaller.__main__.run(arguments)
        print("\n" + "=" * 60)
        print("[OK] BUILD COMPLETED SUCCESSFULLY!")
        print(f"[*] Output Directory: {dist_dir}")
        print(f"[*] Executable File: {dist_dir / 'GitCleanArchiverPro.exe'}")
        print("=" * 60)
    except Exception as e:
        print(f"\n[X] Compilation failed: {e}")
        sys.exit(1)


def build_executable():
    print("=" * 60)
    print("      GitClean Archiver Pro - EXE Build Wizard      ")
    print("=" * 60)

    # Project root directory
    root_dir = Path(__file__).parent.resolve()
    ensure_pyinstaller(root_dir)
    entry_point = root_dir / "main.py"

    if not entry_point.exists():
        print(f"[X] Entry point ({entry_point}) not found!")
        sys.exit(1)

    clean_build_artifacts(root_dir)
    arguments = pyinstaller_arguments(root_dir, entry_point)
    run_pyinstaller(arguments, root_dir / "dist")


if __name__ == "__main__":
    build_executable()
