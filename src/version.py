"""Uygulama sürümü ve yayın deposu: tek kaynak.

Sürüm yükseltme `tools/release.py` ile yapılır (bu dosya, `version_info.txt`, `AppStrings.qml` ve README rozeti birlikte güncellenir);
`tests/unit/test_version.py` kaynakların tutarlılığını denetler.
"""
__version__ = "2.0.0"

APP_NAME = "GitClean Archiver"
RELEASE_REPO = "Yusufygc/Clean_Zipper"      # GitHub "sahip/depo": güncelleme denetimi bu deponun son sürümüne bakar
