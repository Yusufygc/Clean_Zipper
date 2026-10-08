import logging
import os
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from src.core.errors import GitCleanError, ProjectNotSelectedError
from src.utils import logging_config
from src.utils.logging_config import LOG_FILE_NAME, setup_logging, shutdown_logging

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def clean_logging_state(monkeypatch):
    """Kök logger ve istisna kancalarını her testten sonra eski haline getirir."""
    root = logging.getLogger()
    level = root.level
    monkeypatch.setattr(sys, "excepthook", sys.excepthook)
    monkeypatch.setattr(threading, "excepthook", threading.excepthook)
    monkeypatch.setattr(logging_config, "_hooks_installed", False)
    yield
    shutdown_logging()
    root.setLevel(level)


def flush():
    for handler in logging.getLogger().handlers:
        handler.flush()


def test_setup_creates_log_file_and_writes_messages(tmp_path):
    path = setup_logging(tmp_path / "logs")
    logging.getLogger("demo").warning("merhaba şğüıöç")
    flush()
    assert path == tmp_path / "logs" / LOG_FILE_NAME
    text = path.read_text(encoding="utf-8")
    assert "WARNING" in text and "demo" in text and "merhaba şğüıöç" in text


def test_setup_is_idempotent(tmp_path):
    setup_logging(tmp_path)
    setup_logging(tmp_path)
    ours = [h for h in logging.getLogger().handlers if getattr(h, "_gitclean_handler", False)]
    assert len(ours) == 1
    logging.getLogger("x").error("tek satır")
    flush()
    assert (tmp_path / LOG_FILE_NAME).read_text(encoding="utf-8").count("tek satır") == 1


def test_switching_directory_replaces_handler(tmp_path):
    setup_logging(tmp_path / "a")
    setup_logging(tmp_path / "b")
    ours = [h for h in logging.getLogger().handlers if getattr(h, "_gitclean_handler", False)]
    assert len(ours) == 1 and Path(ours[0].baseFilename).parent.name == "b"


def test_level_comes_from_argument_then_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("GITCLEAN_LOG_LEVEL", "debug")
    setup_logging(tmp_path)
    assert logging.getLogger().level == logging.DEBUG
    setup_logging(tmp_path, level="error")
    assert logging.getLogger().level == logging.ERROR
    setup_logging(tmp_path, level="bozuk-seviye")
    assert logging.getLogger().level == logging.INFO          # geçersiz seviye INFO'ya düşer


def test_log_rotates_when_too_large(tmp_path, monkeypatch):
    monkeypatch.setattr(logging_config, "MAX_BYTES", 2000)
    setup_logging(tmp_path)
    for i in range(200):
        logging.getLogger("rot").warning("satır %d %s", i, "x" * 50)
    flush()
    assert (tmp_path / (LOG_FILE_NAME + ".1")).exists()


def test_uncaught_exception_in_thread_is_logged(tmp_path):
    setup_logging(tmp_path)
    previous_hook_calls = []
    # varsayılan kancayı sessizleştir: yalnızca log kaydını doğruluyoruz
    threading.excepthook = lambda args, _orig=threading.excepthook: previous_hook_calls.append(args)
    logging_config._hooks_installed = False
    logging_config._install_exception_hooks()

    thread = threading.Thread(target=lambda: 1 / 0, name="isci-1")
    thread.start()
    thread.join()
    flush()
    text = (tmp_path / LOG_FILE_NAME).read_text(encoding="utf-8")
    assert "Yakalanmayan istisna (iş parçacığı: isci-1)" in text and "ZeroDivisionError" in text


def test_uncaught_exception_in_process_is_written_to_file(tmp_path):
    """Gerçek bir alt süreç: yakalanmayan istisna konsolsuz olsa bile log dosyasında traceback bırakır."""
    script = (
        "import sys\n"
        f"sys.path.insert(0, {str(PROJECT_ROOT)!r})\n"
        "from pathlib import Path\n"
        "from src.utils.logging_config import setup_logging\n"
        f"setup_logging(Path({str(tmp_path)!r}))\n"
        "raise RuntimeError('bilerek patlatıldı')\n"
    )
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True,
                            encoding="utf-8", env=env, cwd=tmp_path)
    assert result.returncode != 0                                  # varsayılan davranış korunur
    assert "bilerek patlatıldı" in result.stderr
    text = (tmp_path / LOG_FILE_NAME).read_text(encoding="utf-8")
    assert "CRITICAL" in text and "RuntimeError: bilerek patlatıldı" in text and "Traceback" in text


def test_project_not_selected_error_is_a_value_error_with_turkish_message():
    error = ProjectNotSelectedError()
    assert isinstance(error, ValueError) and isinstance(error, GitCleanError)
    assert str(error) == "Önce bir proje seçin."


def test_project_service_raises_the_specific_error():
    from src.services.project_service import ProjectService
    service = ProjectService()
    with pytest.raises(ProjectNotSelectedError):
        service.analyze_project()
    with pytest.raises(ValueError):                                # eski yakalayıcılar çalışmaya devam eder
        service.create_backup()
