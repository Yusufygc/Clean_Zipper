"""Derleme sonrası denetim (Akıllı Uygulama Denetimi engeli): engelli / çöken / çalışan exe ve kurulum dosyası durumları."""
import subprocess
from pathlib import Path

import pytest

import build_verify

REAL_SAVE, REAL_RESTORE = build_verify.save_registration, build_verify.restore_registration


def blocked_error():
    error = OSError(22, "Uygulama Denetimi ilkesi bu dosyayı engelledi")
    error.winerror = 4551
    return error


class FakeProcess:
    def __init__(self, alive=True):
        self._alive, self.pid, self.returncode = alive, 4242, None if alive else 1

    def poll(self):
        return None if self._alive else self.returncode


@pytest.fixture(autouse=True)
def fast(monkeypatch, tmp_path):
    monkeypatch.setattr(build_verify.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(build_verify.tempfile, "mkdtemp", lambda prefix="": str(tmp_path / "work"))      # gerçek TEMP'e çöp bırakma
    (tmp_path / "work").mkdir()
    monkeypatch.setattr(build_verify, "save_registration", lambda: (None, None))          # birim testleri gerçek kayda / kısayola dokunmaz
    monkeypatch.setattr(build_verify, "restore_registration", lambda saved: None)
    killed = []
    real_run = subprocess.run
    monkeypatch.setattr(build_verify.subprocess, "run",
                        lambda cmd, *a, **kw: killed.append(cmd) or subprocess.CompletedProcess(cmd, 0) if cmd[0] == "taskkill" else real_run(cmd, *a, **kw))
    return killed


def test_blocked_exe_is_reported_without_raising(monkeypatch, capsys):
    monkeypatch.setattr(build_verify.subprocess, "Popen", lambda *a, **kw: (_ for _ in ()).throw(blocked_error()))
    assert build_verify.launch_check(Path("C:/x/GitCleanArchiver.exe")) is False
    assert "Windows engelledi" in capsys.readouterr().out


def test_other_launch_errors_are_not_mistaken_for_the_block(monkeypatch):
    monkeypatch.setattr(build_verify.subprocess, "Popen", lambda *a, **kw: (_ for _ in ()).throw(FileNotFoundError("yok")))
    with pytest.raises(FileNotFoundError):
        build_verify.launch_check(Path("C:/x/yok.exe"))
    assert build_verify.is_blocked(blocked_error()) and not build_verify.is_blocked(OSError(5, "erişim"))


def test_a_running_exe_passes_and_its_process_tree_is_killed(monkeypatch, fast):
    seen = {}
    monkeypatch.setattr(build_verify.subprocess, "Popen", lambda cmd, **kw: seen.update(kw=kw) or FakeProcess(alive=True))
    assert build_verify.launch_check(Path("C:/x/GitCleanArchiver.exe")) is True
    assert fast == [["taskkill", "/PID", "4242", "/T", "/F"]]
    assert seen["kw"]["env"]["GITCLEAN_NO_UPDATE_CHECK"] == "1"                       # denetim ağa çıkmaz


def test_an_exe_that_exits_immediately_fails_the_check(monkeypatch, capsys):
    monkeypatch.setattr(build_verify.subprocess, "Popen", lambda *a, **kw: FakeProcess(alive=False))
    assert build_verify.launch_check(Path("C:/x/GitCleanArchiver.exe")) is False
    assert "hemen kapandı" in capsys.readouterr().out


def test_blocked_installer_fails_the_check(monkeypatch, capsys):
    def blocked(*a, **kw):
        raise blocked_error()
    monkeypatch.setattr(build_verify.subprocess, "run", blocked)
    assert build_verify.installer_check(Path("C:/x/Setup.exe")) is False
    assert "kurulum dosyasını engelledi" in capsys.readouterr().out


def test_installer_that_installs_nothing_fails_the_check(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(build_verify.subprocess, "run", lambda cmd, *a, **kw: subprocess.CompletedProcess(cmd, 0))
    assert build_verify.installer_check(tmp_path / "Setup.exe") is False               # çıkış 0 ama exe kurulmadı
    assert "Sessiz kurulum başarısız" in capsys.readouterr().out


def test_working_installer_is_installed_launched_and_uninstalled(monkeypatch, tmp_path):
    calls = []

    def fake_run(cmd, *a, **kw):
        calls.append(Path(cmd[0]).name)
        directory = next(Path(arg[5:]) for arg in cmd if arg.startswith("/DIR="))
        if cmd[0].endswith("Setup.exe"):
            directory.mkdir(parents=True)
            (directory / build_verify.EXE_NAME).write_bytes(b"MZ")
            (directory / "unins000.exe").write_bytes(b"MZ")
        return subprocess.CompletedProcess(cmd, 0)

    def fake_run_dispatch(cmd, *a, **kw):
        if cmd[0] == "taskkill":
            calls.append("taskkill")
            return subprocess.CompletedProcess(cmd, 0)
        if cmd[0].endswith("unins000.exe"):
            calls.append("unins000.exe")
            return subprocess.CompletedProcess(cmd, 0)
        return fake_run(cmd, *a, **kw)
    monkeypatch.setattr(build_verify.subprocess, "run", fake_run_dispatch)
    monkeypatch.setattr(build_verify.subprocess, "Popen", lambda *a, **kw: FakeProcess(alive=True))
    assert build_verify.installer_check(tmp_path / "Setup.exe") is True
    assert calls == ["Setup.exe", "taskkill", "unins000.exe"]                          # kur, aç, kapat, kaldır
    assert not (tmp_path / "work").exists()                                            # başarıda geçici klasör silinir


def test_build_installer_retries_after_a_blocked_attempt_and_stops_when_one_passes(monkeypatch, tmp_path):
    import build_installer
    results = iter([None, None, tmp_path / "Setup.exe"])
    attempts = []
    monkeypatch.setattr(build_installer, "find_iscc", lambda: Path("ISCC.exe"))
    monkeypatch.setattr(build_installer, "attempt", lambda iscc, skip, verify: attempts.append(verify) or next(results))
    monkeypatch.setattr(build_installer, "OUTPUT", tmp_path)
    (tmp_path / "Setup.exe").write_bytes(b"MZ")
    assert build_installer.build_installer() == tmp_path / "Setup.exe"
    assert attempts == [True, True, True] and (tmp_path / "Setup.exe.sha256").is_file()


def test_build_installer_gives_up_after_the_maximum_attempts(monkeypatch):
    import build_installer
    monkeypatch.setattr(build_installer, "find_iscc", lambda: Path("ISCC.exe"))
    monkeypatch.setattr(build_installer, "attempt", lambda iscc, skip, verify: None)
    with pytest.raises(SystemExit, match="engellendi"):
        build_installer.build_installer()


def test_skip_build_makes_a_single_attempt(monkeypatch):
    import build_installer
    calls = []
    monkeypatch.setattr(build_installer, "find_iscc", lambda: Path("ISCC.exe"))
    monkeypatch.setattr(build_installer, "attempt", lambda iscc, skip, verify: calls.append(skip))
    with pytest.raises(SystemExit):
        build_installer.build_installer(skip_build=True)
    assert calls == [True]


# ---- gerçek kurulumun kaydı ve kısayolu korunur ---------------------------------------------------------------------------------

@pytest.fixture
def isolated_registration(monkeypatch, tmp_path):
    """Gerçek kayıt yerine izole bir alt anahtar ve geçici bir kısayol dosyası."""
    import uuid
    import winreg
    subkey = rf"Software\GitCleanArchiverTest\{uuid.uuid4().hex}"
    monkeypatch.setattr(build_verify, "UNINSTALL_KEY", subkey)
    monkeypatch.setattr(build_verify, "SHORTCUT", tmp_path / "GitClean Archiver.lnk")
    yield subkey
    for path in (subkey, r"Software\GitCleanArchiverTest"):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)
        except OSError:
            pass


def write_key(subkey, values):
    import winreg
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, subkey, 0, winreg.KEY_SET_VALUE) as key:
        for name, (value, kind) in values.items():
            winreg.SetValueEx(key, name, 0, kind, value)


