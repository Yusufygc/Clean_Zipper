"""Kur / Güncelle penceresi ve Ayarlar'daki kaldırma düğmesi."""
import sys

import pytest
from PySide6.QtCore import QCoreApplication, QMetaObject, QObject
from PySide6.QtQuick import QQuickItem  # noqa: F401  (QtQuick yüklenince kök pencere QQuickWindow olarak çözülür)
from PySide6.QtWidgets import QApplication

from src.qml_ui.viewmodels.install_viewmodel import InstallViewModel
from src.services import install_service as svc
from src.services.install_service import Locations
from src.version import __version__


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


class FakeRegistry:
    def __init__(self, values=None):
        self.values = values

    def read(self):
        return dict(self.values) if self.values is not None else None

    def write(self, values):
        self.values = dict(values)

    def delete(self):
        self.values = None


class Rig:
    """Sahte kayıt defteri, kısayol ve başlatıcıyla kurulmuş ViewModel."""

    def __init__(self, tmp_path, frozen=True):
        self.tmp = tmp_path
        self.exe = tmp_path / "Downloads" / "GitCleanArchiver-2.1.0.exe"
        self.exe.parent.mkdir()
        self.exe.write_bytes(b"MZ" + b"y" * 3000)
        self.locations = Locations(tmp_path / "Programs" / "GitClean Archiver", tmp_path / "Start", tmp_path / "Desktop")
        self.registry = FakeRegistry()
        self.launched, self.finished, self.links = [], [], []
        self.preferences = tmp_path / "install.json"
        self.frozen = frozen

    def vm(self):
        vm = InstallViewModel(exe=self.exe if self.frozen else None, locations=self.locations, registry=self.registry,
                              shortcut=self._shortcut, launcher=self.launched.append, preferences_file=self.preferences)
        vm.finished.connect(lambda: self.finished.append(True))
        return vm

    def _shortcut(self, link, target):
        link.parent.mkdir(parents=True, exist_ok=True)
        link.write_text("lnk", encoding="utf-8")
        self.links.append(link)

    def pretend_installed(self, version=__version__):
        svc.install(self.exe, self.locations.install_dir, version=version, locations=self.locations, registry=self.registry,
                    shortcut=self._shortcut)


@pytest.fixture
def rig(tmp_path, monkeypatch):
    monkeypatch.delenv(svc.PROMPT_OPT_OUT_ENV, raising=False)
    return Rig(tmp_path)


def test_no_prompt_when_not_packaged(qapp, tmp_path):
    vm = Rig(tmp_path, frozen=False).vm()
    assert vm.promptNeeded is False and vm.canUninstall is False
    prompts = []
    vm.promptRequested.connect(lambda: prompts.append(True))
    vm.requestPromptIfNeeded()
    assert prompts == []                                                               # `python main.py` geliştirme çalıştırması: öneri yok


def test_downloaded_exe_that_is_not_installed_offers_to_install(qapp, rig):
    vm = rig.vm()
    prompts = []
    vm.promptRequested.connect(lambda: prompts.append(True))
    vm.requestPromptIfNeeded()
    assert prompts == [True] and vm.mode == "install" and vm.installDir == str(rig.locations.install_dir)
    assert vm.currentVersion == __version__ and vm.canUninstall is False


def test_an_older_installed_version_offers_an_update_and_a_same_or_newer_one_does_not(qapp, rig):
    rig.pretend_installed("2.0.0")
    other = rig.exe.with_name("copy.exe")
    other.write_bytes(b"MZ")
    vm = rig.vm()
    assert vm.promptNeeded is True and vm.mode == "update" and vm.installedVersion == "2.0.0"
    rig.pretend_installed(__version__)
    assert rig.vm().promptNeeded is False
    rig.pretend_installed("9.9.9")
    assert rig.vm().promptNeeded is False


def test_the_installed_copy_never_prompts_and_can_be_uninstalled(qapp, rig):
    rig.pretend_installed()
    installed = rig.locations.install_dir / svc.EXE_NAME
    vm = InstallViewModel(exe=installed, locations=rig.locations, registry=rig.registry, shortcut=rig._shortcut,
                          launcher=rig.launched.append, preferences_file=rig.preferences)
    assert vm.runningFromInstall is True and vm.promptNeeded is False and vm.canUninstall is True


def test_never_ask_again_is_remembered(qapp, rig):
    vm = rig.vm()
    vm.decline(False)
    assert rig.vm().promptNeeded is True                                               # yalnızca "Kurmadan Çalıştır": bir sonraki açılışta yine sorar
    vm.decline(True)
    assert rig.vm().promptNeeded is False and not rig.launched


def test_install_copies_launches_the_installed_copy_and_asks_the_app_to_quit(qapp, rig):
    vm = rig.vm()
    vm.setDesktopShortcut(True)
    vm.install()
    installed = rig.locations.install_dir / svc.EXE_NAME
    assert installed.read_bytes() == rig.exe.read_bytes() and rig.launched == [installed] and rig.finished == [True]
    assert rig.locations.desktop / svc.SHORTCUT_NAME in rig.links and vm.errorText == ""
    assert rig.registry.values["DisplayVersion"] == __version__


