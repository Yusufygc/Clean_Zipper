import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import (
    QObject, QThread, Signal, Slot, Property,
    QAbstractListModel, QModelIndex, Qt, QByteArray
)
from src.models.analysis_models import AnalysisResult, ProjectAnalysis, Severity
from src.services.project_service import ProjectService
from src.services.audit_catalog import RULE_EFFORT, DEFAULT_EFFORT, CATEGORY_NAMES

logger = logging.getLogger(__name__)


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
        }

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._filtered_items)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self._filtered_items)):
            return None
        item = self._filtered_items[index.row()]
        if role == self.TitleRole:
            return item["title"]
        elif role == self.DescriptionRole:
            return item["description"]
        elif role == self.SeverityRole:
            return item["severity"]
        elif role == self.CategoryRole:
            return item["category"]
        elif role == self.CategoryNameRole:
            return item["categoryName"]
        elif role == self.FileNameRole:
            return item["fileName"]
        elif role == self.FilePathRole:
            return item["filePath"]
        elif role == self.LineRole:
            return item["line"]
        elif role == self.SuggestionRole:
            return item["suggestion"]
        elif role == self.RuleRole:
            return item["rule"]
        elif role == self.EffortRole:
            return item["effort"]
        elif role == self.IsSecretRole:
            return item["isSecret"]
        elif role == self.ApproximateRole:
            return item["approximate"]
        return None

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
        self._search_query = (query or "").strip().lower()
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
                haystack = f"{it['title']} {it['description']} {it['fileName']} {it['rule']}".lower()
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
            analysis = self.service.doctor.diagnose(self.project_path, progress=self.progress.emit)
            self.finished.emit(analysis)
        except Exception as e:
            logger.error("DiagnoseWorker çalışırken hata: %s", e, exc_info=True)
            self.error.emit(str(e))


class FindingsViewModel(QObject):
    """QML Sorunlar & Bulgular Gezgini köprüsü."""

    diagnosisStarted = Signal()
    diagnosisProgress = Signal(int, str)
    diagnosisFinished = Signal()
    diagnosisError = Signal(str)
    countsChanged = Signal()
    filterChanged = Signal()

    def __init__(self, project_service: ProjectService, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.service = project_service
        self._worker: Optional[DiagnoseWorker] = None
        self._model = FindingsListModel(self)

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
        self._search_query = ""

    # ── Properties ──

    @Property(QObject, constant=True)
    def model(self) -> FindingsListModel:
        return self._model

    @Property(bool, notify=diagnosisStarted)
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

    @Property(str, notify=filterChanged)
    def searchQuery(self) -> str:
        return self._search_query

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
        self._populate_findings(analysis.all_findings)
        self._progress_pct = 100
        self._progress_text = "Derin teşhis tamamlandı"
        self.diagnosisProgress.emit(100, self._progress_text)
        self.diagnosisFinished.emit()

    def _on_error(self, err_msg: str):
        self._is_diagnosing = False
        self._progress_text = f"Hata: {err_msg}"
        self.diagnosisProgress.emit(0, self._progress_text)
        self.diagnosisError.emit(err_msg)

    def _populate_findings(self, findings: List[AnalysisResult]):
        """Bulguları dönüştürür ve modele yükler."""
        items = []
        c_crit = c_high = c_med = c_low = c_info = 0

        for f in findings:
            sev_name = f.severity.name if hasattr(f.severity, "name") else str(f.severity)
            if sev_name == "CRITICAL": c_crit += 1
            elif sev_name == "HIGH": c_high += 1
            elif sev_name == "MEDIUM": c_med += 1
            elif sev_name == "LOW": c_low += 1
            elif sev_name == "INFO": c_info += 1

            secret = is_sensitive_finding(f)
            effort = get_finding_effort(f)
            cat_name = CATEGORY_NAMES.get(f.category, f.category)

            # Sır ise satır ve yol bilgilerini maskele
            file_name = f.file_path.name if f.file_path else "Proje Geneli"
            file_path_str = str(f.file_path) if f.file_path else ""
            line_num = 0 if secret else (f.metadata.get("line") or 0)
            desc = "Hassas sır bilgisi tespit edildi. Güvenlik nedeniyle kaynak satır maskelendi." if secret else f.description

            items.append({
                "title": f.title,
                "description": desc,
                "severity": sev_name,
                "category": f.category,
                "categoryName": cat_name,
                "fileName": file_name,
                "filePath": file_path_str,
                "line": line_num,
                "suggestion": f.recommendation or "",
                "rule": f.metadata.get("rule", ""),
                "effort": effort,
                "isSecret": secret,
                "approximate": bool(f.metadata.get("approximate", False))
            })

        self._total_count = len(items)
        self._critical_count = c_crit
        self._high_count = c_high
        self._medium_count = c_med
        self._low_count = c_low
        self._info_count = c_info
        self.countsChanged.emit()

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
        self._search_query = query
        self._model.set_search_query(query)
        self.filterChanged.emit()
