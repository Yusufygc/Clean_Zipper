"""Derleme sonrası denetim: üretilen exe ve kurulum dosyası bu makinede GERÇEKTEN açılıyor mu?

Windows Akıllı Uygulama Denetimi (Smart App Control), imzasız her yeni exe'ye dosya özetine (hash) göre bulut kararı verir ve bazı
derlemeleri engeller (`OSError: [WinError 4551] Uygulama Denetimi ilkesi bu dosyayı engelledi`). Aynı kaynak kodun bir derlemesi çalışırken
bir sonraki engellenebilir; bu yüzden dağıtımdan önce denenir ve engellenirse yeniden derlenir (özet değişir).
Ayrıntı: docs/wiki/windows-exe-dagitim.md. Kod imzalama bu denetimin yerini tutmaz ama imzalı derlemede de zararsızdır.

DİKKAT: deneme kurulumu, makinedeki GERÇEK kurulumla aynı `AppId`'yi kullanır; Inno aynı "Uygulamalar ve özellikler" kaydını ve Başlat menüsü
kısayolunu yazar / siler. Bu yüzden deneme boyunca gerçek kaydın ve kısayolun kopyası alınır ve (hata olsa bile) geri yüklenir.
"""
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import List, Optional, Tuple

BLOCKED_WINERRORS = (4551, 1260)          # 4551: Uygulama Denetimi ilkesi engelledi; 1260: grup ilkesi engelledi
EXE_NAME = "GitCleanArchiver.exe"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{B4C7E1A2-5D3F-4E8A-9C21-6F0A7D9E3B58}_is1"     # .iss'deki AppId
SHORTCUT = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "GitClean Archiver.lnk"

Registration = Tuple[Optional[List[tuple]], Optional[bytes]]       # (kayıt değerleri ya da None, kısayol baytları ya da None)


def save_registration() -> Registration:
    """Gerçek kurulumun kaydını ve Başlat menüsü kısayolunu denemeden önce saklar (kurulu değilse None)."""
    import winreg
    values = None
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY) as key:
            values, index = [], 0
            while True:
                try:
                    values.append(winreg.EnumValue(key, index))
                except OSError:
                    break
                index += 1
    except FileNotFoundError:
        values = None
    shortcut = SHORTCUT.read_bytes() if SHORTCUT.is_file() else None
    return values, shortcut


def restore_registration(saved: Registration) -> None:
    """Deneme kurulumunun yazdığı kaydı ve kısayolu siler, gerçek olanları geri yazar."""
    import winreg
    values, shortcut = saved
    try:
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY)
    except FileNotFoundError:
        pass
    if values is not None:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY, 0, winreg.KEY_SET_VALUE) as key:
            for name, value, kind in values:
                winreg.SetValueEx(key, name, 0, kind, value)
    if shortcut is not None:
        SHORTCUT.write_bytes(shortcut)
    else:
        SHORTCUT.unlink(missing_ok=True)


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
    """Kurulum dosyası sessizce geçici bir klasöre kurulur, kurulan exe açılır, ardından sessizce kaldırılır.
    Gerçek kurulumun kaydı ve kısayolu korunur (modül açıklamasına bakın)."""
    saved = save_registration()
    try:
        return _installer_check(installer, seconds)
    finally:
        restore_registration(saved)


def _installer_check(installer: Path, seconds: float) -> bool:
    workdir = Path(tempfile.mkdtemp(prefix="gcverify_"))
    target = workdir / "app"
    flags = ["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CURRENTUSER", f"/DIR={target}", f"/LOG={workdir / 'setup.log'}"]
    try:
        result = subprocess.run([str(installer), *flags], timeout=600, check=False)
    except OSError as e:
        if is_blocked(e):
            print(f"[X] Windows kurulum dosyasını engelledi (Akıllı Uygulama Denetimi): {installer}")
            shutil.rmtree(workdir, ignore_errors=True)
            return False
        raise
    installed = target / EXE_NAME
    ok = result.returncode == 0 and installed.is_file()
    if not ok:
        print(f"[X] Sessiz kurulum başarısız (çıkış kodu {result.returncode}); günlük: {workdir / 'setup.log'}")
        return False
    ok = launch_check(installed, seconds)
    uninstaller = target / "unins000.exe"
    if uninstaller.is_file():
        try:
            subprocess.run([str(uninstaller), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"], timeout=300, check=False)
        except OSError as e:
            if not is_blocked(e):
                raise
            # Kaldırıcı da imzasız bir exe'dir ve engellenebilir: kullanıcı "Uygulamalar ve özellikler"den kaldıramazdı -> deneme başarısız
            print(f"[X] Windows kaldırıcıyı engelledi (Akıllı Uygulama Denetimi): {uninstaller}")
            ok = False
    shutil.rmtree(workdir, ignore_errors=True)                 # başarısız kurulumda günlük için bırakılır (yukarıdaki return)
    return ok
