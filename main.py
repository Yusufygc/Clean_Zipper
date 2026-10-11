"""GitClean Archiver giriş noktası (QML arayüzü)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.qml_ui.app import run  # noqa: E402  (sys.path ayarından sonra)

if __name__ == "__main__":
    run()
