import sys
from pathlib import Path

# Proje kökünü sys.path'e ekle
sys.path.insert(0, str(Path(__file__).parent))

from src.qml_ui.app import run

if __name__ == "__main__":
    run()
