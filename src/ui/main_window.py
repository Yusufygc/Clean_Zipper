import customtkinter as ctk
from tkinter import filedialog, messagebox
from pathlib import Path
import threading

from src.ui.dashboard.dashboard_panel import DashboardPanel
from src.services.project_service import ProjectService
from src.analyzers.size_analyzer import SizeAnalyzer
from src.analyzers.type_analyzer import TypeAnalyzer
from src.analyzers.duplicate_finder import DuplicateFinder
from src.analyzers.empty_folder_finder import EmptyFolderFinder
from src.analyzers.structure_analyzer import StructureAnalyzer

# ── Sabit renk tanımları (ThemeManager kaldırıldı) ─────────────────────── #
_C_PRIMARY   = {"fg_color": "#1565C0", "hover_color": "#0D47A1", "text_color": "white"}
_C_SUCCESS   = {"fg_color": "#2E7D32", "hover_color": "#1B5E20", "text_color": "white"}
_C_WARNING   = {"fg_color": "#E65100", "hover_color": "#BF360C", "text_color": "white"}
_C_DANGER    = {"fg_color": "#C62828", "hover_color": "#B71C1C", "text_color": "white"}
_C_GHOST     = {
    "fg_color": "transparent",
    "border_width": 1,
    "border_color": "gray70",
    "hover_color": "gray90",
    "text_color": "gray20"
}
# ─────────────────────────────────────────────────────────────────────────── #


