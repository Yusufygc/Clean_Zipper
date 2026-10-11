"""QML yerleşim sorunlarının regresyon testleri: kartlar içeriğinin altında kalmamalı, boş sonuç kartı görünmemeli."""
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, QObject, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem  # noqa: F401  (QtQuick yüklenince kök pencere QQuickWindow olarak çözülür)
from PySide6.QtWidgets import QApplication

from src.qml_ui.viewmodels.archive_viewmodel import EMPTY_RESULT, ArchiveViewModel
from src.qml_ui.viewmodels.scan_viewmodel import ScanViewModel
from src.services.project_service import ProjectService

QML_DIR = Path(__file__).resolve().parents[2] / "src" / "qml_ui" / "qml"
COMPONENTS = (QML_DIR / "components").as_uri()


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def build(qapp, source: str):
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    component = QQmlComponent(engine)
    component.setData(source.encode("utf-8"), QUrl.fromLocalFile(str(QML_DIR / "Test.qml")))
    root = component.create()
    assert root is not None, [e.toString() for e in component.errors()]
    for _ in range(20):
        QCoreApplication.processEvents()
    return engine, component, root                                   # üçü de canlı kalmalı (aksi hâlde nesneler silinir)


CARD_IN_COLUMN = f"""
import QtQuick
import QtQuick.Layouts
import "{COMPONENTS}"

Item {{
    width: 600; height: 500
    ColumnLayout {{
        anchors.fill: parent
        spacing: 10
        CardFrame {{
            id: card
            objectName: "card"
            Layout.fillWidth: true
            ColumnLayout {{
                width: parent.width
                spacing: 8
                Text {{ text: "a"; font.pixelSize: 20 }}
                Text {{ text: "b"; font.pixelSize: 20 }}
                RowLayout {{ Text {{ text: "c"; font.pixelSize: 20 }} Rectangle {{ width: 30; height: 60 }} }}
            }}
        }}
        Rectangle {{ id: below; objectName: "below"; Layout.fillWidth: true; Layout.preferredHeight: 20 }}
        Item {{ Layout.fillHeight: true }}
    }}
}}
"""


def test_card_grows_to_hold_its_content_and_does_not_overlap_the_next_item(qapp):
    engine, component, root = build(qapp, CARD_IN_COLUMN)
    card, below = root.findChild(QObject, "card"), root.findChild(QObject, "below")
    # üç satırlık yazı (3 x ~27 px) + satır arası + 60 px yüksekliğindeki satır + 2 x 16 iç boşluk
    assert card.property("height") >= card.property("implicitHeight") - 0.5            # kart içeriğin doğal boyutundan küçük değil
    assert card.property("implicitHeight") >= 20 + 20 + 60 + 2 * 8 + 32
    assert card.property("height") > 60                                                  # çökmedi
    assert below.property("y") >= card.property("y") + card.property("height")           # üst üste binmedi
    assert card.property("width") == 600


CARD_IN_ROW = f"""
import QtQuick
import QtQuick.Layouts
import "{COMPONENTS}"

Item {{
    width: 800; height: 300
    RowLayout {{
        anchors.fill: parent
        spacing: 16
        CardFrame {{
            id: left
            objectName: "left"
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            ColumnLayout {{ width: parent.width; Text {{ text: "x"; font.pixelSize: 18 }} Text {{ text: "y"; font.pixelSize: 18 }} }}
        }}
        CardFrame {{
            id: right
            objectName: "right"
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            ColumnLayout {{ width: parent.width; Repeater {{ model: 6; Text {{ text: "satir"; font.pixelSize: 18 }} }} }}
        }}
    }}
}}
"""


def test_cards_side_by_side_keep_their_own_content_height(qapp):
    engine, component, root = build(qapp, CARD_IN_ROW)
    left, right = root.findChild(QObject, "left"), root.findChild(QObject, "right")
    assert right.property("height") > left.property("height") > 40
    assert left.property("width") >= left.property("implicitWidth") - 0.5 and right.property("width") >= right.property("implicitWidth") - 0.5
    assert left.property("width") + right.property("width") + 16 == pytest.approx(800, abs=1)


