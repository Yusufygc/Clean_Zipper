import logging
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import (
    QObject, QThread, Signal, Slot, Property,
    QAbstractListModel, QModelIndex, Qt, QByteArray
)
from src.qml_ui.viewmodels.findings_groups import FindingsRowsModel
from src.models.analysis_models import AnalysisResult, ProjectAnalysis
from src.services import audit_evidence as source_evidence
from src.services.project_service import ProjectService
from src.services.audit_catalog import RULE_EFFORT, DEFAULT_EFFORT, CATEGORY_NAMES, RULE_LABELS

logger = logging.getLogger(__name__)


_TURKISH_FOLD = str.maketrans("ıüöçşğ", "iuocsg")


def fold_turkish(text: str) -> str:
    """Arama için Türkçe duyarlı katlama: `İ`→`i`, `I`→`ı` (Python'un `lower()`'ı `İ`'yi `i̇` yapar, `I`'yı `i`),
    sonra aksan duyarsız (`ş→s`, `ı→i` ...): `ŞİFRE`, `Şifre`, `şifre` ve `sifre` aynı şeyi bulur."""
    return (text or "").replace("İ", "i").replace("I", "ı").lower().translate(_TURKISH_FOLD)


def is_sensitive_finding(finding: AnalysisResult) -> bool:
    """Sır sızıntısı içerebilecek bulguları tespit eder."""
    rule = finding.metadata.get("rule", "")
    if rule in ("hardcoded-secret", "provider-secret", "secret-in-history"):
        return True
    if finding.metadata.get("kind") == "sensitive_file":
        return True
    if finding.file_path:
        fname = finding.file_path.name.lower()
        if fname.startswith(".env") or fname.endswith((".pem", ".key")) or "id_rsa" in fname:
            return True
    return False


def get_finding_effort(finding: AnalysisResult) -> str:
    """Bulgunun tahmini düzeltme eforunu (S/M/L/XL) belirler."""
    rule = finding.metadata.get("rule", "")
    if rule in RULE_EFFORT:
        return RULE_EFFORT[rule]
    return DEFAULT_EFFORT.get(finding.severity, "M")


def finding_item(f: AnalysisResult, project: Path) -> Dict[str, Any]:
    """Bulguyu QML modelinin satırına çevirir. Sır içerebilecek bulguda satır ve ayrıntı maskelenir."""
    secret = is_sensitive_finding(f)
    description = ("Hassas sır bilgisi tespit edildi. Güvenlik nedeniyle kaynak satır maskelendi."
                   if secret else f.description)
    return {
        "title": f.title,
        "description": description,
        "severity": f.severity.name if hasattr(f.severity, "name") else str(f.severity),
        "category": f.category,
        "categoryName": CATEGORY_NAMES.get(f.category, f.category),
        "fileName": f.file_path.name if f.file_path else "Proje Geneli",
        "filePath": str(f.file_path) if f.file_path else "",
        "relPath": source_evidence.relative(project, f.file_path) if f.file_path else "",
        "line": 0 if secret else (source_evidence.line_of(f) or 0),
        "suggestion": f.recommendation or "",
        "rule": f.metadata.get("rule", ""),
        "ruleLabel": RULE_LABELS.get(f.metadata.get("rule", ""), f.metadata.get("rule", "")),
        "effort": get_finding_effort(f),
        "isSecret": secret,
        "approximate": bool(f.metadata.get("approximate", False)),
    }


