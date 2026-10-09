import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, QThread, Signal, Slot, Property
from src.services.project_service import ProjectService
from src.services.cleanup_service import CleanupService

logger = logging.getLogger(__name__)

# Önizleme satırındaki kategori rozeti için kısa Türkçe adlar
CATEGORY_NAMES = {"python_cache": "Python önbelleği", "temp_files": "Geçici dosya", "logs": "Log", "backups": "Yedek"}


class CleanupWorker(QThread):
    """Önizleme veya temizlik işlemini yürüten arka plan iş parçacığı."""

    progress = Signal(int, str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, service: ProjectService, categories: List[str], is_preview: bool):
        super().__init__()
        self.service = service
        self.categories = categories
        self.is_preview = is_preview

    def run(self):
        try:
            project_path = self.service._current_project
            if not project_path:
                self.error.emit("Temizlik için proje seçilmedi.")
                return

            if self.is_preview:
                self.progress.emit(30, "Geçici dosyalar taranıyor...")
                result = self.service.cleanup_service.preview_cleanup(project_path, categories=self.categories)
                result["action"] = "preview"
            else:
                self.progress.emit(30, "Geri Dönüşüm Kutusu'na taşınıyor...")
                result = self.service.cleanup_service.cleanup(project_path, categories=self.categories, dry_run=False)
                result["action"] = "cleanup"

            self.finished.emit(result)
        except Exception as e:
            logger.error("CleanupWorker çalışırken hata: %s", e, exc_info=True)
            self.error.emit(str(e))


class CleanupViewModel(QObject):
    """QML Proje Temizliği köprüsü."""

    processStarted = Signal()
    processProgress = Signal(int, str)
    processFinished = Signal()
    processError = Signal(str)
    stateChanged = Signal()

    def __init__(self, project_service: ProjectService, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.service = project_service
        self._worker: Optional[CleanupWorker] = None

        self._is_processing = False
        self._progress_percent = 0
        self._progress_text = "Hazır"

        # Kategori seçim durumları
        self._cats = {
            "python_cache": True,
            "temp_files": True,
            "logs": False,
            "backups": False,
        }

        # Önizleme sonuçları
        self._preview_count = 0
        self._preview_size_mb = 0.0
        self._preview_files: List[Dict[str, Any]] = []

        # Son temizlik sonucu
        self._last_result: Dict[str, Any] = {}

    def _selected_categories(self) -> List[str]:
        return [k for k, v in self._cats.items() if v]

    # ── Properties ──

    @Property(bool, notify=stateChanged)
    def isProcessing(self) -> bool:
        return self._is_processing

    @Property(int, notify=processProgress)
    def progressPercent(self) -> int:
        return self._progress_percent

    @Property(str, notify=processProgress)
    def progressText(self) -> str:
        return self._progress_text

    @Property(bool, notify=stateChanged)
    def categoryPythonCache(self) -> bool:
        return self._cats["python_cache"]

    @Property(bool, notify=stateChanged)
    def categoryTempFiles(self) -> bool:
        return self._cats["temp_files"]

    @Property(bool, notify=stateChanged)
    def categoryLogs(self) -> bool:
        return self._cats["logs"]

    @Property(bool, notify=stateChanged)
    def categoryBackups(self) -> bool:
        return self._cats["backups"]

    @Property(int, notify=stateChanged)
    def previewCount(self) -> int:
        return self._preview_count

    @Property(float, notify=stateChanged)
    def previewSizeMb(self) -> float:
        return self._preview_size_mb

    @Property("QVariantList", notify=stateChanged)
    def previewFiles(self) -> List[Dict[str, Any]]:
        return self._preview_files

    @Property("QVariantMap", notify=stateChanged)
    def lastResult(self) -> Dict[str, Any]:
        return self._last_result

    # ── Slots ──

    @Slot(str, bool)
    def setCategory(self, name: str, enabled: bool):
        if name in self._cats:
            self._cats[name] = enabled
            self.stateChanged.emit()

    @Slot()
    def startPreview(self):
        """Dry-run önizleme taramasını başlatır."""
        if self._is_processing:
            return
        if not self.service._current_project:
            self.processError.emit("Önizleme için önce bir proje seçilmelidir.")
            return

        cats = self._selected_categories()
        if not cats:
            self.processError.emit("En az bir temizlik kategorisi seçilmelidir.")
            return

        self._start_worker(is_preview=True, categories=cats)

    @Slot()
    def startCleanup(self):
        """Geri Dönüşüm Kutusu'na taşımayı başlatır."""
        if self._is_processing:
            return
        if not self.service._current_project:
            self.processError.emit("Temizlik için önce bir proje seçilmelidir.")
            return

        cats = self._selected_categories()
        if not cats:
            self.processError.emit("En az bir temizlik kategorisi seçilmelidir.")
            return

        self._start_worker(is_preview=False, categories=cats)

    def _start_worker(self, is_preview: bool, categories: List[str]):
        self._is_processing = True
        self._progress_percent = 10
        self._progress_text = "Taranıyor..." if is_preview else "Temizlik yürütülüyor..."
        self.processStarted.emit()
        self.processProgress.emit(self._progress_percent, self._progress_text)
        self.stateChanged.emit()

        self._worker = CleanupWorker(self.service, categories=categories, is_preview=is_preview)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_progress(self, pct: int, text: str):
        self._progress_percent = pct
        self._progress_text = text
        self.processProgress.emit(pct, text)

    def _on_finished(self, result: Dict[str, Any]):
        self._is_processing = False
        self._progress_percent = 100
        self._progress_text = "Tamamlandı"

        action = result.get("action", "preview")
        if action == "preview":
            self._preview_count = int(result.get("total_files", 0))
            self._preview_size_mb = round(result.get("total_size", 0) / (1024 * 1024), 2)
            raw_files = result.get("files", [])
            formatted = []
            for item in raw_files[:100]:
                p = Path(item["path"])
                formatted.append({
                    "name": p.name,
                    "path": str(p),
                    "sizeKb": round(item["size"] / 1024, 1),
                    "category": item["category"],
                    "categoryName": CATEGORY_NAMES.get(item["category"], item["category"]),
                    "isDir": bool(item.get("is_dir", False))
                })
            self._preview_files = formatted
            self._last_result = {}
        else: # cleanup
            cleaned_mb = round(result.get("cleaned_size", 0) / (1024 * 1024), 2)
            failed_list = [f"{p}: {e}" for p, e in result.get("failed", [])]
            self._last_result = {
                "success": bool(result.get("success", True)),
                "cleanedFiles": int(result.get("cleaned_files", 0)),
                "cleanedSizeMb": cleaned_mb,
                "failedCount": len(failed_list),
                "failedList": failed_list,
            }
            # Temizlik bitince önizlemeyi sıfırla
            self._preview_count = 0
            self._preview_size_mb = 0.0
            self._preview_files = []

        self.processProgress.emit(100, self._progress_text)
        self.stateChanged.emit()
        self.processFinished.emit()

    def _on_error(self, err_msg: str):
        self._is_processing = False
        self._progress_text = f"Hata: {err_msg}"
        self.processProgress.emit(0, self._progress_text)
        self.stateChanged.emit()
        self.processError.emit(err_msg)
