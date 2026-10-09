import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, QThread, Signal, Slot, Property
from src.services.project_service import ProjectService

logger = logging.getLogger(__name__)

# İşlem çalışmadan önce de `lastResult` bu anahtarları taşır; QML bağlamaları `undefined` görmesin.
EMPTY_RESULT: Dict[str, Any] = {
    "success": False, "complete": False, "mode": "", "error": "", "outputPath": "", "totalFiles": 0,
    "addedFiles": 0, "skippedFiles": 0, "failedFilesCount": 0, "failedFiles": [], "backupSizeMb": 0.0,
    "excludedDirsCount": 0,
}


class ArchiveWorker(QThread):
    """Arşivleme, kopyalama veya yedekleme işlemini yürüten iş parçacığı."""

    progress = Signal(int, str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, service: ProjectService, mode: str, target: Path,
                 profile_name: str = "", backup_name: str = ""):
        super().__init__()
        self.service = service
        self.mode = mode
        self.target = target
        self.profile_name = profile_name
        self.backup_name = backup_name

    def run(self):
        try:
            project_path = self.service._current_project
            if not project_path:
                self.error.emit("İşlem için proje seçilmedi.")
                return

            def on_progress(done: int, total: int):
                pct = int((done / total) * 100) if total else 0
                self.progress.emit(pct, f"{done} / {total} dosya işlendi")

            if self.mode == "zip":
                result = self.service.archive_service.create_zip(
                    project_path, self.target, profile_name=self.profile_name,
                    progress_callback=on_progress
                )
                result["output_path"] = str(self.target)
                result["mode"] = "zip"
            elif self.mode == "copy":
                result = self.service.archive_service.copy_project(
                    project_path, self.target, profile_name=self.profile_name,
                    progress_callback=on_progress
                )
                result["output_path"] = str(self.target)
                result["mode"] = "copy"
            elif self.mode == "backup":
                self.progress.emit(20, "Yeniden üretilebilir klasörler ayıklanıyor...")
                result = self.service.create_backup(self.backup_name or None)
                result["mode"] = "backup"
            else:
                self.error.emit(f"Bilinmeyen işlem modu: {self.mode}")
                return

            self.finished.emit(result)
        except Exception as e:
            logger.error("ArchiveWorker çalışırken hata: %s", e, exc_info=True)
            self.error.emit(str(e))