def read_key(subkey):
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subkey) as key:
            result, index = {}, 0
            while True:
                try:
                    name, value, kind = winreg.EnumValue(key, index)
                except OSError:
                    return result
                result[name] = (value, kind)
                index += 1
    except FileNotFoundError:
        return None


def test_the_real_registration_and_shortcut_survive_a_verification_install(isolated_registration):
    import winreg
    real = {"InstallLocation": ("C:/Users/k/AppData/Local/Programs/GitClean Archiver/", winreg.REG_SZ), "EstimatedSize": (172400, winreg.REG_DWORD),
            "UninstallString": ('"C:/Users/k/AppData/Local/Programs/GitClean Archiver/unins000.exe"', winreg.REG_SZ)}
    write_key(isolated_registration, real)
    build_verify.SHORTCUT.write_bytes(b"GERCEK-KISAYOL")
    saved = REAL_SAVE()
    write_key(isolated_registration, {"InstallLocation": ("C:/Temp/gcverify_x/app", winreg.REG_SZ), "ExtraValue": ("deneme", winreg.REG_SZ)})   # deneme kurulumu ezdi
    build_verify.SHORTCUT.write_bytes(b"DENEME-KISAYOL")
    REAL_RESTORE(saved)
    assert read_key(isolated_registration) == real                                    # değerler ve türleri birebir geri geldi, fazlalık silindi
    assert build_verify.SHORTCUT.read_bytes() == b"GERCEK-KISAYOL"


