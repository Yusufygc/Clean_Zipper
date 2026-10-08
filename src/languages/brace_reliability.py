"""Süslü parantezli diller için hata yönetimi ve üretim hijyeni taraması (sözcük tabanlı, yaklaşık)."""
import re
from typing import Dict, List, Optional, Pattern

# Boş `catch` gövdesi ve JS söz vaadi `.catch(() => {})`: hata sessizce yutulur.
_EMPTY_CATCH = re.compile(
    r'\bcatch\s*(?:\([^)]*\))?\s*\{\s*\}'
    r'|\.catch\s*\(\s*(?:\(\s*\w*\s*\)|\w+)?\s*=>\s*\{\s*\}\s*\)')
EMPTY_CATCH_LANGUAGES = frozenset({'javascript', 'typescript', 'java', 'csharp', 'cpp'})

_DEBUGGER = re.compile(r'\bdebugger\s*;')
DEBUGGER_LANGUAGES = frozenset({'javascript', 'typescript'})

# Üretim kodunda günlükleme yerine kullanılan çıktı çağrıları (C/C++ konsol programı olduğundan hariç).
_PRINT_PATTERNS: Dict[str, Pattern] = {
    'javascript': re.compile(r'\bconsole\.(?:log|debug|info|warn|error|trace)\s*\('),
    'typescript': re.compile(r'\bconsole\.(?:log|debug|info|warn|error|trace)\s*\('),
    'java': re.compile(r'\bSystem\.(?:out|err)\.print(?:ln|f)?\s*\(|\.printStackTrace\s*\('),
    'csharp': re.compile(r'\bConsole\.(?:Write|WriteLine)\s*\('),
    'go': re.compile(r'\bfmt\.(?:Print|Println|Printf)\s*\('),
    'rust': re.compile(r'\b(?:println|eprintln|print|eprint|dbg)!\s*\('),
}


def _lines_of(pattern: Pattern, clean: str) -> List[int]:
    starts = [m.start() for m in pattern.finditer(clean)]
    return sorted({clean.count('\n', 0, offset) + 1 for offset in starts})


def find_empty_catches(language: str, clean: str, raw: str) -> List[int]:
    """Boş `catch` blokları. `raw`: `clean` ile aynı uzunlukta özgün metin; gövdesinde açıklama yorumu olan blok
    (`catch { /* kota dolu */ }`) bilinçli yutma sayılır ve atlanır."""
    if language not in EMPTY_CATCH_LANGUAGES:
        return []
    offsets = [m.start() for m in _EMPTY_CATCH.finditer(clean)
               if '/*' not in raw[m.start():m.end()] and '//' not in raw[m.start():m.end()]]
    return sorted({clean.count('\n', 0, offset) + 1 for offset in offsets})


def find_debugger(language: str, clean: str) -> List[int]:
    return _lines_of(_DEBUGGER, clean) if language in DEBUGGER_LANGUAGES else []


def find_prints(language: str, clean: str) -> List[int]:
    pattern: Optional[Pattern] = _PRINT_PATTERNS.get(language)
    return _lines_of(pattern, clean) if pattern is not None else []
