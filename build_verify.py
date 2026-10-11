"""Derleme sonrası denetim: üretilen exe ve kurulum dosyası bu makinede GERÇEKTEN açılıyor mu?

Windows Akıllı Uygulama Denetimi (Smart App Control), imzasız her yeni exe'ye dosya özetine (hash) göre bulut kararı verir ve bazı
derlemeleri engeller (`OSError: [WinError 4551] Uygulama Denetimi ilkesi bu dosyayı engelledi`). Aynı kaynak kodun bir derlemesi çalışırken
bir sonraki engellenebilir; bu yüzden dağıtımdan önce denenir ve engellenirse yeniden derlenir (özet değişir).
Ayrıntı: docs/wiki/windows-exe-dagitim.md. Kod imzalama bu denetimin yerini tutmaz ama imzalı derlemede de zararsızdır.
"""
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

BLOCKED_WINERRORS = (4551, 1260)          # 4551: Uygulama Denetimi ilkesi engelledi; 1260: grup ilkesi engelledi
EXE_NAME = "GitCleanArchiver.exe"


def is_blocked(error: OSError) -> bool:
    return getattr(error, "winerror", None) in BLOCKED_WINERRORS


def _kill_tree(pid: int) -> None:
    subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, check=False)


def launch_check(exe: Path, seconds: float = 8.0) -> bool:
    """Exe başlatılır, `seconds` sonra hâlâ çalışıyorsa kapatılır. Engellenirse ya da hemen çıkarsa False."""
    env = {**os.environ, "GITCLEAN_NO_UPDATE_CHECK": "1"}          # denetim sırasında ağ isteği yapılmasın
    try:
        process = subprocess.Popen([str(exe)], cwd=exe.parent, env=env)
    except OSError as e:
        if is_blocked(e):
            print(f"[X] Windows engelledi (Akıllı Uygulama Denetimi): {exe}")
            return False
        raise
    time.sleep(seconds)
    alive = process.poll() is None
    _kill_tree(process.pid)
    if not alive:
        print(f"[X] Exe başladı ama hemen kapandı (çıkış kodu {process.returncode}): {exe}")
    return alive


def installer_check(installer: Path, seconds: float = 8.0) -> bool:
    """Kurulum dosyası sessizce geçici bir klasöre kurulur, kurulan exe açılır, ardından sessizce kaldırılır."""
    workdir = Path(tempfile.mkdtemp(prefix="gcverify_"))
    target = workdir / "app"
    flags = ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CURRENTUSER", f"/DIR={target}", f"/LOG={workdir / 'setup.log'}"]
    try:
        result = subprocess.run([str(installer), *flags], timeout=600, check=False)
    except OSError as e:
        if is_blocked(e):
            print(f"[X] Windows kurulum dosyasını engelledi (Akıllı Uygulama Denetimi): {installer}")
            return False
        raise
    installed = target / EXE_NAME
    ok = result.returncode == 0 and installed.is_file()
    if not ok:
        print(f"[X] Sessiz kurulum başarısız (çıkış kodu {result.returncode}); günlük: {workdir / 'setup.log'}")
        return False
    try:
        ok = launch_check(installed, seconds)
    finally:
        uninstaller = target / "unins000.exe"
        if uninstaller.is_file():
            subprocess.run([str(uninstaller), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"], timeout=300, check=False)
    shutil.rmtree(workdir, ignore_errors=True)                 # başarısız kurulumda günlük için bırakılır (yukarıdaki return)
    return ok
