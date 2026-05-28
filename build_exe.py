import os
import sys
import shutil
import subprocess
from pathlib import Path

def build_executable():
    print("=" * 60)
    print("      GitClean Archiver Pro - EXE Build Wizard      ")
    print("=" * 60)

    # 1. Check PyInstaller dependency
    try:
        import PyInstaller
        print("[OK] PyInstaller is ready.")
    except ImportError:
        print("[!] PyInstaller not found. Installing...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("[OK] PyInstaller successfully installed.")
        except Exception as e:
            print(f"[X] PyInstaller installation failed! Error: {e}")
            sys.exit(1)

    # Project root directory
    root_dir = Path(__file__).parent.resolve()
    entry_point = root_dir / "main.py"
    
    if not entry_point.exists():
        print(f"[X] Entry point ({entry_point}) not found!")
        sys.exit(1)

    # 2. Clean old build artifacts
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

    # 3. Configure data files and paths
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

    # 4. Configure Icon
    icon_path = root_dir / "resources" / "icons" / "app_icon.ico"
    icon_args = []
    if icon_path.exists():
        icon_args = ["--icon", str(icon_path)]
        print(f"[OK] Added app icon: {icon_path}")
    else:
        print(f"[!] Info: '{icon_path}' not found. Building with default system icon.")

    # 5. Build parameters
    pyinstaller_args = [
        str(entry_point),
        "--name=GitCleanArchiverPro",
        "--onedir",            # Directory distribution
        "--windowed",          # Hide console window
        "--clean",             # Clean cache
        "--noconfirm"          # Do not ask confirmation
    ]

    pyinstaller_args.extend(add_data_args)
    pyinstaller_args.extend(icon_args)

    # 6. Execute compilation
    print("\n[*] Compiling executable, this may take a moment...")
    print(f"    Command: pyinstaller {' '.join(pyinstaller_args[1:])}\n")

    try:
        import PyInstaller.__main__
        PyInstaller.__main__.run(pyinstaller_args)
        print("\n" + "=" * 60)
        print("[OK] BUILD COMPLETED SUCCESSFULLY!")
        print(f"[*] Output Directory: {dist_dir / 'GitCleanArchiverPro'}")
        print(f"[*] Executable File: {dist_dir / 'GitCleanArchiverPro' / 'GitCleanArchiverPro.exe'}")
        print("=" * 60)
    except Exception as e:
        print(f"\n[X] Compilation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build_executable()