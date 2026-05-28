import os
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QTabWidget, QFileDialog, QMessageBox, QSizePolicy
)
from PySide6.QtCore import Qt, QThread, Signal

from src.ui.dashboard.dashboard_panel import DashboardPanel
from src.ui.tabs.archive_tab import ArchiveTab
from src.ui.tabs.cleanup_tab import CleanupTab
from src.services.project_service import ProjectService
from src.analyzers.size_analyzer import SizeAnalyzer
from src.analyzers.type_analyzer import TypeAnalyzer
from src.analyzers.duplicate_finder import DuplicateFinder
from src.analyzers.empty_folder_finder import EmptyFolderFinder
from src.analyzers.structure_analyzer import StructureAnalyzer
from src.analyzers.security_analyzer import SecurityLeakAnalyzer
from src.analyzers.dead_weight_analyzer import DeadWeightAnalyzer
from src.analyzers.code_complexity_analyzer import CodeComplexityAnalyzer


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

        # Servis kurulumu
        self.project_service = ProjectService()
        
        # Tüm aktif analizörlerin sisteme kaydedilmesi
        active_analyzers = [
            SizeAnalyzer(), 
            TypeAnalyzer(),
            DuplicateFinder(), 
            EmptyFolderFinder(), 
            StructureAnalyzer(),
            SecurityLeakAnalyzer(),
            DeadWeightAnalyzer(),
            CodeComplexityAnalyzer()
        ]
        
        for analyzer in active_analyzers:
            self.project_service.doctor.register_analyzer(analyzer)

        self.current_project_path = None
        self.analyze_worker = None

        # Build Central Widget and UI Layout
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self._build_ui(self.main_layout)

        # Load QSS Style Sheet
        self._load_stylesheet()

    def _load_stylesheet(self):
        qss_file = Path(__file__).parent / "themes" / "style.qss"
        if qss_file.exists():
            try:
                with open(qss_file, "r", encoding="utf-8") as f:
                    from PySide6.QtWidgets import QApplication
                    app = QApplication.instance()
                    if app:
                        app.setStyleSheet(f.read())
                    else:
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

    def _build_sidebar(self, parent_layout):
        sb = QFrame(self)
        sb.setFixedWidth(240)
        sb.setObjectName("sidebar")
        
        layout = QVBoxLayout(sb)
        layout.setContentsMargins(16, 18, 16, 18)
        layout.setSpacing(12)

        lbl_proj = QLabel("AKTİF PROJE", sb)
        lbl_proj.setStyleSheet("font-weight: 900; font-size: 15px; color: #0F172A; letter-spacing: 1px;")
        layout.addWidget(lbl_proj)

        div1 = QFrame(sb)
        div1.setFixedHeight(1)
        div1.setStyleSheet("background-color: #CBD5E1;")
        layout.addWidget(div1)

        self._sidebar_name = QLabel("—", sb)
        self._sidebar_name.setStyleSheet("font-weight: 800; font-size: 14px; color: #0F172A;")
        self._sidebar_name.setWordWrap(True)
        layout.addWidget(self._sidebar_name)

        self._sidebar_path = QLabel("Henüz proje açılmadı.", sb)
        self._sidebar_path.setObjectName("sidebar-path-label")
        self._sidebar_path.setWordWrap(True)
        self._sidebar_path.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._sidebar_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
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

    def _build_tabs(self, parent_layout):
        self.tab_view = QTabWidget(self)
        
        # 1. Dashboard Tab
        self._tab_dash = QWidget(self.tab_view)
        self.dashboard = DashboardPanel(self._tab_dash, doctor=self.project_service.doctor)
        self.dashboard.analyze_btn.clicked.connect(self._analyze)
        self.dashboard.export_btn.clicked.connect(self._export_report)
        
        dash_lay = QVBoxLayout(self._tab_dash)
        dash_lay.setContentsMargins(0, 0, 0, 0)
        dash_lay.addWidget(self.dashboard)
        self.tab_view.addTab(self._tab_dash, "  Analiz  ")

        # 2. Archive Tab (Extracted)
        self.archive_tab = ArchiveTab(self)
        self.tab_view.addTab(self.archive_tab, "  Arşivle  ")

        # 3. Cleanup Tab (Extracted)
        self.cleanup_tab = CleanupTab(self)
        self.tab_view.addTab(self.cleanup_tab, "  Temizlik  ")

        parent_layout.addWidget(self.tab_view)

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
        
        path_str = str(self.current_project_path)
        formatted_path = path_str.replace('\\', '\\\u200b').replace('/', '/\u200b').replace('_', '_\u200b').replace('-', '-\u200b')
        self._sidebar_path.setText(formatted_path)

        self._analyze()

    def _export_report(self):
        if not self._require_project():
            return
        
        default_filename = f"{self.current_project_path.name}_saglik_raporu.html"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Sağlık Raporunu Dışa Aktar",
            default_filename,
            "HTML Dosyası (*.html);;Tüm Dosyalar (*.*)"
        )
        if not path:
            return

        self._set_status("Kurumsal rapor üretiliyor…")
        try:
            success = self.project_service.export_project_report(Path(path))
            if success:
                self._set_status("Rapor başarıyla kaydedildi.")
                QMessageBox.information(
                    self,
                    "Rapor Başarılı",
                    f"Kurumsal sağlık analizi ve kritik sorunlar raporu başarıyla kaydedildi:\n\n{path}"
                )
            else:
                self._set_status("Rapor kaydedilemedi.")
                QMessageBox.critical(
                    self,
                    "Hata",
                    "Rapor dosyaya yazılırken bir yazma hatası oluştu."
                )
        except Exception as e:
            self._set_status("Rapor dışa aktarma hatası.")
            QMessageBox.critical(
                self,
                "Rapor Hatası",
                f"Sistem analiz raporu oluşturulurken beklenmeyen bir hata meydana geldi:\n\n{str(e)}"
            )

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