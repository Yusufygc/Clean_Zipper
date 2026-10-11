"""Güncelleme ViewModel'i ve "Yeni sürüm var" penceresi."""
import sys
import time
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QMetaObject, QObject
from PySide6.QtQuick import QQuickItem  # noqa: F401  (QtQuick yüklenince kök pencere QQuickWindow olarak çözülür)
from PySide6.QtWidgets import QApplication

from src.qml_ui.viewmodels import update_viewmodel as module
from src.qml_ui.viewmodels.update_viewmodel import UpdateViewModel
from src.services import update_service as svc
from src.services.update_service import UpdateCheckError, UpdateInfo
from src.version import __version__


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def info(version="99.0.0"):
    base = "https://github.com/Yusufygc/Clean_Zipper"
    return UpdateInfo(version=version, tag="v" + version, page_url=f"{base}/releases/tag/v{version}",
                      download_url=f"{base}/releases/download/v{version}/GitCleanArchiver-Setup-{version}.exe",
                      asset_name=f"GitCleanArchiver-Setup-{version}.exe", size=50 * 1024 * 1024, notes="Yenilikler:\n- gruplu liste",
                      published="2026-10-11")


def pump_until(predicate, timeout=10):
    end = time.time() + timeout
    while time.time() < end:
        QCoreApplication.processEvents()
        if predicate():
            return True
        time.sleep(0.01)
    return False


def make_vm(tmp_path, result, calls=None):
    def check():
        if calls is not None:
            calls.append(1)
        if isinstance(result, Exception):
            raise result
        return result
    return UpdateViewModel(check=check, preferences_file=tmp_path / "updates.json")


def run_check(vm, manual):
    popups = []
    vm.popupRequested.connect(lambda: popups.append(True))
    (vm.checkNow if manual else vm.startupCheck)()
    assert pump_until(lambda: not vm.checking)
    QCoreApplication.processEvents()
    return popups


def test_startup_check_opens_the_popup_when_a_newer_version_exists(qapp, tmp_path):
    vm = make_vm(tmp_path, info())
    assert run_check(vm, manual=False) == [True]
    assert vm.updateAvailable and vm.latestVersion == "99.0.0" and "gruplu liste" in vm.releaseNotes
    assert vm.installerLabel == "GitCleanArchiver-Setup-99.0.0.exe, 50 MB" and vm.publishedDate == "2026-10-11"


def test_startup_check_is_silent_when_up_to_date_or_when_the_network_fails(qapp, tmp_path):
    assert run_check(make_vm(tmp_path, None), manual=False) == []
    vm = make_vm(tmp_path, UpdateCheckError("GitHub'a ulaşılamadı."))
    assert run_check(vm, manual=False) == [] and vm.statusText == ""         # açılışta hata kullanıcıya gösterilmez


def test_manual_check_reports_every_outcome_in_the_status_line(qapp, tmp_path):
    vm = make_vm(tmp_path, None)
    run_check(vm, manual=True)
    assert vm.statusText == f"Güncelsiniz: v{__version__} en son sürüm." and not vm.updateAvailable
    vm = make_vm(tmp_path, UpdateCheckError("GitHub'a ulaşılamadı."))
    run_check(vm, manual=True)
    assert vm.statusText == "GitHub'a ulaşılamadı."
    vm = make_vm(tmp_path, RuntimeError("beklenmedik"))
    run_check(vm, manual=True)
    assert vm.statusText == "Güncelleme denetimi yapılamadı."                  # beklenmeyen hata da arayüzü düşürmez


def test_a_skipped_version_stays_quiet_at_startup_but_a_manual_check_still_shows_it(qapp, tmp_path):
    vm = make_vm(tmp_path, info("99.0.0"))
    run_check(vm, manual=False)
    vm.skipVersion()
    assert svc.load_preferences(tmp_path / "updates.json").skipped_version == "99.0.0"
    again = make_vm(tmp_path, info("99.0.0"))
    assert run_check(again, manual=False) == []                                 # aynı sürüm: açılışta sessiz
    assert run_check(again, manual=True) == [True]                              # elle denetim: yine gösterilir
    newer = make_vm(tmp_path, info("99.1.0"))
    assert run_check(newer, manual=False) == [True]                             # daha yeni sürüm: yeniden sorulur


def test_disabled_check_never_touches_the_network_at_startup(qapp, tmp_path, monkeypatch):
    calls = []
    vm = make_vm(tmp_path, info(), calls)
    vm.setCheckEnabled(False)
    assert vm.checkEnabled is False and svc.load_preferences(tmp_path / "updates.json").check_enabled is False
    vm.startupCheck()
    QCoreApplication.processEvents()
    assert calls == [] and not vm.checking
    vm.setCheckEnabled(True)
    monkeypatch.setenv(svc.OPT_OUT_ENV, "1")                                    # ortam değişkeni de kapatır
    vm.startupCheck()
    assert calls == []
    run_check(vm, manual=True)                                                  # elle denetim her zaman çalışır
    assert calls == [1]


