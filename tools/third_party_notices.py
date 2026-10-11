"""THIRD_PARTY_NOTICES.md üretir: dağıtılan uygulamanın içindeki üçüncü taraf bileşenlerin lisansları.

Kullanım (bağımlılık değişince yeniden üret; `tests/unit/test_release_packaging.py` sürümlerin güncelliğini denetler):
    python tools/third_party_notices.py

Kaynak: `requirements.txt` (çalışma zamanı) + PySide6'nın bağımlılığı shiboken6; lisans metinleri kurulu paketlerin `dist-info/licenses` klasöründen alınır.
LGPL / MPL bileşenlerde tam metin yerine resmî adres ve kaynak kodun nereden alınacağı yazılır.
"""
import re
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "THIRD_PARTY_NOTICES.md"

# paket -> (lisans, kaynak adresi, tam metin gömülsün mü)
COMPONENTS = {
    "PySide6-Essentials": ("LGPL-3.0-only (Qt for Python)", "https://pyside.org", False),
    "shiboken6": ("LGPL-3.0-only (Qt for Python)", "https://pyside.org", False),
    "pathspec": ("MPL-2.0", "https://github.com/cpburnz/python-pathspec", False),
    "Send2Trash": ("BSD-3-Clause", "https://github.com/arsenetar/send2trash", True),
    "tomli": ("MIT", "https://github.com/hukkin/tomli", True),
}

HEADER = """# Üçüncü taraf bileşenler ve lisansları

GitClean Archiver, [MIT lisansı](LICENSE) altındadır. Dağıtılan uygulama (PyInstaller paketi) aşağıdaki bileşenleri içerir.
Bu dosya `python tools/third_party_notices.py` ile üretilir.

## Qt (PySide6 / shiboken6): LGPL-3.0

Arayüz Qt 6 ile (Qt for Python, PySide6-Essentials) çizilir; Qt, **GNU LGPL sürüm 3** koşulları altında kullanılır
([metin](https://www.gnu.org/licenses/lgpl-3.0.html)). Uygulama klasör olarak dağıtılır (`--onedir`): Qt kütüphaneleri `_internal` klasöründe
ayrı dosyalardır ve değiştirilmiş bir Qt sürümüyle değiştirilebilir (yeniden bağlama hakkı). Qt ve PySide6 kaynak kodu:
<https://code.qt.io> ve <https://pyside.org>. Qt'nin ticari lisansı kullanılmaz.

## Python ve PyInstaller

- **Python** ([PSF License](https://docs.python.org/3/license.html)): paketlenmiş yorumlayıcı ve standart kitaplık.
- **PyInstaller** ([GPL-2.0-or-later, derlenen uygulamanın dağıtımına izin veren özel istisnayla](https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt)):
  yalnızca paketleme aracı ve açılış yükleyicisi.

"""


def license_text(distribution) -> str:
    for file in distribution.files or []:
        name = str(file).replace("\\", "/")
        if "/licenses/" in name and Path(name).name.upper().startswith(("LICENSE", "COPYING")):
            return distribution.locate_file(file).read_text(encoding="utf-8").strip()
    return ""


def render() -> str:
    lines = [HEADER.rstrip("\n"), "", "## Python paketleri", ""]
    for package, (license_name, url, embed) in COMPONENTS.items():
        distribution = metadata.distribution(package)
        lines += [f"### {package} {distribution.version}", "", f"- Lisans: {license_name}", f"- Kaynak: <{url}>", ""]
        if embed:
            lines += ["```text", license_text(distribution), "```", ""]
        elif license_name.startswith("MPL"):
            lines += ["Bu bileşen değiştirilmeden kullanılır; kaynak kodu yukarıdaki adresten ve PyPI'dan alınabilir "
                      "([MPL-2.0 metni](https://www.mozilla.org/en-US/MPL/2.0/)).", ""]
    return "\n".join(lines).rstrip("\n") + "\n"


def requirement_versions() -> dict:
    """`requirements.txt` içindeki `paket==sürüm` satırları (ortam koşulu olanlar dahil)."""
    versions = {}
    for line in (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Za-z0-9_.-]+)==([^;\s]+)", line)
        if match:
            versions[match.group(1)] = match.group(2)
    return versions


if __name__ == "__main__":
    OUTPUT.write_bytes(render().encode("utf-8"))
    print("Yazıldı:", OUTPUT)
