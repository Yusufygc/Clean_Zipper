import sys
import ctypes
import logging
from pathlib import Path
from typing import Dict

from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtCore import QCoreApplication, QEvent, QObject, QTimer, QUrl

from src.qml_ui.viewmodels.app_viewmodel import AppViewModel
from src.qml_ui.viewmodels.scan_viewmodel import ScanViewModel
from src.qml_ui.viewmodels.findings_viewmodel import FindingsViewModel
from src.qml_ui.viewmodels.archive_viewmodel import ArchiveViewModel
from src.qml_ui.viewmodels.cleanup_viewmodel import CleanupViewModel
from src.qml_ui.viewmodels.settings_viewmodel import SettingsViewModel
from src.qml_ui.viewmodels.update_viewmodel import UpdateViewModel
from src.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


def _configure_application() -> QApplication:
    """Qt uygulama nesnesi, yazı tipi, simge ve Windows görev çubuğu kimliği (testlerde var olan örnek yeniden kullanılır)."""
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("GitClean Archiver")
    app.setOrganizationName("GitClean")
    app.setFont(QFont("Segoe UI", 10))

    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    icon_path = base_dir / "resources" / "icons" / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("gitclean.archiver.qml")   # sürümsüz: güncellemede görev çubuğu sabitlemesi bozulmaz
    except Exception:
        logger.debug("AppUserModelID ayarlanamadı", exc_info=True)
    return app


def _create_view_models() -> Dict[str, QObject]:
    """Yedi ViewModel'i kurar ve birbirine bağlar; anahtarlar QML'deki context property adlarıdır."""
    app_vm = AppViewModel()
    scan_vm = ScanViewModel(app_vm.service)
    findings_vm = FindingsViewModel(app_vm.service)
    settings_vm = SettingsViewModel(app_vm.service)      # kayıtlı ayarları açılışta servise uygular

    # Proje açıldığında otomatik hızlı tarama ve derin teşhis tetikle
    app_vm.projectChanged.connect(lambda: scan_vm.startQuickScan() if app_vm.hasProject else None)
    app_vm.projectChanged.connect(lambda: findings_vm.startDeepDiagnosis() if app_vm.hasProject else None)

    # Varsayılan ajan klasörü proje adına bağlı; bir kural kapatılıp açılınca bulgular yeni kurallarla yeniden hesaplanır
    app_vm.projectChanged.connect(settings_vm.onProjectChanged)
    def refresh_analysis():
        if app_vm.hasProject:
            scan_vm.startQuickScan()
            findings_vm.startDeepDiagnosis()

    settings_vm.rulesChanged.connect(refresh_analysis)

    archive_vm = ArchiveViewModel(app_vm.service)
    cleanup_vm = CleanupViewModel(app_vm.service)
    # Temizlik ya da proje içine yazılan zip / kopya sonrası dashboard ve bulgu listesi bayat kalmasın
    cleanup_vm.projectModified.connect(refresh_analysis)
    archive_vm.projectModified.connect(refresh_analysis)

    # Güncelleme denetimi projeden bağımsızdır: `ProjectService` kullanmaz, kendi servisiyle konuşur
    return {"appVM": app_vm, "scanVM": scan_vm, "findingsVM": findings_vm,
            "archiveVM": archive_vm, "cleanupVM": cleanup_vm, "settingsVM": settings_vm, "updateVM": UpdateViewModel()}


def create_qml_app():
    setup_logging()
    app = _configure_application()

    # Tüm denetimler (onay kutusu, kaydırma çubuğu, açılır liste) kendi görünümünü çizer: özelleştirilebilen Basic stili
    # açıkça seçilir. Varsayılan yerel Windows stili özelleştirmeyi desteklemez ve ekransız ortamda uyarı üretir.
    QQuickStyle.setStyle("Basic")
    engine = QQmlApplicationEngine()
    qml_dir = Path(__file__).parent / "qml"
    for folder in ("", "singletons", "components", "views"):
        engine.addImportPath(str(qml_dir / folder))

    view_models = _create_view_models()
    for name, view_model in view_models.items():
        engine.rootContext().setContextProperty(name, view_model)

    # Context property'ler yalnızca zayıf referans tutar: referans verilmezse Python çöp toplayıcısı bu nesneleri siler ve
    # QML `archiveVM`, `cleanupVM`, `settingsVM` için "Cannot read property ... of null" hatası verir. Engine ömrü boyunca
    # canlı kalmaları için engine üzerinde tutulur (`create_qml_app` dönüşündeki engine `run()` içinde saklanır).
    engine.viewmodels = list(view_models.values())

    engine.load(QUrl.fromLocalFile(str(qml_dir / "MainView.qml")))
    if not engine.rootObjects():
        logger.error("QML ana penceresi yüklenemedi!")
        sys.exit(-1)

    return app, engine


WORKER_WAIT_MS = 5000


def shutdown_qml_app(engine: QQmlApplicationEngine) -> None:
    """Kapanış sırası: önce çalışan iş parçacıkları beklenir, sonra QML nesneleri, en son ViewModel'ler yok edilir.

    Sıra tersine dönerse (ViewModel'ler önce) açık görünümlerin bağlamaları `null` okur ve konsola yüzlerce
    "Cannot read property ... of null" hatası basılır.
    """
    view_models = list(getattr(engine, "viewmodels", []))
    for view_model in view_models:
        worker = getattr(view_model, "_worker", None)
        if worker is not None and worker.isRunning() and not worker.wait(WORKER_WAIT_MS):
            worker.terminate()                             # çalışan QThread yok edilirse süreç çöker (ör. ağda takılan güncelleme denetimi)
            worker.wait(WORKER_WAIT_MS)
    for root in engine.rootObjects():
        root.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    engine.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    view_models.clear()


UPDATE_CHECK_DELAY_MS = 3000


def run(quit_after_ms: int = 0):
    """Uygulamayı çalıştırır. `quit_after_ms` yalnızca testler içindir (0 = pencere kapanana dek)."""
    app, engine = create_qml_app()
    # Açılışta sessiz güncelleme denetimi: pencere çizildikten sonra, `create_qml_app` içinde değil (testler ağa çıkmasın)
    update_vm = next(vm for vm in engine.viewmodels if isinstance(vm, UpdateViewModel))
    QTimer.singleShot(UPDATE_CHECK_DELAY_MS, update_vm.startupCheck)
    if quit_after_ms:
        QTimer.singleShot(quit_after_ms, app.quit)
    code = app.exec()
    shutdown_qml_app(engine)
    sys.exit(code)


if __name__ == "__main__":
    run()