# ---- arayüz veri köprüsü ---------------------------------------------------------------------------------------------------

def test_archive_view_model_starts_without_a_result_but_with_every_key(qapp):
    vm = ArchiveViewModel(ProjectService())
    assert vm.hasResult is False
    assert set(vm.lastResult) == set(EMPTY_RESULT)
    assert vm.lastResult["addedFiles"] == 0 and vm.lastResult["outputPath"] == "" and vm.lastResult["failedFiles"] == []


def test_archive_view_model_reports_a_result_after_an_operation(qapp):
    vm = ArchiveViewModel(ProjectService())
    vm._on_finished({"success": True, "complete": True, "added_files": 3, "skipped_files": 1, "output_path": "x.zip"})
    assert vm.hasResult is True and vm.lastResult["addedFiles"] == 3 and vm.lastResult["success"] is True


def test_scan_view_model_accepts_the_service_gitignore_counts_dict(qapp):
    vm = ScanViewModel(ProjectService())
    vm._on_finished({"health_score": 80, "total_files": 7, "ignored_by_gitignore": {"files": 5, "dirs": 2}})
    assert vm.ignoredByGitignore == 7 and vm.totalFiles == 7           # sözlük TypeError verip taramayı yarım bırakmamalı


def test_scan_view_model_still_accepts_a_plain_number(qapp):
    vm = ScanViewModel(ProjectService())
    vm._on_finished({"ignored_by_gitignore": 4})
    assert vm.ignoredByGitignore == 4


def test_scan_view_model_exposes_language_lines_and_skip_reasons(qapp):
    vm = ScanViewModel(ProjectService())
    vm._on_finished({"language_stats": {"python": {"code_lines": 120, "files": 3}, "go": {"code_lines": 0, "files": 1},
                                        "rust": {"code_lines": 30, "files": 1}},
                     "skipped_files": {"minified": 1, "too_large": 4, "garip": 2}})
    assert vm.languageLines == {"Python": 120, "Rust": 30}              # satırı olmayan dil gösterilmez
    assert [(d["reason"], d["count"]) for d in vm.skippedDetail] == [("too_large", 4), ("garip", 2), ("minified", 1)]
    assert vm.skippedDetail[0]["label"].startswith("Çok büyük dosya") and vm.skippedDetail[1]["label"] == "garip"


def test_app_view_model_reports_errors_in_the_status_bar_and_opens_paths(qapp, tmp_path, monkeypatch):
    from src.qml_ui.viewmodels import app_viewmodel
    from src.qml_ui.viewmodels.app_viewmodel import AppViewModel
    vm = AppViewModel()
    assert vm.setProjectPath(str(tmp_path / "yok")) is False
    assert vm.statusText.startswith("Hata: geçersiz proje dizini")
    opened = []
    monkeypatch.setattr(app_viewmodel.QDesktopServices, "openUrl", lambda url: opened.append(url.toLocalFile()) or True)
    assert vm.openPath(str(tmp_path)) is True and [Path(o) for o in opened] == [tmp_path]
    assert vm.openPath(str(tmp_path / "yok")) is False and vm.statusText.startswith("Hata: yol bulunamadı")


# ---- uygulama kurulumu: ViewModel'ler çöp toplayıcıdan korunmalı --------------------------------------------------------------

VIEW_MODELS = ("appVM", "scanVM", "findingsVM", "archiveVM", "cleanupVM", "settingsVM")


def test_every_view_model_survives_garbage_collection_after_app_creation(qapp, monkeypatch):
    """Uygulama (`main.py`) çalışırken `archiveVM` / `cleanupVM` / `settingsVM` null kalıyordu: yalnızca yerel değişkende tutuluyorlardı."""
    import gc
    from src.qml_ui import app as qml_app
    monkeypatch.setattr(qml_app, "setup_logging", lambda: None)
    _, engine = qml_app.create_qml_app()
    gc.collect()
    for name in VIEW_MODELS:
        assert engine.rootContext().contextProperty(name) is not None, name


