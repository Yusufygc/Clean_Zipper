"""Hangi klasörlere girilmeyeceği: analiz (ProjectIndex) ve arşivleme aynı kuralı kullanır."""
import fnmatch
import os
from typing import AbstractSet, FrozenSet, Iterable

from src.core.constants import CONDITIONAL_EXCLUDED_DIRS, EXCLUDED_DIRS, VIRTUALENV_MARKER


def _lowered(names: AbstractSet[str]) -> FrozenSet[str]:
    return frozenset(n.lower() for n in names)


_EXCLUDED_LOWER = _lowered(EXCLUDED_DIRS)


def is_excluded_dir(dir_path: str, name: str, sibling_names: Iterable[str],
                    excluded: AbstractSet[str] = EXCLUDED_DIRS) -> bool:
    """True ise klasöre girilmez.

    - `excluded` kümesindeki adlar (venv, node_modules, .next ...)
    - bağlamsal adlar: yanında derleme sistemi dosyası olan `target`, `.csproj` olan `bin`/`obj`
    - adı ne olursa olsun `pyvenv.cfg` içeren klasörler (Python sanal ortamı, ör. `myenv`)
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
    return os.path.isfile(os.path.join(dir_path, VIRTUALENV_MARKER))
