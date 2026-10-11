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


class DownloadWorker(QThread):
    """Arka planda kurulum dosyasını indirir ve doğrular; ilerleme yüzdesini bildirir."""

    progress = Signal(int)
    downloaded = Signal(str)                  # indirilen kurulum dosyasının yolu
    failed = Signal(str)

    def __init__(self, download: Callable[[UpdateInfo, Callable[[int], None]], Path], info: UpdateInfo):
        super().__init__()
        self._download, self._info = download, info

    def run(self):
        try:
            self.downloaded.emit(str(self._download(self._info, self.progress.emit)))
        except UpdateCheckError as e:
            self.failed.emit(str(e))
        except Exception as e:                                   # beklenmeyen hata arayüzü düşürmemeli
            logger.warning("Güncelleme indirilemedi: %s", e, exc_info=True)
            self.failed.emit("Güncelleme indirilemedi.")


class UpdateViewModel(QObject):
    """Güncelleme penceresi ve ayarlar kartı köprüsü. Açılışta sessiz denetim; hata sessizce yutulur, elle denetimde gösterilir.

    "Güncelle": kurulum dosyası indirilir, SHA-256 doğrulanır, kurulum başlatılır ve uygulama kapanır (`quitRequested`)."""

    stateChanged = Signal()
    popupRequested = Signal()                 # yeni sürüm bulundu: pencere açılmalı
    quitRequested = Signal()                  # kurulum başlatıldı: uygulama kapanmalı

    def __init__(self, check: Optional[Callable[[], Optional[UpdateInfo]]] = None, preferences_file: Optional[Path] = None,
                 download: Optional[Callable[[UpdateInfo, Callable[[int], None]], Path]] = None,
                 launcher: Optional[Callable[[Path], None]] = None, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._check = check or (lambda: update_service.check_for_update(__version__, RELEASE_REPO))
        self._download = download or update_service.download_installer
        self._launcher = launcher or update_service.launch_installer
        self._downloading = False
        self._progress = 0
        self._error = ""
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

    @Property(bool, notify=stateChanged)
    def isDownloading(self) -> bool:
        return self._downloading

    @Property(int, notify=stateChanged)
    def downloadProgress(self) -> int:
        return self._progress

    @Property(str, notify=stateChanged)
    def errorMessage(self) -> str:
        return self._error

    @Property(bool, notify=stateChanged)
    def canInstall(self) -> bool:
        """Kurulum dosyası indirilebilir mi (Release'te kurulum dosyası var mı)."""
        return bool(self._info and self._info.download_url)

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
    def startUpdate(self) -> None:
        """Kurulum dosyasını indirir ve doğrular; sonra kurulum başlar ve uygulama kapanır."""
        if self._info is None or self._downloading:
            return
        if not self._info.download_url:
            self.openReleasePage()                  # Release'te kurulum dosyası yok: sayfa açılır
            return
        self._error, self._progress, self._downloading = "", 0, True
        self.stateChanged.emit()
        self._worker = DownloadWorker(self._download, self._info)
        self._worker.progress.connect(self._on_progress)
        self._worker.downloaded.connect(self._on_downloaded)
        self._worker.failed.connect(self._on_download_failed)
        self._worker.start()

    def _on_progress(self, percent: int) -> None:
        self._progress = percent
        self.stateChanged.emit()

    def _on_downloaded(self, path: str) -> None:
        try:
            self._launcher(Path(path))
        except (UpdateCheckError, OSError) as e:
            self._on_download_failed(str(e) if isinstance(e, UpdateCheckError) else "Kurulum başlatılamadı.")
            return
        self.quitRequested.emit()

    def _on_download_failed(self, message: str) -> None:
        self._downloading, self._error = False, message
        self.stateChanged.emit()

    @Slot()
    def openReleasePage(self) -> None:
        if self._info:
            QDesktopServices.openUrl(QUrl(self._info.page_url))
