"""Süslü parantezli diller (C ailesi, Java, C#, JS/TS, Go, Rust) için hafif sözcük tabanlı çözümleyici.

Gerçek bir ayrıştırıcı değildir; sonuçlar yaklaşıktır (`SourceMetrics.approximate = True`).
Üç aşama:
  1. Temizleme: yorum, string, char ve regex literalleri aynı uzunlukta boşlukla değiştirilir,
     satır sonları korunur (satır numaraları doğru kalır).
  2. Yapı: `{` `}` eşlenir; her `{` öncesindeki başlık (header) fonksiyon / sınıf / düz blok olarak sınıflanır.
  3. Ölçüm: fonksiyon gövdelerindeki karar işaretçileri sayılır.
"""
import re
from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from typing import Callable, FrozenSet, List, Optional, Tuple

from src.languages.base import ClassInfo, FunctionInfo, LanguageSupport, SourceMetrics

# --------------------------------------------------------------------------- #
#  Sözcük kalıpları (catalog.py bunlardan dil tanımlarını birleştirir)         #
# --------------------------------------------------------------------------- #

CHAR_LITERAL = r"'(?:\\(?:x[0-9a-fA-F]{1,2}|u[0-9a-fA-F]{4}|u\{[0-9a-fA-F]+\}|[0-7]{1,3}|.)|[^\\'\n])'"
DOUBLE_QUOTED = r'"(?:\\.|[^"\\\n])*"'
SINGLE_QUOTED = r"'(?:\\.|[^'\\\n])*'"
TEMPLATE_LITERAL = r'`(?:(?s:\\.)|[^`\\])*`'
GO_RAW_STRING = r'`[^`]*`'
TRIPLE_QUOTED = r'"""(?s:.*?)"""'                       # Java text block, C# raw string
CSHARP_VERBATIM = r'\$?@\$?"(?:[^"]|"")*"'
CSHARP_INTERPOLATED = r'\$"(?:\\.|[^"\\\n])*"'
CPP_RAW_STRING = r'(?:u8|[uUL])?R"(?P<cppd>[^()\\\s]{0,16})\((?s:.*?)\)(?P=cppd)"'
RUST_RAW_STRING = r'b?r(?P<rsh>#*)"(?s:.*?)"(?P=rsh)'
JS_REGEX_LITERAL = (r'(?:(?<=[(,=:\[!&|?{;])|(?<=\breturn))\s*/(?![/*])'
                    r'(?:\\.|\[(?:\\.|[^\]\\\n])*\]|[^/\\\n\[])+/[a-z]*')

_STRUCTURE_TOKEN = re.compile(r'[(){};]')
_PREPROCESSOR_LINE = re.compile(r'(?m)^[ \t]*#(?:[^\n]*\\\n)*[^\n]*')
_NAME_TAIL = re.compile(
    r'((?:~?[A-Za-z_][\w$]*|operator\s*(?:[^\s\w(]+|\w+))'
    r'(?:\s*::\s*(?:~?[A-Za-z_][\w$]*|operator\s*(?:[^\s\w(]+|\w+)))*)\s*$')
_IDENTIFIER = re.compile(r'[A-Za-z_$][\w$]*')


@dataclass(frozen=True)
class LanguageSpec:
    id: str
    display_name: str
    extensions: Tuple[str, ...]
    family: str                                   # 'c_like' | 'js' | 'go' | 'rust'
    string_patterns: Tuple[str, ...]
    decision_pattern: str
    import_patterns: Tuple[str, ...]
    keywords: FrozenSet[str]                      # fonksiyon adı olamayacak sözcükler (if, for ...)
    class_kinds: Tuple[str, ...] = ()
    class_header_parens: bool = False             # sınıf başlığında '(' serbest mi (C# record, JS mixin)
    char_literal: bool = False
    regex_literal: bool = False
    preprocessor: bool = False
    new_guard: bool = False                       # `new Foo() {` fonksiyon sayılmasın
    header_cleaners: Tuple[str, ...] = ()         # özellik / dekoratör / öznitelik kalıpları
    refine_pattern: Optional[str] = None          # eşleşirse dil `refine_to` olur (.h -> cpp)
    refine_to: Optional[str] = None


def _blank(token: str) -> str:
    if '\n' not in token:
        return ' ' * len(token)
    return re.sub(r'[^\n]', ' ', token)


def _blank_matches(pattern: 're.Pattern', text: str) -> str:
    return pattern.sub(lambda m: _blank(m.group(0)), text)


