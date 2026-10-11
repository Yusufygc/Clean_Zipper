import logging
import subprocess
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.services import install_service as svc
from src.services.install_service import InstallError, Locations, UninstallRegistry
from src.services.update_service import parse_version
from src.version import __version__

logger = logging.getLogger(__name__)


def launch_detached(exe: Path) -> None:
    subprocess.Popen([str(exe)], creationflags=svc.CREATE_NO_WINDOW | svc.DETACHED_PROCESS, close_fds=True)


class InstallViewModel(QObject):
    """"Kur / Güncelle" penceresi ve Ayarlar'daki kaldırma düğmesi köprüsü.

    İndirilen exe kurulu değilse (ya da kurulu sürüm eskiyse) açılışta kurma önerilir; kurulan kopya başlatılır, bu kopya kapanır.
    Geliştirme ortamında (`python main.py`) hiçbir öneri çıkmaz.
    """

    stateChanged = Signal()
    promptRequested = Signal()
    finished = Signal()                       # uygulama kapanmalı (kurulan kopya başlatıldı ya da kaldırma bitti)

    def __init__(self, exe: Optional[Path] = None, locations: Optional[Locations] = None,
                 registry: Optional[UninstallRegistry] = None, shortcut: Callable[[Path, Path], None] = svc.make_shortcut,
                 launcher: Callable[[Path], None] = launch_detached, preferences_file: Optional[Path] = None,
                 parent: Optional[QObject] = None):
        super().__init__(parent)
        self._exe = exe if exe is not None else svc.running_exe()
        self._locations = locations or svc.default_locations()
        self._registry = registry or UninstallRegistry()
        self._shortcut, self._launcher, self._preferences_file = shortcut, launcher, preferences_file
        self._desktop_shortcut = False
        self._error = ""
        self._state = svc.installed_state(self._registry)

    # ── Durum ──

    @Property(str, constant=True)
    def currentVersion(self) -> str:
        return __version__

    @Property(bool, notify=stateChanged)
    def runningFromInstall(self) -> bool:
        return self._exe is not None and self._state.installed and svc.is_inside(self._exe, self._state.location)

    @Property(bool, notify=stateChanged)
    def promptNeeded(self) -> bool:
        """Paketlenmiş exe, kurulu konumda değil; kurulu sürüm yok ya da eski; kullanıcı "bir daha sorma" dememiş."""
        if self._exe is None or self.runningFromInstall or not svc.prompt_enabled(self._preferences_file):
            return False
        installed, current = parse_version(self._state.version), parse_version(__version__)
        return not (self._state.installed and installed is not None and current is not None and installed >= current)

    @Property(str, notify=stateChanged)
    def mode(self) -> str:
        return "update" if self._state.installed else "install"

    @Property(str, notify=stateChanged)
    def installedVersion(self) -> str:
        return self._state.version

    @Property(str, notify=stateChanged)
    def installDir(self) -> str:
        return str(self._state.location or self._locations.install_dir)

    @Property(bool, notify=stateChanged)
    def canUninstall(self) -> bool:
        return self.runningFromInstall

    @Property(bool, notify=stateChanged)
    def desktopShortcut(self) -> bool:
        return self._desktop_shortcut

    @Property(str, notify=stateChanged)
    def errorText(self) -> str:
        return self._error

    @Slot(bool)
    def setDesktopShortcut(self, enabled: bool) -> None:
        self._desktop_shortcut = bool(enabled)
        self.stateChanged.emit()

    @Slot()
    def requestPromptIfNeeded(self) -> None:
        if self.promptNeeded:
            self.promptRequested.emit()

    # ── Eylemler ──

    @Slot()
    def install(self) -> None:
        if self._exe is None:
            return
        try:
            installed = svc.install(self._exe, Path(self.installDir), desktop_shortcut=self._desktop_shortcut,
                                    locations=self._locations, registry=self._registry, shortcut=self._shortcut)
        except InstallError as e:
            self._error = str(e)
            self.stateChanged.emit()
            return
        except OSError as e:
            logger.warning("Kurulum başarısız: %s", e, exc_info=True)
            self._error = "Kurulum yapılamadı."
            self.stateChanged.emit()
            return
        self._error = ""
        self._state = svc.installed_state(self._registry)
        self.stateChanged.emit()
        self._launcher(installed)                 # kurulan kopya açılır, bu kopya kapanır
        self.finished.emit()

    @Slot(bool)
    def decline(self, never_ask_again: bool) -> None:
        if never_ask_again:
            svc.disable_prompt(self._preferences_file)
            self.stateChanged.emit()

    @Slot()
    def uninstall(self) -> None:
        """Kurulu uygulamayı kaldırır (ayarlar, günlük ve yedekler silinmez) ve kapanır."""
        try:
            svc.uninstall(locations=self._locations, registry=self._registry)
        except (OSError, InstallError) as e:
            logger.warning("Kaldırma başarısız: %s", e, exc_info=True)
            self._error = "Kaldırma yapılamadı."
            self.stateChanged.emit()
            return
        self._state = svc.installed_state(self._registry)
        self.stateChanged.emit()
        self.finished.emit()