def test_rule_change_refreshes_analysis_and_project_change_updates_agent_dir(qapp, tmp_path, monkeypatch):
    """Kural kapatılınca bulgular yeniden hesaplanır; proje değişince varsayılan ajan klasörü güncellenir."""
    from src.qml_ui import app as qml_app
    monkeypatch.setattr(qml_app, "setup_logging", lambda: None)
    _, engine = qml_app.create_qml_app()
    app_vm, scan_vm, findings_vm, settings_vm = (engine.rootContext().contextProperty(n) for n in
                                                 ("appVM", "scanVM", "findingsVM", "settingsVM"))
    calls = []
    monkeypatch.setattr(scan_vm, "startQuickScan", lambda: calls.append("scan"))
    monkeypatch.setattr(findings_vm, "startDeepDiagnosis", lambda: calls.append("diagnose"))
    settings_vm.rulesChanged.emit()
    assert calls == []                                                # proje yokken analiz başlatılmaz
    project = tmp_path / "p"
    project.mkdir()
    app_vm.service.set_project(project)
    app_vm._current_path = str(project)
    settings_vm.rulesChanged.emit()
    assert calls == ["scan", "diagnose"]
    changes = []
    settings_vm.settingsChanged.connect(lambda: changes.append(True))
    app_vm.projectChanged.emit()
    assert changes


# ---- bulgu kartı: kod gösterimi ve eylem düğmeleri ------------------------------------------------------------------------------

def finding_card(visible_code: bool, secret: bool = False, rule: str = "unused-import", line: int = 3) -> str:
    return f"""
import QtQuick
import "{COMPONENTS}"

Item {{
    width: 700; height: 600
    FindingCard {{
        objectName: "card"
        width: 700
        title: "Başlık"; description: "Açıklama"; severity: "LOW"; categoryName: "Ölü kod"; fileName: "a.py"
        relPath: "pkg/a.py"; filePath: "C:/proje/pkg/a.py"; line: {line}; rule: "{rule}"; isSecret: {str(secret).lower()}
        suggestion: "Silin"; codeVisible: {str(visible_code).lower()}; codeText: "3: import os\n4: x = 1"
    }}
}}
"""


def card_properties(qapp, source: str):
    engine, component, root = build(qapp, source)
    card = root.findChild(QObject, "card")
    return engine, component, root, card


def test_finding_card_grows_when_the_code_is_shown(qapp):
    closed_ctx = card_properties(qapp, finding_card(False))            # engine ve bileşen canlı kalmalı
    opened_ctx = card_properties(qapp, finding_card(True))
    closed, opened = closed_ctx[3], opened_ctx[3]
    assert opened.property("implicitHeight") > closed.property("implicitHeight") + 20
    assert closed.property("hasCode") is True and closed.property("canDisableRule") is True


def test_secret_findings_offer_neither_code_nor_rule_disabling(qapp):
    ctx = card_properties(qapp, finding_card(False, secret=True, rule="hardcoded-secret"))
    card = ctx[3]
    assert card.property("hasCode") is False and card.property("canDisableRule") is False


def test_findings_without_a_line_or_rule_hide_the_matching_actions(qapp):
    ctx = card_properties(qapp, finding_card(False, rule="", line=0))
    card = ctx[3]
    assert card.property("hasCode") is False and card.property("canDisableRule") is False


# ---- duyarlı başlık: hiçbir pencere genişliğinde taşma / kırpılma olmamalı ----------------------------------------------------------

def header_edges(window, width: int):
    from PySide6.QtCore import QPointF
    window.setWidth(width)
    window.setHeight(700)
    for _ in range(30):
        QCoreApplication.processEvents()
    edges = {}
    for name in ("tabNav", "projectButton", "themeButton"):
        item = window.findChild(QQuickItem, name)
        left = item.mapToScene(QPointF(0, 0)).x()
        edges[name] = (left, left + item.width())
    return edges


