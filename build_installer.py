"""Kurulum sihirbazı üretir: EXE'yi derler (build_exe.py), Inno Setup ile `dist/installer/GitCleanArchiver-Setup-<sürüm>.exe`
ve SHA-256 özeti yazar. Sürüm `src/version.py`'den gelir.

Windows Akıllı Uygulama Denetimi imzasız bazı derlemeleri engeller; bu yüzden (CI dışında) üretilen exe ve kurulum dosyası bu makinede
gerçekten denenir (build_verify.py) ve engellenirse yeniden derlenir. Ayrıntı: docs/wiki/windows-exe-dagitim.md.

Kullanım:
    python build_installer.py                 # derler, dener (engellenirse yeniden derler), kurulum dosyasını üretir
    python build_installer.py --no-verify     # denemeden derler (CI'da otomatik: CI ortam değişkeni varsa denenmez)
    python build_installer.py --skip-build    # dist/GitCleanArchiver/ hazırsa yalnızca kurulum dosyası (tek deneme)
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
EXE = ROOT / "dist" / "GitCleanArchiver" / "GitCleanArchiver.exe"
OUTPUT = ROOT / "dist" / "installer"
MAX_ATTEMPTS = 6
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


def compile_installer(iscc: Path) -> Path:
    print(f"\n[*] Kurulum sihirbazı derleniyor (sürüm {__version__})...")
    result = subprocess.run([str(iscc), f"/DAppVersion={__version__}", str(SCRIPT)], cwd=ROOT)
    if result.returncode != 0:
        sys.exit(f"[X] ISCC başarısız (çıkış kodu {result.returncode}).")
    installer = OUTPUT / f"GitCleanArchiver-Setup-{__version__}.exe"
    if not installer.is_file():
        sys.exit(f"[X] Beklenen çıktı yok: {installer}")
    return installer


def attempt(iscc: Path, skip_build: bool, verify: bool) -> Path:
    """Tek deneme: derle, (istenirse) dene. Başarısızsa None döner."""
    if not skip_build:
        import build_exe
        build_exe.build_executable()
    if not EXE.is_file():
        sys.exit(f"[X] {EXE} yok; önce `python build_exe.py` çalıştırın ya da --skip-build kullanmayın.")
    if verify:
        import build_verify
        print("\n[*] Derlenen exe bu makinede deneniyor...")
        if not build_verify.launch_check(EXE):
            return None
    installer = compile_installer(iscc)
    if verify:
        print("\n[*] Kurulum dosyası sessizce kurulup kaldırılarak deneniyor...")
        if not build_verify.installer_check(installer):
            return None
    return installer


def build_installer(skip_build: bool = False, verify: bool = True) -> Path:
    iscc = find_iscc()
    if iscc is None:
        sys.exit("[X] Inno Setup 6 bulunamadı (ISCC.exe). https://jrsoftware.org/isdl.php adresinden kurun ya da ISCC ortam değişkenini ayarlayın.")
    attempts = 1 if skip_build else MAX_ATTEMPTS
    installer = None
    for number in range(1, attempts + 1):
        installer = attempt(iscc, skip_build, verify)
        if installer is not None:
            break
        print(f"[!] Deneme {number}/{attempts} engellendi; özet değişsin diye yeniden derleniyor...\n")
    if installer is None:
        sys.exit("[X] Derleme Windows tarafından engellendi. Kalıcı çözüm kod imzalama; ayrıntı: docs/wiki/windows-exe-dagitim.md")

    checksum = sha256_of(installer)
    (OUTPUT / (installer.name + ".sha256")).write_text(f"{checksum} *{installer.name}\n", encoding="utf-8")
    print("=" * 60)
    print(f"[OK] {installer}  ({installer.stat().st_size / (1024 * 1024):.1f} MB)")
    print(f"[OK] SHA-256: {checksum}")
    print("=" * 60)
    return installer


if __name__ == "__main__":
    arguments = sys.argv[1:]
    on_ci = bool(os.environ.get("CI"))                       # GitHub Actions: Akıllı Uygulama Denetimi yok, deneme gereksiz
    build_installer(skip_build="--skip-build" in arguments, verify="--no-verify" not in arguments and not on_ci)
