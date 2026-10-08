"""Süslü parantezli diller için kullanım analizi (sözcük tabanlı, yaklaşık): import, ulaşılamaz kod, sihirli sayı."""
import re
from typing import Dict, Iterable, List, Tuple

from src.languages.python_usage import ALLOWED_NUMBERS, MagicNumber, UnreachableCode, UnusedImport

UNREACHABLE_LANGUAGES = frozenset({'c', 'cpp', 'java', 'csharp', 'javascript', 'typescript'})
UNUSED_IMPORT_LANGUAGES = frozenset({'javascript', 'typescript', 'java'})

# ---- kullanılmayan import ---------------------------------------------------------------------

_JS_IMPORT = re.compile(
    r'''(?m)^[ \t]*import\s+(?:type\s+)?(?P<clause>[\w$*{}\s,]+?)\s+from\s+['"](?P<module>[^'"\n]+)['"][ \t]*;?''')
_JAVA_IMPORT = re.compile(r'(?m)^[ \t]*import\s+(?:static\s+)?(?P<path>[\w.]+?)(?P<star>\.\*)?\s*;')


def find_unused_imports(language: str, no_comments: str, raw: str) -> List[UnusedImport]:
    """JS/TS ve Java: içe aktarılan ad, import satırları çıkarılmış metinde hiç geçmiyorsa kullanılmamıştır.

    Yorum içeren ham metinde aranır (JSDoc / Javadoc `@link` gibi kullanımlar yanlış pozitif üretmesin).
    """
    if language in ('javascript', 'typescript'):
        pattern, bindings = _JS_IMPORT, _js_bindings
    elif language == 'java':
        pattern, bindings = _JAVA_IMPORT, _java_bindings
    else:
        return []
    body = pattern.sub(' ', raw)
    found: List[UnusedImport] = []
    for match in pattern.finditer(no_comments):
        line = no_comments.count('\n', 0, match.start()) + 1
        source = match.groupdict().get('module') or match.group('path')
        for name in bindings(match):
            if language != 'java' and name == 'React':
                continue                                      # JSX derleyicisi örtük kullanır
            if not re.search(r'(?:(?<![\w$.])|(?<=\.\.\.))' + re.escape(name) + r'(?![\w$])', body):
                found.append(UnusedImport(name, line, source))
    return found


def _js_bindings(match: 're.Match') -> List[str]:
    clause = match.group('clause').strip()
    names: List[str] = []
    named = re.search(r'\{([^}]*)\}', clause)
    if named:
        for part in named.group(1).split(','):
            words = part.replace('type ', ' ', 1).split() if part.strip().startswith('type ') else part.split()
            if words:
                names.append(words[-1])                       # `a as b` -> b
        clause = clause.replace(named.group(0), '')
    star = re.search(r'\*\s+as\s+([\w$]+)', clause)
    if star:
        names.append(star.group(1))
        clause = clause.replace(star.group(0), '')
    default = re.match(r'\s*([\w$]+)\s*,?\s*$', clause)
    if default:
        names.append(default.group(1))
    return names


def _java_bindings(match: 're.Match') -> List[str]:
    if match.group('star'):
        return []                                             # joker import: hangi adın kullanıldığı bilinemez
    return [match.group('path').rsplit('.', 1)[-1]]


# ---- ulaşılamaz kod ---------------------------------------------------------------------------------

_TERMINATOR = re.compile(r'(?<![\w$.])(return|throw|break|continue)(?![\w$])')
_NEXT_OK_WORDS = frozenset({'case', 'default', 'else', 'function'})      # `function`: JS bildirimleri yukarı çekilir
_LABEL = re.compile(r'[A-Za-z_$][\w$]*\s*:(?!:)')


def _statement_end(clean: str, position: int) -> int:
    """`position`tan sonraki ifade sonu `;` indeksi; parantez dengesiz, `{`/`}` içeren veya `;` yoksa -1.

    JSX metni (`&apos;`) ve `for(;;)` gibi parantez içi `;` ifade sonu sayılmaz.
    """
    depth = 0
    for cursor in range(position, len(clean)):
        char = clean[cursor]
        if char in '([':
            depth += 1
        elif char in ')]':
            depth -= 1
            if depth < 0:
                return -1
        elif char in '{}':
            return -1
        elif char == ';':
            return cursor if depth == 0 else -1
    return -1


