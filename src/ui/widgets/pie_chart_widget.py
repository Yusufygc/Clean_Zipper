import math
from typing import Dict
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPaintEvent
from PySide6.QtCore import Qt, QRectF

_SLICE_COLORS = [
    "#2563EB", "#16A34A", "#7C3AED", "#EA580C", "#06B6D4",
    "#DB2777", "#4D7C0F", "#4338CA", "#0F766E", "#1E3A8A"
]

class PieCanvas(QWidget):
    def __init__(self, parent=None, size: int = 200):
        super().__init__(parent)
        self.size = size
        self.data_dict = {}
        self.setFixedSize(size, size)

    def set_data(self, data: Dict[str, float]):
        self.data_dict = data
        self.update()

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self.data_dict:
            return

        total = sum(self.data_dict.values())
        if total == 0:
            return

        s = self.size
        cx, cy = s / 2.0, s / 2.0
        r = s / 2.0 - 12.0
        inner_r = r * 0.55  # Donut boşluğu kurumsal oran

        rect = QRectF(cx - r, cy - r, 2 * r, 2 * r)

        # Net Çizgi Çeperi
        painter.setPen(QPen(QColor("#E2E8F0"), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(rect)

        start = 90.0
        slice_data = []
        for i, (label, value) in enumerate(self.data_dict.items()):
            if value <= 0:
                continue
            extent = (value / total) * 360.0
            color = _SLICE_COLORS[i % len(_SLICE_COLORS)]
            slice_data.append((label, value, extent, color))

        for label, value, extent, color in slice_data:
            painter.setPen(QPen(QColor("#FFFFFF"), 2))  # Dilimler arası beyaz kurumsal şerit
            painter.setBrush(QBrush(QColor(color)))
            painter.drawPie(rect, int(start * 16), int(-extent * 16))

            pct = (value / total) * 100.0
            if pct > 8:
                mid_angle = math.radians(start - extent / 2.0)
                lx = cx + (r * 0.72) * math.cos(mid_angle)
                ly = cy - (r * 0.72) * math.sin(mid_angle)

                painter.setPen(QColor("#FFFFFF"))
                painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
                painter.drawText(QRectF(lx - 20, ly - 8, 40, 16), Qt.AlignmentFlag.AlignCenter, f"{pct:.0f}%")

            start -= extent

        # Donut Deliği - SAF BEYAZA BOYANDI (Light Tema Uyumu)
        inner_rect = QRectF(cx - inner_r, cy - inner_r, 2 * inner_r, 2 * inner_r)
        painter.setPen(QPen(QColor("#E2E8F0"), 1))
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(inner_rect)

        if slice_data:
            top_label, top_val, _, top_color = max(slice_data, key=lambda x: x[1])
            pct = (top_val / total) * 100.0

            painter.setPen(QColor(top_color))
            painter.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
            painter.drawText(QRectF(cx - inner_r, cy - 14, 2 * inner_r, 18), Qt.AlignmentFlag.AlignCenter, f"{pct:.0f}%")

            short = top_label[:9] + "…" if len(top_label) > 9 else top_label
            painter.setPen(QColor("#64748B"))
            painter.setFont(QFont("Segoe UI", 9, QFont.Weight.Medium))
            painter.drawText(QRectF(cx - inner_r, cy + 6, 2 * inner_r, 14), Qt.AlignmentFlag.AlignCenter, short)

class PieChartWidget(QWidget):
    def __init__(self, parent=None, data: Dict[str, float] = None, title: str = "Dağılım", size: int = 210, **kwargs):
        super().__init__(parent)
        self.data = data or {}
        self.title = title
        self.size = size

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(10)

        self.title_lbl = QLabel(self.title, self)
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_lbl.setStyleSheet("font-weight: 700; font-size: 14px; color: #1E293B;")
        self.layout.addWidget(self.title_lbl)

        self.canvas = PieCanvas(self, size=self.size)
        self.layout.addWidget(self.canvas, alignment=Qt.AlignmentFlag.AlignCenter)

        self.legend_widget = QWidget(self)
        self.legend_layout = QGridLayout(self.legend_widget)
        self.legend_layout.setContentsMargins(4, 4, 4, 4)
        self.legend_layout.setHorizontalSpacing(16)
        self.legend_layout.setVerticalSpacing(6)
        self.layout.addWidget(self.legend_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        if self.data:
            self.update_data(self.data)

    def update_data(self, new_data: Dict[str, float]):
        self.data = new_data
        self.canvas.set_data(new_data)
        self._build_legend()

    def _build_legend(self):
        while self.legend_layout.count():
            item = self.legend_layout.takeAt(0)
            widget = item.widget()
            if widget: widget.deleteLater()

        if not self.data: return
        total = sum(self.data.values())
        if total == 0: return

        slice_data = []
        for i, (label, value) in enumerate(self.data.items()):
            if value <= 0: continue
            color = _SLICE_COLORS[i % len(_SLICE_COLORS)]
            slice_data.append((label, value, color))

        for i, (label, value, color) in enumerate(slice_data[:6]):
            pct = (value / total) * 100.0
            
            cell = QWidget(self.legend_widget)
            cell_layout = QHBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(8)

            marker = QFrame(cell)
            marker.setFixedSize(12, 12)
            marker.setStyleSheet(f"background-color: {color}; border-radius: 3px;")
            cell_layout.addWidget(marker)

            short = label[:12] + "…" if len(label) > 12 else label
            lbl = QLabel(f"<b>{short}</b>  {pct:.0f}%", cell)
            lbl.setStyleSheet("font-size: 11px; color: #334155;")
            cell_layout.addWidget(lbl)

            row = i // 2
            col = i % 2
            self.legend_layout.addWidget(cell, row, col)