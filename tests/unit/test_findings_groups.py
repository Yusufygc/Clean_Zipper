"""Bulgu listesi: kurala göre gruplama, grup katlama, satır içi ayrıntı ve kompakt satır yerleşimi."""
import sys
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtQuick import QQuickItem  # noqa: F401  (QtQuick yüklenince kök pencere QQuickWindow olarak çözülür)
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from src.models.analysis_models import AnalysisResult, Severity
from src.qml_ui.viewmodels.findings_viewmodel import FindingsViewModel
from src.services.project_service import ProjectService


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def finding(rule, severity, title, suggestion="Böl", category="complexity", name="a.py", secret=False):
    return AnalysisResult("A", category, severity, title, "Açıklama " + title, file_path=Path("C:/p") / name,
                          recommendation=suggestion, metadata={"rule": rule, **({"kind": "sensitive_file"} if secret else {})})


def make_vm(findings):
    vm = FindingsViewModel(ProjectService())
    vm._populate_findings(findings, Path("C:/p"))
    return vm


def rows(vm):
    model = vm.rows
    keys = {bytes(v).decode(): k for k, v in model.roleNames().items()}
    return [{name: model.data(model.index(i, 0), role) for name, role in keys.items()} for i in range(model.rowCount())]


def kinds(vm):
    return [(r["kind"], r["title"]) for r in rows(vm)]


GOD = [finding("god-class", Severity.HIGH, f"Tanrı {n}", name=f"{n}.py") for n in "ABC"]
LONG = [finding("long-function", Severity.LOW, f"Uzun {n}", suggestion="Parçala", name=f"{n}.py") for n in "XY"]
SINGLE = finding("unused-import", Severity.MEDIUM, "Tek", suggestion="Sil", category="deadcode")


def test_rules_with_two_or_more_findings_get_their_own_header_and_single_findings_share_an_other_header():
    vm = make_vm(GOD + LONG + [SINGLE])
    headers = [r for r in rows(vm) if r["kind"] == "header"]
    assert sorted(h["count"] for h in headers) == [1, 2, 3]
    other = next(h for h in headers if h["title"] == "Diğer bulgular")
    assert other["rule"] == "" and other["canDisable"] is False and other["suggestion"] == ""
    vm.rows.toggleGroup("other")                                               # ORTA grup kapalı başlar
    single = next(r for r in rows(vm) if r["title"] == "Tek")
    assert single["grouped"] is True and single["mixed"] is True               # kategori ve kuralı satır kendisi taşır
    assert next(r for r in rows(vm) if r["title"] == "Tanrı A")["mixed"] is False


def test_a_single_finding_is_never_left_as_a_headerless_row_under_another_group():
    vm = make_vm(GOD + [SINGLE])
    seen = rows(vm)
    assert all(r["kind"] == "header" or r["grouped"] for r in seen)           # her satır bir başlığın altında
    assert seen[0]["kind"] == "header" and seen[0]["severity"] == "HIGH"


def test_result_count_counts_findings_not_header_rows():
    vm = make_vm(GOD + LONG + [SINGLE])
    assert vm.rows.resultCount == 6 and vm.model.rowCount() == 6
    assert vm.rows.groupCount == 3


def test_groups_are_ordered_by_their_worst_severity_and_high_groups_start_open_while_low_groups_start_closed():
    vm = make_vm(LONG + GOD + [SINGLE])
    seen = rows(vm)
    assert [r["title"] for r in seen if r["kind"] == "header"][0] != "Uzun X"            # YÜKSEK grup, DÜŞÜK gruptan önce
    god_header = next(r for r in seen if r["kind"] == "header" and r["severity"] == "HIGH")
    low_header = next(r for r in seen if r["kind"] == "header" and r["severity"] == "LOW")
    assert god_header["expanded"] is True and low_header["expanded"] is False
    titles = [r["title"] for r in seen if r["kind"] == "item"]
    assert "Tanrı A" in titles and "Uzun X" not in titles                                  # kapalı grubun satırları listede yok


