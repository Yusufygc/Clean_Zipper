"""QA denetiminde (QA_RAPORU.md) bulunan hataların gerileme testleri: her test, düzeltmeden önce kırmızıydı."""
import re
import sys
import time
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QUrl, Qt
from PySide6.QtGui import QAccessible
from PySide6.QtQuick import QQuickItem  # noqa: F401  (QtQuick yüklenince kök pencere QQuickWindow olarak çözülür)
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from src.qml_ui.viewmodels.findings_viewmodel import FindingsListModel, fold_turkish
from src.services.archive_service import ArchiveService
from src.services.cleanup_service import CleanupService
from src.utils.gitignore_parser import GitignoreParser

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def write(path: Path, text: str = "x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def pump_until(predicate, timeout=40):
    end = time.time() + timeout
    while time.time() < end:
        QCoreApplication.processEvents()
        if predicate():
            return True
        time.sleep(0.02)
    return False


def open_app(monkeypatch, project: Path):
    from src.qml_ui import app as qml_app
    monkeypatch.setattr(qml_app, "setup_logging", lambda: None)
    _, engine = qml_app.create_qml_app()
    window = engine.rootObjects()[0]
    window.setWidth(1400)
    window.setHeight(860)
    vm = {name: engine.rootContext().contextProperty(name) for name in
          ("appVM", "scanVM", "findingsVM", "archiveVM", "cleanupVM", "settingsVM")}
    vm["appVM"].setProjectPath(str(project))
    idle = lambda: not (vm["scanVM"].isScanning or vm["findingsVM"].isDiagnosing)
    assert pump_until(lambda: vm["scanVM"].totalFiles > 0 and idle())
    return engine, window, vm, idle


# ---- QA-03: Türkçe duyarlı arama -------------------------------------------------------------

@pytest.mark.parametrize("query", ["şifre", "Şifre", "ŞİFRE", "ŞIFRE", "sifre", "SIFRE"])
def test_turkish_search_ignores_case_and_accents(query):
    model = FindingsListModel()
    model.set_items([{"title": "Açık Şifre / Anahtar Sızıntısı", "description": "", "fileName": "a.py", "rule": "x",
                      "severity": "HIGH", "category": "security"}])
    model.set_search_query(query)
    assert model.rowCount() == 1, query


@pytest.mark.parametrize("query", ["AÇIK", "açık", "ACIK", "ANAHTAR", "SIZINTI"])
def test_turkish_capital_letters_find_lowercase_titles(query):
    assert fold_turkish(query) in fold_turkish("Açık Şifre / Anahtar Sızıntısı")


def test_search_still_rejects_unrelated_text():
    model = FindingsListModel()
    model.set_items([{"title": "Çift dosyalar", "description": "", "fileName": "a.py", "rule": "x",
                      "severity": "LOW", "category": "duplicate"}])
    model.set_search_query("zzz")
    assert model.rowCount() == 0


# ---- QA-02 / QA-10: analiz bayat kalmaz ------------------------------------------------------

def test_dashboard_refreshes_itself_after_a_real_cleanup(qapp, monkeypatch, tmp_path):
    project = tmp_path / "p"
    write(project / "app.py", "x = 1\n")
    write(project / "a.tmp")
    write(project / "b.tmp")
    _, _, vm, idle = open_app(monkeypatch, project)
    before = vm["scanVM"].totalFiles
    vm["appVM"].service.cleanup_service = CleanupService(trash_func=lambda path: Path(path).unlink())
    vm["cleanupVM"].startCleanup()
    assert pump_until(lambda: not vm["cleanupVM"].isProcessing)
    assert pump_until(lambda: vm["scanVM"].totalFiles == before - 2 and idle()), (before, vm["scanVM"].totalFiles)


def test_dashboard_refreshes_when_a_zip_is_written_inside_the_project(qapp, monkeypatch, tmp_path):
    project = tmp_path / "p"
    write(project / "app.py", "x = 1\n")
    _, _, vm, idle = open_app(monkeypatch, project)
    before = vm["scanVM"].totalFiles
    vm["archiveVM"].startZipArchive(QUrl.fromLocalFile(str(project / "cikti.zip")).toString())
    assert pump_until(lambda: not vm["archiveVM"].isProcessing)
    assert pump_until(lambda: vm["scanVM"].totalFiles == before + 1 and idle()), (before, vm["scanVM"].totalFiles)


def test_zip_outside_the_project_does_not_trigger_a_rescan(qapp, monkeypatch, tmp_path):
    project = tmp_path / "p"
    write(project / "app.py", "x = 1\n")
    _, _, vm, idle = open_app(monkeypatch, project)
    started = []
    vm["archiveVM"].projectModified.connect(lambda: started.append(1))
    vm["archiveVM"].startZipArchive(QUrl.fromLocalFile(str(tmp_path / "disarida.zip")).toString())
    assert pump_until(lambda: not vm["archiveVM"].isProcessing)
    QCoreApplication.processEvents()
    assert started == []


def test_applying_settings_re_runs_the_analysis(qapp, monkeypatch, tmp_path):
    project = tmp_path / "p"
    write(project / "app.py", "x = 1\n")
    write(project / "run.log")
    write(project / ".gitignore", "*.log\n")
    _, _, vm, idle = open_app(monkeypatch, project)
    messages = []
    vm["settingsVM"].settingsApplied.connect(messages.append)
    files = vm["scanVM"].totalFiles
    vm["settingsVM"].setRespectGitignore(False)
    vm["settingsVM"].applySettings()
    assert "yenileniyor" in messages[-1]
    assert pump_until(lambda: vm["scanVM"].totalFiles == files + 1 and idle()), (files, vm["scanVM"].totalFiles)


# ---- QA-09: puan yuvarlanır -------------------------------------------------------------------

def test_dashboard_score_is_rounded_not_truncated(qapp):
    from src.qml_ui.viewmodels.scan_viewmodel import ScanViewModel
    from src.services.project_service import ProjectService
    vm = ScanViewModel(ProjectService())
    vm._on_finished({"health_score": 80.7, "health_status": "B", "category_scores": {}})
    assert vm.healthScore == 81


# ---- QA-08: paylaşılacak arşivdeki hassas dosyalar --------------------------------------------

def test_archive_and_copy_report_the_sensitive_files_they_contain(tmp_path):
    project = tmp_path / "p"
    write(project / "app.py")
    write(project / ".env", "TOKEN=1")
    write(project / ".env.example", "TOKEN=")
    write(project / "keys" / "id_rsa", "x")
    service = ArchiveService(GitignoreParser(str(project)))
    zip_result = service.create_zip(project, tmp_path / "o.zip")
    assert zip_result["sensitive_files"] == [".env", "keys/id_rsa"]                # .env.example hassas sayılmaz
    copy_result = service.copy_project(project, tmp_path / "kopya")
    assert copy_result["sensitive_files"] == [".env", "keys/id_rsa"]
    customer = service.create_zip(project, tmp_path / "m.zip", profile_name="Müşteri Teslimi (Temiz)")
    assert ".env" not in customer["sensitive_files"]


def test_archive_view_model_exposes_sensitive_files(qapp, tmp_path):
    from src.qml_ui.viewmodels.archive_viewmodel import ArchiveViewModel
    from src.services.project_service import ProjectService
    vm = ArchiveViewModel(ProjectService())
    vm._on_finished({"success": True, "mode": "zip", "output_path": "x.zip", "sensitive_files": [".env"]})
    assert vm.lastResult["sensitiveCount"] == 1 and vm.lastResult["sensitiveFiles"] == [".env"]


# ---- QA-04: klavye ve erişilebilirlik ---------------------------------------------------------

def test_tabs_and_buttons_work_from_the_keyboard(qapp, monkeypatch, tmp_path):
    from src.qml_ui import app as qml_app
    QAccessible.setActive(True)
    monkeypatch.setattr(qml_app, "setup_logging", lambda: None)
    _, engine = qml_app.create_qml_app()
    window = engine.rootObjects()[0]
    window.setWidth(1400)
    window.setHeight(860)
    for _ in range(30):
        QCoreApplication.processEvents()

    def items():
        stack = [window.contentItem()]
        while stack:
            item = stack.pop()
            yield item
            stack.extend(item.childItems())

    focusable = [i for i in items() if i.isVisible() and i.property("activeFocusOnTab") is True]
    assert len(focusable) >= 6                                         # 5 sekme + proje düğmesi + tema düğmesi
    # Ekran okuyucunun gördüğü gerçek erişilebilirlik ağacı (QML ekli özellikleri property() ile okunamaz)
    unnamed = []
    for item in focusable:
        iface = QAccessible.queryAccessibleInterface(item)
        assert iface is not None
        if not iface.text(QAccessible.Text.Name):
            unnamed.append(item.metaObject().className())
    assert unnamed == []
    assert window.property("currentTab") == 0
    for _ in range(2):                                                 # Tab, Tab: ikinci sekmeye odaklan
        QTest.keyClick(window, Qt.Key.Key_Tab)
        QCoreApplication.processEvents()
    focused = window.activeFocusItem()
    assert focused is not None and QAccessible.queryAccessibleInterface(focused).text(QAccessible.Text.Name)
    QTest.keyClick(window, Qt.Key.Key_Return)
    QCoreApplication.processEvents()
    assert window.property("currentTab") == 1                          # Enter sekmeyi açtı
    QTest.keyClick(window, Qt.Key.Key_Tab)                             # sonraki sekmeye geç, Boşluk ile aç
    QTest.keyClick(window, Qt.Key.Key_Space)
    QCoreApplication.processEvents()
    assert window.property("currentTab") == 2


def test_buttons_do_not_redeclare_the_base_enabled_property():
    for name in ("CustomButton", "IconButton"):
        text = (ROOT / "src/qml_ui/qml/components" / f"{name}.qml").read_text(encoding="utf-8")
        assert "property bool enabled" not in text, name               # temel sınıfı ezip Qt uyarısı üretiyordu


# ---- QA-05: kontrast --------------------------------------------------------------------------

def _luminance(color: str) -> float:
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _ratio(a: str, b: str) -> float:
    high, low = sorted((_luminance(a), _luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _token(theme: str, name: str, dark: bool = False) -> str:
    match = re.search(rf'property color {name}:\s*(?:isDark \? "(#[0-9A-Fa-f]{{6}})" : "(#[0-9A-Fa-f]{{6}})"|"(#[0-9A-Fa-f]{{6}})")',
                      theme)
    assert match, name
    return (match.group(1) if dark else match.group(2)) if match.group(1) else match.group(3)


def test_white_text_on_every_gradient_end_has_aa_contrast():
    theme = (ROOT / "src/qml_ui/qml/singletons/AppTheme.qml").read_text(encoding="utf-8")
    for name in ("startTop", "startBottom", "accentBtnTop", "accentBtnBottom", "dangerBtnTop", "dangerBtnBottom",
                 "titleTop", "titleMid", "titleBottom", "tabIdleTop", "tabIdleBottom", "tabIdleHover"):
        assert _ratio("#FFFFFF", _token(theme, name)) >= 4.5, (name, _token(theme, name))


def test_status_colors_have_aa_contrast_on_surfaces_in_both_themes():
    theme = (ROOT / "src/qml_ui/qml/singletons/AppTheme.qml").read_text(encoding="utf-8")
    for dark in (False, True):
        for name in ("textPrimary", "textSecondary", "textMuted", "accent", "primary", "success", "warning", "danger"):
            assert _ratio(_token(theme, name, dark), _token(theme, "surface", dark)) >= 4.5, (name, dark)
        assert _ratio(_token(theme, "textMuted", dark), _token(theme, "bg", dark)) >= 4.5


def test_severity_badge_text_has_aa_contrast_on_every_severity_color_in_both_themes():
    theme = (ROOT / "src/qml_ui/qml/singletons/AppTheme.qml").read_text(encoding="utf-8")
    for dark in (False, True):
        for name in ("danger", "severityHigh", "warning", "primary", "success"):
            assert _ratio(_token(theme, "onSeverity", dark), _token(theme, name, dark)) >= 4.5, (name, dark)


# ---- QA-06: Türkçe karakterler ----------------------------------------------------------------

def test_analyzer_names_and_titles_use_turkish_characters(tmp_path):
    from src.analyzers.duplicate_finder import DuplicateFinder
    from src.analyzers.empty_folder_finder import EmptyFolderFinder
    from src.analyzers.size_analyzer import SizeAnalyzer
    from src.analyzers.structure_analyzer import StructureAnalyzer
    from src.analyzers.type_analyzer import TypeAnalyzer
    from src.core.project_index import ProjectIndex
    names = [a().name for a in (DuplicateFinder, EmptyFolderFinder, SizeAnalyzer, StructureAnalyzer, TypeAnalyzer)]
    assert names == ["Çift Dosya Bulucu", "Boş Klasör Bulucu", "Boyut Analizörü", "Yapı Analizörü", "Dosya Türü Analizörü"]
    write(tmp_path / "a.dat", "A" * 4000)
    write(tmp_path / "b.dat", "A" * 4000)
    write(tmp_path / "big.bin", "B" * 3000)
    index = ProjectIndex.build(tmp_path)
    assert [r.title for r in DuplicateFinder().analyze(index)] == ["Çift dosyalar: a.dat"]
    assert [r.title for r in SizeAnalyzer(large_file_threshold_mb=0.002).analyze(index) if r.metadata["rule"] == "large-file"][0].startswith("Büyük dosya")


# ---- QA-12: beklenen kullanıcı hatası günlüğe traceback'le yazılmaz -----------------------------

def test_verify_without_exported_tasks_is_logged_as_a_warning_without_traceback(qapp, tmp_path, caplog):
    import logging
    from src.qml_ui.viewmodels.settings_viewmodel import SettingsViewModel
    from src.services.project_service import ProjectService
    service = ProjectService()
    write(tmp_path / "p" / "a.py")
    service.set_project(tmp_path / "p")
    vm = SettingsViewModel(service)
    vm.setAgentOutputDir(str(tmp_path / "yok"))
    with caplog.at_level(logging.WARNING):
        vm.verifyAgentTasks()
    records = [r for r in caplog.records if "doğrulanamadı" in r.getMessage()]
    assert records and records[0].levelno == logging.WARNING and not records[0].exc_info


