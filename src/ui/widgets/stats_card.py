import customtkinter as ctk


class StatsCard(ctk.CTkFrame):
    """Nötr, minimal kurumsal istatistik kartı."""

    # İkona göre nötr ikon renkleri (bant yok, değer rengi yok)
    _ICON_COLORS = {
        "📄": "#1565C0",
        "💾": "#6A1B9A",
        "📁": "#E65100",
        "⚠️": "#C62828",
    }

    def __init__(self, parent, title: str, value: str, icon: str = "📊",
                 width: int = 170, height: int = 90, **kwargs):
        super().__init__(
            parent, width=width, height=height,
            corner_radius=8,
            border_width=1,
            border_color=("gray80", "gray30"),
            **kwargs
        )
        self.pack_propagate(False)

        icon_color = self._ICON_COLORS.get(icon, "#1565C0")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=14, pady=10)

        # Üst satır: ikon solda, başlık sağda
        top_row = ctk.CTkFrame(body, fg_color="transparent")
        top_row.pack(fill="x")

        ctk.CTkLabel(
            top_row, text=icon,
            font=ctk.CTkFont(size=18),
            text_color=icon_color
        ).pack(side="left")

        ctk.CTkLabel(
            top_row, text=title.upper(),
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color="gray50"
        ).pack(side="right", pady=(4, 0))

        # Değer — büyük, koyu, nötr
        self._value_lbl = ctk.CTkLabel(
            body, text=str(value),
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=("gray10", "gray90"),
            anchor="w"
        )
        self._value_lbl.pack(fill="x", pady=(4, 0))

    def update_value(self, new_value: str):
        self._value_lbl.configure(text=str(new_value))
