from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QPaintEvent
from PySide6.QtCore import Qt, QTimer, QRectF

class HealthScoreWidget(QWidget):
    """Animasyonlu dairesel sağlık skoru göstergesi (PySide6 QPainter ile modernize edilmiş)."""

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

    def __init__(self, parent, score: float = 0, status: str = "—", size: int = 180, **kwargs):
        super().__init__(parent)
        self.score = score
        self.status = status
        self.size = size
        self._animated_score = 0.0
        self._timer = None

        self.setFixedSize(size, size)
        self.update_score(score, status)

    def _get_score_color(self, score: float) -> str:
        for (lo, hi), color in self.GRADE_COLORS.items():
            if lo <= score <= hi:
                return color
        return "#C62828"

    def paintEvent(self, event: QPaintEvent):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx = self.width() / 2.0
        cy = self.height() / 2.0
        r = (self.width() - 28) / 2.0  # radius with padding
        track_w = 12.0
        rect = QRectF(cx - r, cy - r, 2 * r, 2 * r)

        color = QColor(self._get_score_color(self.score))

        # 1. Background Track Circle
        pen_track = QPen(QColor("#2E3035"), track_w)
        painter.setPen(pen_track)
        painter.drawEllipse(rect)

        # 2. Foreground Score Arc
        if self._animated_score > 0:
            pen_arc = QPen(color, track_w)
            pen_arc.setCapStyle(Qt.PenCapStyle.RoundCap) # Round caps for a premium look
            painter.setPen(pen_arc)
            # Start at top (90 degrees) and sweep clockwise (negative)
            start_angle = 90 * 16
            span_angle = int(-(self._animated_score / 100.0) * 360.0 * 16)
            painter.drawArc(rect, start_angle, span_angle)

        # 3. Draw Inner Texts
        # Score Value
        painter.setPen(color)
        font_score = QFont("Segoe UI", 28, QFont.Weight.Bold)
        painter.setFont(font_score)
        rect_score = QRectF(0, cy - 36, self.width(), 40)
        painter.drawText(rect_score, Qt.AlignmentFlag.AlignCenter, f"{self.score:.0f}")

        # Status Grade
        font_status = QFont("Segoe UI", 11, QFont.Weight.Bold)
        painter.setFont(font_status)
        rect_status = QRectF(0, cy + 10, self.width(), 20)
        painter.drawText(rect_status, Qt.AlignmentFlag.AlignCenter, self.status)

        # /100 indicator
        painter.setPen(QColor("#8E8F94"))
        font_sub = QFont("Segoe UI", 9)
        painter.setFont(font_sub)
        rect_sub = QRectF(0, cy + 28, self.width(), 20)
        painter.drawText(rect_sub, Qt.AlignmentFlag.AlignCenter, "/100")

    def _animate(self, target: float, step: float = 4.0):
        if self._timer:
            self._timer.stop()

        self._animated_score = 0.0
        
        def step_anim():
            if self._animated_score < target:
                self._animated_score = min(self._animated_score + step, target)
                self.update()
            else:
                self._animated_score = target
                self.update()
                self._timer.stop()

        self._timer = QTimer(self)
        self._timer.timeout.connect(step_anim)
        self._timer.start(16)  # ~60 FPS

    def update_score(self, new_score: float, new_status: str = None):
        self.score = new_score
        if new_status:
            self.status = new_status
        self._animate(new_score)
