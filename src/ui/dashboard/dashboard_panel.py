import customtkinter as ctk
from src.ui.widgets.stats_card import StatsCard
from src.ui.widgets.health_score_widget import HealthScoreWidget
from src.ui.widgets.pie_chart_widget import PieChartWidget
from src.ui.widgets.progress_card import ProgressCard

# Sabit buton renkleri (ThemeManager kaldırıldı)
_BTN_PRIMARY = {"fg_color": "#1565C0", "hover_color": "#0D47A1", "text_color": "white"}


class DashboardPanel(ctk.CTkFrame):
    """
    Analiz dashboard paneli.
    Yalnızca analiz verilerini görüntüler; işlem butonları kendi
    sekmelerinde yer alır (Arşivle, Temizlik).
    """

    def __init__(self, parent, doctor=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.doctor = doctor
        self._build_dashboard()

    # ------------------------------------------------------------------ #
    #  UI İnşası                                                           #
    # ------------------------------------------------------------------ #

    def _build_dashboard(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_stats_row()
        self._build_content_row()
        self._build_status_bar()

    def _build_header(self):
        header = ctk.CTkFrame(self, corner_radius=8, height=50)
        header.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        header.grid_propagate(False)

        ctk.CTkLabel(
            header,
            text="Proje Analizi",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="gray20"
        ).pack(side="left", padx=16, pady=12)

        self.analyze_btn = ctk.CTkButton(
            header,
            text="Yenile",
            width=90, height=30,
            **_BTN_PRIMARY
        )
        self.analyze_btn.pack(side="right", padx=12, pady=10)

    def _build_stats_row(self):
        sf = ctk.CTkFrame(self, fg_color="transparent")
        sf.grid(row=1, column=0, sticky="ew", padx=12, pady=6)

        # Sağlık skoru widget'ı
        self.health_widget = HealthScoreWidget(sf, size=170)
        self.health_widget.pack(side="left", padx=(0, 12))

        # Dikey ayırıcı
        ctk.CTkFrame(sf, width=1, fg_color="gray80").pack(
            side="left", fill="y", pady=8, padx=(0, 12)
        )

        # İstatistik kartları
        cards_frame = ctk.CTkFrame(sf, fg_color="transparent")
        cards_frame.pack(side="left", fill="both", expand=True)

        stats = [
            ("files",  "📄", "Dosyalar",  "—"),
            ("size",   "💾", "Boyut",     "—"),
            ("dirs",   "📁", "Klasörler", "—"),
            ("issues", "⚠️", "Sorunlar",  "—"),
        ]
        self.cards = {}
        for i, (key, icon, title, val) in enumerate(stats):
            card = StatsCard(
                cards_frame, title=title, value=val, icon=icon,
                width=160, height=85
            )
            card.grid(row=i // 2, column=i % 2, padx=4, pady=4, sticky="nsew")
            self.cards[key] = card

        cards_frame.grid_columnconfigure((0, 1), weight=1)

    def _build_content_row(self):
        cf = ctk.CTkFrame(self, corner_radius=8)
        cf.grid(row=2, column=0, sticky="nsew", padx=12, pady=6)
        cf.grid_columnconfigure(1, weight=1)
        cf.grid_rowconfigure(0, weight=1)

        # Sol: Dosya türleri grafiği
        self.pie_chart = PieChartWidget(
            cf, title="Dosya Türleri", size=210
        )
        self.pie_chart.grid(row=0, column=0, padx=16, pady=14, sticky="ns")

        # Dikey ayırıcı
        ctk.CTkFrame(cf, width=1, fg_color="gray80").grid(
            row=0, column=1, sticky="ns", pady=14
        )

        # Sağ: Öneriler ve Sorunlar (Sekmeli)
        self.right_tabview = ctk.CTkTabview(cf, corner_radius=6)
        self.right_tabview.grid(row=0, column=2, sticky="nsew", padx=16, pady=14)
        
        self.tab_recs = self.right_tabview.add("Öneriler")
        self.tab_issues = self.right_tabview.add("Sorunlar")
        
        # --- Öneriler Sekmesi ---
        self.tab_recs.grid_rowconfigure(0, weight=1)
        self.tab_recs.grid_columnconfigure(0, weight=1)
        self.rec_text = ctk.CTkTextbox(
            self.tab_recs,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            corner_radius=6,
            wrap="word",
            border_width=1,
            border_color="gray80"
        )
        self.rec_text.grid(row=0, column=0, sticky="nsew", pady=(4, 0))
        self.rec_text.insert("1.0", "Proje açıldığında analiz otomatik başlar.")
        self.rec_text.configure(state="disabled")

        # --- Sorunlar Sekmesi ---
        self.tab_issues.grid_rowconfigure(0, weight=1)
        self.tab_issues.grid_columnconfigure(0, weight=1)
        self.issues_scroll = ctk.CTkScrollableFrame(
            self.tab_issues,
            fg_color="transparent"
        )
        self.issues_scroll.grid(row=0, column=0, sticky="nsew", pady=(4, 0))
        
        # İlk başta boş olduğunu belirten bir etiket
        self.no_issues_label = ctk.CTkLabel(
            self.issues_scroll,
            text="Proje açıldığında tespit edilen sorunlar burada listelenecek.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="gray50"
        )
        self.no_issues_label.pack(pady=20)

    def _build_status_bar(self):
        """Alt ilerleme çubuğu — analiz ve işlem durumunu gösterir."""
        status_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        status_frame.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 10))

        self.progress_card = ProgressCard(
            status_frame, title="Durum", value=0, status="Hazır"
        )
        self.progress_card.pack(fill="x")

    # ------------------------------------------------------------------ #
    #  Veri Güncelleme                                                     #
    # ------------------------------------------------------------------ #

    def update_dashboard(self, data: dict):
        self.health_widget.update_score(
            data.get("health_score", 0),
            data.get("health_status", "—")
        )
        self.cards["files"].update_value(str(data.get("total_files", 0)))
        self.cards["size"].update_value(f"{data.get('total_size_mb', 0):.1f} MB")
        self.cards["dirs"].update_value(str(data.get("total_dirs", 0)))
        self.cards["issues"].update_value(str(data.get("issues_count", 0)))

        if data.get("file_type_distribution"):
            self.pie_chart.update_data(data["file_type_distribution"])

        # Önerileri Güncelle
        self.rec_text.configure(state="normal")
        self.rec_text.delete("1.0", "end")
        recs = data.get("top_recommendations", [])
        if recs:
            for i, (title, desc, _) in enumerate(recs[:5], 1):
                self.rec_text.insert("end", f"{i}. {title}\n")
                self.rec_text.insert("end", f"   {desc}\n\n")
        else:
            self.rec_text.insert("1.0", "Proje iyi durumda, önerilecek bir şey bulunamadı.")
        self.rec_text.configure(state="disabled")

        # Sorunları Güncelle
        for widget in self.issues_scroll.winfo_children():
            widget.destroy()

        all_issues = data.get("all_issues", [])
        if not all_issues:
            ctk.CTkLabel(
                self.issues_scroll,
                text="Harika! Tespit edilen hiçbir sorun yok. 🎉",
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color="gray50"
            ).pack(pady=20)
        else:
            # Severity renkleri
            sev_colors = {
                "CRITICAL": "#C62828",
                "HIGH": "#E65100",
                "MEDIUM": "#F57F17",
                "LOW": "#1565C0",
                "INFO": "#2E7D32"
            }
            
            for issue in all_issues:
                issue_frame = ctk.CTkFrame(
                    self.issues_scroll,
                    fg_color="white",
                    corner_radius=6,
                    border_width=1,
                    border_color="gray85"
                )
                issue_frame.pack(fill="x", pady=4, padx=4)
                
                sev_name = issue.severity.name if hasattr(issue.severity, 'name') else str(issue.severity)
                color = sev_colors.get(sev_name, "gray50")
                
                # Sol taraf: Severity göstergesi (renkli ince dikey çizgi/kutu)
                sev_indicator = ctk.CTkFrame(issue_frame, width=4, corner_radius=2, fg_color=color)
                sev_indicator.pack(side="left", fill="y", padx=(4, 8), pady=4)
                
                # İçerik
                content_frame = ctk.CTkFrame(issue_frame, fg_color="transparent")
                content_frame.pack(side="left", fill="both", expand=True, pady=6)
                
                # Başlık
                ctk.CTkLabel(
                    content_frame,
                    text=issue.title,
                    font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                    text_color="gray20",
                    anchor="w"
                ).pack(fill="x")
                
                # Açıklama / Dosya yolu
                desc = issue.description
                if issue.file_path:
                    # Sadece dosya adını göstermek veya son klasörleri göstermek daha temiz olabilir
                    desc += f" ({issue.file_path.name})"
                
                ctk.CTkLabel(
                    content_frame,
                    text=desc,
                    font=ctk.CTkFont(family="Segoe UI", size=10),
                    text_color="gray50",
                    anchor="w",
                    wraplength=350,
                    justify="left"
                ).pack(fill="x", pady=(2, 0))