def test_when_nothing_was_installed_the_verification_leaves_no_registration_behind(isolated_registration):
    import winreg
    assert read_key(isolated_registration) is None and not build_verify.SHORTCUT.exists()
    saved = REAL_SAVE()
    write_key(isolated_registration, {"InstallLocation": ("C:/Temp/gcverify_x/app", winreg.REG_SZ)})
    build_verify.SHORTCUT.write_bytes(b"DENEME-KISAYOL")
    REAL_RESTORE(saved)
    assert read_key(isolated_registration) is None and not build_verify.SHORTCUT.exists()


def test_installer_check_restores_the_registration_even_when_the_check_blows_up(monkeypatch):
    events = []
    monkeypatch.setattr(build_verify, "save_registration", lambda: events.append("save") or ("kayit", "kisayol"))
    monkeypatch.setattr(build_verify, "restore_registration", lambda saved: events.append(("restore", saved)))
    monkeypatch.setattr(build_verify, "_installer_check", lambda installer, seconds: (_ for _ in ()).throw(RuntimeError("beklenmedik")))
    with pytest.raises(RuntimeError):
        build_verify.installer_check(Path("C:/x/Setup.exe"))
    assert events == ["save", ("restore", ("kayit", "kisayol"))]


def test_a_blocked_uninstaller_fails_the_check_and_the_temp_install_is_removed(monkeypatch, tmp_path, capsys):
    def fake_run(cmd, *a, **kw):
        if cmd[0] == "taskkill":
            return subprocess.CompletedProcess(cmd, 0)
        directory = next(Path(arg[5:]) for arg in cmd if arg.startswith("/DIR=")) if any(arg.startswith("/DIR=") for arg in cmd) else None
        if cmd[0].endswith("Setup.exe"):
            directory.mkdir(parents=True)
            (directory / build_verify.EXE_NAME).write_bytes(b"MZ")
            (directory / "unins000.exe").write_bytes(b"MZ")
            return subprocess.CompletedProcess(cmd, 0)
        raise blocked_error()                                                         # unins000.exe engellendi
    monkeypatch.setattr(build_verify.subprocess, "run", fake_run)
    monkeypatch.setattr(build_verify.subprocess, "Popen", lambda *a, **kw: FakeProcess(alive=True))
    assert build_verify.installer_check(tmp_path / "Setup.exe") is False
    assert "kaldırıcıyı engelledi" in capsys.readouterr().out
    assert not (tmp_path / "work").exists()


def test_the_app_id_used_for_the_registration_matches_the_installer_script():
    script = (Path(__file__).resolve().parents[2] / "packaging" / "GitCleanArchiver.iss").read_text(encoding="utf-8")
    app_id = script.split("AppId={{", 1)[1].split("}", 1)[0]
    assert build_verify.UNINSTALL_KEY.endswith("{" + app_id + "}_is1")