def test_a_second_check_while_one_runs_is_ignored(qapp, tmp_path):
    calls = []
    vm = make_vm(tmp_path, None, calls)
    vm.checkNow()
    vm.checkNow()
    assert pump_until(lambda: not vm.checking)
    assert calls == [1]


def make_updating_vm(tmp_path, download, launcher):
    return UpdateViewModel(check=lambda: info(), preferences_file=tmp_path / "updates.json", download=download, launcher=launcher)


def test_update_downloads_verifies_launches_the_installer_and_asks_the_app_to_quit(qapp, tmp_path):
    launched, quits, states = [], [], []

    def download(update_info, progress):
        for percent in (10, 60, 100):
            progress(percent)
        return tmp_path / "GitCleanArchiver-Setup-99.0.0.exe"
    vm = make_updating_vm(tmp_path, download, launched.append)
    vm.quitRequested.connect(lambda: quits.append(True))
    vm.stateChanged.connect(lambda: states.append(vm.downloadProgress))
    run_check(vm, manual=True)
    assert vm.canInstall is True and vm.isDownloading is False
    vm.startUpdate()
    assert vm.isDownloading is True
    assert pump_until(lambda: quits)
    assert launched == [tmp_path / "GitCleanArchiver-Setup-99.0.0.exe"] and {10, 60, 100} <= set(states)


def test_a_failed_download_shows_the_error_and_neither_launches_nor_quits(qapp, tmp_path):
    launched, quits = [], []

    def download(update_info, progress):
        raise UpdateCheckError("İndirilen dosya doğrulanamadı; özet uyuşmuyor.")
    vm = make_updating_vm(tmp_path, download, launched.append)
    vm.quitRequested.connect(lambda: quits.append(True))
    run_check(vm, manual=True)
    vm.startUpdate()
    assert pump_until(lambda: vm.errorMessage != "")
    assert vm.errorMessage == "İndirilen dosya doğrulanamadı; özet uyuşmuyor." and vm.isDownloading is False
    assert launched == [] and quits == []
    vm.startUpdate()                                                                   # yeniden denenebilir
    assert vm.isDownloading is True and vm.errorMessage == ""
    assert pump_until(lambda: vm.errorMessage != "")


def test_a_launcher_failure_is_reported_and_the_app_stays_open(qapp, tmp_path):
    quits = []

    def launcher(path):
        raise UpdateCheckError("Kurulum dosyası bulunamadı.")
    vm = make_updating_vm(tmp_path, lambda i, p: tmp_path / "GitCleanArchiver-Setup-99.0.0.exe", launcher)
    vm.quitRequested.connect(lambda: quits.append(True))
    run_check(vm, manual=True)
    vm.startUpdate()
    assert pump_until(lambda: vm.errorMessage != "")
    assert vm.errorMessage == "Kurulum dosyası bulunamadı." and quits == []


def test_update_without_an_installer_asset_opens_the_release_page_and_never_downloads(qapp, tmp_path, monkeypatch):
    opened = []
    monkeypatch.setattr(module.QDesktopServices, "openUrl", staticmethod(lambda url: opened.append(url.toString())))
    no_asset = info()
    object.__setattr__(no_asset, "download_url", "")
    vm = UpdateViewModel(check=lambda: no_asset, preferences_file=tmp_path / "updates.json",
                         download=lambda i, p: pytest.fail("indirilmemeli"), launcher=lambda p: pytest.fail("başlatılmamalı"))
    vm.startUpdate()
    assert opened == []                                                                # bilgi yokken hiçbir şey açılmaz
    run_check(vm, manual=True)
    vm.startUpdate()
    assert opened[-1].endswith("/releases/tag/v99.0.0") and vm.canInstall is False and vm.isDownloading is False


def test_a_second_start_while_downloading_is_ignored(qapp, tmp_path):
    import threading
    release_download, started = threading.Event(), []

    def download(update_info, progress):
        started.append(1)
        release_download.wait(10)
        return tmp_path / "GitCleanArchiver-Setup-99.0.0.exe"
    vm = make_updating_vm(tmp_path, download, lambda path: None)
    run_check(vm, manual=True)
    vm.startUpdate()
    vm.startUpdate()
    pump_until(lambda: started, timeout=3)
    release_download.set()
    assert pump_until(lambda: vm._worker.isFinished())
    assert started == [1]                                                              # ikinci tık ikinci indirme başlatmadı


# ---- gerçek pencerede -----------------------------------------------------------------------------------------------------

