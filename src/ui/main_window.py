import os
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTabWidget, QLineEdit, QTextEdit,
    QFileDialog, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal

from src.ui.dashboard.dashboard_panel import DashboardPanel
from src.services.project_service import ProjectService
from src.analyzers.size_analyzer import SizeAnalyzer
from src.analyzers.type_analyzer import TypeAnalyzer
from src.analyzers.duplicate_finder import DuplicateFinder
from src.analyzers.empty_folder_finder import EmptyFolderFinder
from src.analyzers.structure_analyzer import StructureAnalyzer


# ================================================================== #
#  Background Workers (Safe Threading Architecture)                  #
# ================================================================== #

class AnalyzeWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, service: ProjectService):
        super().__init__()
        self.service = service

    def run(self):
        try:
            result = self.service.analyze_project()
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class ArchiveWorker(QThread):
    progress = Signal(int, str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, service: ProjectService, path: Path, output: Path, mode: str):
        super().__init__()
        self.service = service
        self.path = path
        self.output = output
        self.mode = mode

    def run(self):
        try:
            def on_progress(done, total):
                pct = int(done / total * 100) if total else 0
                self.progress.emit(pct, f"{done} / {total} dosya")

            if self.mode == "zip":
                result = self.service.archive_service.create_zip(
                    self.path, self.output, progress_callback=on_progress
                )
            else:
                result = self.service.archive_service.copy_project(
                    self.path, self.output, progress_callback=on_progress
                )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class CleanupWorker(QThread):
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, service: ProjectService, path: Path):
        super().__init__()
        self.service = service
        self.path = path

    def run(self):
        try:
            result = self.service.cleanup_service.cleanup(
                self.path, dry_run=False
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


# ================================================================== #
#  Main Window Class                                                #
# ================================================================== #

class GitCleanArchiverPro(QMainWindow):
    APP_NAME = "GitClean Archiver Pro"
    APP_VERSION = "2.0.0"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{self.APP_NAME}  v{self.APP_VERSION}")
        self.resize(1280, 820)
        self.setMinimumSize(1050, 720)

        # Setup services
        self.project_service = ProjectService()
        for analyzer in [SizeAnalyzer(), TypeAnalyzer(),
                         DuplicateFinder(), EmptyFolderFinder(), StructureAnalyzer()]:
            self.project_service.doctor.register_analyzer(analyzer)

        self.current_project_path = None
        
        # Worker variables
        self.analyze_worker = None
        self.archive_worker = None
        self.cleanup_worker = None

        # Central widget and UI Layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self._build_ui(self.main_layout)
        self._load_stylesheet()

    def _load_stylesheet(self):
        qss_file = Path(__file__).parent / "themes" / "style.qss"
        if qss_file.exists():
            try:
                with open(qss_file, "r", encoding="utf-8") as f:
                    self.setStyleSheet(f.read())
            except Exception as e:
                print(f"Warning: Could not load stylesheet: {e}")

    # ================================================================== #
    #  UI Construction                                                   #
    # ================================================================== #

    def _build_ui(self, parent_layout):
        self._build_toolbar(parent_layout)
        
        body_frame = QFrame(self)
        body_frame.setStyleSheet("background: transparent;")
        body_layout = QHBoxLayout(body_frame)
        body_layout.setContentsMargins(8, 6, 8, 0)
        body_layout.setSpacing(6)
        
        self._build_sidebar(body_layout)
        self._build_tabs(body_layout)
        
        parent_layout.addWidget(body_frame, stretch=1)
        self._build_statusbar()

    # ── Top Toolbar ─────────────────────────────────────────────────── #

    def _build_toolbar(self, parent_layout):
        bar = QFrame(self)
        bar.setFixedHeight(46)
        bar.setStyleSheet("background-color: #111216; border-bottom: 1px solid #232429;")
        
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)

        title_lbl = QLabel(self.APP_NAME, bar)
        title_lbl.setStyleSheet("font-size: 13px; font-weight: bold; color: #E3E3E6;")
        layout.addWidget(title_lbl)
        
        layout.addStretch()
        parent_layout.addWidget(bar)

    # ── Sidebar Panel ───────────────────────────────────────────────── #

    def _build_sidebar(self, parent_layout):
        sb = QFrame(self)
        sb.setFixedWidth(220)
        sb.setObjectName("sidebar") # style.qss targeting QFrame#sidebar
        
        layout = QVBoxLayout(sb)
        layout.setContentsMargins(16, 18, 16, 18)
        layout.setSpacing(12)

        # "AKTİF PROJE" Başlığı (İstenen büyük ve bold yapı)
        lbl_proj = QLabel("AKTİF PROJE", sb)
        lbl_proj.setStyleSheet("font-weight: 900; font-size: 15px; color: #0F172A; letter-spacing: 1px;")
        layout.addWidget(lbl_proj)

        self._sidebar_name = QLabel("—", sb)
        self._sidebar_name.setStyleSheet("font-weight: 800; font-size: 14px; color: #0F172A;")
        self._sidebar_name.setWordWrap(True)
        layout.addWidget(self._sidebar_name)

        # Proje Yolu (Taşarsa aşağı satıra kayacak wrap düzeni)
        self._sidebar_path = QLabel("Henüz proje açılmadı.", sb)
        self._sidebar_path.setObjectName("sidebar-path-label") 
        self._sidebar_path.setWordWrap(True)
        self._sidebar_path.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self._sidebar_path)

        div2 = QFrame(sb)
        div2.setFixedHeight(1)
        div2.setStyleSheet("background-color: #CBD5E1;")
        layout.addWidget(div2)

        btn_open = QPushButton("Proje Dizini Aç", sb)
        btn_open.setObjectName("btn_ghost")
        btn_open.setFixedHeight(34)
        btn_open.clicked.connect(self._open_project)
        layout.addWidget(btn_open)

        layout.addStretch()
        parent_layout.addWidget(sb)

    # ── Main Tab Widget ─────────────────────────────────────────────── #

    def _build_tabs(self, parent_layout):
        self.tab_view = QTabWidget(self)
        
        # 1. Dashboard Tab
        self._tab_dash = QWidget(self.tab_view)
        self.dashboard = DashboardPanel(self._tab_dash, doctor=self.project_service.doctor)
        self.dashboard.analyze_btn.clicked.connect(self._analyze)
        
        dash_lay = QVBoxLayout(self._tab_dash)
        dash_lay.setContentsMargins(0, 0, 0, 0)
        dash_lay.addWidget(self.dashboard)
        
        self.tab_view.addTab(self._tab_dash, "  Analiz  ")

        # 2. Archive Tab
        self._tab_archive = QWidget(self.tab_view)
        self._build_archive_tab()
        self.tab_view.addTab(self._tab_archive, "  Arşivle  ")

        # 3. Cleanup Tab
        self._tab_cleanup = QWidget(self.tab_view)
        self._build_cleanup_tab()
        self.tab_view.addTab(self._tab_cleanup, "  Temizlik  ")

        parent_layout.addWidget(self.tab_view)

    # ── Archive Tab UI ──────────────────────────────────────────────── #

    def _build_archive_tab(self):
        layout = QVBoxLayout(self._tab_archive)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        title = QLabel("Proje Arşivleme ve Dağıtım", self._tab_archive)
        title.setStyleSheet("font-size: 16px; font-weight: 800; color: #0F172A;")
        layout.addWidget(title)

        desc = QLabel(".gitignore kurallarına tam uyumlu ZIP paketi hazırlar veya temiz kopya dizini çıkarır.", self._tab_archive)
        desc.setStyleSheet("font-size: 12px; font-weight: 500; color: #475569;")
        layout.addWidget(desc)

        path_row = QHBoxLayout()
        path_row.setSpacing(10)

        path_lbl = QLabel("Çıktı Hedefi", self._tab_archive)
        path_lbl.setStyleSheet("font-size: 13px; font-weight: 800; color: #0F172A;")
        path_lbl.setFixedWidth(90)
        path_row.addWidget(path_lbl)

        self.archive_output = QLineEdit(self._tab_archive)
        self.archive_output.setPlaceholderText("Boş bırakılırsa ana dizine otomatik derives edilir")
        self.archive_output.setFixedHeight(36)
        path_row.addWidget(self.archive_output)

        btn_browse = QPushButton("Gözat…", self._tab_archive)
        btn_browse.setFixedSize(80, 36)
        btn_browse.clicked.connect(self._browse_archive_path)
        path_row.addWidget(btn_browse)
        layout.addLayout(path_row)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(14)

        # Zipleme Butonu -> Mor (btn_purple)
        btn_zip = QPushButton("🚀 ZIP Arşivi Oluştur", self._tab_archive)
        btn_zip.setObjectName("btn_purple")
        btn_zip.setFixedHeight(40)
        btn_zip.clicked.connect(self._create_zip)
        btn_row.addWidget(btn_zip)
    

        # Kopyalama Butonu -> Soluk Sarı (btn_paleyellow)
        btn_copy = QPushButton("📋 Temiz Dağıtım Kopyası Oluştur", self._tab_archive)
        btn_copy.setObjectName("btn_paleyellow")
        btn_copy.setFixedHeight(40)
        btn_copy.clicked.connect(self._create_copy)
        btn_row.addWidget(btn_copy)
        layout.addLayout(btn_row)

        div = QFrame(self._tab_archive)
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #E2E8F0;")
        layout.addWidget(div)

        log_lbl = QLabel("İşlem Raporlama Logu", self._tab_archive)
        log_lbl.setStyleSheet("font-size: 12px; font-weight: 800; color: #0F172A;")
        layout.addWidget(log_lbl)

        self.archive_log = QTextEdit(self._tab_archive)
        self.archive_log.setReadOnly(True)
        layout.addWidget(self.archive_log, stretch=1)

    # ── Cleanup Tab UI ──────────────────────────────────────────────── #

    def _build_cleanup_tab(self):
        layout = QVBoxLayout(self._tab_cleanup)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Başlık bold, parlak ve büyük yapıldı
        title = QLabel("Proje Temizliği", self._tab_cleanup)
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #0F172A;") 
        layout.addWidget(title)

        # Açıklama fontu büyük ve rengi koyu yapıldı
        desc = QLabel("Geçici dosyaları, önbellek klasörlerini ve gereksiz artifact'ları siler.", self._tab_cleanup)
        desc.setStyleSheet("font-size: 13px; font-weight: 600; color: #334155;")
        layout.addWidget(desc)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        btn_preview = QPushButton("Önizleme", self._tab_cleanup)
        btn_preview.setObjectName("btn_ghost")
        btn_preview.setFixedHeight(38)
        btn_preview.clicked.connect(self._preview_cleanup)
        btn_row.addWidget(btn_preview)

        # Temizle Butonu -> Kırmızı (btn_danger)
        btn_clean = QPushButton("Temizliği Başlat", self._tab_cleanup)
        btn_clean.setObjectName("btn_danger")
        btn_clean.setFixedHeight(38)
        btn_clean.clicked.connect(self._execute_cleanup)
        btn_row.addWidget(btn_clean)

        layout.addLayout(btn_row)

        div = QFrame(self._tab_cleanup)
        div.setFixedHeight(1)
        div.setStyleSheet("background-color: #E2E8F0;")
        layout.addWidget(div)

        # Önizleme / sonuç yazısı büyük bold ve parlak yapıldı
        log_lbl = QLabel("Önizleme / Sonuç", self._tab_cleanup)
        log_lbl.setStyleSheet("font-size: 15px; font-weight: 800; color: #0F172A;")
        layout.addWidget(log_lbl)

        self.cleanup_log = QTextEdit(self._tab_cleanup)
        self.cleanup_log.setReadOnly(True)
        self.cleanup_log.setPlainText("Önizleme için Önizleme butonuna tıklayın.")
        layout.addWidget(self.cleanup_log, stretch=1)

    # ── Status Bar ──────────────────────────────────────────────────── #

    def _build_statusbar(self):
        sb = self.statusBar()
        sb.showMessage("Hazır")

        self._status_version_lbl = QLabel(f"v{self.APP_VERSION} ", self)
        self._status_version_lbl.setStyleSheet("color: #475569; font-size: 11px; font-weight: bold; margin-right: 8px;")
        sb.addPermanentWidget(self._status_version_lbl)

    # ================================================================== #
    #  Logic / Handlers                                                  #
    # ================================================================== #

    def _require_project(self) -> bool:
        if not self.current_project_path:
            QMessageBox.warning(
                self,
                "Proje Seçilmedi",
                "Lütfen önce bir proje dizini açın."
            )
            return False
        return True

    def _set_status(self, text: str):
        self.statusBar().showMessage(text)

    def _open_project(self):
        d = QFileDialog.getExistingDirectory(self, "Proje Dizini Seçin", "")
        if not d:
            return
        
        self.current_project_path = Path(d)
        self.project_service.set_project(self.current_project_path)

        self._sidebar_name.setText(self.current_project_path.name)
        self._sidebar_path.setText(str(self.current_project_path))

        self._analyze()

    # ── Background Scanning ─────────────────────────────────────────── #

    def _analyze(self):
        if not self._require_project():
            return
        
        if self.analyze_worker and self.analyze_worker.isRunning():
            return

        self._set_status("Analiz ediliyor…")
        self.dashboard.progress_card.update_progress(5, "Başlatılıyor…")

        self.analyze_worker = AnalyzeWorker(self.project_service)
        self.analyze_worker.finished.connect(self._handle_analyze_finished)
        self.analyze_worker.error.connect(self._handle_analyze_error)
        self.analyze_worker.start()

    def _handle_analyze_finished(self, result: dict):
        self.dashboard.update_dashboard(result)
        self._set_status("Analiz tamamlandı.")
        self.dashboard.progress_card.update_progress(100, "Tamamlandı")

    def _handle_analyze_error(self, err_msg: str):
        self._set_status(f"Hata: {err_msg}")
        QMessageBox.critical(self, "Analiz Hatası", err_msg)

    # ── Background Archiving ────────────────────────────────────────── #

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
        return self.current_project_path.parent / f"{self.current_project_path.name}{suffix}"

    def _create_zip(self):
        if not self._require_project():
            return
        
        if self.archive_worker and self.archive_worker.isRunning():
            return

        output = self._get_archive_output(".zip")
        self._set_status("ZIP oluşturuluyor…")
        self.dashboard.progress_card.update_progress(5, "ZIP hazırlanıyor…")

        self.archive_worker = ArchiveWorker(self.project_service, self.current_project_path, output, "zip")
        self.archive_worker.progress.connect(self._handle_archive_progress)
        self.archive_worker.finished.connect(lambda res: self._handle_archive_finished(res, output, "zip"))
        self.archive_worker.error.connect(self._handle_archive_error)
        self.archive_worker.start()

    def _create_copy(self):
        if not self._require_project():
            return

        if self.archive_worker and self.archive_worker.isRunning():
            return

        output = self._get_archive_output("_clean")
        self._set_status("Kopyalanıyor…")
        self.dashboard.progress_card.update_progress(5, "Kopyalama başlatılıyor…")

        self.archive_worker = ArchiveWorker(self.project_service, self.current_project_path, output, "copy")
        self.archive_worker.progress.connect(self._handle_archive_progress)
        self.archive_worker.finished.connect(lambda res: self._handle_archive_finished(res, output, "copy"))
        self.archive_worker.error.connect(self._handle_archive_error)
        self.archive_worker.start()

    def _handle_archive_progress(self, pct: int, text: str):
        self.dashboard.progress_card.update_progress(pct, text)

    def _handle_archive_finished(self, result: dict, output: Path, mode: str):
        self._write_log(self.archive_log, result, output, mode=mode)
        
        if result["success"]:
            msg = f"{output.name} oluşturuldu." if mode == "zip" else f"Temiz kopya {output.name} dizinine çıkarıldı."
            self._set_status(f"Tamamlandı: {msg}")
            self.dashboard.progress_card.update_progress(100, "İşlem tamamlandı")
            
            QMessageBox.information(
                self,
                "Başarılı",
                f"İşlem başarıyla tamamlandı.\n\n"
                f"Konum   : {output}\n"
                f"Eklenen : {result.get('added_files', result.get('copied_files', 0))} dosya\n"
                f"Atlanan : {result.get('skipped_files', 0)} dosya"
            )
        else:
            self._set_status("İşlem başarısız oldu.")
            QMessageBox.critical(
                self,
                "Hata",
                f"İşlem başarısız.\n\n{result.get('error', '')}"
            )

    def _handle_archive_error(self, err_msg: str):
        self._set_status(f"Hata: {err_msg}")
        QMessageBox.critical(self, "İşlem Hatası", err_msg)

    # ── Background Cleanup ──────────────────────────────────────────── #

    def _preview_cleanup(self):
        if not self._require_project():
            return
            
        preview = self.project_service.cleanup_service.preview_cleanup(
            self.current_project_path
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
        if not self._require_project():
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

        self._set_status("Temizlik yapılıyor…")

        self.cleanup_worker = CleanupWorker(self.project_service, self.current_project_path)
        self.cleanup_worker.finished.connect(self._handle_cleanup_finished)
        self.cleanup_worker.error.connect(self._handle_cleanup_error)
        self.cleanup_worker.start()

    def _handle_cleanup_finished(self, result: dict):
        if result["success"]:
            self._set_status("Temizlik tamamlandı.")
            QMessageBox.information(
                self,
                "Tamamlandı",
                f"Temizlik başarıyla tamamlandı.\n\n"
                f"Silinen  : {result['cleaned_files']} dosya\n"
                f"Kazanılan: {result['cleaned_size'] / 1024:.1f} KB"
            )
            self._preview_cleanup()
        else:
            self._set_status("Temizlik sırasında hata oluştu.")
            QMessageBox.critical(self, "Hata", "Temizlik işlemi başarısız oldu.")

    def _handle_cleanup_error(self, err_msg: str):
        self._set_status(f"Hata: {err_msg}")
        QMessageBox.critical(self, "Temizlik Hatası", err_msg)

    # ── Logging Helper ──────────────────────────────────────────────── #

    def _write_log(self, widget: QTextEdit, result: dict, output: Path, mode: str):
        sep = "─" * 50
        text = ""
        if mode == "zip":
            text += f"ZIP İşlemi\n{sep}\n\n"
            text += f"Durum   : {'Başarılı' if result['success'] else 'Başarısız'}\n"
            text += f"Konum   : {output}\n"
            text += f"Eklenen : {result.get('added_files', 0)} dosya\n"
            text += f"Atlanan : {result.get('skipped_files', 0)} dosya\n"
        else:
            text += f"Kopyalama İşlemi\n{sep}\n\n"
            text += f"Durum      : {'Başarılı' if result['success'] else 'Başarısız'}\n"
            text += f"Konum      : {output}\n"
            text += f"Kopyalanan : {result.get('copied_files', 0)} dosya\n"
            text += f"Atlanan    : {result.get('skipped_files', 0)} dosya\n"

        if result.get("error"):
            text += f"\nHata Detayı:\n{result['error']}\n"

        widget.setPlainText(text)