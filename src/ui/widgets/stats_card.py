from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QGraphicsDropShadowEffect
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt

class StatsCard(QFrame):
    """Gölge efektli ve net çerçeveli kompakt kurumsal istatistik kartı."""
    
    _ICON_COLORS = {"📄": "#2563EB", "💾": "#7C3AED", "📁": "#EA580C", "⚠️": "#DC2626"}

    def __init__(self, parent, title: str, value: str, icon: str = "📊", **kwargs):
        super().__init__(parent)
        self.setObjectName("card")
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        
        # Soft Gölgelendirme (Shadow) Entegrasyonu
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 35)) # Hafif soluk kurumsal gölge
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)
        
        icon_color = self._ICON_COLORS.get(icon, "#2563EB")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        self.icon_lbl = QLabel(icon, self)
        self.icon_lbl.setStyleSheet(f"color: {icon_color}; font-size: 18px;")
        top_row.addWidget(self.icon_lbl)

        self.title_lbl = QLabel(title.upper(), self)
        self.title_lbl.setStyleSheet("color: #334155; font-size: 11px; font-weight: 800; letter-spacing: 0.5px;")
        top_row.addWidget(self.title_lbl, stretch=1)
        layout.addLayout(top_row)

        self._value_lbl = QLabel(str(value), self)
        self._value_lbl.setStyleSheet("color: #0F172A; font-size: 24px; font-weight: 800; margin-top: 2px;")
        layout.addWidget(self._value_lbl)

    def update_value(self, new_value: str):
        self._value_lbl.setText(str(new_value))