class BraceLanguage(LanguageSupport):
    approximate = True

    def __init__(self, spec: LanguageSpec):
        self.spec = spec
        self.id = spec.id
        self.display_name = spec.display_name
        self.extensions = spec.extensions
        self._lexer = self._build_lexer(spec)
        self._decision = re.compile(spec.decision_pattern)
        self._imports = [re.compile(p) for p in spec.import_patterns]
        self._cleaners = [re.compile(p) for p in spec.header_cleaners]
        self._class_keyword = (re.compile(r'(?<![.\w$])(%s)\b' % '|'.join(spec.class_kinds))
                               if spec.class_kinds else None)
        self._refine = re.compile(spec.refine_pattern) if spec.refine_pattern else None

    # ------------------------------------------------------------------ #
    #  Genel arayüz                                                      #
    # ------------------------------------------------------------------ #

    def refine(self, text: str) -> str:
        if self._refine is not None and self._refine.search(text):
            return self.spec.refine_to
        return self.id

    def analyze(self, text: str) -> SourceMetrics:
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        original_lines = text.split('\n')
        if original_lines and original_lines[-1] == '':
            original_lines.pop()

        no_comments, clean = self._strip(text)
        if self.spec.preprocessor:
            clean = _blank_matches(_PREPROCESSOR_LINE, clean)

        blank, comment = self._classify_lines(original_lines, no_comments.split('\n'))
        metrics = SourceMetrics(
            language=self.id, total_lines=len(original_lines),
            code_lines=len(original_lines) - blank - comment,
            comment_lines=comment, blank_lines=blank, approximate=True,
        )
        metrics.imports = self._extract_imports(no_comments)
        metrics.functions, metrics.classes, metrics.parse_ok = self._scan_structure(clean)
        return metrics

    # ------------------------------------------------------------------ #
    #  Aşama 1: temizleme                                                #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _build_lexer(spec: LanguageSpec) -> 're.Pattern':
        parts = [r'(?P<bc>/\*(?s:.*?)(?:\*/|\Z))', r'(?P<lc>//[^\n]*)']
        parts += [f'(?P<s{i}>{pattern})' for i, pattern in enumerate(spec.string_patterns)]
        if spec.char_literal:
            parts.append(f'(?P<ch>{CHAR_LITERAL})')
        if spec.regex_literal:
            parts.append(f'(?P<rx>{JS_REGEX_LITERAL})')
        return re.compile('|'.join(parts))

    def _strip(self, text: str) -> Tuple[str, str]:
        """(yalnızca yorumsuz, yorumsuz ve stringsiz) metinler; ikisi de orijinalle aynı uzunlukta."""
        no_comments: List[str] = []
        clean: List[str] = []
        last = 0
        for match in self._lexer.finditer(text):
            gap = text[last:match.start()]
            no_comments.append(gap)
            clean.append(gap)
            token = match.group(0)
            blank = _blank(token)
            clean.append(blank)
            is_comment = match.group('bc') is not None or match.group('lc') is not None
            no_comments.append(blank if is_comment else token)
            last = match.end()
        tail = text[last:]
        no_comments.append(tail)
        clean.append(tail)
        return ''.join(no_comments), ''.join(clean)

    @staticmethod
    def _classify_lines(original: List[str], without_comments: List[str]) -> Tuple[int, int]:
        blank = comment = 0
        for line, stripped in zip(original, without_comments):
            if not line.strip():
                blank += 1
            elif not stripped.strip():
                comment += 1
        return blank, comment

    # ------------------------------------------------------------------ #
    #  İçe aktarmalar                                                    #
    # ------------------------------------------------------------------ #

    def _extract_imports(self, no_comments: str) -> List[str]:
        found: List[str] = []
        for pattern in self._imports:
            found.extend(m.group(1).strip().rstrip(':') for m in pattern.finditer(no_comments))
        if self.spec.family == 'go':
            found.extend(self._go_block_imports(no_comments))
        return list(dict.fromkeys(i for i in found if i))

    @staticmethod
    def _go_block_imports(text: str) -> List[str]:
        found = []
        for block in re.finditer(r'(?m)^\s*import\s*\((?P<body>[^)]*)\)', text):
            found.extend(re.findall(r'"([^"\n]+)"', block.group('body')))
        return found

    # ------------------------------------------------------------------ #
    #  Aşama 2: yapı                                                     #
    # ------------------------------------------------------------------ #

    def _scan_structure(self, clean: str) -> Tuple[List[FunctionInfo], List[ClassInfo], bool]:
        line_starts = [0] + [m.end() for m in re.finditer('\n', clean)]

        def line_of(offset: int) -> int:
            return bisect_right(line_starts, offset)

        nodes: List[dict] = []
        stack: List[Tuple[Optional[int], int, int]] = []    # (düğüm no, sahip düğüm no, kaydedilen parantez derinliği)
        paren_depth = 0
        boundary = 0
        balanced = True

        for match in _STRUCTURE_TOKEN.finditer(clean):
            pos = match.start()
            char = clean[pos]
            if char == '(':
                paren_depth += 1
            elif char == ')':
                paren_depth = max(0, paren_depth - 1)
            elif char == ';':
                if paren_depth == 0:
                    boundary = pos + 1
            elif char == '{':
                owner = stack[-1][1] if stack else -1
                node_id = None
                if paren_depth == 0:
                    found = self._classify_header(clean[boundary:pos])
                    if found:
                        kind, name, rel = found
                        nodes.append({'kind': kind, 'name': name, 'start': boundary + rel,
                                      'open': pos, 'close': None, 'owner': owner})
                        node_id = len(nodes) - 1
                stack.append((node_id, node_id if node_id is not None else owner, paren_depth))
                paren_depth = 0
                boundary = pos + 1
            else:  # '}'
                if stack:
                    node_id, _, paren_depth = stack.pop()
                    if node_id is not None:
                        nodes[node_id]['close'] = pos
                else:
                    balanced = False
                boundary = pos + 1

        if stack:
            balanced = False
        return (*self._build_infos(clean, nodes, line_of), balanced)

    def _build_infos(self, clean: str, nodes: List[dict], line_of: Callable[[int], int]):
        decision_positions = [m.start() for m in self._decision.finditer(clean)]
        method_counts = {}
        for node in nodes:
            if node['kind'] == 'func' and node['close'] is not None and node['owner'] >= 0 \
                    and nodes[node['owner']]['kind'] == 'class':
                method_counts[node['owner']] = method_counts.get(node['owner'], 0) + 1

        functions: List[FunctionInfo] = []
        classes: List[ClassInfo] = []
        for index, node in enumerate(nodes):
            if node['close'] is None:
                continue                      # eşleşmeyen '{': taşan sınıf/fonksiyon uydurma
            start_line, end_line = line_of(node['start']), line_of(node['close'])
            if node['kind'] == 'class':
                classes.append(ClassInfo(node['name'], start_line, end_line, method_counts.get(index, 0)))
            else:
                inside = bisect_left(decision_positions, node['close']) - bisect_left(decision_positions, node['open'] + 1)
                functions.append(FunctionInfo(node['name'], start_line, end_line, 1 + inside))
        return functions, classes

    # ------------------------------------------------------------------ #
    #  Başlık sınıflama                                                  #
    # ------------------------------------------------------------------ #

    def _classify_header(self, header: str) -> Optional[Tuple[str, str, int]]:
        """`{` öncesi başlığı ('class'|'func', ad, başlık içi ofset) olarak sınıflar; düz blok ise None."""
        cleaned = header
        for cleaner in self._cleaners:
            cleaned = _blank_matches(cleaner, cleaned)
        if not cleaned.strip(' \t\r\n,'):
            return None

        family = self.spec.family
        if family == 'go':
            return self._go_function(cleaned)
        if family == 'rust':
            return self._rust_header(cleaned)
        found = self._class_header(cleaned)
        if found:
            return found
        return self._js_function(cleaned) if family == 'js' else self._c_like_function(cleaned)

    # ---- sınıflar (c_like, js) ------------------------------------------------

    def _class_header(self, header: str) -> Optional[Tuple[str, str, int]]:
        if self._class_keyword is None:
            return None
        for match in self._class_keyword.finditer(header):
            before = header[:match.start()].rstrip()
            if before.endswith(('<', ',')) or re.search(r'\benum$', before):
                continue                                   # template<class T>, enum class
            rest = header[match.end():]
            if '=' in header[match.start():] or ';' in rest:
                continue
            if not self.spec.class_header_parens and '(' in rest:
                continue
            name = self._class_name(rest)
            if name:
                return 'class', name, match.start()
        return None

    def _class_name(self, rest: str) -> Optional[str]:
        if self.spec.id in ('c', 'cpp'):
            rest = re.split(r'(?<!:):(?!:)|<', rest, maxsplit=1)[0]
            names = [n for n in _IDENTIFIER.findall(rest) if n not in ('final', 'sealed')]
            return names[-1] if names else None
        match = _IDENTIFIER.match(rest.lstrip())
        return match.group(0) if match else None

    # ---- C ailesi, Java, C# ----------------------------------------------------

    def _c_like_function(self, header: str) -> Optional[Tuple[str, str, int]]:
        paren = header.find('(')
        if paren < 0:
            return None
        name_part = header[:paren].rstrip()
        match = _NAME_TAIL.search(name_part)
        if not match:
            return None
        prefix = name_part[:match.start()]
        name = re.split(r'\s*::\s*', match.group(1))[-1].strip()
        if name in self.spec.keywords or '=' in prefix or prefix.rstrip().endswith(('.', '->')):
            return None
        if self.spec.new_guard and re.search(r'\bnew\b', prefix):
            return None
        return 'func', name, match.start(1)

    # ---- JavaScript / TypeScript ---------------------------------------------------

    _JS_FUNCTION = re.compile(
        r'(?m)^[ \t,]*(?:export\s+)?(?:default\s+)?(?:(?:const|let|var)\s+[\w$]+\s*(?::[^=]+)?=\s*)?'
        r'(?:async\s+)?function\b\s*\*?\s*(?P<name>[\w$]*)\s*(?:<[^>]*>)?\s*\(.*\)\s*(?::[^=]*)?\Z',
        re.S)
    _JS_KEYED_FUNCTION = re.compile(
        r'(?m)^[ \t,]*(?P<name>[\w$]+)\s*:\s*(?:async\s+)?function\b\s*\*?\s*[\w$]*\s*\(.*\)\s*(?::[^=]*)?\Z', re.S)
    _JS_ARROW_NAME = re.compile(
        r'(?m)^[ \t,]*(?:(?:export|default|const|let|var|public|private|protected|static|readonly|async)\s+)*'
        r'(?P<name>[\w$.]+)\s*(?::[^=()]*)?=\s*(?!=)(?:async\b|\(|<|[\w$]+\s*=>)')
    _JS_METHOD = re.compile(
        r'(?m)^[ \t,]*(?:(?:public|private|protected|static|async|get|set|readonly|abstract|override|declare)\s+)*'
        r'\*?\s*(?P<name>[\w$]+|\[[^\]\n]+\])\s*(?:<[^>]*>)?\s*\(.*\)\s*(?::\s*[^={]*)?\Z', re.S)

    def _js_function(self, header: str) -> Optional[Tuple[str, str, int]]:
        stripped = header.rstrip()
        if stripped.endswith('=>'):
            match = self._JS_ARROW_NAME.search(header)
            return 'func', match.group('name') if match else '<anonymous>', match.start('name') if match else 0
        for pattern in (self._JS_FUNCTION, self._JS_KEYED_FUNCTION):
            match = pattern.search(header)
            if match:
                return 'func', match.group('name') or '<anonymous>', match.start()
        match = self._JS_METHOD.search(header)
        if match and match.group('name') not in self.spec.keywords:
            return 'func', match.group('name'), match.start('name')
        return None

    # ---- Go --------------------------------------------------------------------------

    _GO_FUNCTION = re.compile(r'(?m)^[ \t]*func\b\s*(?:\([^)]*\)\s*)?(?P<name>\w+)\s*(?:\[[^\]]*\]\s*)?\(')

    def _go_function(self, header: str) -> Optional[Tuple[str, str, int]]:
        match = self._GO_FUNCTION.search(header)
        return ('func', match.group('name'), match.start('name')) if match else None

    # ---- Rust ----------------------------------------------------------------------------

    _RUST_FN = re.compile(r'(?<![\w])fn\s+(?P<name>[A-Za-z_]\w*)')
    _RUST_IMPL = re.compile(r'^\s*(?:unsafe\s+)?impl\b(?P<rest>.*)\Z', re.S)
    _RUST_TYPE = re.compile(r'^\s*(?:pub(?:\([^)]*\))?\s+)?(?:unsafe\s+)?(?:struct|trait)\s+(?P<name>[A-Za-z_]\w*)')

    def _rust_header(self, header: str) -> Optional[Tuple[str, str, int]]:
        fn = self._RUST_FN.search(header)
        if fn:
            return 'func', fn.group('name'), fn.start('name')
        impl = self._RUST_IMPL.match(header)
        if impl:
            name = self._rust_impl_name(impl.group('rest'))
            return ('class', name, impl.start()) if name else None
        typed = self._RUST_TYPE.match(header)
        return ('class', typed.group('name'), typed.start('name')) if typed else None

    @staticmethod
    def _rust_impl_name(rest: str) -> Optional[str]:
        rest = re.sub(r'\bwhere\b.*', '', rest, flags=re.S)
        previous = None
        while previous != rest:                          # jenerikleri içten dışa sil
            previous, rest = rest, re.sub(r'<[^<>]*>', '', rest)
        rest = re.split(r'\bfor\b', rest)[-1]
        names = re.findall(r'[A-Za-z_]\w*', rest)
        return names[-1] if names else None
