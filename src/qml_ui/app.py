import sys
import ctypes
import logging
from pathlib import Path
from typing import Dict

from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QCoreApplication, QEvent, QObject, QTimer, QUrl

from src.qml_ui.viewmodels.app_viewmodel import AppViewModel
from src.qml_ui.viewmodels.scan_viewmodel import ScanViewModel
from src.qml_ui.viewmodels.findings_viewmodel import FindingsViewModel
from src.qml_ui.viewmodels.archive_viewmodel import ArchiveViewModel
from src.qml_ui.viewmodels.cleanup_viewmodel import CleanupViewModel
from src.qml_ui.viewmodels.settings_viewmodel import SettingsViewModel
from src.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


def _configure_application() -> QApplication:
    """Qt uygulama nesnesi, yazı tipi, simge ve Windows görev çubuğu kimliği (testlerde var olan örnek yeniden kullanılır)."""
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("GitClean Archiver Pro")
    app.setOrganizationName("GitClean")
    app.setFont(QFont("Segoe UI", 10))

    icon_path = Path(__file__).resolve().parents[2] / "resources" / "icons" / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("gitclean.archiver.pro.2.0.0.qml")
    except Exception:
        logger.debug("AppUserModelID ayarlanamadı", exc_info=True)
    return app


def _create_view_models() -> Dict[str, QObject]:
    """Altı ViewModel'i kurar ve birbirine bağlar; anahtarlar QML'deki context property adlarıdır."""
    app_vm = AppViewModel()
    scan_vm = ScanViewModel(app_vm.service)
    findings_vm = FindingsViewModel(app_vm.service)
    settings_vm = SettingsViewModel(app_vm.service)      # kayıtlı ayarları açılışta servise uygular

    # Proje açıldığında otomatik hızlı tarama ve derin teşhis tetikle
    app_vm.projectChanged.connect(lambda: scan_vm.startQuickScan() if app_vm.hasProject else None)
    app_vm.projectChanged.connect(lambda: findings_vm.startDeepDiagnosis() if app_vm.hasProject else None)

    # Varsayılan ajan klasörü proje adına bağlı; bir kural kapatılıp açılınca bulgular yeni kurallarla yeniden hesaplanır
    app_vm.projectChanged.connect(settings_vm.onProjectChanged)
    settings_vm.rulesChanged.connect(
        lambda: (scan_vm.startQuickScan(), findings_vm.startDeepDiagnosis()) if app_vm.hasProject else None)

    return {"appVM": app_vm, "scanVM": scan_vm, "findingsVM": findings_vm,
            "archiveVM": ArchiveViewModel(app_vm.service), "cleanupVM": CleanupViewModel(app_vm.service),
            "settingsVM": settings_vm}


def create_qml_app():
    setup_logging()
    app = _configure_application()

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
        if worker is not None and worker.isRunning():
            worker.wait(WORKER_WAIT_MS)                    # çalışan QThread yok edilirse süreç çöker
    for root in engine.rootObjects():
        root.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    engine.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    view_models.clear()


def run(quit_after_ms: int = 0):
    """Uygulamayı çalıştırır. `quit_after_ms` yalnızca testler içindir (0 = pencere kapanana dek)."""
    app, engine = create_qml_app()
    if quit_after_ms:
        QTimer.singleShot(quit_after_ms, app.quit)
    code = app.exec()
    shutdown_qml_app(engine)
    sys.exit(code)


if __name__ == "__main__":
    run()
