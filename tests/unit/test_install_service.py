"""Kendi kendini kuran uygulama: kopyalama, kısayol, kaldırma kaydı, kaldırma ve komut satırı."""
import os
import uuid
from pathlib import Path

import pytest

from src.services import install_service as svc
from src.services.install_service import InstallError, Locations
from src.version import __version__


class FakeRegistry:
    def __init__(self):
        self.values = None

    def read(self):
        return dict(self.values) if self.values is not None else None

    def write(self, values):
        self.values = dict(values)

    def delete(self):
        self.values = None


@pytest.fixture
def env(tmp_path):
    source = tmp_path / "download" / "GitCleanArchiver-2.1.0.exe"
    source.parent.mkdir()
    source.write_bytes(b"MZ" + b"x" * 5000)
    links = []

    def fake_shortcut(link: Path, target: Path):
        link.parent.mkdir(parents=True, exist_ok=True)
        link.write_text(str(target), encoding="utf-8")
        links.append(link)
    locations = Locations(install_dir=tmp_path / "Programs" / "GitClean Archiver", start_menu=tmp_path / "StartMenu",
                          desktop=tmp_path / "Desktop")
    return source, locations, FakeRegistry(), fake_shortcut, links


def do_install(env, **kwargs):
    source, locations, registry, shortcut, _ = env
    return svc.install(source, kwargs.pop("target", locations.install_dir), locations=locations, registry=registry, shortcut=shortcut,
                       **kwargs)


# ---- kurulum ----------------------------------------------------------------------------------------------------------------

def test_install_copies_the_exe_creates_the_start_menu_shortcut_and_the_uninstall_entry(env):
    source, locations, registry, _, links = env
    installed = do_install(env)
    assert installed == locations.install_dir / svc.EXE_NAME and installed.read_bytes() == source.read_bytes()
    assert links == [locations.start_menu / svc.SHORTCUT_NAME]                       # masaüstü kısayolu istenmedi
    values = registry.values
    assert values["DisplayName"] == "GitClean Archiver" and values["DisplayVersion"] == __version__
    assert values["InstallLocation"] == str(locations.install_dir)
    assert values["UninstallString"] == f'"{installed}" --uninstall'
    assert values["QuietUninstallString"].endswith("--uninstall --silent")
    assert values["NoModify"] == 1 and values["EstimatedSize"] >= 1


def test_desktop_shortcut_only_when_requested(env):
    _, locations, _, _, links = env
    do_install(env, desktop_shortcut=True)
    assert locations.desktop / svc.SHORTCUT_NAME in links


def test_reinstall_replaces_the_old_exe_and_leaves_no_staging_files(env):
    _, locations, registry, _, _ = env
    do_install(env)
    new_source = env[0].with_name("GitCleanArchiver-2.2.0.exe")
    new_source.write_bytes(b"MZ-NEW")
    svc.install(new_source, locations.install_dir, version="2.2.0", locations=locations, registry=registry, shortcut=env[3])
    assert (locations.install_dir / svc.EXE_NAME).read_bytes() == b"MZ-NEW" and registry.values["DisplayVersion"] == "2.2.0"
    assert [p.name for p in locations.install_dir.iterdir()] == [svc.EXE_NAME]


def test_installing_over_a_running_copy_gives_a_readable_error_and_keeps_the_old_one(env):
    _, locations, _, _, _ = env
    installed = do_install(env)
    with installed.open("rb"):                                                         # Windows: açık dosya değiştirilemez (çalışan exe gibi)
        with pytest.raises(InstallError, match="kapatıp yeniden deneyin"):
            do_install(env)
    assert installed.read_bytes() == env[0].read_bytes()
    assert [p.name for p in locations.install_dir.iterdir()] == [svc.EXE_NAME]         # yarım dosya kalmadı


def test_running_from_the_install_folder_does_not_copy_onto_itself(env):
    _, locations, registry, shortcut, _ = env
    installed = do_install(env)
    svc.install(installed, locations.install_dir, locations=locations, registry=registry, shortcut=shortcut)
    assert installed.is_file() and registry.values["InstallLocation"] == str(locations.install_dir)


