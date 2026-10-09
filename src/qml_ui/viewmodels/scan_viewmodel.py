import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, QThread, Signal, Slot, Property
from src.languages import default_languages
from src.services.audit_catalog import SKIP_REASONS
from src.services.project_service import ProjectService
from src.qml_ui.viewmodels.paths import local_path

logger = logging.getLogger(__name__)


class ScanWorker(QThread):
    """Proje analizini arka planda yürüten iş parçacığı."""

    progress = Signal(int, str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, service: ProjectService):
        super().__init__()
        self.service = service

    def run(self):
        try:
            result = self.service.analyze_project(progress=self.progress.emit)
            self.finished.emit(result)
        except Exception as e:
            logger.error("ScanWorker analizi sırasında hata: %s", e, exc_info=True)
            self.error.emit(str(e))


class ScanViewModel(QObject):
    """QML Gösterge Paneli ve Sağlık Analizi köprüsü."""

    scanStarted = Signal()
    scanProgress = Signal(int, str)
    scanFinished = Signal()
    scanError = Signal(str)
    dataChanged = Signal()

    def __init__(self, project_service: ProjectService, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.service = project_service
        self._worker: Optional[ScanWorker] = None

        self._is_scanning = False
        self._progress_percent = 0
        self._progress_text = "Hazır"

        # Analiz sonuç verileri
        self._health_score = 0
        self._health_status = "—"
        self._total_files = 0
        self._total_size_mb = 0.0
        self._total_dirs = 0
        self._issues_count = 0
        self._potential_savings_mb = 0.0
        self._category_scores: Dict[str, int] = {}
        self._file_type_dist: Dict[str, int] = {}
        self._language_stats: Dict[str, Dict] = {}
        self._top_recommendations: List[Dict] = []
        self._failed_analyzers: List[str] = []
        self._skipped_files: Dict[str, int] = {}
        self._gitignore_applied = True
        self._ignored_by_gitignore = 0

    # ── Properties ──

    @Property(bool, notify=dataChanged)
    def isScanning(self) -> bool:
        return self._is_scanning

    @Property(int, notify=scanProgress)
    def progressPercent(self) -> int:
        return self._progress_percent

    @Property(str, notify=scanProgress)
    def progressText(self) -> str:
        return self._progress_text

    @Property(int, notify=dataChanged)
    def healthScore(self) -> int:
        return self._health_score

    @Property(str, notify=dataChanged)
    def healthStatus(self) -> str:
        return self._health_status

    @Property(int, notify=dataChanged)
    def totalFiles(self) -> int:
        return self._total_files

    @Property(float, notify=dataChanged)
    def totalSizeMb(self) -> float:
        return self._total_size_mb

    @Property(int, notify=dataChanged)
    def totalDirs(self) -> int:
        return self._total_dirs

    @Property(int, notify=dataChanged)
    def issuesCount(self) -> int:
        return self._issues_count

    @Property(float, notify=dataChanged)
    def potentialSavingsMb(self) -> float:
        return self._potential_savings_mb

    @Property("QVariantMap", notify=dataChanged)
    def categoryScores(self) -> Dict[str, int]:
        return self._category_scores

    @Property("QVariantMap", notify=dataChanged)
    def fileTypeDistribution(self) -> Dict[str, int]:
        return self._file_type_dist

    @Property("QVariantMap", notify=dataChanged)
    def languageLines(self) -> Dict[str, int]:
        """Dil -> kod satırı sayısı (dil dağılımı kartı için)."""
        return {self._language_name(lang): int(stats.get("code_lines", 0)) for lang, stats in self._language_stats.items()
                if int(stats.get("code_lines", 0)) > 0}

    @staticmethod
    def _language_name(language_id: str) -> str:
        spec = default_languages.get(language_id)
        return spec.display_name if spec else language_id

    @Property("QVariantList", notify=dataChanged)
    def skippedDetail(self) -> List[Dict[str, Any]]:
        """Analize girmeyen dosyaların neden -> sayı dökümü (okunur etiketlerle)."""
        return [{"reason": reason, "label": SKIP_REASONS.get(reason, reason), "count": int(count)}
                for reason, count in sorted(self._skipped_files.items(), key=lambda item: -item[1])]

    @Property("QVariantList", notify=dataChanged)
    def topRecommendations(self) -> List[Dict]:
        return self._top_recommendations

    @Property("QVariantList", notify=dataChanged)
    def failedAnalyzers(self) -> List[str]:
        return self._failed_analyzers

    @Property("QVariantMap", notify=dataChanged)
    def skippedFiles(self) -> Dict[str, int]:
        return self._skipped_files

    @Property(bool, notify=dataChanged)
    def gitignoreApplied(self) -> bool:
        return self._gitignore_applied

    @Property(int, notify=dataChanged)
    def ignoredByGitignore(self) -> int:
        return self._ignored_by_gitignore

    # ── Slots ──

    @Slot()
    def startQuickScan(self):
        """Asenkron hızlı analizi başlatır."""
        if self._is_scanning:
            return
        if not self.service._current_project:
            self.scanError.emit("Analiz için önce bir proje seçilmelidir.")
            return

        self._is_scanning = True
        self._progress_percent = 5
        self._progress_text = "Analiz başlatılıyor..."
        self.scanStarted.emit()
        self.scanProgress.emit(self._progress_percent, self._progress_text)
        self.dataChanged.emit()

        self._worker = ScanWorker(self.service)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, pct: int, text: str):
        self._progress_percent = pct
        self._progress_text = text
        self.scanProgress.emit(pct, text)

    def _on_finished(self, data: Dict[str, Any]):
        self._is_scanning = False
        self._health_score = int(data.get("health_score", 0))
        self._health_status = str(data.get("health_status", "—"))
        self._total_files = int(data.get("total_files", 0))
        self._total_size_mb = float(data.get("total_size_mb", 0.0))
        self._total_dirs = int(data.get("total_dirs", 0))
        self._issues_count = int(data.get("issues_count", 0))
        self._potential_savings_mb = float(data.get("potential_savings_mb", 0.0))
        self._category_scores = dict(data.get("category_scores", {}))
        self._file_type_dist = dict(data.get("file_type_distribution", {}))
        self._language_stats = dict(data.get("language_stats", {}))
        
        # Recommendations formatı: (title, desc, priority) -> dict
        raw_recs = data.get("top_recommendations", [])
        formatted_recs = []
        for item in raw_recs:
            if isinstance(item, (list, tuple)) and len(item) >= 3:
                formatted_recs.append({
                    "title": str(item[0]),
                    "description": str(item[1]),
                    "priority": str(item[2])
                })
        self._top_recommendations = formatted_recs

        self._failed_analyzers = list(data.get("failed_analyzers", []))
        self._skipped_files = dict(data.get("skipped_files", {}))
        self._gitignore_applied = bool(data.get("gitignore_applied", True))
        ignored = data.get("ignored_by_gitignore", 0)
        # servis {'files': n, 'dirs': m} sözlüğü döner; arayüz tek sayı gösterir
        self._ignored_by_gitignore = (sum(int(v) for v in ignored.values()) if isinstance(ignored, dict)
                                      else int(ignored or 0))

        self._progress_percent = 100
        self._progress_text = "Analiz tamamlandı"
        self.scanProgress.emit(100, self._progress_text)
        self.dataChanged.emit()
        self.scanFinished.emit()

    def _on_error(self, err_msg: str):
        self._is_scanning = False
        self._progress_text = f"Hata: {err_msg}"
        self.scanProgress.emit(0, self._progress_text)
        self.dataChanged.emit()
        self.scanError.emit(err_msg)

    @Slot(str, result=bool)
    def exportHtmlReport(self, file_path_str: str) -> bool:
        """HTML sağlık analiz raporunu kaydeder."""
        try:
            target = Path(local_path(file_path_str)).resolve()
            return self.service.export_project_report(target)
        except Exception as e:
            logger.error("HTML rapor kaydedilemedi: %s", e, exc_info=True)
            self.scanError.emit(f"Rapor yazma hatası: {e}")
            return False

    @Slot(str, result=bool)
    def exportAuditReport(self, file_path_str: str) -> bool:
        """Markdown V2 denetim raporunu kaydeder."""
        try:
            target = Path(local_path(file_path_str)).resolve()
            return self.service.export_audit_report(target)
        except Exception as e:
            logger.error("Markdown denetim raporu kaydedilemedi: %s", e, exc_info=True)
            self.scanError.emit(f"Denetim raporu yazma hatası: {e}")
            return False
