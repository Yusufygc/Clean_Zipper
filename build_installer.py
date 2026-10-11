"""Kurulum sihirbazı üretir: EXE'yi derler (build_exe.py), Inno Setup ile `dist/installer/GitCleanArchiver-Setup-<sürüm>.exe`
ve SHA-256 özeti yazar. Sürüm `src/version.py`'den gelir.

Kullanım:
    python build_installer.py                 # EXE'yi yeniden derler, sonra kurulum dosyasını üretir
    python build_installer.py --skip-build    # dist/GitCleanArchiver.exe hazırsa yalnızca kurulum dosyası
"""
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

from src.version import __version__

ROOT = Path(__file__).parent.resolve()
SCRIPT = ROOT / "packaging" / "GitCleanArchiver.iss"
EXE = ROOT / "dist" / "GitCleanArchiver.exe"
OUTPUT = ROOT / "dist" / "installer"
ISCC_CANDIDATES = (
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
)


def find_iscc():
    """ISCC.exe: ISCC ortam değişkeni, PATH, standart kurulum yolları."""
    for candidate in (os.environ.get("ISCC"), shutil.which("ISCC"), *ISCC_CANDIDATES):
        if candidate and Path(candidate).is_file():
            return Path(candidate)
    return None


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_installer(skip_build: bool = False) -> Path:
    iscc = find_iscc()
    if iscc is None:
        sys.exit("[X] Inno Setup 6 bulunamadı (ISCC.exe). https://jrsoftware.org/isdl.php adresinden kurun ya da ISCC ortam değişkenini ayarlayın.")
    if not skip_build:
        import build_exe
        build_exe.build_executable()
    if not EXE.is_file():
        sys.exit(f"[X] {EXE} yok; önce `python build_exe.py` çalıştırın ya da --skip-build kullanmayın.")

    print(f"\n[*] Kurulum sihirbazı derleniyor (sürüm {__version__})...")
    result = subprocess.run([str(iscc), f"/DAppVersion={__version__}", str(SCRIPT)], cwd=ROOT)
    if result.returncode != 0:
        sys.exit(f"[X] ISCC başarısız (çıkış kodu {result.returncode}).")

    installer = OUTPUT / f"GitCleanArchiver-Setup-{__version__}.exe"
    if not installer.is_file():
        sys.exit(f"[X] Beklenen çıktı yok: {installer}")
    checksum = sha256_of(installer)
    (OUTPUT / (installer.name + ".sha256")).write_text(f"{checksum} *{installer.name}\n", encoding="utf-8")
    print("=" * 60)
    print(f"[OK] {installer}  ({installer.stat().st_size / (1024 * 1024):.1f} MB)")
    print(f"[OK] SHA-256: {checksum}")
    print("=" * 60)
    return installer


if __name__ == "__main__":
    build_installer(skip_build="--skip-build" in sys.argv[1:])
