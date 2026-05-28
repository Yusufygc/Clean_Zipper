import os
from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QTextEdit, QFileDialog, QMessageBox, QComboBox
)
from PySide6.QtCore import QThread, Signal
from src.services.project_service import ProjectService

class ArchiveWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, service: ProjectService, path: Path, output: Path, mode: str, profile_name: str):
        super().__init__()
        self.service = service
        self.path = path
        self.output = output
        self.mode = mode
        self.profile_name = profile_name

    def run(self):
        try:
            def on_progress(done, total):
                pct = int(done / total * 100) if total else 0
                self.progress.emit(pct, f"{done} / {total} dosya")

            if self.mode == "zip":
                result = self.service.archive_service.create_zip(
                    self.path, self.output, profile_name=self.profile_name, progress_callback=on_progress
                )
            else:
                result = self.service.archive_service.copy_project(
                    self.path, self.output, profile_name=self.profile_name, progress_callback=on_progress
                )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

class ArchiveTab(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.project_service = main_window.project_service
        self.archive_worker = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header Title
        title = QLabel("Proje Arşivleme ve Dağıtım", self)
        title.setStyleSheet("font-size: 16px; font-weight: 800; color: #0F172A;")
        layout.addWidget(title)

        # Subtitle description
        desc = QLabel(".gitignore kurallarına ve sıkıştırma profillerine uygun arşiv hazırlar veya temiz kopya çıkarır.", self)
        desc.setStyleSheet("font-size: 12px; font-weight: 500; color: #475569;")
        layout.addWidget(desc)

        # Sıkıştırma Profil Yönetimi Seçim Paneli
        profile_frame = QFrame(self)
        profile_frame.setObjectName("card")
        profile_frame.setStyleSheet("background-color: #F8FAFC; border: 1px solid #CBD5E1; border-radius: 6px;")
        profile_layout = QHBoxLayout(profile_frame)
        profile_layout.setContentsMargins(12, 10, 12, 10)
        profile_layout.setSpacing(12)

        profile_lbl = QLabel("Sıkıştırma Profili:", profile_frame)
        profile_lbl.setStyleSheet("font-size: 12px; font-weight: 800; color: #0F172A;")
        profile_layout.addWidget(profile_lbl)

        self.profile_combo = QComboBox(profile_frame)
        self.profile_combo.setFixedHeight(32)
        self.profile_combo.setStyleSheet("""
            QComboBox { 
                background-color: #FFFFFF; 
                border: 2px solid #94A3B8; 
                border-radius: 4px; 
                padding: 4px 10px;
                font-weight: 700;
                color: #0F172A;
            }
            QComboBox::drop-down { border: none; }
        """)
        
        for p_name in self.project_service.archive_service.PROFILES.keys():
            self.profile_combo.addItem(p_name)
        profile_layout.addWidget(self.profile_combo, stretch=1)

        self.profile_desc_lbl = QLabel("", profile_frame)
        self.profile_desc_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #475569;")
        profile_layout.addWidget(self.profile_desc_lbl, stretch=2)
        
        def update_desc():
            p_name = self.profile_combo.currentText()
            p_info = self.project_service.archive_service.PROFILES.get(p_name, {})
            self.profile_desc_lbl.setText(p_info.get("description", ""))
            
        self.profile_combo.currentTextChanged.connect(update_desc)
        update_desc()
        
        layout.addWidget(profile_frame)

        # Output folder row
        path_row = QHBoxLayout()
        path_row.setSpacing(10)

        path_lbl = QLabel("Çıktı Hedefi", self)
        path_lbl.setStyleSheet("font-size: 13px; font-weight: 800; color: #0F172A;")
        path_lbl.setFixedWidth(90)
        path_row.addWidget(path_lbl)

        self.archive_output = QLineEdit(self)
        self.archive_output.setPlaceholderText("Boş bırakılırsa ana dizine otomatik derives edilir")
        self.archive_output.setFixedHeight(36)
        path_row.addWidget(self.archive_output)

        btn_browse = QPushButton("Gözat…", self)
        btn_browse.setFixedSize(80, 36)
        btn_browse.clicked.connect(self._browse_archive_path)
        path_row.addWidget(btn_browse)

        layout.addLayout(path_row)

        # Button row: Zip & Copy
        btn_row = QHBoxLayout()
        btn_row.setSpacing(14)

        # Zipleme Butonu -> Mor (btn_purple)
        btn_zip = QPushButton(" ZIP Arşivi Oluştur", self)
        btn_zip.setObjectName("btn_purple")
        btn_zip.setFixedHeight(40)
        btn_zip.clicked.connect(self._create_zip)
        btn_row.addWidget(btn_zip)

        # Kopyalama Butonu -> Soluk Sarı (btn_paleyellow)
        btn_copy = QPushButton(" Temiz Dağıtım Kopyası Oluştur", self)
        btn_copy.setObjectName("btn_paleyellow")
        btn_copy.setFixedHeight(40)
        btn_copy.clicked.connect(self._create_copy)
        btn_row.addWidget(btn_copy)

        layout.addLayout(btn_row)

        # Divider line
        div = QFrame(self)
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #E2E8F0;")
        layout.addWidget(div)

        # Logging View
        log_lbl = QLabel("İşlem Raporlama Logu", self)
        log_lbl.setStyleSheet("font-size: 12px; font-weight: 800; color: #0F172A;")
        layout.addWidget(log_lbl)

        self.archive_log = QTextEdit(self)
        self.archive_log.setReadOnly(True)
        self.archive_log.setPlainText("İşlem başlatıldığında sonuçlar burada görünür.")
        layout.addWidget(self.archive_log, stretch=1)

    def _browse_archive_path(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Çıktı Konumu Seçin",
            "",
            "ZIP Dosyası (*.zip);;Tüm Dosyalar (*.*)"
        )
        if path:
            self.archive_output.setText(path)

    def _get_archive_output(self, suffix: str) -> Path:
        raw = self.archive_output.text().strip()
        if raw:
            return Path(raw)
        return self.main_window.current_project_path.parent / f"{self.main_window.current_project_path.name}{suffix}"

    def _create_zip(self):
        if not self.main_window._require_project():
            return
        
        if self.archive_worker and self.archive_worker.isRunning():
            return

        output = self._get_archive_output(".zip")
        profile = self.profile_combo.currentText()
        
        self.main_window._set_status(f"ZIP oluşturuluyor ({profile})…")
        self.main_window.dashboard.progress_card.update_progress(5, "ZIP hazırlanıyor…")

        self.archive_worker = ArchiveWorker(
            self.project_service, self.main_window.current_project_path, output, "zip", profile_name=profile
        )
        self.archive_worker.progress.connect(self._handle_archive_progress)
        self.archive_worker.finished.connect(lambda res: self._handle_archive_finished(res, output, "zip"))
        self.archive_worker.error.connect(self._handle_archive_error)
        self.archive_worker.start()

    def _create_copy(self):
        if not self.main_window._require_project():
            return

        if self.archive_worker and self.archive_worker.isRunning():
            return

        output = self._get_archive_output("_clean")
        profile = self.profile_combo.currentText()
        
        self.main_window._set_status(f"Kopyalanıyor ({profile})…")
        self.main_window.dashboard.progress_card.update_progress(5, "Kopyalama başlatılıyor…")

        self.archive_worker = ArchiveWorker(
            self.project_service, self.main_window.current_project_path, output, "copy", profile_name=profile
        )
        self.archive_worker.progress.connect(self._handle_archive_progress)
        self.archive_worker.finished.connect(lambda res: self._handle_archive_finished(res, output, "copy"))
        self.archive_worker.error.connect(self._handle_archive_error)
        self.archive_worker.start()

    def _handle_archive_progress(self, pct: int, text: str):
        self.main_window.dashboard.progress_card.update_progress(pct, text)

    def _handle_archive_finished(self, result: dict, output: Path, mode: str):
        self._write_log(self.archive_log, result, output, mode=mode)
        
        if result["success"]:
            msg = f"{output.name} oluşturuldu." if mode == "zip" else f"Temiz kopya {output.name} dizinine çıkarıldı."
            self.main_window._set_status(f"Tamamlandı: {msg}")
            self.main_window.dashboard.progress_card.update_progress(100, "İşlem tamamlandı")
            
            QMessageBox.information(
                self,
                "Başarılı",
                f"İşlem başarıyla tamamlandı.\n\n"
                f"Seçilen Profil: {self.profile_combo.currentText()}\n"
                f"Konum         : {output}\n"
                f"Eklenen       : {result.get('added_files', result.get('copied_files', 0))} dosya\n"
                f"Atlanan       : {result.get('skipped_files', 0)} dosya"
            )
        else:
            self.main_window._set_status("İşlem başarısız oldu.")
            QMessageBox.critical(
                self,
                "Hata",
                f"İşlem başarısız.\n\n{result.get('error', '')}"
            )

    def _handle_archive_error(self, err_msg: str):
        self.main_window._set_status(f"Hata: {err_msg}")
        QMessageBox.critical(self, "İşlem Hatası", err_msg)

    def _write_log(self, widget: QTextEdit, result: dict, output: Path, mode: str):
        sep = "─" * 50
        text = ""
        profile_name = self.profile_combo.currentText()
        if mode == "zip":
            text += f"ZIP İşlemi ({profile_name} Profili)\n{sep}\n\n"
            text += f"Durum   : {'Başarılı' if result['success'] else 'Başarısız'}\n"
            text += f"Konum   : {output}\n"
            text += f"Eklenen : {result.get('added_files', 0)} dosya\n"
            text += f"Atlanan : {result.get('skipped_files', 0)} dosya\n"
        else:
            text += f"Kopyalama İşlemi ({profile_name} Profili)\n{sep}\n\n"
            text += f"Durum      : {'Başarılı' if result['success'] else 'Başarısız'}\n"
            text += f"Konum      : {output}\n"
            text += f"Kopyalanan : {result.get('copied_files', 0)} dosya\n"
            text += f"Atlanan    : {result.get('skipped_files', 0)} dosya\n"

        if result.get("error"):
            text += f"\nHata Detayı:\n{result['error']}\n"

        widget.setPlainText(text)
