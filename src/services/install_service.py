"""Kendi kendini kuran uygulama: indirilen `GitCleanArchiver-X.Y.Z.exe` kendini kullanıcının programlar klasörüne kurar.

Neden ayrı bir kurulum programı yok: Windows Akıllı Uygulama Denetimi (Smart App Control), imzasız ve itibarı olmayan her yeni
`.exe` dosyasını engeller. Ayrı derlenen bir kurulum programı (ör. Inno Setup) engellenir; PyInstaller ile paketlenmiş
uygulama ise çalışır (açılış yükleyicisi tanınan, imzalı Python / Qt DLL'lerini yükler, uygulama kodu PE dosyası değildir).
Bu yüzden kurulum, uygulamanın kendisinin bir özelliğidir: kopyalama, kısayol, "Uygulamalar ve özellikler" kaydı, kaldırma.

Kapsam ve güvenlik:
- Yönetici hakkı gerekmez: dosyalar `%LOCALAPPDATA%\\Programs\\GitClean Archiver`, kayıt `HKCU`, kısayollar kullanıcıya ait klasörlerdedir.
- Yalnızca `GitCleanArchiver.exe` yazılır ve silinir; hedef klasörde başka dosyaya dokunulmaz, klasör boşsa kaldırılır.
- Kullanıcı verisi (`~/.gitclean`: ayarlar, günlük, yedekler) kaldırmada silinmez.
- Kısayol PowerShell ile oluşturulur; yollar komut metnine değil ortam değişkenlerine konur (komut enjeksiyonu olmaz).
"""
import ctypes
import logging
import os
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional

from src.version import APP_NAME, RELEASE_REPO, __version__

logger = logging.getLogger(__name__)

EXE_NAME = "GitCleanArchiver.exe"
SHORTCUT_NAME = f"{APP_NAME}.lnk"
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\GitCleanArchiver"
CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008
POWERSHELL = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"


class InstallError(Exception):
    """Kurulum / kaldırma yapılamadı; mesaj kullanıcıya gösterilebilir."""


@dataclass(frozen=True)
class Locations:
    install_dir: Path
    start_menu: Path          # Başlat menüsü > Programlar
    desktop: Path


@dataclass(frozen=True)
class InstallState:
    installed: bool
    version: str = ""
    location: Optional[Path] = None

    @property
    def exe(self) -> Optional[Path]:
        return self.location / EXE_NAME if self.location else None


def _known_folder(folder_id: str, fallback: Path) -> Path:
    """Windows özel klasörü (OneDrive yönlendirmeli masaüstü dahil); alınamazsa `fallback`."""
    class GUID(ctypes.Structure):
        _fields_ = [("a", ctypes.c_ulong), ("b", ctypes.c_ushort), ("c", ctypes.c_ushort), ("d", ctypes.c_ubyte * 8)]
    try:
        guid = GUID()
        ctypes.windll.ole32.CLSIDFromString(ctypes.c_wchar_p("{" + folder_id + "}"), ctypes.byref(guid))
        path = ctypes.c_wchar_p()
        if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(path)) == 0 and path.value:
            result = Path(path.value)
            ctypes.windll.ole32.CoTaskMemFree(path)
            return result
    except (OSError, AttributeError):
        logger.debug("Özel klasör alınamadı: %s", folder_id, exc_info=True)
    return fallback


def default_locations() -> Locations:
    home = Path.home()
    local = Path(os.environ.get("LOCALAPPDATA") or home / "AppData" / "Local")
    return Locations(
        install_dir=local / "Programs" / APP_NAME,
        start_menu=_known_folder("A77F5D77-2E2B-44C3-A6A2-ABA601054A51", home / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs"),
        desktop=_known_folder("B4BFCC3A-DB2C-424C-B029-7FE99A87C641", home / "Desktop"))


# ── Kayıt defteri (HKCU): "Uygulamalar ve özellikler" girdisi ──

class UninstallRegistry:
    """`HKCU\\...\\Uninstall\\GitCleanArchiver`; testlerde sahte bir nesneyle değiştirilir."""

    def __init__(self, subkey: str = UNINSTALL_KEY):
        self._subkey = subkey

    def read(self) -> Optional[Dict[str, object]]:
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._subkey) as key:
                values, index = {}, 0
                while True:
                    try:
                        name, value, _ = winreg.EnumValue(key, index)
                    except OSError:
                        return values
                    values[name] = value
                    index += 1
        except FileNotFoundError:
            return None

    def write(self, values: Dict[str, object]) -> None:
        import winreg
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, self._subkey, 0, winreg.KEY_SET_VALUE) as key:
            for name, value in values.items():
                kind = winreg.REG_DWORD if isinstance(value, int) else winreg.REG_SZ
                winreg.SetValueEx(key, name, 0, kind, value)

    def delete(self) -> None:
        import winreg
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, self._subkey)
        except FileNotFoundError:
            pass