def test_toggling_a_group_inserts_and_removes_only_its_rows():
    vm = make_vm(LONG)
    model = vm.rows
    inserted, removed = [], []
    model.rowsInserted.connect(lambda parent, first, last: inserted.append((first, last)))
    model.rowsAboutToBeRemoved.connect(lambda parent, first, last: removed.append((first, last)))
    assert model.rowCount() == 1                                           # yalnızca kapalı başlık
    model.toggleGroup("long-function")
    assert inserted == [(1, 2)] and model.rowCount() == 3
    assert rows(vm)[0]["expanded"] is True and model.allExpanded is True
    model.toggleGroup("long-function")
    assert removed == [(1, 2)] and model.rowCount() == 1 and rows(vm)[0]["expanded"] is False


def test_group_choice_survives_a_new_diagnosis():
    vm = make_vm(LONG)
    vm.rows.toggleGroup("long-function")
    vm._populate_findings(LONG + [SINGLE], Path("C:/p"))                   # analiz yenilendi (temizlik sonrası vb.)
    assert next(r for r in rows(vm) if r["kind"] == "header" and r["rule"] == "long-function")["expanded"] is True


def test_active_filters_open_every_group_and_lock_collapsing_so_no_result_is_hidden():
    vm = make_vm(LONG + GOD)
    assert vm.rows.groupsLocked is False
    vm.setSearchQuery("uzun")
    assert vm.rows.groupsLocked is True
    assert [r["title"] for r in rows(vm) if r["kind"] == "item"] == ["Uzun X", "Uzun Y"]
    count = vm.rows.rowCount()
    vm.rows.toggleGroup("long-function")                                   # kilitliyken etkisiz
    assert vm.rows.rowCount() == count
    vm.setSearchQuery("")
    assert vm.rows.groupsLocked is False and vm.rows.resultCount == 5


def test_a_shared_suggestion_is_shown_once_on_the_header_and_removed_from_the_rows():
    vm = make_vm(GOD)
    seen = rows(vm)
    assert seen[0]["suggestion"] == "Böl"
    assert all(r["suggestion"] == "" for r in seen[1:])
    mixed = make_vm([finding("god-class", Severity.HIGH, "A", suggestion="1"), finding("god-class", Severity.HIGH, "B", suggestion="2")])
    seen = rows(mixed)
    assert seen[0]["suggestion"] == "" and [r["suggestion"] for r in seen[1:]] == ["1", "2"]


def test_detail_state_lives_in_the_model_and_survives_group_collapsing():
    vm = make_vm(GOD)
    model = vm.rows
    changed = []
    model.dataChanged.connect(lambda top, bottom, roles: changed.append(top.row()))
    key = rows(vm)[1]["rowKey"]
    model.toggleDetail(key)
    assert changed == [1] and rows(vm)[1]["detailOpen"] is True
    model.toggleGroup("god-class")                                         # kapat
    model.toggleGroup("god-class")                                         # aç
    assert rows(vm)[1]["detailOpen"] is True
    model.toggleDetail("group:god-class")                                  # başlık satırı ayrıntı açmaz
    assert rows(vm)[0]["detailOpen"] is False


def test_expand_and_collapse_all_groups():
    vm = make_vm(GOD + LONG)
    vm.rows.setAllGroupsExpanded(True)
    assert vm.rows.rowCount() == 7 and vm.rows.allExpanded is True
    vm.rows.setAllGroupsExpanded(False)
    assert vm.rows.rowCount() == 2 and vm.rows.allExpanded is False


def test_a_group_with_secrets_never_offers_to_disable_its_rule():
    secrets = [finding("hardcoded-secret", Severity.CRITICAL, f"Sır {n}", name=f"{n}.env") for n in "AB"]
    vm = make_vm(secrets + GOD)
    headers = {r["rule"]: r for r in rows(vm) if r["kind"] == "header"}
    assert headers["hardcoded-secret"]["canDisable"] is False and headers["god-class"]["canDisable"] is True
    assert all(r["canDisable"] is False for r in rows(vm) if r["rule"] == "hardcoded-secret")


# ---- gerçek pencerede: kompakt satırlar, tıklama ve klavye ------------------------------------------------------------------------------

def open_findings(qapp, monkeypatch, vm_findings, tmp_path, width=1400, height=900):
    from src.qml_ui import app as qml_app
    monkeypatch.setattr(qml_app, "setup_logging", lambda: None)
    _, engine = qml_app.create_qml_app()
    window = engine.rootObjects()[0]
    window.setWidth(width)
    window.setHeight(height)
    window.setProperty("currentTab", 1)
    engine.rootContext().contextProperty("findingsVM")._populate_findings(vm_findings, tmp_path)
    pump()
    return engine, window


