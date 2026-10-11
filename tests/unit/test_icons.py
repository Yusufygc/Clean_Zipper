"""Uygulama ikonu: `build_icons.py` ile üretilen ICO tüm boyutları içermeli ve çözülebilmeli (EXE ve görev çubuğu bunu kullanır)."""
import struct
from pathlib import Path

from PySide6.QtGui import QImage

ICONS = Path(__file__).resolve().parents[2] / "resources" / "icons"
SIZES = [16, 24, 32, 48, 64, 128, 256]


def ico_entries():
    data = (ICONS / "app_icon.ico").read_bytes()
    reserved, kind, count = struct.unpack("<HHH", data[:6])
    assert (reserved, kind) == (0, 1)
    for i in range(count):
        width, _, _, _, _, bits, length, offset = struct.unpack("<BBBBHHII", data[6 + 16 * i:22 + 16 * i])
        yield (width or 256), bits, data[offset:offset + length]


def test_ico_has_every_size_decodable_with_transparency():
    entries = list(ico_entries())
    assert [size for size, _, _ in entries] == SIZES
    for size, bits, blob in entries:
        image = QImage.fromData(blob, "PNG")
        assert (image.width(), image.height()) == (size, size) and bits == 32 and image.hasAlphaChannel()
        assert image.pixelColor(0, 0).alpha() == 0                      # köşe saydam: kalkan dışı arka plan yok


def test_png_and_svg_sources_are_consistent():
    png = QImage(str(ICONS / "app.png"))
    assert (png.width(), png.height()) == (1024, 1024) and png.hasAlphaChannel()
    svg = (ICONS / "app.svg").read_text(encoding="utf-8")
    assert svg.startswith("<svg") and 'viewBox="0 0 1024 1024"' in svg