def test_header_never_clips_the_theme_button_and_never_overlaps(qapp, monkeypatch):
    """Kullanıcı ekran görüntüsü: açılış boyutunda tema düğmesi pencere dışına taşıp kırpılıyordu."""
    from src.qml_ui import app as qml_app
    monkeypatch.setattr(qml_app, "setup_logging", lambda: None)
    _, engine = qml_app.create_qml_app()
    window = engine.rootObjects()[0]
    for width in (900, 1000, 1050, 1120, 1200, 1282, 1399, 1400, 1600, 1920):
        edges = header_edges(window, width)
        nav, project, theme = edges["tabNav"], edges["projectButton"], edges["themeButton"]
        assert theme[1] <= width, (width, edges)                       # tema düğmesi pencerenin içinde
        assert nav[0] >= 0, (width, edges)                             # sol taraf da kırpılmaz
        assert nav[1] <= project[0] + 0.5 and project[1] <= theme[0] + 0.5, (width, edges)   # öğeler üst üste binmez


def test_window_has_a_reasonable_minimum_size_and_centres_on_the_screen(qapp, monkeypatch):
    from src.qml_ui import app as qml_app
    monkeypatch.setattr(qml_app, "setup_logging", lambda: None)
    _, engine = qml_app.create_qml_app()
    window = engine.rootObjects()[0]
    screen = window.screen().availableGeometry()
    assert window.minimumWidth() == min(900, screen.width()) and window.minimumHeight() == min(600, screen.height())
    assert window.minimumWidth() <= window.width() <= screen.width() and window.minimumHeight() <= window.height() <= screen.height()


def all_items(item):
    for child in item.childItems():
        yield child
        yield from all_items(child)


def test_no_page_scrolls_past_its_ends_and_snaps_back(qapp, monkeypatch):
    """Kullanıcı: sayfa uçtan öteye sürüklenebiliyor, bırakınca geri sıçrıyor. Tüm kaydırma alanları uçta durmalı."""
    from src.qml_ui import app as qml_app
    monkeypatch.setattr(qml_app, "setup_logging", lambda: None)
    _, engine = qml_app.create_qml_app()
    window = engine.rootObjects()[0]
    scrollers = [item for item in all_items(window.contentItem())
                 if item.metaObject().indexOfProperty("boundsBehavior") >= 0]
    assert len(scrollers) == 5                                   # 3 sayfa kaydırıcısı + 2 liste görünümü
    from PySide6.QtQml import QQmlContext, QQmlExpression
    stops = []
    for item in scrollers:                                        # PySide `QFlags` değerini okuyamaz: QML ifadesiyle sorulur
        context = QQmlContext(engine.rootContext())
        expression = QQmlExpression(context, item, "boundsBehavior === 0")   # 0 = Flickable.StopAtBounds
        stops.append((item.metaObject().className(), expression.evaluate()[0]))
    assert all(value is True for _, value in stops), stops


def test_threshold_buttons_sit_right_next_to_their_label(qapp, monkeypatch):
    """Kullanıcı: eşik etiketi ile eksi / artı düğmeleri birbirinden çok uzaktı."""
    from PySide6.QtCore import QPointF
    from src.qml_ui import app as qml_app
    monkeypatch.setattr(qml_app, "setup_logging", lambda: None)
    _, engine = qml_app.create_qml_app()
    window = engine.rootObjects()[0]
    window.setWidth(1400)
    window.setHeight(900)
    window.setProperty("currentTab", 4)
    for _ in range(20):
        QCoreApplication.processEvents()
    items = list(all_items(window.contentItem()))
    labels = [i for i in items if i.objectName() == "thresholdLabel"]
    minus = [i for i in items if i.objectName() == "thresholdMinus"]
    assert len(labels) == len(minus) == 9
    for label, button in zip(labels, minus):
        gap = button.mapToScene(QPointF(0, 0)).x() - (label.mapToScene(QPointF(0, 0)).x() + label.width())
        assert 0 <= gap <= 24, gap


def test_cleanup_preview_list_is_visible_and_fills_the_card(qapp, monkeypatch):
    """Kullanıcı: Proje Temizliği önizleme listesi görünmüyordu (liste 0 px yükseklikteydi)."""
    from src.qml_ui import app as qml_app
    monkeypatch.setattr(qml_app, "setup_logging", lambda: None)
    _, engine = qml_app.create_qml_app()
    window = engine.rootObjects()[0]
    window.setWidth(1400)
    window.setHeight(900)
    window.setProperty("currentTab", 3)
    cleanup = engine.rootContext().contextProperty("cleanupVM")
    cleanup._preview_files = [{"name": f"a{i}.pyc", "path": f"C:/p/a{i}.pyc", "sizeKb": 1.0,
                               "category": "python_cache", "isDir": False} for i in range(30)]
    cleanup._preview_count = 30
    cleanup.stateChanged.emit()
    for _ in range(20):
        QCoreApplication.processEvents()
    lst = next(i for i in all_items(window.contentItem()) if i.objectName() == "cleanList")
    assert lst.isVisible() and lst.height() > 200 and lst.width() > 500, (lst.height(), lst.width())