def test_a_failed_install_shows_the_error_and_neither_launches_nor_quits(qapp, rig):
    vm = rig.vm()
    rig.locations.install_dir.mkdir(parents=True)
    (rig.locations.install_dir / svc.EXE_NAME).write_bytes(b"eski")
    with (rig.locations.install_dir / svc.EXE_NAME).open("rb"):                        # çalışan kurulu sürüm
        vm.install()
    assert "kapatıp yeniden deneyin" in vm.errorText and rig.launched == [] and rig.finished == []


def test_uninstall_clears_the_registration_and_asks_the_app_to_quit(qapp, rig):
    rig.pretend_installed()
    installed = rig.locations.install_dir / svc.EXE_NAME
    vm = InstallViewModel(exe=installed, locations=rig.locations, registry=rig.registry, shortcut=rig._shortcut,
                          launcher=rig.launched.append, preferences_file=rig.preferences)
    vm.finished.connect(lambda: rig.finished.append(True))
    vm.uninstall()
    assert rig.registry.values is None and rig.finished == [True]
    assert not (rig.locations.start_menu / svc.SHORTCUT_NAME).exists()


# ---- gerçek pencerede -----------------------------------------------------------------------------------------------------

def open_app(qapp, monkeypatch):
    from src.qml_ui import app as qml_app
    monkeypatch.setattr(qml_app, "setup_logging", lambda: None)
    _, engine = qml_app.create_qml_app()
    window = engine.rootObjects()[0]
    window.setWidth(1400)
    window.setHeight(900)
    for _ in range(30):
        QCoreApplication.processEvents()
    return engine, window, next(vm for vm in engine.viewmodels if isinstance(vm, InstallViewModel))


def pump(times=40):
    for _ in range(times):
        QCoreApplication.processEvents()


def find_item(window, name):
    stack = [window.contentItem()]
    while stack:
        item = stack.pop()
        if item.objectName() == name:
            return item
        stack.extend(item.childItems())
    return None


def rewire(vm, rig):
    vm._exe, vm._locations, vm._registry = rig.exe, rig.locations, rig.registry
    vm._shortcut, vm._launcher, vm._preferences_file = rig._shortcut, rig.launched.append, rig.preferences
    vm._state = svc.installed_state(rig.registry)
    vm.stateChanged.emit()


def test_install_dialog_opens_shows_the_target_and_the_buttons_work(qapp, monkeypatch, rig):
    engine, window, vm = open_app(qapp, monkeypatch)
    dialog = window.findChild(QObject, "installDialog")
    assert dialog.property("opened") is False                                          # geliştirme ortamı: açılışta pencere yok
    rewire(vm, rig)
    vm.finished.connect(lambda: rig.finished.append(True))
    vm.requestPromptIfNeeded()
    pump()
    assert dialog.property("opened") is True
    assert window.findChild(QObject, "installHeadline").property("text") == f"GitClean Archiver v{__version__} bu bilgisayara kurulsun mu?"
    assert window.findChild(QObject, "installDir").property("text") == str(rig.locations.install_dir)
    QMetaObject.invokeMethod(window.findChild(QObject, "installButton"), "clicked")
    pump()
    assert rig.launched == [rig.locations.install_dir / svc.EXE_NAME] and rig.finished == [True]


def test_run_portable_button_closes_the_dialog_and_remembers_never_ask(qapp, monkeypatch, rig):
    engine, window, vm = open_app(qapp, monkeypatch)
    rewire(vm, rig)
    vm.requestPromptIfNeeded()
    pump()
    dialog = window.findChild(QObject, "installDialog")
    assert dialog.property("opened") is True
    window.findChild(QObject, "neverAskCheck").setProperty("checked", True)
    QMetaObject.invokeMethod(window.findChild(QObject, "runPortableButton"), "clicked")
    pump()
    assert dialog.property("opened") is False and svc.prompt_enabled(rig.preferences) is False and not rig.launched


def test_update_mode_headline_names_both_versions(qapp, monkeypatch, rig):
    rig.pretend_installed("2.0.0")
    engine, window, vm = open_app(qapp, monkeypatch)
    rewire(vm, rig)
    vm.requestPromptIfNeeded()
    pump()
    assert window.findChild(QObject, "installHeadline").property("text") == f"v2.0.0 sürümünden v{__version__} sürümüne güncellensin mi?"


def test_settings_uninstall_button_needs_a_second_click_to_confirm(qapp, monkeypatch, rig):
    rig.pretend_installed()
    engine, window, vm = open_app(qapp, monkeypatch)
    installed = rig.locations.install_dir / svc.EXE_NAME
    rewire(vm, rig)
    vm._exe = installed
    vm.stateChanged.emit()
    window.setProperty("currentTab", 4)
    pump()
    button = find_item(window, "uninstallButton")
    assert button is not None and button.property("text") == "Uygulamayı Kaldır"
    QMetaObject.invokeMethod(button, "clicked")
    pump()
    assert button.property("text") == "Emin misiniz? Kaldır" and rig.registry.values is not None     # ilk tık yalnızca onay ister
    QMetaObject.invokeMethod(button, "clicked")
    pump()
    assert rig.registry.values is None
