import pytest

from src.services import archive_profiles


@pytest.fixture(autouse=True)
def isolated_user_profiles(tmp_path_factory, monkeypatch):
    """Testler gerçek ~/.gitclean/profiles klasöründen etkilenmesin."""
    empty = tmp_path_factory.mktemp("kullanici_profilleri")
    monkeypatch.setattr(archive_profiles, "user_profiles_dir", lambda: empty)
