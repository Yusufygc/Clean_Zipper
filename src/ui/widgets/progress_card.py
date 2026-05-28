from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt

class ProgressCard(QFrame):
    """Flicker-free kalınlaştırılmış ve gradyan uyumlu ilerleme çubuğu kartı."""

    def __init__(self, parent, title: str = "", value: float = 0, status: str = "", **kwargs):
        super().__init__(parent)
        self.setObjectName("card")  # Matches style.qss targeting QFrame#card
        
        self._value = max(0.0, min(100.0, value))
        self._status = status

        # Main Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        # Header Row: title on left, status on right
        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 0)

        if title:
            self._title_lbl = QLabel(title, self)
            self._title_lbl.setStyleSheet("font-weight: 800; font-size: 13px; color: #0F172A;")
            hdr.addWidget(self._title_lbl)

        hdr.addStretch()

        self._status_lbl = QLabel(self._status, self)
        self._status_lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #475569;")
        hdr.addWidget(self._status_lbl)

        layout.addLayout(hdr)

        # Progress Row
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        self._pb = QProgressBar(self)
        self._pb.setRange(0, 100)
        self._pb.setValue(int(self._value))
        self._pb.setFixedHeight(22) # Daha kalın progress bar
        self._pb.setTextVisible(True) # Barın iç metnini aktif et
        self._pb.setAlignment(Qt.AlignmentFlag.AlignCenter) # Metni tam ortaya hizala
        row.addWidget(self._pb, stretch=1)

        # Not: Siyah dış yüzde etiketi kaldırıldı, artık metin beyaz renkte barın içinde ortalanmıştır.

        layout.addLayout(row)

    def update_progress(self, value: float, status: str = None):
        self._value = max(0.0, min(100.0, value))
        if status is not None:
            self._status = status
            self._status_lbl.setText(self._status)
        self._pb.setValue(int(self._value))