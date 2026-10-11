"""Kurulum sihirbazı görselleri (`wizard_large.bmp`, `wizard_small.bmp`): XP Luna mavisi zemin üzerinde uygulama simgesi.

Yazı içermez (yazı tipine bağlı kalmaz); `resources/icons/app.png` değişince yeniden üretmek için:
    python packaging/make_wizard_images.py
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PySide6.QtCore import QPointF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QGuiApplication, QImage, QLinearGradient, QPainter  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ICON = ROOT / "resources" / "icons" / "app.png"
OUT = Path(__file__).resolve().parent

LUNA_TOP, LUNA_BOTTOM = QColor("#0A5BEB"), QColor("#0B3FA8")     # AppTheme.titleTop / koyu uç
BEIGE = QColor("#ECE9D8")                                         # AppTheme.bg


def render(width: int, height: int, icon: QImage, icon_size: int, top: int, gradient: bool) -> QImage:
    image = QImage(width, height, QImage.Format.Format_RGB32)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    if gradient:
        fill = QLinearGradient(QPointF(0, 0), QPointF(0, height))
        fill.setColorAt(0.0, LUNA_TOP)
        fill.setColorAt(1.0, LUNA_BOTTOM)
        painter.fillRect(0, 0, width, height, fill)
        painter.fillRect(width - 3, 0, 3, height, QColor("#FFC73C"))       # XP sarı vurgu çizgisi
    else:
        painter.fillRect(0, 0, width, height, BEIGE)
    scaled = icon.scaled(icon_size, icon_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    painter.drawImage((width - scaled.width()) // 2, top, scaled)
    painter.end()
    return image


def main() -> int:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)   # noqa: F841  (QImage için uygulama nesnesi)
    icon = QImage(str(ICON))
    if icon.isNull():
        print(f"Simge okunamadı: {ICON}")
        return 1
    # Inno Setup: büyük görsel 164x314 (sihirbazın ilk / son sayfası), küçük görsel 55x55 (üst sağ köşe)
    render(164, 314, icon, 120, 40, gradient=True).save(str(OUT / "wizard_large.bmp"), "BMP")
    render(55, 55, icon, 44, 5, gradient=False).save(str(OUT / "wizard_small.bmp"), "BMP")
    print("Yazıldı:", OUT / "wizard_large.bmp", OUT / "wizard_small.bmp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