def test_install_never_touches_other_files_in_the_target_folder(env):
    _, locations, _, _, _ = env
    locations.install_dir.mkdir(parents=True)
    other = locations.install_dir / "notlarim.txt"
    other.write_text("benim", encoding="utf-8")
    do_install(env)
    assert other.read_text(encoding="utf-8") == "benim"


@pytest.mark.parametrize("bad", [Path("relative/dir"), Path(Path.home().anchor), Path.home()])
def test_dangerous_install_folders_are_rejected(env, bad):
    with pytest.raises(InstallError):
        do_install(env, target=bad)


def test_a_file_cannot_be_the_install_folder(env, tmp_path):
    file = tmp_path / "dosya.txt"
    file.write_text("x", encoding="utf-8")
    with pytest.raises(InstallError, match="klasör değil"):
        do_install(env, target=file)


# ---- durum ve konum -----------------------------------------------------------------------------------------------------------

def test_installed_state_requires_the_registered_exe_to_exist(env):
    _, locations, registry, _, _ = env
    assert svc.installed_state(registry) == svc.InstallState(False)
    do_install(env)
    state = svc.installed_state(registry)
    assert state.installed and state.version == __version__ and state.location == locations.install_dir
    (locations.install_dir / svc.EXE_NAME).unlink()
    assert svc.installed_state(registry).installed is False                           # dosyası silinmiş kayıt: kurulu sayılmaz


def test_is_inside_ignores_case_and_rejects_other_folders(tmp_path):
    folder = tmp_path / "Programs"
    folder.mkdir()
    exe = folder / "a.exe"
    exe.write_bytes(b"x")
    assert svc.is_inside(exe, folder) and svc.is_inside(Path(str(exe).upper()), Path(str(folder).lower()))
    assert not svc.is_inside(tmp_path / "a.exe", folder) and not svc.is_inside(exe, None)
    assert not svc.is_inside(folder / "alt" / "a.exe", folder)                        # alt klasör "içinde" sayılmaz


# ---- kaldırma -----------------------------------------------------------------------------------------------------------------

def test_uninstall_removes_exe_shortcuts_and_registry_but_keeps_foreign_files(env):
    _, locations, registry, _, _ = env
    installed = do_install(env, desktop_shortcut=True)
    foreign = locations.install_dir / "baska.txt"
    foreign.write_text("kalsın", encoding="utf-8")
    assert svc.uninstall(locations=locations, registry=registry, schedule_delete=lambda exe: pytest.fail("çalışmıyordu")) is True
    assert not installed.exists() and registry.values is None
    assert not (locations.start_menu / svc.SHORTCUT_NAME).exists() and not (locations.desktop / svc.SHORTCUT_NAME).exists()
    assert foreign.read_text(encoding="utf-8") == "kalsın" and locations.install_dir.is_dir()      # klasör boş değil: silinmez


def test_uninstall_removes_the_empty_folder_and_is_safe_when_nothing_is_installed(env):
    _, locations, registry, _, _ = env
    do_install(env)
    svc.uninstall(locations=locations, registry=registry)
    assert not locations.install_dir.exists()
    assert svc.uninstall(locations=locations, registry=registry) is False              # ikinci kez: zararsız


def test_uninstalling_the_running_exe_schedules_its_deletion(env):
    _, locations, registry, _, _ = env
    installed = do_install(env)
    scheduled = []
    with installed.open("rb"):                                                         # çalışan exe silinemez
        assert svc.uninstall(locations=locations, registry=registry, schedule_delete=scheduled.append) is True
    assert scheduled == [installed] and registry.values is None                       # kayıt ve kısayollar yine de kalktı


def test_user_data_directory_is_never_touched(env, tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path / "home"))
    data = tmp_path / "home" / ".gitclean"
    data.mkdir(parents=True)
    (data / "settings.json").write_text("{}", encoding="utf-8")
    _, locations, registry, _, _ = env
    do_install(env)
    svc.uninstall(locations=locations, registry=registry)
    assert (data / "settings.json").is_file()


# ---- tercih -------------------------------------------------------------------------------------------------------------------