class GitCleanArchiverPro(ctk.CTk):
    APP_NAME    = "GitClean Archiver Pro"
    APP_VERSION = "2.0.0"

    def __init__(self):
        super().__init__()
        self.title(f"{self.APP_NAME}  v{self.APP_VERSION}")
        self.geometry("1280x820")
        self.minsize(1050, 720)

        # Light tema sabit — toggle yok
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.project_service = ProjectService()
        for analyzer in [SizeAnalyzer(), TypeAnalyzer(),
                         DuplicateFinder(), EmptyFolderFinder(), StructureAnalyzer()]:
            self.project_service.doctor.register_analyzer(analyzer)

        self.current_project_path = None
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ================================================================== #
    #  UI İnşası                                                           #
    # ================================================================== #

    def _build_ui(self):
        self._build_toolbar()
        self._build_body()
        self._build_statusbar()

    # ── Araç Çubuğu ──────────────────────────────────────────────────── #

    def _build_toolbar(self):
        bar = ctk.CTkFrame(self, height=46, corner_radius=0,
                           fg_color=("gray95", "gray15"),
                           border_width=0)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        # Uygulama adı
        ctk.CTkLabel(
            bar,
            text=f"  {self.APP_NAME}",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="gray20"
        ).pack(side="left", padx=(10, 0))

    # ── Gövde (Sidebar + Sekmeler) ────────────────────────────────────── #

    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=8, pady=(6, 0))

        self._build_sidebar(body)
        self._build_tabs(body)

    def _build_sidebar(self, parent):
        """
        Sidebar — yalnızca proje bilgisi.
        Eylem butonları sekmeler içinde yer alır.
        """
        sb = ctk.CTkFrame(parent, width=200, corner_radius=8)
        sb.pack(side="left", fill="y", padx=(0, 6))
        sb.pack_propagate(False)

        # Başlık
        ctk.CTkLabel(
            sb,
            text="PROJE",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="gray50"
        ).pack(anchor="w", padx=14, pady=(16, 4))

        ctk.CTkFrame(sb, height=1, fg_color="gray80").pack(
            fill="x", padx=14, pady=(0, 10)
        )

        # Proje adı
        self._sidebar_name = ctk.CTkLabel(
            sb,
            text="—",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="gray15",
            wraplength=172,
            justify="left"
        )
        self._sidebar_name.pack(anchor="w", padx=14)

        # Proje yolu
        self._sidebar_path = ctk.CTkLabel(
            sb,
            text="Henüz proje açılmadı.",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color="gray50",
            wraplength=172,
            justify="left"
        )
        self._sidebar_path.pack(anchor="w", padx=14, pady=(4, 16))

        ctk.CTkFrame(sb, height=1, fg_color="gray80").pack(
            fill="x", padx=14, pady=(0, 12)
        )

        # Proje Aç butonu (sidebar'ın tek eylemi)
        ctk.CTkButton(
            sb, text="Proje Aç", command=self._open_project,
            height=32, **_C_GHOST
        ).pack(fill="x", padx=14)

    def _build_tabs(self, parent):
        self.tab_view = ctk.CTkTabview(parent, corner_radius=8)
        self.tab_view.pack(side="right", fill="both", expand=True)

        self._tab_dash    = self.tab_view.add("  Analiz  ")
        self._tab_archive = self.tab_view.add("  Arşivle  ")
        self._tab_cleanup = self.tab_view.add("  Temizlik  ")

        # Dashboard
        self.dashboard = DashboardPanel(
            self._tab_dash,
            doctor=self.project_service.doctor
        )
        self.dashboard.pack(fill="both", expand=True)
        self.dashboard.analyze_btn.configure(command=self._analyze)

        self._build_archive_tab()
        self._build_cleanup_tab()

    # ── Arşivle Sekmesi ──────────────────────────────────────────────── #

    def _build_archive_tab(self):
        wrap = ctk.CTkFrame(self._tab_archive, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=24, pady=20)

        # Başlık
        ctk.CTkLabel(
            wrap,
            text="Proje Arşivleme",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="gray15"
        ).pack(anchor="w", pady=(0, 4))

        ctk.CTkLabel(
            wrap,
            text=".gitignore kurallarına uygun ZIP dosyası oluşturur veya temiz kopya çıkarır.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="gray50"
        ).pack(anchor="w", pady=(0, 16))

        # Çıktı yolu satırı
        path_row = ctk.CTkFrame(wrap, fg_color="transparent")
        path_row.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            path_row,
            text="Çıktı Yolu",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="gray30",
            width=90
        ).pack(side="left")

        self.archive_output = ctk.CTkEntry(
            path_row,
            placeholder_text="Boş bırakılırsa proje dizinine otomatik kaydedilir",
            height=34, corner_radius=6
        )
        self.archive_output.pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            path_row, text="Gözat", width=70, height=34,
            command=self._browse_archive_path,
            **_C_GHOST
        ).pack(side="right")

        # Eylem butonları
        btn_row = ctk.CTkFrame(wrap, fg_color="transparent")
        btn_row.pack(fill="x", pady=(4, 0))

        ctk.CTkButton(
            btn_row, text="ZIP Oluştur",
            command=self._create_zip, height=38,
            **_C_PRIMARY
        ).pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            btn_row, text="Temiz Kopya Oluştur",
            command=self._create_copy, height=38,
            **_C_SUCCESS
        ).pack(side="right", fill="x", expand=True, padx=(6, 0))

        # Ayırıcı
        ctk.CTkFrame(wrap, height=1, fg_color="gray80").pack(
            fill="x", pady=16
        )

        # İşlem logu
        ctk.CTkLabel(
            wrap,
            text="İşlem Logu",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="gray30"
        ).pack(anchor="w", pady=(0, 6))

        self.archive_log = ctk.CTkTextbox(
            wrap,
            font=ctk.CTkFont(family="Consolas", size=11),
            corner_radius=6,
            border_width=1,
            border_color="gray80"
        )
        self.archive_log.pack(fill="both", expand=True)
        self.archive_log.insert("1.0", "İşlem başlatıldığında sonuçlar burada görünür.")
        self.archive_log.configure(state="disabled")

    # ── Temizlik Sekmesi ─────────────────────────────────────────────── #

    def _build_cleanup_tab(self):
        wrap = ctk.CTkFrame(self._tab_cleanup, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=24, pady=20)

        # Başlık
        ctk.CTkLabel(
            wrap,
            text="Proje Temizliği",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="gray15"
        ).pack(anchor="w", pady=(0, 4))

        ctk.CTkLabel(
            wrap,
            text="Geçici dosyaları, önbellek klasörlerini ve gereksiz artifact'ları siler.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="gray50"
        ).pack(anchor="w", pady=(0, 16))

        # Eylem butonları
        btn_row = ctk.CTkFrame(wrap, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 0))

        ctk.CTkButton(
            btn_row, text="Önizleme",
            command=self._preview_cleanup, height=38,
            **_C_GHOST
        ).pack(side="left", fill="x", expand=True, padx=(0, 6))

        ctk.CTkButton(
            btn_row, text="Temizliği Başlat",
            command=self._execute_cleanup, height=38,
            **_C_DANGER
        ).pack(side="right", fill="x", expand=True, padx=(6, 0))

        # Ayırıcı
        ctk.CTkFrame(wrap, height=1, fg_color="gray80").pack(
            fill="x", pady=16
        )

        # Önizleme / sonuç alanı
        ctk.CTkLabel(
            wrap,
            text="Önizleme / Sonuç",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="gray30"
        ).pack(anchor="w", pady=(0, 6))

        self.cleanup_log = ctk.CTkTextbox(
            wrap,
            font=ctk.CTkFont(family="Consolas", size=11),
            corner_radius=6,
            border_width=1,
            border_color="gray80"
        )
        self.cleanup_log.pack(fill="both", expand=True)
        self.cleanup_log.insert("1.0", "Önizleme için Önizleme butonuna tıklayın.")
        self.cleanup_log.configure(state="disabled")

    # ── Durum Çubuğu ─────────────────────────────────────────────────── #

    def _build_statusbar(self):
        bar = ctk.CTkFrame(
            self, height=26, corner_radius=0,
            fg_color=("gray90", "gray20"),
            border_width=0
        )
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        self.status_label = ctk.CTkLabel(
            bar, text="Hazır",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color="gray40"
        )
        self.status_label.pack(side="left", padx=12)

        ctk.CTkLabel(
            bar,
            text=f"v{self.APP_VERSION}",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color="gray60"
        ).pack(side="right", padx=12)

    # ================================================================== #
    #  Proje İşlemleri                                                     #
    # ================================================================== #

    def _open_project(self):
        d = filedialog.askdirectory(title="Proje Dizini Seçin")
        if not d:
            return
        self.current_project_path = Path(d)
        self.project_service.set_project(self.current_project_path)

        # Sidebar güncelle
        self._sidebar_name.configure(text=self.current_project_path.name)
        self._sidebar_path.configure(text=str(self.current_project_path))

        self._analyze()

    def _analyze(self):
        if not self._require_project():
            return
        self._set_status("Analiz ediliyor…")
        self.dashboard.progress_card.update_progress(5, "Başlatılıyor…")

        def worker():
            try:
                result = self.project_service.analyze_project()
                self.after(0, lambda: self.dashboard.update_dashboard(result))
                self.after(0, lambda: self._set_status("Analiz tamamlandı."))
                self.after(0, lambda: self.dashboard.progress_card.update_progress(
                    100, "Tamamlandı"
                ))
            except Exception as e:
                self.after(0, lambda: self._set_status(f"Hata: {e}"))
                self.after(0, lambda: messagebox.showerror("Analiz Hatası", str(e)))

        threading.Thread(target=worker, daemon=True).start()

    # ── Arşivleme ───────────────────────────────────────────────────── #

    def _browse_archive_path(self):
        path = filedialog.asksaveasfilename(
            title="Çıktı Konumu Seçin",
            defaultextension=".zip",
            filetypes=[("ZIP Dosyası", "*.zip"), ("Tüm Dosyalar", "*.*")]
        )
        if path:
            self.archive_output.delete(0, "end")
            self.archive_output.insert(0, path)

    def _get_archive_output(self, suffix: str) -> Path:
        raw = self.archive_output.get().strip()
        if raw:
            return Path(raw)
        return self.current_project_path.parent / f"{self.current_project_path.name}{suffix}"

    def _create_zip(self):
        if not self._require_project():
            return
        output = self._get_archive_output(".zip")
        self._set_status("ZIP oluşturuluyor…")
        self.dashboard.progress_card.update_progress(5, "ZIP hazırlanıyor…")

        def worker():
            def on_progress(done, total):
                pct = int(done / total * 100) if total else 0
                self.after(0, lambda p=pct, d=done, t=total:
                           self.dashboard.progress_card.update_progress(
                               p, f"{d} / {t} dosya"
                           ))

            result = self.project_service.archive_service.create_zip(
                self.current_project_path, output,
                progress_callback=on_progress
            )
            self.after(0, lambda: self._handle_zip_result(result, output))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_zip_result(self, result: dict, output: Path):
        self._write_log(self.archive_log, result, output, mode="zip")
        if result["success"]:
            self._set_status(f"ZIP oluşturuldu — {output.name}")
            self.dashboard.progress_card.update_progress(100, "ZIP tamamlandı")
            messagebox.showinfo(
                "Başarılı",
                f"ZIP dosyası oluşturuldu.\n\n"
                f"Konum   : {output}\n"
                f"Eklenen : {result.get('added_files', 0)} dosya\n"
                f"Atlanan : {result.get('skipped_files', 0)} dosya"
            )
        else:
            self._set_status("ZIP oluşturulamadı.")
            messagebox.showerror(
                "Hata",
                f"ZIP oluşturulamadı.\n\n{result.get('error', '')}"
            )

    def _create_copy(self):
        if not self._require_project():
            return
        output = self._get_archive_output("_clean")
        self._set_status("Kopyalanıyor…")
        self.dashboard.progress_card.update_progress(5, "Kopyalama başlatılıyor…")

        def worker():
            def on_progress(done, total):
                pct = int(done / total * 100) if total else 0
                self.after(0, lambda p=pct, d=done, t=total:
                           self.dashboard.progress_card.update_progress(
                               p, f"{d} / {t} dosya"
                           ))

            result = self.project_service.archive_service.copy_project(
                self.current_project_path, output,
                progress_callback=on_progress
            )
            self.after(0, lambda: self._handle_copy_result(result, output))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_copy_result(self, result: dict, output: Path):
        self._write_log(self.archive_log, result, output, mode="copy")
        if result["success"]:
            self._set_status(f"Kopya oluşturuldu — {output.name}")
            self.dashboard.progress_card.update_progress(100, "Kopyalama tamamlandı")
            messagebox.showinfo(
                "Başarılı",
                f"Temiz kopya oluşturuldu.\n\n"
                f"Konum      : {output}\n"
                f"Kopyalanan : {result.get('copied_files', 0)} dosya\n"
                f"Atlanan    : {result.get('skipped_files', 0)} dosya"
            )
        else:
            self._set_status("Kopyalama başarısız.")
            messagebox.showerror(
                "Hata",
                f"Kopyalama başarısız.\n\n{result.get('error', '')}"
            )

    # ── Temizlik ────────────────────────────────────────────────────── #

    def _preview_cleanup(self):
        if not self._require_project():
            return
        preview = self.project_service.cleanup_service.preview_cleanup(
            self.current_project_path
        )
        self.cleanup_log.configure(state="normal")
        self.cleanup_log.delete("1.0", "end")
        self.cleanup_log.insert(
            "end",
            f"Önizleme Sonucu\n"
            f"{'─' * 50}\n"
            f"Toplam : {preview['total_files']} dosya,  "
            f"{preview['total_size'] / 1024:.1f} KB\n\n"
        )
        for f in preview["files"][:50]:
            self.cleanup_log.insert(
                "end",
                f"  {Path(f['path']).name}  ({f['size'] / 1024:.1f} KB)\n"
            )
        if len(preview["files"]) > 50:
            self.cleanup_log.insert(
                "end",
                f"\n  … ve {len(preview['files']) - 50} dosya daha\n"
            )
        self.cleanup_log.configure(state="disabled")

    def _execute_cleanup(self):
        if not self._require_project():
            return
        if not messagebox.askyesno(
            "Onay Gerekli",
            "Bu işlem geri alınamaz.\n\n"
            "Geçici dosyalar ve önbellek klasörleri kalıcı olarak silinecek.\n\n"
            "Devam etmek istiyor musunuz?"
        ):
            return

        self._set_status("Temizlik yapılıyor…")

        def worker():
            result = self.project_service.cleanup_service.cleanup(
                self.current_project_path, dry_run=False
            )
            self.after(0, lambda: self._handle_cleanup_result(result))

        threading.Thread(target=worker, daemon=True).start()

    def _handle_cleanup_result(self, result: dict):
        if result["success"]:
            self._set_status("Temizlik tamamlandı.")
            messagebox.showinfo(
                "Tamamlandı",
                f"Temizlik başarıyla tamamlandı.\n\n"
                f"Silinen  : {result['cleaned_files']} dosya\n"
                f"Kazanılan: {result['cleaned_size'] / 1024:.1f} KB"
            )
            self._preview_cleanup()
        else:
            self._set_status("Temizlik sırasında hata oluştu.")
            messagebox.showerror("Hata", "Temizlik işlemi başarısız oldu.")

    # ================================================================== #
    #  Yardımcılar                                                         #
    # ================================================================== #

    def _require_project(self) -> bool:
        if not self.current_project_path:
            messagebox.showwarning(
                "Proje Seçilmedi",
                "Lütfen önce bir proje dizini açın."
            )
            return False
        return True

    def _set_status(self, text: str):
        self.status_label.configure(text=text)

    def _write_log(self, widget: ctk.CTkTextbox, result: dict,
                   output: Path, mode: str):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        sep = "─" * 50

        if mode == "zip":
            widget.insert("end", f"ZIP İşlemi\n{sep}\n\n")
            widget.insert("end", f"Durum   : {'Başarılı' if result['success'] else 'Başarısız'}\n")
            widget.insert("end", f"Konum   : {output}\n")
            widget.insert("end", f"Eklenen : {result.get('added_files', 0)} dosya\n")
            widget.insert("end", f"Atlanan : {result.get('skipped_files', 0)} dosya\n")
        else:
            widget.insert("end", f"Kopyalama İşlemi\n{sep}\n\n")
            widget.insert("end", f"Durum      : {'Başarılı' if result['success'] else 'Başarısız'}\n")
            widget.insert("end", f"Konum      : {output}\n")
            widget.insert("end", f"Kopyalanan : {result.get('copied_files', 0)} dosya\n")
            widget.insert("end", f"Atlanan    : {result.get('skipped_files', 0)} dosya\n")

        if result.get("error"):
            widget.insert("end", f"\nHata Detayı:\n{result['error']}\n")

        widget.configure(state="disabled")

    def _on_close(self):
        self.destroy()


# ── Giriş Noktası ──────────────────────────────────────────────────────── #

def main():
    app = GitCleanArchiverPro()
    app.mainloop()


if __name__ == "__main__":
    main()
