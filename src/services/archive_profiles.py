"""Arşiv profilleri: hangi dosyaların arşive girmeyeceğini söyleyen gitignore sözdizimli desen kümeleri.

Profiller JSON dosyasıdır: paketli `resources/profiles/*.json` ve kullanıcının `~/.gitclean/profiles/*.json`
dosyaları (aynı adlı kullanıcı profili paketliyi geçersiz kılar). Dosya adı sırası listeleme sırasıdır.
Biçim: {"name": ..., "description": ..., "extends": <başka profil adı, isteğe bağlı>, "exclude": [desen, ...]}
Desenler gitignore kurallarıdır: `tests/` her derinlikte, `/README*` yalnızca kökte, `!` ile istisna.
"""
import json
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set

from src.utils.gitignore_parser import make_pathspec

logger = logging.getLogger(__name__)

DEFAULT_PROFILE_NAME = "Geliştirici (Standart)"


@dataclass
class ArchiveProfile:
    name: str
    description: str
    patterns: List[str]
    source: str = ''
    _spec: object = field(init=False, repr=False, compare=False, default=None)

    def __post_init__(self):
        self._spec = make_pathspec(self.patterns)

    def matches(self, relative_path: str) -> bool:
        """`/` ayraçlı, köke göre yol bu profil tarafından elenmeli mi."""
        return bool(self.patterns) and self._spec.match_file(relative_path.replace('\\', '/'))


def bundled_profiles_dir() -> Path:
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2]))
    return base / 'resources' / 'profiles'


def user_profiles_dir() -> Path:
    return Path.home() / '.gitclean' / 'profiles'


def load_profiles(directories: Optional[Sequence[Path]] = None) -> Dict[str, ArchiveProfile]:
    """Sıralı {ad: profil}. Bozuk dosya atlanır ve loglanır; hiç profil yoksa eleme yapmayan varsayılan döner."""
    directories = list(directories) if directories is not None else [bundled_profiles_dir(), user_profiles_dir()]
    raw: Dict[str, dict] = {}
    for directory in directories:
        if not Path(directory).is_dir():
            continue
        for path in sorted(Path(directory).glob('*.json')):
            data = _read_profile_file(path)
            if data is not None:
                raw[data['name']] = data                  # ilk görülen konum korunur, içerik son görülenle değişir

    profiles: Dict[str, ArchiveProfile] = {}
    for name in raw:
        patterns = _resolve_patterns(name, raw, set())
        if patterns is not None:
            profiles[name] = ArchiveProfile(name, raw[name]['description'], patterns, raw[name]['source'])

    if not profiles:
        logger.error("Hiç arşiv profili yüklenemedi (%s); eleme yapmayan varsayılan kullanılıyor.",
                     [str(d) for d in directories])
        profiles[DEFAULT_PROFILE_NAME] = ArchiveProfile(
            DEFAULT_PROFILE_NAME, "Sadece .gitignore kurallarını uygular.", [], 'yerleşik')
    return profiles


def _read_profile_file(path: Path) -> Optional[dict]:
    try:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as e:
        logger.warning("Profil dosyası okunamadı, atlandı: %s (%s)", path, e)
        return None
    name = data.get('name') if isinstance(data, dict) else None
    exclude = data.get('exclude', []) if isinstance(data, dict) else None
    if not isinstance(name, str) or not name.strip() or not isinstance(exclude, list) \
            or not all(isinstance(p, str) for p in exclude) \
            or not isinstance(data.get('description', ''), str) or not isinstance(data.get('extends', ''), str):
        logger.warning("Profil dosyası geçersiz (name/description/extends metin, exclude metin listesi olmalı), atlandı: %s", path)
        return None
    return {'name': name.strip(), 'description': data.get('description', ''), 'extends': data.get('extends') or None,
            'exclude': [p.strip() for p in exclude if p.strip()], 'source': str(path)}


def _resolve_patterns(name: str, raw: Dict[str, dict], visiting: Set[str]) -> Optional[List[str]]:
    if name in visiting:
        logger.warning("Profil 'extends' döngüsü, atlandı: %s", name)
        return None
    parent_name = raw[name]['extends']
    inherited: List[str] = []
    if parent_name:
        if parent_name not in raw:
            logger.warning("Profil '%s' bilinmeyen profili genişletiyor ('%s'), atlandı.", name, parent_name)
            return None
        parent_patterns = _resolve_patterns(parent_name, raw, visiting | {name})
        if parent_patterns is None:
            return None
        inherited = parent_patterns
    return inherited + raw[name]['exclude']