def installed_state(registry: Optional[UninstallRegistry] = None) -> InstallState:
    values = (registry or UninstallRegistry()).read() or {}
    location = values.get("InstallLocation")
    if isinstance(location, str) and location and (Path(location) / EXE_NAME).is_file():
        version = values.get("DisplayVersion")
        return InstallState(True, version if isinstance(version, str) else "", Path(location))
    return InstallState(False)


def is_inside(path: Path, folder: Optional[Path]) -> bool:
    """`path`, `folder` içinde mi (büyük / küçük harf ve sembolik bağ duyarsız)."""
    if folder is None:
        return False
    try:
        return Path(os.path.normcase(os.path.realpath(path))).parent == Path(os.path.normcase(os.path.realpath(folder)))
    except OSError:
        return False


# ── Kısayol ──

def make_shortcut(link: Path, target: Path) -> None:
    script = ("$w = New-Object -ComObject WScript.Shell; $l = $w.CreateShortcut($env:GC_LINK); $l.TargetPath = $env:GC_TARGET; "
              "$l.WorkingDirectory = Split-Path -Parent $env:GC_TARGET; $l.IconLocation = $env:GC_TARGET + ',0'; "
              "$l.Description = $env:GC_NAME; $l.Save()")
    env = {**os.environ, "GC_LINK": str(link), "GC_TARGET": str(target), "GC_NAME": APP_NAME}
    link.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([str(POWERSHELL), "-NoProfile", "-NonInteractive", "-Command", script], env=env, capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=60, creationflags=CREATE_NO_WINDOW)
    if result.returncode != 0 or not link.is_file():
        raise InstallError("Kısayol oluşturulamadı: " + (result.stderr.strip() or "bilinmeyen hata"))


# ── Kurulum ──

def validate_target(target: Path) -> Path:
    """Kurulum klasörü: mutlak yol, sürücü kökü ya da kullanıcı klasörünün kendisi değil; dosya olmamalı."""
    if not target.is_absolute():
        raise InstallError("Kurulum klasörü tam bir yol olmalı.")
    if target == Path(target.anchor) or target == Path.home():
        raise InstallError("Sürücü kökü ya da kullanıcı klasörü kurulum klasörü olamaz; bir alt klasör seçin.")
    if target.exists() and not target.is_dir():
        raise InstallError("Seçilen yol bir klasör değil.")
    return target