def category_summary(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Kategori -> bulgu sayısı; en çok bulgusu olan başta."""
    counts: Dict[str, Dict[str, Any]] = {}
    for item in items:
        entry = counts.setdefault(item["category"], {"key": item["category"], "name": item["categoryName"], "count": 0})
        entry["count"] += 1
    return sorted(counts.values(), key=lambda e: (-e["count"], e["name"]))


class FindingsListModel(QAbstractListModel):
    """QML ListView için filtrelenebilir yüksek performanslı bulgu modeli."""

    TitleRole = Qt.UserRole + 1
    DescriptionRole = Qt.UserRole + 2
    SeverityRole = Qt.UserRole + 3
    CategoryRole = Qt.UserRole + 4
    CategoryNameRole = Qt.UserRole + 5
    FileNameRole = Qt.UserRole + 6
    FilePathRole = Qt.UserRole + 7
    LineRole = Qt.UserRole + 8
    SuggestionRole = Qt.UserRole + 9
    RuleRole = Qt.UserRole + 10
    EffortRole = Qt.UserRole + 11
    IsSecretRole = Qt.UserRole + 12
    ApproximateRole = Qt.UserRole + 13
    RelPathRole = Qt.UserRole + 14
    RuleLabelRole = Qt.UserRole + 15

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self._all_items: List[Dict[str, Any]] = []
        self._filtered_items: List[Dict[str, Any]] = []
        self._severity_filter = "ALL"
        self._category_filter = "ALL"
        self._search_query = ""

    def roleNames(self) -> Dict[int, QByteArray]:
        return {
            self.TitleRole: QByteArray(b"title"),
            self.DescriptionRole: QByteArray(b"description"),
            self.SeverityRole: QByteArray(b"severity"),
            self.CategoryRole: QByteArray(b"category"),
            self.CategoryNameRole: QByteArray(b"categoryName"),
            self.FileNameRole: QByteArray(b"fileName"),
            self.FilePathRole: QByteArray(b"filePath"),
            self.LineRole: QByteArray(b"line"),
            self.SuggestionRole: QByteArray(b"suggestion"),
            self.RuleRole: QByteArray(b"rule"),
            self.EffortRole: QByteArray(b"effort"),
            self.IsSecretRole: QByteArray(b"isSecret"),
            self.ApproximateRole: QByteArray(b"approximate"),
            self.RelPathRole: QByteArray(b"relPath"),
            self.RuleLabelRole: QByteArray(b"ruleLabel"),
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._filtered_items)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._filtered_items)):
            return None
        key = self._role_keys().get(role)
        return self._filtered_items[index.row()][key] if key else None

    @classmethod
    def _role_keys(cls) -> Dict[int, str]:
        """Rol numarası -> öğe sözlüğündeki anahtar."""
        return {cls.TitleRole: "title", cls.DescriptionRole: "description", cls.SeverityRole: "severity",
                cls.CategoryRole: "category", cls.CategoryNameRole: "categoryName", cls.FileNameRole: "fileName",
                cls.FilePathRole: "filePath", cls.LineRole: "line", cls.SuggestionRole: "suggestion",
                cls.RuleRole: "rule", cls.EffortRole: "effort", cls.IsSecretRole: "isSecret",
                cls.ApproximateRole: "approximate", cls.RelPathRole: "relPath",
                cls.RuleLabelRole: "ruleLabel"}

    @property
    def filtered_items(self) -> List[Dict[str, Any]]:
        """Süzgeçlerden geçen bulgular (gruplanmış görünüm modeli bunu kullanır)."""
        return self._filtered_items

    @property
    def filters_active(self) -> bool:
        return self._severity_filter != "ALL" or self._category_filter != "ALL" or bool(self._search_query)

    def set_items(self, items: List[Dict[str, Any]]):
        self._all_items = items
        self._apply_filter()

    def set_severity_filter(self, severity: str):
        self._severity_filter = (severity or "ALL").upper()
        self._apply_filter()

    def set_category_filter(self, category: str):
        self._category_filter = category or "ALL"
        self._apply_filter()

    def set_search_query(self, query: str):
        self._search_query = fold_turkish((query or "").strip())
        self._apply_filter()

    def _apply_filter(self):
        self.beginResetModel()
        filtered = []
        for it in self._all_items:
            # 1. Şiddet filtresi
            if self._severity_filter != "ALL" and it["severity"] != self._severity_filter:
                continue

            # 2. Kategori filtresi
            if self._category_filter != "ALL" and it["category"] != self._category_filter:
                continue

            # 3. Metin araması
            if self._search_query:
                haystack = fold_turkish(f"{it['title']} {it['description']} {it['fileName']} {it['rule']}")
                if self._search_query not in haystack:
                    continue

            filtered.append(it)

        self._filtered_items = filtered
        self.endResetModel()


class DiagnoseWorker(QThread):
    """Arka planda tam teşhis ve tüm bulguları toplayan iş parçacığı."""

    progress = Signal(int, str)
    finished = Signal(object)
    error = Signal(str)

    def __init__(self, service: ProjectService, project_path: Path):
        super().__init__()
        self.service = service
        self.project_path = project_path

    def run(self):
        try:
            # Dashboard'un aynı anda başlattığı taramayla birleşir (tek teşhis, ortak sonuç).
            analysis = self.service.diagnose(progress=self.progress.emit, refresh=True)
            self.finished.emit(analysis)
        except Exception as e:
            logger.error("DiagnoseWorker çalışırken hata: %s", e, exc_info=True)
            self.error.emit(str(e))


class FindingsViewModel(QObject):
    """QML Sorunlar & Bulgular Gezgini köprüsü."""

    diagnosisStarted = Signal()
    diagnosingChanged = Signal()                  # `isDiagnosing` değişince (başlangıç, bitiş, hata)
    diagnosisProgress = Signal(int, str)
    diagnosisFinished = Signal()
    diagnosisError = Signal(str)
    countsChanged = Signal()
    filterChanged = Signal()
    categoriesChanged = Signal()

    def __init__(self, project_service: ProjectService, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.service = project_service
        self._worker: Optional[DiagnoseWorker] = None
        self._model = FindingsListModel(self)
        self._rows = FindingsRowsModel(self._model, self)

        self._is_diagnosing = False
        self._progress_pct = 0
        self._progress_text = "Hazır"

        self._total_count = 0
        self._critical_count = 0
        self._high_count = 0
        self._medium_count = 0
        self._low_count = 0
        self._info_count = 0

        self._selected_severity = "ALL"
        self._selected_category = "ALL"
        self._categories: List[Dict[str, Any]] = []

    # ── Properties ──

    @Property(QObject, constant=True)
    def model(self) -> FindingsListModel:
        return self._model

    @Property(QObject, constant=True)
    def rows(self) -> FindingsRowsModel:
        """Listenin görünüm modeli: kurala göre gruplanmış başlık ve bulgu satırları."""
        return self._rows

    @Property(bool, notify=diagnosingChanged)
    def isDiagnosing(self) -> bool:
        return self._is_diagnosing

    @Property(int, notify=diagnosisProgress)
    def progressPercent(self) -> int:
        return self._progress_pct

    @Property(str, notify=diagnosisProgress)
    def progressText(self) -> str:
        return self._progress_text

    @Property(int, notify=countsChanged)
    def totalCount(self) -> int:
        return self._total_count

    @Property(int, notify=countsChanged)
    def criticalCount(self) -> int:
        return self._critical_count

    @Property(int, notify=countsChanged)
    def highCount(self) -> int:
        return self._high_count

    @Property(int, notify=countsChanged)
    def mediumCount(self) -> int:
        return self._medium_count

    @Property(int, notify=countsChanged)
    def lowCount(self) -> int:
        return self._low_count

    @Property(int, notify=countsChanged)
    def infoCount(self) -> int:
        return self._info_count

    @Property(str, notify=filterChanged)
    def selectedSeverity(self) -> str:
        return self._selected_severity

    @Property(str, notify=filterChanged)
    def selectedCategory(self) -> str:
        return self._selected_category

    @Property("QVariantList", notify=categoriesChanged)
    def categories(self) -> List[Dict[str, Any]]:
        """Bulguların bulunduğu kategoriler ve sayıları (en çok bulgusu olandan başlayarak)."""
        return self._categories

    # ── Slots ──

    @Slot()
    def startDeepDiagnosis(self):
        """doctor.diagnose() ile tüm 5 şiddet seviyesinde derin teşhis başlatır."""
        if self._is_diagnosing:
            return
        if not self.service._current_project:
            self.diagnosisError.emit("Derin analiz için önce bir proje seçilmelidir.")
            return

        self._is_diagnosing = True
        self._progress_pct = 5
        self._progress_text = "Derin teşhis başlatılıyor..."
        self.diagnosingChanged.emit()
        self.diagnosisStarted.emit()
        self.diagnosisProgress.emit(self._progress_pct, self._progress_text)

        self._worker = DiagnoseWorker(self.service, self.service._current_project)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, pct: int, text: str):
        self._progress_pct = pct
        self._progress_text = text
        self.diagnosisProgress.emit(pct, text)

    def _on_finished(self, analysis: ProjectAnalysis):
        self._is_diagnosing = False
        self._populate_findings(analysis.all_findings, analysis.project_path)
        self._progress_pct = 100
        self._progress_text = "Derin teşhis tamamlandı"
        self.diagnosingChanged.emit()
        self.diagnosisProgress.emit(100, self._progress_text)
        self.diagnosisFinished.emit()

    def _on_error(self, err_msg: str):
        self._is_diagnosing = False
        self._progress_text = f"Hata: {err_msg}"
        self.diagnosingChanged.emit()
        self.diagnosisProgress.emit(0, self._progress_text)
        self.diagnosisError.emit(err_msg)

    def _populate_findings(self, findings: List[AnalysisResult], project: Path):
        """Bulguları dönüştürür ve modele yükler."""
        items = [finding_item(f, project) for f in findings]
        counts = Counter(item["severity"] for item in items)
        self._total_count = len(items)
        self._critical_count = counts["CRITICAL"]
        self._high_count = counts["HIGH"]
        self._medium_count = counts["MEDIUM"]
        self._low_count = counts["LOW"]
        self._info_count = counts["INFO"]
        self.countsChanged.emit()

        self._categories = category_summary(items)
        self.categoriesChanged.emit()

        self._model.set_items(items)

    @Slot(str)
    def setSeverityFilter(self, severity: str):
        self._selected_severity = severity
        self._model.set_severity_filter(severity)
        self.filterChanged.emit()

    @Slot(str)
    def setCategoryFilter(self, category: str):
        self._selected_category = category
        self._model.set_category_filter(category)
        self.filterChanged.emit()

    @Slot(str)
    def setSearchQuery(self, query: str):
        self._model.set_search_query(query)
        self.filterChanged.emit()

    @Slot(str, int, bool, result=str)
    def evidenceFor(self, file_path: str, line: int, is_secret: bool) -> str:
        """Bulgunun kaynak satırları (tembel: kart açılınca okunur). Sır içerebilecek bulgularda her zaman boş döner."""
        if is_secret or not file_path or line < 1:
            return ""
        path = Path(file_path)
        if not path.is_absolute():
            return ""
        return source_evidence.snippet(path, line) or ""