def _starts_statement(clean: str, position: int) -> bool:
    """Anahtar sözcük bir ifadenin başında mı (öncesi `{ } ; :` veya dosya başı)?"""
    cursor = position - 1
    while cursor >= 0 and clean[cursor].isspace():
        cursor -= 1
    return cursor < 0 or clean[cursor] in '{};:'


def _next_statement(clean: str, no_comments: str, end: int) -> int:
    """`;` (indeks `end`) sonrasındaki ulaşılamaz ifadenin başlangıç indeksi; ulaşılabilir veya belirsizse -1."""
    rest = clean[end + 1:]
    stripped = rest.lstrip()
    if not stripped or stripped[0] in '}#)':
        return -1
    next_pos = end + 1 + (len(rest) - len(stripped))
    word = re.match(r'[A-Za-z_$][\w$]*', stripped)
    if (word and word.group(0) in _NEXT_OK_WORDS) or _LABEL.match(stripped):
        return -1
    return -1 if '#' in no_comments[end + 1:next_pos] else next_pos


def find_unreachable(clean: str, no_comments: str) -> List[UnreachableCode]:
    """`return/throw/break/continue ...;` sonrasında `}` / `case` / `default` olmayan ifade.

    Yalnızca ifade başında (öncesi `{ } ; :`) olan sonlandırıcılar sayılır; `if (x) return;` gibi süslü parantezsiz
    koşullar atlanır. Önişlemci (`#if`/`#else`) satırı arada kalıyorsa farklı dallar olabileceğinden atlanır.
    """
    found: List[UnreachableCode] = []
    for match in _TERMINATOR.finditer(clean):
        if not _starts_statement(clean, match.start()):
            continue
        end = _statement_end(clean, match.end())
        next_pos = _next_statement(clean, no_comments, end) if end >= 0 else -1
        if next_pos >= 0:
            found.append(UnreachableCode(
                clean.count('\n', 0, next_pos) + 1, match.group(1), clean.count('\n', 0, match.start()) + 1))
    return found


# ---- sihirli sayı ---------------------------------------------------------------------------------------

_NUMBER = re.compile(
    r'(?<![\w.$#])(?:0[xXbB][0-9a-fA-F_]+|\d[\d_]*(?:\.\d+)?(?:[eE][+-]?\d+)?|\.\d+)[fFlLuUdD]*(?![\w.$])')
_DECLARATION = re.compile(
    r'(?:\b(?:const|final|static|readonly|constexpr|enum|case|define)\b)|^\s*(?:[\w$<>\[\],.?*&:\s]+\s)?[\w$]+\s*[:=]+\s*-?[\d.][\w.]*\s*[;,]?\s*$')
_NUMERIC_LIST = re.compile(r'(?:-?[\d.][\w.]*\s*,\s*){2,}-?[\d.]')
_INDEX = re.compile(r'\[\s*-?[\d.]+\s*\]')
_NAMED_ARGUMENT = re.compile(r'[\w$]+\s*:\s*-?[\d.]+[\w.]*')


def find_magic_numbers(clean: str, ranges: Iterable[Tuple[int, int]]) -> List[MagicNumber]:
    """Fonksiyon gövdelerindeki (satır aralıkları) adsız sayısal sabitler. `clean`: yorum ve string silinmiş metin."""
    lines = clean.split('\n')
    wanted: Dict[int, None] = {}
    for start, end in ranges:
        for number in range(start + 1, min(end, len(lines)) + 1):       # başlık satırı dahil edilmez
            wanted[number] = None
    found: List[MagicNumber] = []
    for number in wanted:
        line = lines[number - 1]
        if not line.strip() or _DECLARATION.search(line):
            continue
        line = _INDEX.sub(' ', _NUMERIC_LIST.sub(' ', line))
        line = _NAMED_ARGUMENT.sub(' ', line)
        for match in _NUMBER.finditer(line):
            value = _to_number(match.group(0))
            if value is not None and value not in ALLOWED_NUMBERS:
                found.append(MagicNumber(value, number))
    return found


def _to_number(token: str):
    text = token.rstrip('fFlLuUdD_') if not token.lower().startswith('0x') else token
    try:
        if text.lower().startswith(('0x', '0b')):
            return int(text.replace('_', ''), 0)
        return float(text.replace('_', '')) if any(c in text for c in '.eE') else int(text.replace('_', ''))
    except ValueError:
        return None