def _registry_values(exe: Path, version: str) -> Dict[str, object]:
    return {
        "DisplayName": APP_NAME, "DisplayVersion": version, "Publisher": APP_NAME,
        "InstallLocation": str(exe.parent), "DisplayIcon": str(exe),
        "UninstallString": f'"{exe}" --uninstall', "QuietUninstallString": f'"{exe}" --uninstall --silent',
        "URLInfoAbout": f"https://github.com/{RELEASE_REPO}", "NoModify": 1, "NoRepair": 1,
        "EstimatedSize": max(1, exe.stat().st_size // 1024),
    }


def install(source: Path, target_dir: Path, *, version: str = __version__, desktop_shortcut: bool = False,
            locations: Optional[Locations] = None, registry: Optional[UninstallRegistry] = None,
            shortcut: Callable[[Path, Path], None] = make_shortcut) -> Path:
    """`source` (çalışan exe) dosyasını `target_dir`'e kopyalar, kısayol ve kaldırma kaydı oluşturur; kurulan exe'nin yolunu döner."""
    locations, registry = locations or default_locations(), registry or UninstallRegistry()
    target_dir = validate_target(target_dir)
    destination = target_dir / EXE_NAME
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        if not (destination.exists() and destination.samefile(source)):
            staging = destination.with_name(EXE_NAME + f".{uuid.uuid4().hex[:8]}.new")
            try:
                shutil.copyfile(source, staging)
                os.replace(staging, destination)                       # çalışan kurulu sürüm varsa PermissionError verir
            finally:
                staging.unlink(missing_ok=True)
    except PermissionError as e:
        raise InstallError("Kurulu uygulama çalışıyor olabilir: GitClean Archiver'ı kapatıp yeniden deneyin.") from e
    except OSError as e:
        raise InstallError(f"Dosyalar kopyalanamadı: {e.strerror or e}") from e
    shortcut(locations.start_menu / SHORTCUT_NAME, destination)
    desktop_link = locations.desktop / SHORTCUT_NAME
    if desktop_shortcut:
        shortcut(desktop_link, destination)
    registry.write(_registry_values(destination, version))
    logger.info("Kuruldu: %s (sürüm %s)", destination, version)
    return destination


def _schedule_delete(exe: Path) -> None:
    """Çalışan exe kendini silemez: çıkıştan sonra silecek ayrı bir komut başlatır (yol ortam değişkeniyle geçer).

    `cmd /s /c "..."`: dış tırnaklar soyulur, içteki tırnaklı yollar korunur; komut tek dize olarak verilir (liste verilirse
    Python ek tırnak ekler ve cmd komutu bozar)."""
    command = 'cmd /d /s /c "ping -n 4 127.0.0.1 >nul & del /f /q "%GC_EXE%" & rmdir "%GC_DIR%""'
    subprocess.Popen(command, env={**os.environ, "GC_EXE": str(exe), "GC_DIR": str(exe.parent)},
                     creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS, close_fds=True)


def uninstall(*, locations: Optional[Locations] = None, registry: Optional[UninstallRegistry] = None,
              schedule_delete: Callable[[Path], None] = _schedule_delete) -> bool:
    """Kısayolları, kaydı ve kurulu exe'yi kaldırır. Kurulu değilse False döner. Kullanıcı verisine dokunmaz."""
    locations, registry = locations or default_locations(), registry or UninstallRegistry()
    state = installed_state(registry)
    for link in (locations.start_menu / SHORTCUT_NAME, locations.desktop / SHORTCUT_NAME):
        link.unlink(missing_ok=True)
    registry.delete()
    if not state.installed:
        return False
    exe = state.exe
    try:
        exe.unlink()
        try:
            state.location.rmdir()                                      # yalnızca boşsa
        except OSError:
            pass
    except PermissionError:
        schedule_delete(exe)                                            # çalışıyor: çıkıştan sonra silinir
    logger.info("Kaldırıldı: %s", state.location)
    return True


# ── Komut satırı: sessiz kurulum / kaldırma (betik ve "Uygulamalar ve özellikler" için) ──

def running_exe() -> Optional[Path]:
    """Donmuş (PyInstaller) uygulamanın kendi exe yolu; geliştirme ortamında None."""
    return Path(sys.executable) if getattr(sys, "frozen", False) else None


def run_cli(argv: list) -> Optional[int]:
    """`--install` / `--uninstall` bayrakları varsa işler ve çıkış kodunu döner; yoksa None (uygulama normal açılır).

    --install [--silent] [--dir <klasör>] [--desktop-shortcut]
    --uninstall [--silent]
    """
    if "--uninstall" in argv:
        try:
            uninstall()
        except (OSError, InstallError) as e:
            logger.error("Kaldırma başarısız: %s", e)
            return 1
        return 0
    if "--install" in argv:
        source = running_exe()
        if source is None:
            logger.error("--install yalnızca paketlenmiş exe ile çalışır.")
            return 2
        directory = default_locations().install_dir
        if "--dir" in argv and argv.index("--dir") + 1 < len(argv):
            directory = Path(argv[argv.index("--dir") + 1])
        try:
            install(source, directory, desktop_shortcut="--desktop-shortcut" in argv)
        except (OSError, InstallError) as e:
            logger.error("Kurulum başarısız: %s", e)
            return 1
        return 0
    return None


# ── Tercih: "Bir daha sorma" ──

PROMPT_OPT_OUT_ENV = "GITCLEAN_NO_INSTALL_PROMPT"


def preferences_path() -> Path:
    return Path.home() / ".gitclean" / "install.json"


def prompt_enabled(path: Optional[Path] = None) -> bool:
    """Kurulu olmayan exe açılınca kurma önerisi gösterilsin mi (varsayılan evet)."""
    import json
    target = Path(path) if path else preferences_path()
    try:
        data = json.loads(target.read_text(encoding="utf-8")) if target.is_file() else {}
    except (OSError, ValueError):
        return True
    return not (isinstance(data, dict) and data.get("ask_install") is False) and \
        os.environ.get(PROMPT_OPT_OUT_ENV, "").strip().lower() not in ("1", "true", "yes")


def disable_prompt(path: Optional[Path] = None) -> None:
    import json
    target = Path(path) if path else preferences_path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps({"ask_install": False}), encoding="utf-8")
    except OSError as e:
        logger.warning("Kurulum tercihi kaydedilemedi: %s (%s)", target, e)
