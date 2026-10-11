"""Bulgu listesinin görünüm modeli: bulgular kurala göre gruplanır, gruplar katlanır, bulgu ayrıntısı satır içinde açılır.

`FindingsListModel` yalnızca süzülmüş bulguları tutar (sayım, test ve arama onu kullanır). `FindingsRowsModel` aynı
bulguları QML `ListView` için satırlara çevirir: iki ve daha çok bulgusu olan her kural bir başlık satırı alır; tek
bulgulu kurallar "Diğer bulgular" başlığında toplanır (başlıksız satır, üstündeki gruba aitmiş gibi görünürdü).
"""
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QAbstractListModel, QByteArray, QModelIndex, QObject, Property, Qt, Signal, Slot

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
OPEN_BY_DEFAULT = ("CRITICAL", "HIGH")      # kritik ve yüksek gruplar açık başlar, gerisi kapalı
MIN_GROUP_SIZE = 2                          # bundan az bulgulu kurallar "Diğer bulgular" grubunda toplanır
OTHER_KEY = "other"

ROW_DEFAULTS: Dict[str, Any] = {
    "kind": "item", "rowKey": "", "groupKey": "", "title": "", "description": "", "severity": "INFO",
    "categoryName": "", "fileName": "", "filePath": "", "relPath": "", "line": 0, "suggestion": "", "rule": "",
    "ruleLabel": "", "effort": "S", "isSecret": False, "approximate": False,
    "count": 0, "expanded": False, "collapsible": False, "detailOpen": False, "grouped": False, "mixed": False,
    "canDisable": False,
}
ROW_KEYS = tuple(ROW_DEFAULTS)


def group_key(item: Dict[str, Any]) -> str:
    return item["rule"] or "category:" + item["category"]


def row_key(item: Dict[str, Any]) -> str:
    return "|".join((item["rule"], item["filePath"], str(item["line"]), item["title"]))


def _group(key: str, label: str, members: List[Dict[str, Any]], mixed: bool) -> Dict[str, Any]:
    first = members[0]
    suggestions = {m["suggestion"] for m in members}
    return {
        "key": key,
        "label": label,
        "mixed": mixed,                                  # karışık kurallar: satırlar kategori ve kural bilgisini kendisi taşır
        "severity": min((m["severity"] for m in members), key=lambda s: SEVERITY_ORDER.get(s, 4)),
        "categoryName": "" if mixed else first["categoryName"],
        "rule": "" if mixed else first["rule"],
        "canDisable": not mixed and bool(first["rule"]) and not any(m["isSecret"] for m in members),
        "shared": suggestions.pop() if len(suggestions) == 1 and not mixed else "",
        "items": members,
    }


