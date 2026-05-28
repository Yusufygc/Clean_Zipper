from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar
from PySide6.QtCore import Qt
from typing import Dict

class HistogramChartWidget(QWidget):
    """Dosya türü dağılımı için kurumsal dikey/yatay çubuk histogram widget'ı."""
    
    def __init__(self, parent=None, data: Dict[str, float] = None, title: str = "Dosya Türü Dağılımı"):
        super().__init__(parent)
        self.data = data or {}
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.main_layout.setSpacing(10)
        
        self.title_lbl = QLabel(title, self)
        self.title_lbl.setStyleSheet("font-weight: 800; font-size: 14px; color: #0F172A;")
        self.title_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.main_layout.addWidget(self.title_lbl)
        
        self.bars_container = QWidget(self)
        self.bars_layout = QVBoxLayout(self.bars_container)
        self.bars_layout.setContentsMargins(0, 0, 0, 0)
        self.bars_layout.setSpacing(8)
        self.main_layout.addWidget(self.bars_container)
        
        if self.data:
            self.update_data(self.data)

    def update_data(self, new_data: Dict[str, float]):
        self.data = new_data
        
        # Temizle
        while self.bars_layout.count():
            item = self.bars_layout.takeAt(0)
            w = item.widget()
            if w: w.deleteLater()
            
        total = sum(self.data.values())
        if total == 0: return

        # En yüksek ilk 6 türü listele
        sorted_data = sorted(self.data.items(), key=lambda x: x[1], reverse=True)[:6]
        
        for ext, count in sorted_data:
            pct = (count / total) * 100
            
            row = QWidget(self.bars_container)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(10)
            
            # Uzantı Etiketi (Büyük ve Parlak)
            ext_name = ext if ext else "uzantisiz"
            lbl_ext = QLabel(f"<b>{ext_name}</b>", row)
            lbl_ext.setFixedWidth(75)
            lbl_ext.setStyleSheet("font-size: 12px; color: #1E293B;")
            row_layout.addWidget(lbl_ext)
            
            # Histogram Çubuğu
            bar = QProgressBar(row)
            bar.setRange(0, 100)
            bar.setValue(int(pct))
            bar.setFixedHeight(14)
            bar.setTextVisible(False)
            bar.setStyleSheet("""
                QProgressBar { background-color: #E2E8F0; border: none; border-radius: 4px; }
                QProgressBar::chunk { background-color: #2563EB; border-radius: 4px; }
            """)
            row_layout.addWidget(bar, stretch=1)
            
            # Yüzde ve Adet Skoru
            lbl_val = QLabel(f"{pct:.1f}% ({count} adet)", row)
            lbl_val.setStyleSheet("font-size: 12px; font-weight: 600; color: #475569;")
            lbl_val.setFixedWidth(110)
            row_layout.addWidget(lbl_val)
            
            self.bars_layout.addWidget(row)