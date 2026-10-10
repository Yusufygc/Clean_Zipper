"""Hangi klasörlere girilmeyeceği: analiz (ProjectIndex), temizlik, arşiv ve yedek aynı kuralı kullanır."""
import fnmatch
import os
import stat
from typing import AbstractSet, FrozenSet, Iterable

from src.core.constants import CONDITIONAL_EXCLUDED_DIRS, EXCLUDED_DIRS, VIRTUALENV_MARKER

# Windows yeniden ayrıştırma etiketleri: dizin birleşimi / bağlama noktası (junction) ve sembolik bağ.
# OneDrive gibi bulut yer tutucuları da yeniden ayrıştırma noktasıdır ama başka etiket taşır; onlar normal klasördür.
_LINK_REPARSE_TAGS = frozenset({0xA0000003, 0xA000000C})


def _lowered(names: AbstractSet[str]) -> FrozenSet[str]:
    return frozenset(n.lower() for n in names)


_EXCLUDED_LOWER = _lowered(EXCLUDED_DIRS)


def is_link(path) -> bool:
    """Sembolik bağ ya da Windows dizin birleşimi (junction): proje dışına ya da kendi üstüne (döngü) işaret edebilir.

    Python 3.10'da `os.walk` / `DirEntry.is_symlink` junction'ı normal klasör sanar; bu yüzden etiketine bakılır.
    """
    try:
        st = os.lstat(path)
    except OSError:
        return False
    return stat.S_ISLNK(st.st_mode) or getattr(st, 'st_reparse_tag', 0) in _LINK_REPARSE_TAGS


def is_excluded_dir(dir_path: str, name: str, sibling_names: Iterable[str],
                    excluded: AbstractSet[str] = EXCLUDED_DIRS) -> bool:
    """True ise klasöre girilmez.

    - `excluded` kümesindeki adlar (venv, node_modules, .next ...)
    - bağlamsal adlar: yanında derleme sistemi dosyası olan `target`, `.csproj` olan `bin`/`obj`
    - adı ne olursa olsun `pyvenv.cfg` içeren klasörler (Python sanal ortamı, ör. `myenv`)
    - sembolik bağ ve junction klasörler (proje dışını taramak, temizlemek, arşive koymak; döngü)
    `sibling_names`: aynı üst klasördeki tüm girdi adları.
    """
    lowered = name.lower()                       # Windows / macOS dosya sistemi harf duyarsız: `Build`, `Dist`, `Bin`
    if lowered in (_EXCLUDED_LOWER if excluded is EXCLUDED_DIRS else _lowered(excluded)):
        return True
    patterns = CONDITIONAL_EXCLUDED_DIRS.get(lowered)
    if patterns:
        siblings = list(sibling_names)
        if any(fnmatch.fnmatch(sibling, pattern) for sibling in siblings for pattern in patterns):
            return True
    return is_link(dir_path) or os.path.isfile(os.path.join(dir_path, VIRTUALENV_MARKER))
