import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from src.ui.main_window import GitCleanArchiverPro

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = GitCleanArchiverPro()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
