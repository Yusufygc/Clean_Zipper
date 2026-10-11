import os
import sys
import shutil
import importlib.util
import subprocess
from pathlib import Path


def pyinstaller_requirement(root_dir: Path):
    """pip argümanları: sürümü sabitlenmiş requirements-build.txt varsa o, yoksa sürümsüz paket adı."""
    requirements = root_dir / "requirements-build.txt"
    return ["-r", str(requirements)] if requirements.exists() else ["pyinstaller"]


def ensure_pyinstaller(root_dir: Path):
    """PyInstaller yoksa pip ile kurar; kurulamazsa çıkar."""
    if importlib.util.find_spec("PyInstaller") is not None:
        print("[OK] PyInstaller is ready.")
    else:
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
    spec_files = [
        root_dir / "GitCleanArchiver.spec",
        root_dir / "GitCleanArchiverPro.spec",
    ]

    print("\n[*] Cleaning old build directories...")
    for path in [build_dir, dist_dir]:
        if path.exists():
            try:
                shutil.rmtree(path)
                print(f"  - Cleaned directory: {path.name}")
            except Exception as e:
                print(f"  - Warning cleaning {path.name}: {e}")
    for spec_file in spec_files:
        if spec_file.exists():
            try:
                spec_file.unlink()
                print(f"  - Cleaned old .spec file: {spec_file.name}")
            except Exception as e:
                print(f"  - Warning cleaning .spec file: {e}")


# (kaynak, paketteki hedef): QML arayüzü dosyaları, arayüz simgeleri ve uygulama kaynakları (kurallar, profiller, simge).
DATA_DIRS = (
    ("src/qml_ui/qml", "src/qml_ui/qml"),
    ("src/qml_ui/resources", "src/qml_ui/resources"),
    ("resources", "resources"),
)


def data_file_args(root_dir: Path):
    """Pakete eklenecek veri klasörleri için --add-data argümanları; eksik klasör derlemeyi durdurur."""
    add_data_args = []
    for source, destination in DATA_DIRS:
        source_path = root_dir / source
        if not source_path.is_dir():
            raise FileNotFoundError(f"Pakete eklenecek klasör yok: {source_path}")
        add_data_args.extend(["--add-data", f"{source_path}{os.pathsep}{destination}"])
        print(f"[OK] Pakete eklendi: {source}")
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
        "--name=GitCleanArchiver",
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
        print(f"[*] Executable File: {dist_dir / 'GitCleanArchiver.exe'}")
        print("=" * 60)
    except Exception as e:
        print(f"\n[X] Compilation failed: {e}")
        sys.exit(1)


def build_executable():
    print("=" * 60)
    print("      GitClean Archiver - EXE Build Wizard      ")
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
