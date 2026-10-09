import os

import pytest

# QT_QPA_PLATFORM=offscreen ile yazı tipi bulunamazsa metin genişlikleri gerçekçi olmaz (yerleşim testleri bozulur)
if os.name == "nt" and os.path.isdir("C:/Windows/Fonts"):
    os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")

from src.services import archive_profiles


@pytest.fixture(autouse=True)
def isolated_user_profiles(tmp_path_factory, monkeypatch):
    """Testler gerçek ~/.gitclean/profiles klasöründen etkilenmesin."""
    empty = tmp_path_factory.mktemp("kullanici_profilleri")
    monkeypatch.setattr(archive_profiles, "user_profiles_dir", lambda: empty)


@pytest.fixture(autouse=True)
def isolated_app_settings(tmp_path_factory, monkeypatch):
    """Testler gerçek ~/.gitclean/settings.json dosyasını okumasın / yazmasın."""
    from src.services import app_settings
    folder = tmp_path_factory.mktemp("kullanici_ayarlari")
    monkeypatch.setattr(app_settings, "settings_path", lambda: folder / "settings.json")
    monkeypatch.setattr(app_settings, "default_agent_dir", lambda project: folder / "agent-tasks" / (project.name if project else "proje"))