def count_null_errors_when_closing(qapp, monkeypatch, qml_first: bool) -> int:
    import shiboken6
    from PySide6.QtCore import qInstallMessageHandler
    from src.qml_ui import app as qml_app
    monkeypatch.setattr(qml_app, "setup_logging", lambda: None)
    messages = []
    qInstallMessageHandler(lambda mode, context, text: messages.append(text))
    try:
        _, engine = qml_app.create_qml_app()
        for _ in range(20):
            QCoreApplication.processEvents()
        view_models = list(engine.viewmodels)
        if qml_first:
            qml_app.shutdown_qml_app(engine)
        for view_model in view_models:                          # Python'un kapanışta yaptığı gibi ViewModel'ler yok edilir
            shiboken6.delete(view_model)
        for _ in range(20):
            QCoreApplication.processEvents()
    finally:
        qInstallMessageHandler(None)
    return sum("of null" in text for text in messages)


def test_closing_the_app_does_not_flood_the_console_with_null_property_errors(qapp, monkeypatch):
    """Kullanıcı: uygulamayı kapatınca konsola yüzlerce `Cannot read property ... of null` basılıyordu."""
    assert count_null_errors_when_closing(qapp, monkeypatch, qml_first=False) > 0    # sıra bozulursa hata üretildiğinin kanıtı
    assert count_null_errors_when_closing(qapp, monkeypatch, qml_first=True) == 0    # `shutdown_qml_app` sırayı korur


def open_tab(qapp, monkeypatch, tab: int, width: int = 1400, height: int = 900):
    from src.qml_ui import app as qml_app
    monkeypatch.setattr(qml_app, "setup_logging", lambda: None)
    _, engine = qml_app.create_qml_app()
    window = engine.rootObjects()[0]
    window.setWidth(width)
    window.setHeight(height)
    window.setProperty("currentTab", tab)
    for _ in range(20):
        QCoreApplication.processEvents()
    return engine, window


def find_item(window, name: str):
    return next(i for i in all_items(window.contentItem()) if i.objectName() == name)


def test_dashboard_rows_are_symmetric_equal_columns_with_equal_heights(qapp, monkeypatch):
    """Kullanıcı: gösterge paneli dağınık; her satır eşit sütunlu ve aynı yükseklikte kartlardan oluşmalı."""
    for width in (900, 1400, 1920):
        _, window = open_tab(qapp, monkeypatch, 0, width=width, height=1000)
        grid = find_item(window, "metricGrid")
        cards = [c for c in grid.childItems() if c.width() > 0]
        widths = [c.width() for c in cards]                       # kesirli genişlik: ekranda 1 px yuvarlama farkı simetriyi bozmaz
        assert len(cards) == 4 and max(widths) - min(widths) <= 1, (width, widths)
        for row_name in ("healthRow", "distributionRow", "insightRow"):
            row = find_item(window, row_name)
            left, right = [c for c in row.childItems() if c.width() > 0]
            assert abs(left.width() - right.width()) <= 1, (width, row_name, left.width(), right.width())
            assert abs(left.height() - right.height()) <= 1, (width, row_name, left.height(), right.height())


