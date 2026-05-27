import customtkinter as ctk
import math
from typing import Dict


_CANVAS_BG   = "#EBEBEB"
_TRACK_COLOR = "#D5D5D5"

# Kurumsal, profesyonel renk paleti (light arka plan üstünde okunabilir)
_SLICE_COLORS = [
    "#1565C0",  # koyu mavi
    "#2E7D32",  # koyu yeşil
    "#6A1B9A",  # koyu mor
    "#E65100",  # koyu turuncu
    "#00838F",  # koyu camgöbeği
    "#AD1457",  # koyu pembe
    "#558B2F",  # zeytin yeşili
    "#4527A0",  # derin mor
    "#00695C",  # zümrüt
    "#283593",  # lacivert
]


class PieChartWidget(ctk.CTkFrame):
    """Light tema uyumlu, legend'lı donut pasta grafik widget'ı."""

    def __init__(self, parent, data: Dict[str, float] = None,
                 title: str = "Dağılım", size: int = 200, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.data = data or {}
        self.title = title
        self.size = size

        ctk.CTkLabel(
            self, text=title,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=("gray20", "gray80")
        ).pack(pady=(8, 4))

        self.canvas = ctk.CTkCanvas(
            self, width=size, height=size,
            highlightthickness=0, bg=_CANVAS_BG
        )
        self.canvas.pack()

        self.legend_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.legend_frame.pack(fill="x", padx=10, pady=(6, 8))

        if self.data:
            self._draw_chart()

    # ------------------------------------------------------------------ #

    def _draw_chart(self):
        self.canvas.delete("all")
        if not self.data:
            return

        total = sum(self.data.values())
        if total == 0:
            return

        s = self.size
        cx, cy   = s // 2, s // 2
        r        = s // 2 - 12
        inner_r  = r * 0.50

        start = 90.0
        slice_data = []
        for i, (label, value) in enumerate(self.data.items()):
            if value <= 0:
                continue
            extent = (value / total) * 360.0
            color  = _SLICE_COLORS[i % len(_SLICE_COLORS)]
            slice_data.append((label, value, extent, color))

        # Dış çerçeve
        self.canvas.create_oval(
            cx - r - 1, cy - r - 1, cx + r + 1, cy + r + 1,
            outline=_TRACK_COLOR, width=1, fill=""
        )

        for label, value, extent, color in slice_data:
            self.canvas.create_arc(
                cx - r, cy - r, cx + r, cy + r,
                start=start, extent=-extent,
                fill=color, outline=_CANVAS_BG, width=2
            )
            # Yüzde etiketi (dilim yeterince büyükse)
            pct = (value / total) * 100
            if pct > 8:
                mid_angle = math.radians(start - extent / 2)
                lx = cx + (r * 0.68) * math.cos(mid_angle)
                ly = cy - (r * 0.68) * math.sin(mid_angle)
                self.canvas.create_text(
                    lx, ly,
                    text=f"{pct:.0f}%",
                    font=("Segoe UI", 8, "bold"),
                    fill="white"
                )
            start -= extent

        # Donut deliği
        self.canvas.create_oval(
            cx - inner_r, cy - inner_r,
            cx + inner_r, cy + inner_r,
            fill=_CANVAS_BG, outline=_CANVAS_BG
        )

        # Merkez: en büyük kategori etiketi
        if slice_data:
            top_label, top_val, _, top_color = max(slice_data, key=lambda x: x[1])
            pct = (top_val / total) * 100
            self.canvas.create_text(
                cx, cy - 9,
                text=f"{pct:.0f}%",
                font=("Segoe UI", 12, "bold"),
                fill=top_color
            )
            short = top_label[:9] + "…" if len(top_label) > 9 else top_label
            self.canvas.create_text(
                cx, cy + 10,
                text=short,
                font=("Segoe UI", 8),
                fill="#666666"
            )

        self._build_legend(slice_data, total)

    def _build_legend(self, slice_data, total):
        for w in self.legend_frame.winfo_children():
            w.destroy()

        grid = ctk.CTkFrame(self.legend_frame, fg_color="transparent")
        grid.pack()

        for i, (label, value, _, color) in enumerate(slice_data[:6]):
            pct  = (value / total) * 100
            cell = ctk.CTkFrame(grid, fg_color="transparent")
            cell.grid(row=i // 2, column=i % 2, sticky="w", padx=4, pady=1)

            ctk.CTkFrame(
                cell, width=10, height=10,
                corner_radius=2, fg_color=color
            ).pack(side="left", padx=(0, 4))

            short = label[:11] + "…" if len(label) > 11 else label
            ctk.CTkLabel(
                cell,
                text=f"{short}  {pct:.0f}%",
                font=ctk.CTkFont(family="Segoe UI", size=10),
                text_color="gray30"
            ).pack(side="left")

    def update_data(self, new_data: Dict[str, float]):
        self.data = new_data
        self._draw_chart()
