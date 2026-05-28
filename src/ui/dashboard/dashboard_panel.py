from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QFrame, QTabWidget, QTextBrowser, QScrollArea
from PySide6.QtCore import Qt

from src.ui.widgets.stats_card import StatsCard
from src.ui.widgets.health_score_widget import HealthScoreWidget
from src.ui.widgets.histogram_chart_widget import HistogramChartWidget
from src.ui.widgets.progress_card import ProgressCard

class DashboardPanel(QWidget):
    def __init__(self, parent=None, doctor=None, **kwargs):
        super().__init__(parent)
        self.doctor = doctor
        self._build_dashboard()

    def _build_dashboard(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        self._build_header(main_layout)
        self._build_stats_row(main_layout)
        self._build_content_row(main_layout)
        self._build_status_bar(main_layout)

    def _build_header(self, parent_layout):
        header_frame = QFrame(self)
        header_frame.setFixedHeight(54)
        header_frame.setObjectName("card")
        
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(16, 0, 16, 0)

        title_lbl = QLabel("Proje Sağlık Analiz Paneli", header_frame)
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #0F172A;")
        header_layout.addWidget(title_lbl)

        header_layout.addStretch()

        # Yenile Butonu (Buz Mavisi stiliyle başlık hizasında sabitlendi)
        self.analyze_btn = QPushButton("Yeniden Analiz Et", header_frame)
        self.analyze_btn.setObjectName("btn_iceblue") # QSS'te tanımlı buz mavisi sınıfı
        self.analyze_btn.setFixedSize(140, 34)
        header_layout.addWidget(self.analyze_btn)

        parent_layout.addWidget(header_frame)

    def _build_stats_row(self, parent_layout):
        stats_frame = QFrame(self)
        stats_frame.setStyleSheet("background: transparent; border: none;")
        
        layout = QHBoxLayout(stats_frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        self.health_widget = HealthScoreWidget(stats_frame, score=0, status="—", size=170)
        layout.addWidget(self.health_widget)

        cards_widget = QWidget(stats_frame)
        cards_layout = QGridLayout(cards_widget)
        cards_layout.setContentsMargins(0, 0, 0, 0)
        cards_layout.setHorizontalSpacing(14)
        cards_layout.setVerticalSpacing(14)

        stats_meta = [
            ("files",  "📄", "Toplam Dosya",  "—"),
            ("size",   "💾", "Proje Boyutu",  "—"),
            ("dirs",   "📁", "Klasör Sayısı", "—"),
            ("issues", "⚠️", "Tespit Edilen Sorunlar",  "—"),
        ]
        self.cards = {}
        for i, (key, icon, title, val) in enumerate(stats_meta):
            card = StatsCard(cards_widget, title=title, value=val, icon=icon)
            row = i // 2
            col = i % 2
            cards_layout.addWidget(card, row, col)
            self.cards[key] = card

        layout.addWidget(cards_widget, stretch=1)
        parent_layout.addWidget(stats_frame)

    def _build_content_row(self, parent_layout):
        content_frame = QFrame(self)
        content_frame.setObjectName("card")
        
        layout = QHBoxLayout(content_frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(20)

        self.histogram_chart = HistogramChartWidget(content_frame, title="Dosya Türü Dağılımı")
        layout.addWidget(self.histogram_chart, stretch=1)

        self.right_tabview = QTabWidget(content_frame)
        
        self.rec_text = QTextBrowser(self.right_tabview)
        self.right_tabview.addTab(self.rec_text, "Sistem Önerileri")

        self.issues_scroll = QScrollArea(self.right_tabview)
        self.issues_scroll.setWidgetResizable(True)
        self.issues_scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.issues_container = QWidget()
        self.issues_layout = QVBoxLayout(self.issues_container)
        self.issues_layout.setContentsMargins(4, 4, 4, 4)
        self.issues_layout.setSpacing(10)
        self.issues_layout.setAlignment(Qt.AlignTop)
        self.issues_scroll.setWidget(self.issues_container)

        self.right_tabview.addTab(self.issues_scroll, "Kritik Sorunlar")
        layout.addWidget(self.right_tabview, stretch=1)

        parent_layout.addWidget(content_frame, stretch=1)

    def _build_status_bar(self, parent_layout):
        self.progress_card = ProgressCard(self, title="İşlem Durumu", value=0, status="Hazır")
        parent_layout.addWidget(self.progress_card)

    def update_dashboard(self, data: dict):
        self.health_widget.update_score(data.get("health_score", 0), data.get("health_status", "—"))
        self.cards["files"].update_value(str(data.get("total_files", 0)))
        self.cards["size"].update_value(f"{data.get('total_size_mb', 0):.1f} MB")
        self.cards["dirs"].update_value(str(data.get("total_dirs", 0)))
        self.cards["issues"].update_value(str(data.get("issues_count", 0)))

        if data.get("file_type_distribution"):
            self.histogram_chart.update_data(data["file_type_distribution"])

        self.rec_text.clear()
        recs = data.get("top_recommendations", [])
        if recs:
            html = "<ol style='margin-left: 20px; color: #1E293B; font-family: Segoe UI; font-size: 13px; line-height: 1.6;'>"
            for title, desc, _ in recs[:5]:
                html += f"<li style='margin-bottom: 12px;'><b><span style='color: #2563EB;'>{title}</span></b><br/><span style='color: #475569;'>{desc}</span></li>"
            html += "</ol>"
            self.rec_text.setHtml(html)

        while self.issues_layout.count():
            item = self.issues_layout.takeAt(0)
            w = item.widget()
            if w: w.deleteLater()

        all_issues = data.get("all_issues", [])
        if not all_issues:
            no_lbl = QLabel("Harika! Yapısal hiçbir sorun tespit edilmedi. 🎉", self.issues_container)
            no_lbl.setStyleSheet("color: #16A34A; font-size: 13px; font-weight: bold; padding: 20px;")
            self.issues_layout.addWidget(no_lbl)
        else:
            sev_colors = {"CRITICAL": "#DC2626", "HIGH": "#EA580C", "MEDIUM": "#D97706", "LOW": "#2563EB", "INFO": "#16A34A"}
            for issue in all_issues:
                issue_frame = QFrame(self.issues_container)
                issue_frame.setFixedHeight(68)
                issue_frame.setStyleSheet("QFrame { background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; }")
                
                ifr_layout = QHBoxLayout(issue_frame)
                ifr_layout.setContentsMargins(10, 6, 12, 6)
                ifr_layout.setSpacing(12)

                sev_name = issue.severity.name if hasattr(issue.severity, 'name') else str(issue.severity)
                color = sev_colors.get(sev_name, "#64748B")

                indicator = QFrame(issue_frame)
                indicator.setFixedWidth(6)
                indicator.setStyleSheet(f"background-color: {color}; border-radius: 3px; border: none;")
                ifr_layout.addWidget(indicator)

                text_widget = QWidget(issue_frame)
                text_layout = QVBoxLayout(text_widget)
                text_layout.setContentsMargins(0, 0, 0, 0)
                text_layout.setSpacing(2)

                title_lbl = QLabel(issue.title, text_widget)
                title_lbl.setStyleSheet("font-weight: 700; font-size: 13px; color: #0F172A; border: none;")
                text_layout.addWidget(title_lbl)

                desc = issue.description
                if issue.file_path: desc += f" ({issue.file_path.name})"

                desc_lbl = QLabel(desc, text_widget)
                desc_lbl.setStyleSheet("font-size: 11px; color: #475569; border: none;")
                text_layout.addWidget(desc_lbl)

                ifr_layout.addWidget(text_widget, stretch=1)
                self.issues_layout.addWidget(issue_frame)