def test_install_prompt_preference_and_environment_opt_out(tmp_path, monkeypatch):
    monkeypatch.delenv(svc.PROMPT_OPT_OUT_ENV, raising=False)
    path = tmp_path / "install.json"
    assert svc.prompt_enabled(path) is True
    svc.disable_prompt(path)
    assert svc.prompt_enabled(path) is False
    path.write_text("{bozuk", encoding="utf-8")
    assert svc.prompt_enabled(path) is True                                            # bozuk dosya: varsayılan
    monkeypatch.setenv(svc.PROMPT_OPT_OUT_ENV, "1")
    assert svc.prompt_enabled(tmp_path / "yok.json") is False


# ---- komut satırı --------------------------------------------------------------------------------------------------------------

def test_cli_install_needs_a_packaged_exe_and_passes_the_options(env, monkeypatch):
    source, locations, _, _, _ = env
    monkeypatch.setattr(svc, "running_exe", lambda: None)
    assert svc.run_cli(["--install", "--silent"]) == 2                                 # geliştirme ortamında kurulum yapılmaz
    calls = []
    monkeypatch.setattr(svc, "running_exe", lambda: source)
    monkeypatch.setattr(svc, "install", lambda src, target, **kw: calls.append((src, target, kw)) or target / svc.EXE_NAME)
    assert svc.run_cli(["--install", "--silent", "--dir", str(locations.install_dir), "--desktop-shortcut"]) == 0
    assert calls == [(source, locations.install_dir, {"desktop_shortcut": True})]
    monkeypatch.setattr(svc, "install", lambda *a, **kw: (_ for _ in ()).throw(InstallError("hata")))
    assert svc.run_cli(["--install"]) == 1


def test_cli_uninstall_and_normal_start(monkeypatch):
    calls = []
    monkeypatch.setattr(svc, "uninstall", lambda **kw: calls.append(True) or True)
    assert svc.run_cli(["--uninstall", "--silent"]) == 0 and calls == [True]
    assert svc.run_cli([]) is None and svc.run_cli(["C:/proje"]) is None               # bayrak yok: uygulama normal açılır


# ---- gerçek Windows: kısayol ve kayıt defteri -------------------------------------------------------------------------------------------

def test_real_shortcut_is_created_even_when_the_path_contains_shell_metacharacters(tmp_path):
    target = tmp_path / "x $(Get-Date) 'y' & z" / "GitCleanArchiver.exe"
    target.parent.mkdir()
    target.write_bytes(b"MZ")
    link = tmp_path / "Başlat Menüsü" / svc.SHORTCUT_NAME
    svc.make_shortcut(link, target)
    assert link.is_file() and link.stat().st_size > 0
    assert str(target).encode("utf-16-le") in link.read_bytes() or target.name.encode() in link.read_bytes()


def test_real_registry_round_trip_in_an_isolated_key():
    subkey = rf"Software\GitCleanArchiverTest\{uuid.uuid4().hex}"
    registry = svc.UninstallRegistry(subkey)
    try:
        assert registry.read() is None
        registry.write({"DisplayName": "Test", "NoModify": 1, "InstallLocation": r"C:\x"})
        assert registry.read() == {"DisplayName": "Test", "NoModify": 1, "InstallLocation": r"C:\x"}
    finally:
        registry.delete()
        import winreg
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, r"Software\GitCleanArchiverTest")
        except OSError:
            pass
    assert registry.read() is None and os.name == "nt"


def test_real_deferred_delete_removes_the_exe_and_the_empty_folder_after_the_process_exits(tmp_path):
    """Çalışan exe kendini silemez; gecikmeli komut yolu boşluklu ve özel karakterli yolla da çalışmalı (cmd tırnak kuralları)."""
    import time
    folder = tmp_path / "Programs & Files" / "GitClean Archiver"
    folder.mkdir(parents=True)
    exe = folder / svc.EXE_NAME
    exe.write_bytes(b"MZ")
    svc._schedule_delete(exe)
    deadline = time.time() + 15
    while time.time() < deadline and folder.exists():
        time.sleep(0.25)
    assert not exe.exists() and not folder.exists()
