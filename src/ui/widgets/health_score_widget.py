import customtkinter as ctk
import math


# Light temada CTkFrame'in varsayılan arka plan rengi
_CANVAS_BG = "#EBEBEB"
_TRACK_COLOR = "#D5D5D5"


class HealthScoreWidget(ctk.CTkFrame):
    """Animasyonlu dairesel sağlık skoru göstergesi (light tema sabit)."""

    GRADE_COLORS = {
        (95, 100): "#00C853",  # A+ Mükemmel
        (85, 94):  "#2E7D32",  # A  İyi
        (75, 84):  "#558B2F",  # B+ Ortalama Üstü
        (65, 74):  "#F9A825",  # B  Ortalama
        (55, 64):  "#EF6C00",  # C+ Ortalama Altı
        (45, 54):  "#E64A19",  # C  Zayıf
        (35, 44):  "#C62828",  # D  Kritik
        (0,  34):  "#B71C1C",  # F  Başarısız
    }

    def __init__(self, parent, score: float = 0, status: str = "—",
                 size: int = 180, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.score = score
        self.status = status
        self.size = size
        self._animated_score = 0.0
        self._animation_id = None

        self.canvas = ctk.CTkCanvas(
            self, width=size, height=size,
            highlightthickness=0, bg=_CANVAS_BG
        )
        self.canvas.pack(padx=10, pady=10)
        self._draw_score()

    # ------------------------------------------------------------------ #

    def _get_score_color(self, score: float) -> str:
        for (lo, hi), color in self.GRADE_COLORS.items():
            if lo <= score <= hi:
                return color
        return "#C62828"

    def _draw_score(self):
        self.canvas.delete("all")
        s = self.size
        cx, cy = s // 2, s // 2
        r = s // 2 - 18
        track_w = 14

        color = self._get_score_color(self.score)

        # Arka plan halkası
        self.canvas.create_oval(
            cx - r, cy - r, cx + r, cy + r,
            outline=_TRACK_COLOR, width=track_w, fill=_CANVAS_BG
        )

        # Skor yayı
        if self._animated_score > 0:
            extent = -(self._animated_score / 100) * 359.9
            self.canvas.create_arc(
                cx - r, cy - r, cx + r, cy + r,
                start=90, extent=extent,
                outline=color, width=track_w, style="arc"
            )

        # İç delik
        ir = r - track_w // 2 - 4
        self.canvas.create_oval(
            cx - ir, cy - ir, cx + ir, cy + ir,
            outline=_TRACK_COLOR, width=1, fill=_CANVAS_BG
        )

        # Skor rakamı
        self.canvas.create_text(
            cx, cy - 16,
            text=f"{self.score:.0f}",
            font=("Segoe UI", 28, "bold"),
            fill=color
        )
        # Grade etiketi
        self.canvas.create_text(
            cx, cy + 14,
            text=self.status,
            font=("Segoe UI", 12, "bold"),
            fill=color
        )
        # /100
        self.canvas.create_text(
            cx, cy + 34,
            text="/100",
            font=("Segoe UI", 9),
            fill="#AAAAAA"
        )

    def _animate(self, target: float, step: float = 4.0):
        if self._animation_id:
            self.after_cancel(self._animation_id)
        if self._animated_score < target:
            self._animated_score = min(self._animated_score + step, target)
            self._draw_score()
            self._animation_id = self.after(16, lambda: self._animate(target, step))
        else:
            self._animated_score = target
            self._draw_score()

    def update_score(self, new_score: float, new_status: str = None):
        self.score = new_score
        if new_status:
            self.status = new_status
        self._animated_score = 0.0
        self._animate(new_score)