def open_app(qapp, monkeypatch):
    from src.qml_ui import app as qml_app

    def no_network(*args, **kwargs):
        raise AssertionError("Uygulama kurulurken ağ isteği yapılmamalı")
    monkeypatch.setattr(svc.urllib.request, "urlopen", no_network)
    monkeypatch.setattr(qml_app, "setup_logging", lambda: None)
    _, engine = qml_app.create_qml_app()
    window = engine.rootObjects()[0]
    window.setWidth(1400)
    window.setHeight(900)
    for _ in range(30):
        QCoreApplication.processEvents()
    return engine, window, next(vm for vm in engine.viewmodels if isinstance(vm, UpdateViewModel))


def test_creating_the_app_makes_no_network_request(qapp, monkeypatch):
    open_app(qapp, monkeypatch)


def test_popup_shows_the_new_version_and_the_buttons_act_on_the_view_model(qapp, monkeypatch, tmp_path):
    engine, window, vm = open_app(qapp, monkeypatch)
    vm._preferences_file = tmp_path / "updates.json"
    vm._info = info()
    vm.stateChanged.emit()
    vm.popupRequested.emit()
    for _ in range(40):
        QCoreApplication.processEvents()
    dialog = window.findChild(QObject, "updateDialog")
    assert dialog.property("opened") is True
    assert window.findChild(QObject, "updateHeadline").property("text") == "GitClean Archiver v99.0.0 yayınlandı"
    dialog_source = (Path(__file__).resolve().parents[2] / "src/qml_ui/qml/components/UpdateDialog.qml").read_text(encoding="utf-8")
    assert "textFormat: Text.PlainText" in dialog_source                          # sürüm notunda biçim / bağlantı çalışmaz
    assert window.findChild(QObject, "downloadButton").property("text") == "Güncelle"
    QMetaObject.invokeMethod(window.findChild(QObject, "skipVersionButton"), "clicked")
    for _ in range(40):
        QCoreApplication.processEvents()
    assert dialog.property("opened") is False
    assert svc.load_preferences(tmp_path / "updates.json").skipped_version == "99.0.0"


def test_later_button_closes_the_popup_without_saving_anything(qapp, monkeypatch, tmp_path):
    engine, window, vm = open_app(qapp, monkeypatch)
    vm._preferences_file = tmp_path / "updates.json"
    vm._info = info()
    vm.popupRequested.emit()
    for _ in range(40):
        QCoreApplication.processEvents()
    dialog = window.findChild(QObject, "updateDialog")
    assert dialog.property("opened") is True
    QMetaObject.invokeMethod(window.findChild(QObject, "laterButton"), "clicked")
    for _ in range(40):
        QCoreApplication.processEvents()
    assert dialog.property("opened") is False and not (tmp_path / "updates.json").exists()


def test_settings_page_has_a_manual_check_button_and_shows_the_status(qapp, monkeypatch):
    engine, window, vm = open_app(qapp, monkeypatch)
    window.setProperty("currentTab", 4)
    vm._check = lambda: None
    for _ in range(30):
        QCoreApplication.processEvents()

    def find(name):
        stack = [window.contentItem()]
        while stack:
            item = stack.pop()
            if item.objectName() == name:
                return item
            stack.extend(item.childItems())
    assert find("updateStatus").property("text") == f"Kurulu sürüm: v{__version__}"
    QMetaObject.invokeMethod(find("checkUpdateButton"), "clicked")
    assert pump_until(lambda: not vm.checking)
    for _ in range(20):
        QCoreApplication.processEvents()
    assert find("updateStatus").property("text") == f"Güncelsiniz: v{__version__} en son sürüm."


def test_update_button_starts_the_download_and_the_dialog_cannot_be_dismissed_meanwhile(qapp, monkeypatch, tmp_path):
    import threading
    engine, window, vm = open_app(qapp, monkeypatch)
    hold, launched = threading.Event(), []
    vm._preferences_file = tmp_path / "updates.json"
    vm._info = info()
    vm._download = lambda update_info, progress: (progress(40), hold.wait(10), tmp_path / "GitCleanArchiver-Setup-99.0.0.exe")[2]
    vm._launcher = launched.append
    vm.stateChanged.emit()
    vm.popupRequested.emit()
    pump_until(lambda: window.findChild(QObject, "updateDialog").property("opened") is True, timeout=5)
    QMetaObject.invokeMethod(window.findChild(QObject, "downloadButton"), "clicked")
    assert pump_until(lambda: vm.downloadProgress == 40)
    assert window.findChild(QObject, "downloadButton").property("text") == "İndiriliyor… %40"
    assert window.findChild(QObject, "laterButton").property("enabled") is False and window.findChild(QObject, "downloadProgress").property("visible") is True
    hold.set()
    assert pump_until(lambda: launched)
