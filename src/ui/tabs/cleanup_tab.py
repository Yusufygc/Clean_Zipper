from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTextEdit, QMessageBox, QCheckBox
)
from PySide6.QtCore import QThread, Signal
from src.services.cleanup_service import CleanupService
from src.services.project_service import ProjectService

class CleanupWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, service: ProjectService, path: Path, categories: list):
        super().__init__()
        self.service = service
        self.path = path
        self.categories = categories

    def run(self):
        try:
            result = self.service.cleanup_service.cleanup(
                self.path, categories=self.categories, dry_run=False
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class CleanupTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.project_service = main_window.project_service
        self.cleanup_worker = None
        self.category_checks = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header Title
        title = QLabel("Proje Temizliği", self)
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #0F172A;")
        layout.addWidget(title)

        # Subtitle description
        desc = QLabel("Geçici dosyaları, önbellek klasörlerini ve gereksiz artifact'ları siler.", self)
        desc.setStyleSheet("font-size: 13px; font-weight: 600; color: #334155;")
        layout.addWidget(desc)

        # Kategori seçimi
        for name, spec in CleanupService.CLEANUP_CATEGORIES.items():
            check = QCheckBox(spec['label'], self)
            check.setChecked(spec['default_enabled'])
            self.category_checks[name] = check
            layout.addWidget(check)

        # Button row: Preview & Cleanup
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        btn_preview = QPushButton("Önizleme", self)
        btn_preview.setObjectName("btn_ghost")
        btn_preview.setFixedHeight(38)
        btn_preview.clicked.connect(self._preview_cleanup)
        btn_row.addWidget(btn_preview)

        # Temizle Butonu -> Kırmızı (btn_danger)
        btn_clean = QPushButton("Temizliği Başlat", self)
        btn_clean.setObjectName("btn_danger")
        btn_clean.setFixedHeight(38)
        btn_clean.clicked.connect(self._execute_cleanup)
        btn_row.addWidget(btn_clean)

        layout.addLayout(btn_row)

        # Divider line
        div = QFrame(self)
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #E2E8F0;")
        layout.addWidget(div)

        # Result View
        log_lbl = QLabel("Önizleme / Sonuç", self)
        log_lbl.setStyleSheet("font-size: 15px; font-weight: 800; color: #0F172A;")
        layout.addWidget(log_lbl)

        self.cleanup_log = QTextEdit(self)
        self.cleanup_log.setReadOnly(True)
        self.cleanup_log.setPlainText("Önizleme için Önizleme butonuna tıklayın.")
        layout.addWidget(self.cleanup_log, stretch=1)

    def _selected_categories(self) -> list:
        return [name for name, check in self.category_checks.items() if check.isChecked()]

    def _preview_cleanup(self):
        if not self.main_window._require_project():
            return
            
        categories = self._selected_categories()
        if not categories:
            self.cleanup_log.setPlainText("En az bir temizlik kategorisi seçin.")
            return

        preview = self.project_service.cleanup_service.preview_cleanup(
            self.main_window.current_project_path, categories
        )
        
        sep = "─" * 50
        text = f"Önizleme Sonucu\n{sep}\n"
        text += f"Toplam : {preview['total_files']} dosya,  {preview['total_size'] / 1024:.1f} KB\n\n"
        
        for f in preview["files"][:50]:
            text += f"  {Path(f['path']).name}  ({f['size'] / 1024:.1f} KB)\n"
            
        if len(preview["files"]) > 50:
            text += f"\n  … ve {len(preview['files']) - 50} dosya daha\n"
            
        self.cleanup_log.setPlainText(text)

    def _execute_cleanup(self):
        if not self.main_window._require_project():
            return

        reply = QMessageBox.question(
            self,
            "Onay Gerekli",
            "Bu işlem geri alınamaz.\n\nGeçici dosyalar ve önbellek klasörleri kalıcı olarak silinecek.\n\nDevam etmek istiyor musunuz?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        if self.cleanup_worker and self.cleanup_worker.isRunning():
            return

        self.main_window._set_status("Temizlik yapılıyor…")

        self.cleanup_worker = CleanupWorker(self.project_service, self.main_window.current_project_path, categories)
        self.cleanup_worker.finished.connect(self._handle_cleanup_finished)
        self.cleanup_worker.error.connect(self._handle_cleanup_error)
        self.cleanup_worker.start()

    def _handle_cleanup_finished(self, result: dict):
        if result["success"]:
            self.main_window._set_status("Temizlik tamamlandı.")
            QMessageBox.information(
                self,
                "Tamamlandı",
                f"Temizlik başarıyla tamamlandı.\n\n"
                f"Geri Dönüşüm Kutusu'na taşınan: {result['cleaned_files']} dosya\n"
                f"Kazanılan: {result['cleaned_size'] / 1024:.1f} KB"
            )
        else:
            self.main_window._set_status("Temizlik sırasında hata oluştu.")
            failed = result["failed"]
            details = "\n".join(f"{Path(p).name}: {msg}" for p, msg in failed[:10])
            if len(failed) > 10:
                details += f"\n… ve {len(failed) - 10} hata daha"
            QMessageBox.warning(
                self.main_window,
                "Temizlik Kısmen Tamamlandı",
                f"Taşınan: {result['cleaned_files']} dosya\n"
                f"Taşınamayan: {len(failed)} öğe\n\n{details}"
            )
        self._preview_cleanup()

    def _handle_cleanup_error(self, err_msg: str):
        self.main_window._set_status(f"Hata: {err_msg}")
        QMessageBox.critical(self.main_window, "Temizlik Hatası", err_msg)
