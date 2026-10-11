import logging
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Property, QObject, QThread, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from src.services import update_service
from src.services.update_service import UpdateCheckError, UpdateInfo
from src.version import RELEASE_REPO, __version__

logger = logging.getLogger(__name__)


class UpdateWorker(QThread):
    """Arka planda tek bir güncelleme denetimi (ağ beklerken arayüz donmaz)."""

    finished_check = Signal(object)          # UpdateInfo | None
    failed = Signal(str)

    def __init__(self, check: Callable[[], Optional[UpdateInfo]]):
        super().__init__()
        self._check = check

    def run(self):
        try:
            self.finished_check.emit(self._check())
        except UpdateCheckError as e:
            self.failed.emit(str(e))
        except Exception as e:                                   # beklenmeyen hata arayüzü düşürmemeli
            logger.warning("Güncelleme denetimi beklenmedik şekilde başarısız: %s", e, exc_info=True)
            self.failed.emit("Güncelleme denetimi yapılamadı.")


class UpdateViewModel(QObject):
    """Güncelleme penceresi ve ayarlar kartı köprüsü. Açılışta sessiz denetim; hata sessizce yutulur, elle denetimde gösterilir."""

    stateChanged = Signal()
    popupRequested = Signal()                 # yeni sürüm bulundu: pencere açılmalı

    def __init__(self, check: Optional[Callable[[], Optional[UpdateInfo]]] = None, preferences_file: Optional[Path] = None,
                 parent: Optional[QObject] = None):
        super().__init__(parent)
        self._check = check or (lambda: update_service.check_for_update(__version__, RELEASE_REPO))
        self._preferences_file = preferences_file
        self._preferences = update_service.load_preferences(preferences_file)
        self._worker: Optional[UpdateWorker] = None
        self._manual = False
        self._checking = False
        self._info: Optional[UpdateInfo] = None
        self._status = ""

    # ── Özellikler ──

    @Property(str, constant=True)
    def currentVersion(self) -> str:
        return __version__

    @Property(bool, notify=stateChanged)
    def checking(self) -> bool:
        return self._checking

    @Property(bool, notify=stateChanged)
    def updateAvailable(self) -> bool:
        return self._info is not None

    @Property(str, notify=stateChanged)
    def latestVersion(self) -> str:
        return self._info.version if self._info else ""

    @Property(str, notify=stateChanged)
    def releaseNotes(self) -> str:
        return self._info.notes if self._info else ""

    @Property(str, notify=stateChanged)
    def publishedDate(self) -> str:
        return self._info.published if self._info else ""

    @Property(str, notify=stateChanged)
    def installerLabel(self) -> str:
        """Kurulum dosyasının adı ve boyutu; dosya yoksa sürüm sayfası açılacağı belirtilir."""
        if not self._info:
            return ""
        if not self._info.download_url:
            return "Sürüm sayfası tarayıcıda açılır."
        megabytes = f", {self._info.size / (1024 * 1024):.0f} MB" if self._info.size else ""
        return f"{self._info.asset_name}{megabytes}"

    @Property(str, notify=stateChanged)
    def statusText(self) -> str:
        return self._status

    @Property(bool, notify=stateChanged)
    def checkEnabled(self) -> bool:
        return self._preferences.check_enabled

    # ── Denetim ──

    def _start(self, manual: bool) -> None:
        if self._checking:
            return
        self._manual, self._checking = manual, True
        self._status = "Güncellemeler denetleniyor…" if manual else ""
        self.stateChanged.emit()
        self._worker = UpdateWorker(self._check)
        self._worker.finished_check.connect(self._on_checked)
        self._worker.failed.connect(self._on_failed)
        self._worker.start()

    @Slot()
    def startupCheck(self) -> None:
        """Açılışta sessiz denetim (kapalıysa hiç ağ isteği yapılmaz)."""
        if self._preferences.check_enabled and not update_service.updates_disabled_by_environment():
            self._start(manual=False)

    @Slot()
    def checkNow(self) -> None:
        self._start(manual=True)

    def _on_checked(self, info: Optional[UpdateInfo]) -> None:
        self._checking = False
        self._info = info
        if info is None:
            self._status = f"Güncelsiniz: v{__version__} en son sürüm." if self._manual else ""
        else:
            self._status = f"Yeni sürüm var: v{info.version}"
        self.stateChanged.emit()
        if info is not None and (self._manual or info.version != self._preferences.skipped_version):
            self.popupRequested.emit()               # atlanan sürüm yalnızca açılışta sessiz kalır, elle denetimde gösterilir

    def _on_failed(self, message: str) -> None:
        self._checking = False
        self._status = message if self._manual else ""
        self.stateChanged.emit()

    # ── Kullanıcı eylemleri ──

    @Slot(bool)
    def setCheckEnabled(self, enabled: bool) -> None:
        self._preferences.check_enabled = bool(enabled)
        update_service.save_preferences(self._preferences, self._preferences_file)
        self.stateChanged.emit()

    @Slot()
    def skipVersion(self) -> None:
        if self._info:
            self._preferences.skipped_version = self._info.version
            update_service.save_preferences(self._preferences, self._preferences_file)

    @Slot()
    def openDownload(self) -> None:
        """Kurulum dosyasını (yoksa sürüm sayfasını) varsayılan tarayıcıda açar; uygulama hiçbir şey indirip çalıştırmaz."""
        if self._info:
            QDesktopServices.openUrl(QUrl(self._info.download_url or self._info.page_url))

    @Slot()
    def openReleasePage(self) -> None:
        if self._info:
            QDesktopServices.openUrl(QUrl(self._info.page_url))
