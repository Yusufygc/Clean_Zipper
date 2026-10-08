import os
import sys
import ctypes
import logging
from pathlib import Path

from PySide6.QtGui import QIcon, QFont
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QUrl

from src.qml_ui.viewmodels.app_viewmodel import AppViewModel
from src.qml_ui.viewmodels.scan_viewmodel import ScanViewModel
from src.qml_ui.viewmodels.findings_viewmodel import FindingsViewModel
from src.utils.logging_config import setup_logging

logger = logging.getLogger(__name__)


def create_qml_app():
    setup_logging()

    # 1. Qt Application Nesnesi
    app = QApplication(sys.argv)
    app.setApplicationName("GitClean Archiver Pro")
    app.setOrganizationName("GitClean")

    # Font ayarı
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # 2. İkon & Windows AppUserModelID
    base_dir = Path(__file__).resolve().parents[2]
    icon_path = base_dir / "resources" / "icons" / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    try:
        myappid = "gitclean.archiver.pro.2.0.0.qml"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        logger.debug("AppUserModelID ayarlanamadı", exc_info=True)

    # 3. QML Engine Kurulumu
    engine = QQmlApplicationEngine()
    
    qml_dir = Path(__file__).parent / "qml"
    engine.addImportPath(str(qml_dir))
    engine.addImportPath(str(qml_dir / "singletons"))
    engine.addImportPath(str(qml_dir / "components"))
    engine.addImportPath(str(qml_dir / "views"))

    # 4. ViewModel & Bridge Kaydı
    app_vm = AppViewModel()
    scan_vm = ScanViewModel(app_vm.service)
    findings_vm = FindingsViewModel(app_vm.service)

    # Proje açıldığında otomatik hızlı tarama ve derin teşhis tetikle
    app_vm.projectChanged.connect(lambda: scan_vm.startQuickScan() if app_vm.hasProject else None)
    app_vm.projectChanged.connect(lambda: findings_vm.startDeepDiagnosis() if app_vm.hasProject else None)

    engine.rootContext().setContextProperty("appVM", app_vm)
    engine.rootContext().setContextProperty("scanVM", scan_vm)
    engine.rootContext().setContextProperty("findingsVM", findings_vm)

    # 5. QML Ana Penceresini Yükleme
    main_qml_path = qml_dir / "MainView.qml"
    engine.load(QUrl.fromLocalFile(str(main_qml_path)))

    if not engine.rootObjects():
        logger.error("QML ana penceresi yüklenemedi!")
        sys.exit(-1)

    return app, engine


def run():
    app, _ = create_qml_app()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