def test_findings_filter_bar_has_severity_segments_a_category_dropdown_and_a_result_count(qapp, monkeypatch, tmp_path):
    from src.models.analysis_models import AnalysisResult, Severity
    engine, window = open_tab(qapp, monkeypatch, 1)
    vm = engine.rootContext().contextProperty("findingsVM")
    source = tmp_path / "a.py"
    source.write_text("x = 1\n", encoding="utf-8")
    findings = [AnalysisResult("A", "security", Severity.HIGH, "T1", "D", file_path=source, metadata={"rule": "r"}),
                AnalysisResult("A", "deadcode", Severity.LOW, "T2", "D", file_path=source, metadata={"rule": "r"}),
                AnalysisResult("A", "deadcode", Severity.LOW, "T3", "D", file_path=source, metadata={"rule": "r"})]
    vm._populate_findings(findings, tmp_path)
    for _ in range(20):
        QCoreApplication.processEvents()
    assert find_item(window, "severityFilter") and find_item(window, "categoryFilter")
    assert find_item(window, "resultCount").property("text") == "3 sonuç"
    assert not find_item(window, "clearFilters").isVisible()          # süzgeç yokken "Temizle" görünmez
    vm.setCategoryFilter("deadcode")
    for _ in range(20):
        QCoreApplication.processEvents()
    assert find_item(window, "resultCount").property("text") == "2 sonuç"
    assert find_item(window, "clearFilters").isVisible()


def test_diagnosis_banner_state_is_reported_when_the_diagnosis_ends(qapp):
    """`isDiagnosing` bitişte de bildirilmeli; aksi hâlde ilerleme çubuğu ve düğme kilidi ekranda takılı kalır."""
    from types import SimpleNamespace
    from src.qml_ui.viewmodels.findings_viewmodel import FindingsViewModel
    vm = FindingsViewModel(ProjectService())
    changes = []
    vm.diagnosingChanged.connect(lambda: changes.append(vm.isDiagnosing))
    vm._is_diagnosing = True
    vm._on_finished(SimpleNamespace(all_findings=[], project_path=Path(".")))
    assert changes == [False]
    vm._is_diagnosing = True
    vm._on_error("hata")
    assert changes == [False, False] and vm.isDiagnosing is False


def test_scroll_areas_cover_their_whole_content_so_the_last_row_is_not_cut(qapp, monkeypatch, tmp_path):
    """Kullanıcı: gösterge panelinin alt kartları kesik duruyordu (proje yüklenince kaydırma içeriğin sonuna ulaşmıyordu)."""
    import time
    from PySide6.QtQml import QQmlContext, QQmlExpression
    for index in range(6):
        (tmp_path / f"m{index}.py").write_text("import os\n\n\ndef f(a):\n    return a + 41\n", encoding="utf-8")
    (tmp_path / "bos_klasor").mkdir()                                   # "Boş klasörler" önerisi: içerik uzar
    engine, window = open_tab(qapp, monkeypatch, 0, width=1900, height=700)
    engine.rootContext().contextProperty("appVM").setProjectPath(str(tmp_path))
    scan = engine.rootContext().contextProperty("scanVM")
    deadline = time.time() + 40
    while time.time() < deadline and (scan.isScanning or scan.totalFiles == 0):
        QCoreApplication.processEvents()
        time.sleep(0.02)
    for _ in range(30):
        QCoreApplication.processEvents()
    for tab in (0, 2, 4):
        window.setProperty("currentTab", tab)
        for _ in range(20):
            QCoreApplication.processEvents()
        flicks = [i for i in all_items(window.contentItem()) if i.isVisible()
                  and i.metaObject().className() == "QQuickFlickable"]
        assert flicks, tab
        for flick in flicks:
            content = QQmlExpression(QQmlContext(engine.rootContext()), flick, "contentHeight").evaluate()[0]
            column = flick.childItems()[0].childItems()[0]            # contentItem -> ColumnLayout
            assert abs(content - column.height()) <= 1, (tab, content, column.height())   # içerik yüksekliği düzeni izler


def test_tab_navigation_is_centred_in_the_header_when_it_fits(qapp, monkeypatch):
    """Kullanıcı: navbar butonları çubuğun ortasında durmalı."""
    from src.qml_ui import app as qml_app
    monkeypatch.setattr(qml_app, "setup_logging", lambda: None)
    _, engine = qml_app.create_qml_app()
    window = engine.rootObjects()[0]
    for width in (1400, 1600, 1920):
        edges = header_edges(window, width)
        nav = edges["tabNav"]
        assert abs((nav[0] + nav[1]) / 2 - width / 2) <= 1, (width, nav)
