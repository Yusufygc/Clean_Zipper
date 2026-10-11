"""Derleme sonrası denetim (Akıllı Uygulama Denetimi engeli): engelli / çöken / çalışan exe ve kurulum dosyası durumları."""
import subprocess
from pathlib import Path

import pytest

import build_verify


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
