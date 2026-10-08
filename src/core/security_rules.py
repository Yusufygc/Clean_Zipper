"""Güvenlik kural kümesi (SAST-lite): paketli `resources/rules/*.json` ve kullanıcının `~/.gitclean/rules/*.json` dosyaları.

Biçim: {"version": 1, "rules": [{"id", "title", "severity", "languages", "scope", "pattern", "flags", "cwe", "advice"}]}
- `languages`: dil kimlikleri (`python`, `javascript`, `typescript`, `java`, `csharp`, `c`, `cpp`, `go`, `rust`) veya `["*"]`.
- `scope`: `code` (yorum ve string içeriği silinmiş metin) veya `text` (yalnızca yorumlar silinmiş; string içeriği durur).
- `flags`: `i` büyük/küçük harf duyarsız. Aynı `id` kullanıcı dosyasında paketliyi geçersiz kılar.
Bozuk kural atlanır ve loglanır; diğer kurallar yüklenir.
"""
import json
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Pattern, Sequence, Tuple

from src.models.analysis_models import Severity

logger = logging.getLogger(__name__)

SCOPES = ('code', 'text')


@dataclass(frozen=True)
class SecurityRule:
    id: str
    title: str
    severity: Severity
    languages: Tuple[str, ...]
    scope: str
    pattern: Pattern
    cwe: str
    advice: str

    def applies_to(self, language: str) -> bool:
        return '*' in self.languages or language in self.languages


def bundled_rules_dir() -> Path:
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2]))
    return base / 'resources' / 'rules'


def user_rules_dir() -> Path:
    return Path.home() / '.gitclean' / 'rules'


def load_security_rules(directories: Optional[Sequence[Path]] = None) -> List[SecurityRule]:
    """Kimliğe göre tekilleştirilmiş kurallar (sonra gelen dizin öncekini geçersiz kılar)."""
    directories = list(directories) if directories is not None else [bundled_rules_dir(), user_rules_dir()]
    by_id: Dict[str, SecurityRule] = {}
    for directory in directories:
        if not Path(directory).is_dir():
            continue
        for path in sorted(Path(directory).glob('*.json')):
            for rule in _read_rule_file(path):
                by_id[rule.id] = rule
    if not by_id:
        logger.error("Hiç güvenlik kuralı yüklenemedi (%s).", [str(d) for d in directories])
    return list(by_id.values())


def _read_rule_file(path: Path) -> List[SecurityRule]:
    try:
        data = json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError) as e:
        logger.warning("Kural dosyası okunamadı, atlandı: %s (%s)", path, e)
        return []
    raw_rules = data.get('rules') if isinstance(data, dict) else None
    if not isinstance(raw_rules, list):
        logger.warning("Kural dosyası geçersiz ('rules' listesi yok), atlandı: %s", path)
        return []
    rules = []
    for raw in raw_rules:
        rule = _build_rule(raw, path)
        if rule is not None:
            rules.append(rule)
    return rules


def _build_rule(raw: object, path: Path) -> Optional[SecurityRule]:
    try:
        if not isinstance(raw, dict):
            raise ValueError("kural bir nesne olmalı")
        rule_id = _text(raw, 'id')
        severity = Severity[_text(raw, 'severity').upper()]
        languages = raw.get('languages')
        if not isinstance(languages, list) or not languages or not all(isinstance(x, str) for x in languages):
            raise ValueError("languages boş olmayan metin listesi olmalı")
        scope = raw.get('scope', 'code')
        if scope not in SCOPES:
            raise ValueError(f"scope {SCOPES} olmalı")
        flags = re.IGNORECASE if 'i' in str(raw.get('flags', '')) else 0
        return SecurityRule(rule_id, _text(raw, 'title'), severity, tuple(languages), scope,
                            re.compile(_text(raw, 'pattern'), flags), str(raw.get('cwe', '')),
                            str(raw.get('advice', '')))
    except (KeyError, ValueError, re.error) as e:
        logger.warning("Güvenlik kuralı geçersiz, atlandı: %s (%s: %s)", path,
                       raw.get('id') if isinstance(raw, dict) else '?', e)
        return None


def _text(raw: dict, key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"'{key}' boş olmayan metin olmalı")
    return value
