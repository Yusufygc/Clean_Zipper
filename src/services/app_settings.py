"""Kalıcı kullanıcı ayarları: `~/.gitclean/settings.json`.

Bozuk ya da eksik dosya, bilinmeyen anahtar ve sınır dışı değer güvenle karşılanır (varsayılana dönülür, uyarı loglanır);
ayar dosyası yüzünden uygulama açılmaz hâle gelmez.
"""
import json
import logging
import os
import re
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Dict, List, Optional

from src.core.thresholds import QualityThresholds

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 1
DEFAULT_BATCH_SIZE = 15
MAX_BATCH_SIZE = 200
_DEFAULTS = QualityThresholds()

# eşik adı -> (en küçük değer, arayüz adımı); varsayılanlar `QualityThresholds` içindedir (tek kaynak)
THRESHOLD_LIMITS: Dict[str, tuple] = {
    'cyclomatic': (1, 1), 'cognitive': (1, 1), 'function_lines': (5, 5), 'class_lines': (20, 25), 'file_lines': (50, 50),
    'parameters': (1, 1), 'nesting': (1, 1), 'class_methods': (1, 1), 'module_imports': (1, 1),
}


def settings_path() -> Path:
    return Path.home() / '.gitclean' / 'settings.json'


def default_agent_dir(project: Optional[Path]) -> Path:
    """Ajan görevleri için varsayılan çıktı klasörü: projenin DIŞINDA (analiz görev dosyalarını bulgu saymasın)."""
    name = re.sub(r'[^\w.-]+', '_', project.name) if project else 'proje'
    return Path.home() / '.gitclean' / 'agent-tasks' / (name or 'proje')


def default_thresholds() -> Dict[str, int]:
    return {name: getattr(_DEFAULTS, name) for name in THRESHOLD_LIMITS}


@dataclass
class AppSettings:
    respect_gitignore: bool = True
    disabled_analyzers: List[str] = field(default_factory=list)
    disabled_rules: List[str] = field(default_factory=list)
    thresholds: Dict[str, int] = field(default_factory=default_thresholds)
    agent_batch_size: int = DEFAULT_BATCH_SIZE
    agent_output_dir: str = ''                      # boş: `default_agent_dir`

    def quality_thresholds(self) -> QualityThresholds:
        return QualityThresholds(**self.thresholds)

    def set_threshold(self, name: str, value: int) -> int:
        """Değeri en küçük sınırın altına düşürmeden kaydeder; kaydedilen değeri döner."""
        if name not in THRESHOLD_LIMITS:
            raise KeyError(name)
        self.thresholds[name] = max(int(value), THRESHOLD_LIMITS[name][0])
        return self.thresholds[name]


def _clean_names(raw) -> List[str]:
    if not isinstance(raw, list):
        return []
    return sorted({str(item) for item in raw if isinstance(item, str) and item.strip()})


def _clean_thresholds(raw) -> Dict[str, int]:
    values = default_thresholds()
    if isinstance(raw, dict):
        for name, (minimum, _) in THRESHOLD_LIMITS.items():
            value = raw.get(name)
            if isinstance(value, int) and not isinstance(value, bool):
                values[name] = max(value, minimum)
    return values


def settings_from_dict(data) -> AppSettings:
    if not isinstance(data, dict):
        return AppSettings()
    batch = data.get('agent_batch_size')
    batch = batch if isinstance(batch, int) and not isinstance(batch, bool) else DEFAULT_BATCH_SIZE
    output = data.get('agent_output_dir')
    return AppSettings(
        respect_gitignore=data.get('respect_gitignore') is not False,
        disabled_analyzers=_clean_names(data.get('disabled_analyzers')),
        disabled_rules=_clean_names(data.get('disabled_rules')),
        thresholds=_clean_thresholds(data.get('thresholds')),
        agent_batch_size=min(max(batch, 1), MAX_BATCH_SIZE),
        agent_output_dir=output if isinstance(output, str) else '')


def load_settings(path: Optional[Path] = None) -> AppSettings:
    """Kayıtlı ayarlar; dosya yoksa ya da okunamıyorsa varsayılanlar."""
    target = Path(path) if path else settings_path()
    if not target.is_file():
        return AppSettings()
    try:
        return settings_from_dict(json.loads(target.read_text(encoding='utf-8')))
    except (OSError, ValueError) as e:
        logger.warning("Ayar dosyası okunamadı, varsayılanlar kullanılıyor: %s (%s)", target, e)
        return AppSettings()


def save_settings(settings: AppSettings, path: Optional[Path] = None) -> bool:
    """Ayarları atomik yazar (yarım dosya kalmaz); başarısızsa False döner ve loglar."""
    target = Path(path) if path else settings_path()
    payload = {'version': SCHEMA_VERSION, **{f.name: getattr(settings, f.name) for f in fields(settings)}}
    temporary = target.with_name(target.name + '.tmp')
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding='utf-8')
        os.replace(temporary, target)
        return True
    except OSError as e:
        logger.warning("Ayarlar kaydedilemedi: %s (%s)", target, e)
        try:
            temporary.unlink()
        except OSError:
            pass
        return False