def build_groups(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Bulguları kurala göre gruplar; en ciddi grup başta, eşitlikte en kalabalık, "Diğer bulgular" eşitlikte en sonda."""
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for item in items:
        buckets.setdefault(group_key(item), []).append(item)
    groups = []
    others: List[Dict[str, Any]] = []
    for key, members in buckets.items():
        if len(members) >= MIN_GROUP_SIZE:
            groups.append(_group(key, members[0]["ruleLabel"] or members[0]["categoryName"], members, False))
        else:
            others.extend(members)
    if others:
        groups.append(_group(OTHER_KEY, "Diğer bulgular", others, True))
    groups.sort(key=lambda g: (SEVERITY_ORDER.get(g["severity"], 4), g["mixed"], -len(g["items"]), g["label"]))
    return groups


class FindingsRowsModel(QAbstractListModel):
    """Başlık ve bulgu satırlarından oluşan düz liste; grup katlama ve satır ayrıntısı durumu burada tutulur."""

    summaryChanged = Signal()

    def __init__(self, source: QAbstractListModel, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._source = source
        self._groups: List[Dict[str, Any]] = []
        self._rows: List[Dict[str, Any]] = []
        self._forced = False                    # süzgeç ya da arama açıkken tüm gruplar açık (sonuç gizlenmesin)
        self._overrides: Dict[str, bool] = {}   # kullanıcının grup başına seçimi; yeni tanıdan sonra da korunur
        self._open: set = set()                 # ayrıntısı açık bulgu satırları
        source.modelReset.connect(self.rebuild)

    # ── Qt model ──

    def roleNames(self) -> Dict[int, QByteArray]:
        return {Qt.UserRole + 1 + i: QByteArray(key.encode()) for i, key in enumerate(ROW_KEYS)}

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._rows)):
            return None
        position = role - Qt.UserRole - 1
        return self._rows[index.row()][ROW_KEYS[position]] if 0 <= position < len(ROW_KEYS) else None

    @staticmethod
    def _role(key: str) -> int:
        return Qt.UserRole + 1 + ROW_KEYS.index(key)

    # ── Özet ──

    @Property(int, notify=summaryChanged)
    def resultCount(self) -> int:
        """Süzgeçlerden geçen bulgu sayısı (başlık satırları sayılmaz)."""
        return len(self._source.filtered_items)

    @Property(int, notify=summaryChanged)
    def groupCount(self) -> int:
        return len(self._groups)

    @Property(bool, notify=summaryChanged)
    def allExpanded(self) -> bool:
        return all(self._expanded(g) for g in self._groups)

    @Property(bool, notify=summaryChanged)
    def groupsLocked(self) -> bool:
        """Süzgeç açıkken gruplar katlanamaz."""
        return self._forced

    # ── Satır üretimi ──

    def _expanded(self, group: Dict[str, Any]) -> bool:
        if self._forced:
            return True
        return self._overrides.get(group["key"], group["severity"] in OPEN_BY_DEFAULT)

    def _header_row(self, group: Dict[str, Any]) -> Dict[str, Any]:
        return {**ROW_DEFAULTS, "kind": "header", "rowKey": "group:" + group["key"], "groupKey": group["key"],
                "title": group["label"], "severity": group["severity"], "categoryName": group["categoryName"],
                "rule": group["rule"], "suggestion": group["shared"], "count": len(group["items"]),
                "expanded": self._expanded(group), "collapsible": not self._forced, "canDisable": group["canDisable"]}

    def _item_row(self, group: Dict[str, Any], item: Dict[str, Any]) -> Dict[str, Any]:
        key = row_key(item)
        row = {**ROW_DEFAULTS, **{k: item[k] for k in ROW_KEYS if k in item}}
        row.update(kind="item", rowKey=key, groupKey=group["key"], grouped=True, mixed=group["mixed"], detailOpen=key in self._open,
                   suggestion="" if group["shared"] else item["suggestion"],
                   canDisable=bool(item["rule"]) and not item["isSecret"])
        return row

    def _rows_of(self, group: Dict[str, Any]) -> List[Dict[str, Any]]:
        rows = [self._header_row(group)]
        if self._expanded(group):
            rows.extend(self._item_row(group, item) for item in group["items"])
        return rows

    @Slot()
    def rebuild(self) -> None:
        self.beginResetModel()
        self._forced = bool(self._source.filters_active)
        self._groups = build_groups(self._source.filtered_items)
        self._rows = [row for group in self._groups for row in self._rows_of(group)]
        self.endResetModel()
        self.summaryChanged.emit()

    # ── Etkileşim ──

    def _row_index(self, key: str) -> int:
        return next((i for i, row in enumerate(self._rows) if row["rowKey"] == key), -1)

    @Slot(str)
    def toggleGroup(self, key: str) -> None:
        group = next((g for g in self._groups if g["key"] == key), None)
        position = self._row_index("group:" + key)
        if group is None or position < 0 or self._forced:
            return
        expand = not self._expanded(group)
        self._overrides[key] = expand
        size = len(group["items"])
        if expand:
            self.beginInsertRows(QModelIndex(), position + 1, position + size)
            self._rows[position + 1:position + 1] = [self._item_row(group, item) for item in group["items"]]
            self.endInsertRows()
        else:
            self.beginRemoveRows(QModelIndex(), position + 1, position + size)
            del self._rows[position + 1:position + 1 + size]
            self.endRemoveRows()
        self._rows[position]["expanded"] = expand
        index = self.index(position, 0)
        self.dataChanged.emit(index, index, [self._role("expanded")])
        self.summaryChanged.emit()

    @Slot(bool)
    def setAllGroupsExpanded(self, expanded: bool) -> None:
        for group in self._groups:
            self._overrides[group["key"]] = expanded
        self.rebuild()

    @Slot(str)
    def toggleDetail(self, key: str) -> None:
        position = self._row_index(key)
        if position < 0 or self._rows[position]["kind"] != "item":
            return
        self._open.symmetric_difference_update({key})
        self._rows[position]["detailOpen"] = key in self._open
        index = self.index(position, 0)
        self.dataChanged.emit(index, index, [self._role("detailOpen")])
