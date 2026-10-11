"""GitClean Archiver giriş noktası (QML arayüzü)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.services.install_service import run_cli  # noqa: E402  (sys.path ayarından sonra)
from src.utils.logging_config import setup_logging  # noqa: E402

if __name__ == "__main__":
    # --install / --uninstall: arayüz açmadan kurar ya da kaldırır ("Uygulamalar ve özellikler" ve betikler için)
    if any(flag in sys.argv for flag in ("--install", "--uninstall")):
        setup_logging()
        sys.exit(run_cli(sys.argv[1:]))
    from src.qml_ui.app import run
    run()
