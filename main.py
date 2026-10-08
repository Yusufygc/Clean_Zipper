import sys
import ctypes
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPalette, QColor, QIcon
from src.ui.main_window import GitCleanArchiverPro
from src.utils.logging_config import setup_logging

def main():
    setup_logging()
    app = QApplication(sys.argv)
    
    # 1. Temel stili belirle
    app.setStyle("Fusion")
    
    # 2. İŞLETİM SİSTEMİ DARK MODE'UNU EZEN KURUMSAL PALET (KRİTİK ÇÖZÜM)
    # Bu ayar, QSS'in etki edemediği diyalog pencerelerinin arkaplanını beyaza zorlar.
    light_palette = QPalette()
    light_palette.setColor(QPalette.ColorRole.Window, QColor("#FFFFFF"))      # Arkaplan saf beyaz
    light_palette.setColor(QPalette.ColorRole.WindowText, QColor("#0F172A"))  # Metinler antrasit
    light_palette.setColor(QPalette.ColorRole.Base, QColor("#FFFFFF"))
    light_palette.setColor(QPalette.ColorRole.Text, QColor("#0F172A"))
    light_palette.setColor(QPalette.ColorRole.Button, QColor("#FFFFFF"))
    light_palette.setColor(QPalette.ColorRole.ButtonText, QColor("#0F172A"))
    app.setPalette(light_palette)
    
    # 3. İkon Yolu Çözümleme (PyInstaller Desteği)
    if hasattr(sys, '_MEIPASS'):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent
        
    icon_path = base_path / "resources" / "icons" / "app_icon.ico"
    app.setWindowIcon(QIcon(str(icon_path)))
    
    # 4. Görev çubuğunda ikonun görünmesi için AppUserModelID ayarı (Windows)
    try:
        myappid = 'gitclean.archiver.pro.2.0.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass
    
    window = GitCleanArchiverPro()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()