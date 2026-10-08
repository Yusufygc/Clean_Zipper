"""Uygulama genelinde dosyaya loglama ve yakalanmayan istisnaların kaydı.

Windowed (konsolsuz) exe'de stderr yoktur; bu kurulum olmadan loglar ve traceback'ler kaybolur.
"""
import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

LOG_FILE_NAME = 'gitclean.log'
LOG_FORMAT = '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
LEVEL_ENV_VAR = 'GITCLEAN_LOG_LEVEL'
MAX_BYTES = 1_000_000
BACKUP_COUNT = 3

_HANDLER_ATTR = '_gitclean_handler'


def default_log_dir() -> Path:
    return Path.home() / '.gitclean' / 'logs'


def setup_logging(log_dir: Optional[Path] = None, level: Optional[str] = None) -> Path:
    """Kök logger'a dönen dosya handler'ı ekler, yakalanmayan istisna kancalarını kurar. İdempotenttir.

    Döner: log dosyasının yolu.
    """
    directory = Path(log_dir) if log_dir else default_log_dir()
    directory.mkdir(parents=True, exist_ok=True)
    log_path = directory / LOG_FILE_NAME

    root = logging.getLogger()
    resolved_level = _resolve_level(level)
    existing = next((h for h in root.handlers if getattr(h, _HANDLER_ATTR, False)), None)
    if existing is not None and Path(existing.baseFilename) == log_path.resolve():
        root.setLevel(resolved_level)
        return log_path
    if existing is not None:                                   # farklı dizine geçiş: eskiyi bırak
        root.removeHandler(existing)
        existing.close()

    handler = RotatingFileHandler(log_path, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT, encoding='utf-8')
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    setattr(handler, _HANDLER_ATTR, True)
    root.addHandler(handler)
    root.setLevel(resolved_level)
    _install_exception_hooks()
    return log_path


def shutdown_logging():
    """Testler ve temiz kapanış için: kurulan handler'ı kaldırır ve dosyayı kapatır."""
    root = logging.getLogger()
    for handler in [h for h in root.handlers if getattr(h, _HANDLER_ATTR, False)]:
        root.removeHandler(handler)
        handler.close()


def _resolve_level(level: Optional[str]) -> int:
    name = (level or os.environ.get(LEVEL_ENV_VAR) or 'INFO').upper()
    resolved = logging.getLevelName(name)
    return resolved if isinstance(resolved, int) else logging.INFO


_hooks_installed = False


def _install_exception_hooks():
    global _hooks_installed
    if _hooks_installed:
        return
    _hooks_installed = True
    previous_excepthook = sys.excepthook
    previous_thread_hook = threading.excepthook

    def log_uncaught(exc_type, exc_value, exc_traceback):
        if not issubclass(exc_type, KeyboardInterrupt):
            logging.getLogger('uncaught').critical(
                'Yakalanmayan istisna', exc_info=(exc_type, exc_value, exc_traceback))
        previous_excepthook(exc_type, exc_value, exc_traceback)

    def log_uncaught_in_thread(args):
        logging.getLogger('uncaught').critical(
            'Yakalanmayan istisna (iş parçacığı: %s)', getattr(args.thread, 'name', '?'),
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback))
        previous_thread_hook(args)

    sys.excepthook = log_uncaught
    threading.excepthook = log_uncaught_in_thread