def pump(times=30):
    for _ in range(times):
        QCoreApplication.processEvents()


def walk(item):
    for child in item.childItems():
        yield child
        yield from walk(child)


def cards(window):
    return [i for i in walk(window.contentItem()) if i.property("rowHeight") == 38]


def headers(window):
    return [i for i in walk(window.contentItem()) if i.property("bandHeight") == 36]


def many(tmp_path):
    return [finding("god-class", Severity.HIGH, f"Tanrı Sınıf Riski {n}", name=f"pkg/deep/module_{n}.py") for n in range(6)] \
        + [finding("long-function", Severity.MEDIUM, f"Uzun işlev {n}", suggestion="Parçala", name=f"util_{n}.py") for n in range(8)]


def test_collapsed_rows_are_compact_so_many_findings_fit_on_screen(qapp, monkeypatch, tmp_path):
    engine, window = open_findings(qapp, monkeypatch, many(tmp_path), tmp_path)
    listing = next(i for i in walk(window.contentItem()) if i.objectName() == "findingsList")
    shown = cards(window)
    assert shown and all(card.height() == 38 for card in shown)                         # kapalı satır 38 px
    assert len(headers(window)) == 2
    # 14 bulgu: eski kartlarda ~170 px x 14 = ~2400 px; gruplu kompakt listede bir ekrana yakın
    assert listing.property("contentHeight") < 14 * 70


def test_a_row_opens_in_place_on_click_and_closes_again(qapp, monkeypatch, tmp_path):
    engine, window = open_findings(qapp, monkeypatch, many(tmp_path), tmp_path)
    card = cards(window)[0]
    closed_height = card.height()
    vm = engine.rootContext().contextProperty("findingsVM")
    position = card.mapToScene(card.boundingRect().center()).toPoint()
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, position)
    pump()
    opened = next(c for c in cards(window) if c.property("detailOpen"))
    assert opened.height() > closed_height + 30
    assert sum(1 for r in rows(vm) if r["detailOpen"]) == 1
    top = opened.mapToScene(opened.boundingRect().topLeft()).toPoint()
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, type(top)(top.x() + 200, top.y() + 19))   # satırın kapalı şeridi
    pump()
    assert all(c.height() == 38 for c in cards(window))


def test_group_header_collapses_and_expands_by_click_and_by_keyboard(qapp, monkeypatch, tmp_path):
    engine, window = open_findings(qapp, monkeypatch, many(tmp_path), tmp_path)
    vm = engine.rootContext().contextProperty("findingsVM")
    open_header = next(h for h in headers(window) if h.property("expanded"))
    assert open_header.property("count") == 6 and len(cards(window)) >= 6
    open_header.forceActiveFocus()
    QTest.keyClick(window, Qt.Key_Return)
    pump()
    assert vm.rows.rowCount() < 14 + 2 and not next(h for h in headers(window) if h.property("count") == 6).property("expanded")
    QTest.keyClick(window, Qt.Key_Space)
    pump()
    assert next(h for h in headers(window) if h.property("count") == 6).property("expanded")


def test_row_texts_are_elided_inside_the_row_at_every_window_width(qapp, monkeypatch, tmp_path):
    for width in (900, 1400, 1920):
        engine, window = open_findings(qapp, monkeypatch, many(tmp_path), tmp_path, width=width)
        for card in cards(window):
            for text in (i for i in walk(card) if i.metaObject().className().startswith("QQuickText")):
                right = text.mapToItem(card, text.boundingRect().topRight()).x()
                assert right <= card.width() + 0.5, (width, text.property("text"), right, card.width())
            assert card.height() == 38


def test_row_is_reachable_by_keyboard_and_named_for_screen_readers(qapp, monkeypatch, tmp_path):
    from PySide6.QtGui import QAccessible
    engine, window = open_findings(qapp, monkeypatch, many(tmp_path), tmp_path)
    card = cards(window)[0]
    assert card.property("activeFocusOnTab") is True
    interface = QAccessible.queryAccessibleInterface(card)
    assert interface.role() == QAccessible.Role.Button and interface.text(QAccessible.Text.Name).startswith("Tanrı Sınıf")
    card.forceActiveFocus()
    QTest.keyClick(window, Qt.Key_Return)
    pump()
    assert next(c for c in cards(window) if c.property("detailOpen")).property("title") == card.property("title")
