import customtkinter as ctk


class ProgressCard(ctk.CTkFrame):
    """Flicker-free ilerleme çubuğu kartı."""

    def __init__(self, parent, title: str = "", value: float = 0,
                 status: str = "", height: int = 70, **kwargs):
        super().__init__(parent, height=height, corner_radius=10, **kwargs)

        self._value = max(0.0, min(100.0, value))
        self._status = status

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=14, pady=8)

        hdr = ctk.CTkFrame(inner, fg_color="transparent")
        hdr.pack(fill="x")

        if title:
            ctk.CTkLabel(
                hdr, text=title,
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
            ).pack(side="left")

        self._status_lbl = ctk.CTkLabel(
            hdr, text=self._status,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=("gray40", "gray60")
        )
        self._status_lbl.pack(side="right")

        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x", pady=(4, 0))

        self._pb = ctk.CTkProgressBar(row, height=10, corner_radius=5)
        self._pb.pack(side="left", fill="x", expand=True)
        self._pb.set(self._value / 100)

        self._pct_lbl = ctk.CTkLabel(
            row,
            text=f"{self._value:.0f}%",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            width=42
        )
        self._pct_lbl.pack(side="right", padx=(8, 0))

    def update_progress(self, value: float, status: str = None):
        self._value = max(0.0, min(100.0, value))
        if status is not None:
            self._status = status
            self._status_lbl.configure(text=self._status)
        self._pb.set(self._value / 100)
        self._pct_lbl.configure(text=f"{self._value:.0f}%")