class ArchiveViewModel(QObject):
    """QML Arşivleme, Temiz Kopya ve Yedekleme köprüsü."""

    processStarted = Signal()
    processProgress = Signal(int, str)
    processFinished = Signal()
    processError = Signal(str)
    stateChanged = Signal()
    profilesChanged = Signal()

    def __init__(self, project_service: ProjectService, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.service = project_service
        self._worker: Optional[ArchiveWorker] = None

        self._is_processing = False
        self._progress_percent = 0
        self._progress_text = "Hazır"

        profs_keys = list(self.service.archive_service.PROFILES.keys())
        self._selected_profile = profs_keys[0] if profs_keys else ""
        self._last_result: Dict[str, Any] = dict(EMPTY_RESULT)
        self._has_result = False
        self._backup_list: List[Dict[str, Any]] = []

        self._load_profiles()
        self.refreshBackupList()

    def _load_profiles(self):
        """Profil listesini ArchiveService'den okur."""
        try:
            profs = []
            for name, data in self.service.archive_service.PROFILES.items():
                profs.append({
                    "name": name,
                    "description": data.get("description", ""),
                    "patterns": data.get("excludes", [])
                })
            self._profiles = profs
            if profs and not self._selected_profile:
                self._selected_profile = profs[0]["name"]
            self.profilesChanged.emit()
        except Exception as e:
            logger.error("Profiller yüklenirken hata: %s", e, exc_info=True)

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

    @Property("QVariantList", notify=profilesChanged)
    def profiles(self) -> List[Dict[str, Any]]:
        return self._profiles

    @Property(str, notify=stateChanged)
    def selectedProfile(self) -> str:
        return self._selected_profile

    @Property("QVariantMap", notify=stateChanged)
    def lastResult(self) -> Dict[str, Any]:
        return self._last_result

    @Property(bool, notify=stateChanged)
    def hasResult(self) -> bool:
        """Henüz hiçbir işlem çalışmadıysa False: arayüz boş sonuç kartı göstermesin."""
        return self._has_result

    @Property("QVariantList", notify=stateChanged)
    def backupList(self) -> List[Dict[str, Any]]:
        return self._backup_list

    # ── Slots ──

    @Slot(str)
    def selectProfile(self, name: str):
        self._selected_profile = name
        self.stateChanged.emit()

    @Slot(str)
    def startZipArchive(self, target_path_str: str):
        """Zip arşivi oluşturmayı başlatır."""
        if self._is_processing:
            return
        if not self.service._current_project:
            self.processError.emit("Arşivleme için önce bir proje seçilmelidir.")
            return

        if target_path_str.startswith("file:///"):
            target_path_str = target_path_str[8:]
        target = Path(target_path_str).resolve()

        self._start_worker(mode="zip", target=target, profile_name=self._selected_profile)

    @Slot(str)
    def startCleanCopy(self, target_dir_str: str):
        """Temiz klasör kopyası oluşturmayı başlatır."""
        if self._is_processing:
            return
        if not self.service._current_project:
            self.processError.emit("Kopya için önce bir proje seçilmelidir.")
            return

        if target_dir_str.startswith("file:///"):
            target_dir_str = target_dir_str[8:]
        target = Path(target_dir_str).resolve()

        self._start_worker(mode="copy", target=target, profile_name=self._selected_profile)

    @Slot(str)
    def startBackup(self, custom_name: str = ""):
        """~/.gitclean_backups dizinine hızlı yedek alır."""
        if self._is_processing:
            return
        if not self.service._current_project:
            self.processError.emit("Yedekleme için önce bir proje seçilmelidir.")
            return

        self._start_worker(mode="backup", target=Path(), backup_name=custom_name)

    def _start_worker(self, mode: str, target: Path, profile_name: str = "", backup_name: str = ""):
        self._is_processing = True
        self._progress_percent = 5
        self._progress_text = "İşlem başlatılıyor..."
        self.processStarted.emit()
        self.processProgress.emit(self._progress_percent, self._progress_text)
        self.stateChanged.emit()

        self._worker = ArchiveWorker(
            self.service, mode=mode, target=target,
            profile_name=profile_name, backup_name=backup_name
        )
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
        self._progress_text = "İşlem tamamlandı"

        # QML için sonuç haritasını düzenle
        formatted = {
            "success": bool(result.get("success", False)),
            "complete": bool(result.get("complete", False)),
            "mode": result.get("mode", "zip"),
            "error": str(result.get("error") or ""),
            "outputPath": str(result.get("output_path") or result.get("backup_name") or ""),
            "totalFiles": int(result.get("total_files", 0)),
            "addedFiles": int(result.get("added_files", result.get("copied_files", 0))),
            "skippedFiles": int(result.get("skipped_files", 0)),
            "failedFilesCount": len(result.get("failed_files", [])),
            "failedFiles": [f"{p}: {e}" for p, e in result.get("failed_files", [])[:20]],
            "backupSizeMb": round(result.get("size", 0) / (1024 * 1024), 2),
            "excludedDirsCount": int(result.get("excluded_dir_count", 0)),
        }
        self._last_result = formatted
        self._has_result = True
        self.refreshBackupList()

        self.processProgress.emit(100, self._progress_text)
        self.stateChanged.emit()
        self.processFinished.emit()

    def _on_error(self, err_msg: str):
        self._is_processing = False
        self._progress_text = f"Hata: {err_msg}"
        self.processProgress.emit(0, self._progress_text)
        self.stateChanged.emit()
        self.processError.emit(err_msg)

    @Slot()
    def refreshBackupList(self):
        """Mevcut yedekleri listeler."""
        try:
            backup_root = Path.home() / ".gitclean_backups"
            items = []
            if backup_root.exists():
                for p in sorted(backup_root.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
                    if p.is_dir():
                        zip_file = p / f"{p.name}.zip"
                        size_mb = round(zip_file.stat().st_size / (1024 * 1024), 2) if zip_file.exists() else 0.0
                        items.append({
                            "name": p.name,
                            "path": str(zip_file if zip_file.exists() else p),
                            "sizeMb": size_mb,
                        })
            self._backup_list = items[:10]
            self.stateChanged.emit()
        except Exception as e:
            logger.error("Yedekler listelenirken hata: %s", e, exc_info=True)
