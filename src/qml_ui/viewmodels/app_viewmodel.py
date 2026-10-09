import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

from PySide6.QtCore import QObject, QUrl, Signal, Slot, Property
from PySide6.QtGui import QDesktopServices
from src.services.project_service import ProjectService


class AppViewModel(QObject):
    """QML ile ana uygulama yaşam döngüsü ve proje durumu arasındaki MVVM köprüsü.
    
    İş mantığı barındırmaz; ProjectService'i yönetir ve QML arayüzüne
    reaktif özellikler ve sinyaller sunar.
    """

    projectChanged = Signal()
    statusChanged = Signal(str)

    def __init__(self, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.service = ProjectService()
        self._current_path = ""
        self._current_name = ""
        self._status_text = "Hazır"

    # ── Properties ──

    @Property(str, notify=projectChanged)
    def projectPath(self) -> str:
        return self._current_path

    @Property(str, notify=projectChanged)
    def projectName(self) -> str:
        return self._current_name

    @Property(bool, notify=projectChanged)
    def hasProject(self) -> bool:
        return bool(self._current_path and Path(self._current_path).exists())

    @Property(str, notify=statusChanged)
    def statusText(self) -> str:
        return self._status_text

    # ── Slots ──

    @Slot(str)
    def setProjectPath(self, path_str: str) -> bool:
        """Dışarıdan veya dosya seçim penceresinden gelen yolu doğrular ve servise yükler."""
        if not path_str:
            return False

        # QML fileUrl ("file:///C:/...") temizleme
        if path_str.startswith("file:///"):
            path_str = path_str[8:]
        elif path_str.startswith("file://"):
            path_str = path_str[7:]

        clean_path = Path(path_str).resolve()
        if not clean_path.exists() or not clean_path.is_dir():
            self.setStatus(f"Hata: geçersiz proje dizini: {path_str}")
            return False

        try:
            self.service.set_project(clean_path)
            self._current_path = str(clean_path)
            self._current_name = clean_path.name
            self._status_text = f"Proje açıldı: {self._current_name}"
            self.projectChanged.emit()
            self.statusChanged.emit(self._status_text)
            return True
        except Exception as e:
            logger.error("Proje yüklenirken hata: %s", e, exc_info=True)
            self.setStatus(f"Hata: proje yüklenemedi: {e}")
            return False

    @Slot(str)
    def setStatus(self, text: str):
        self._status_text = text
        self.statusChanged.emit(text)

    @Slot(str, result=bool)
    def openPath(self, path_str: str) -> bool:
        """Klasörü / dosyayı sistemin varsayılan uygulamasıyla (Gezgin) açar."""
        if not path_str or not Path(path_str).exists():
            self.setStatus(f"Hata: yol bulunamadı: {path_str}")
            return False
        return QDesktopServices.openUrl(QUrl.fromLocalFile(path_str))
