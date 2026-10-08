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
from typing import Callable, FrozenSet, List, NamedTuple, Optional, Tuple

from src.languages.base import ClassInfo, FunctionInfo, LanguageSupport, SourceMetrics, StrippedSource
from src.languages.brace_headers import HeaderClassifier, blank, blank_matches

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
_GO_HEADER_START = re.compile(r'\s*(?:else\s+)?(?:for|if|switch)\b')
_PREPROCESSOR_LINE = re.compile(r'(?m)^[ \t]*#(?:[^\n]*\\\n)*[^\n]*')
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
    # Bilişsel karmaşıklık / derinlik için
    structural_keywords: Tuple[str, ...] = ('if', 'for', 'foreach', 'while', 'catch', 'switch')
    ternary_pattern: Optional[str] = None         # üçlü `?` belirteci; yoksa dilde üçlü ifade yok
    bool_or_pattern: str = r'\|\|'


class _Frame(NamedTuple):
    """Açık `{` yığın girdisi."""
    node_id: Optional[int]        # bu `{` sınıf / fonksiyon düğümü açtıysa numarası
    owner: int                    # en yakın sınıf / fonksiyon düğümü (-1: yok)
    paren_depth: int              # `{` açılırken kaydedilen parantez derinliği
    function_id: int              # en yakın fonksiyon düğümü (-1: yok)
    block_depth: int              # kontrol bloğu iç içe derinliği
    cognitive: bool               # bilişsel karmaşıklığı artıran kontrol bloğu mu


_ROOT_FRAME = _Frame(None, -1, 0, -1, 0, False)


class _StructureScanner:
    """`{` `}` `(` `)` `;` belirteçlerini gezip sınıf / fonksiyon düğümlerini ve kontrol bloklarını çıkarır."""

    def __init__(self, headers: HeaderClassifier, go_family: bool, clean: str):
        self.headers = headers
        self.go_family = go_family
        self.clean = clean
        self.nodes: List[dict] = []
        self.stack: List[_Frame] = []
        self.cognitive_opens: List[int] = []             # bilişsel kontrol bloklarının açılış / kapanış konumları
        self.cognitive_closes: List[int] = []
        self.paren_depth = 0
        self.boundary = 0                                # geçerli başlığın başladığı konum
        self.balanced = True

    def run(self) -> None:
        for match in _STRUCTURE_TOKEN.finditer(self.clean):
            pos = match.start()
            char = self.clean[pos]
            if char == '(':
                self.paren_depth += 1
            elif char == ')':
                self.paren_depth = max(0, self.paren_depth - 1)
            elif char == ';':
                self._semicolon(pos)
            elif char == '{':
                self._open(pos)
            else:
                self._close(pos)

    def _semicolon(self, pos: int) -> None:
        # Go: `for i := 0; i < n; i++ {` başlığının `;`i bölmez
        if self.paren_depth == 0 and not (self.go_family and _GO_HEADER_START.match(self.clean, self.boundary, pos)):
            self.boundary = pos + 1

    def _open(self, pos: int) -> None:
        parent = self.stack[-1] if self.stack else _ROOT_FRAME
        node_id, function_id, block_depth, cognitive = None, parent.function_id, parent.block_depth, False
        if self.paren_depth == 0:
            node_id, function_id, block_depth, cognitive = self._classify_open(pos, parent)
        self.stack.append(_Frame(node_id, node_id if node_id is not None else parent.owner, self.paren_depth,
                                 function_id, block_depth, cognitive))
        if self.paren_depth == 0:
            self.boundary = pos + 1                      # parantez içindeki `{` (destructuring, nesne) başlığı bölmez
        self.paren_depth = 0

    def _classify_open(self, pos: int, parent: _Frame) -> Tuple[Optional[int], int, int, bool]:
        """Üst düzey `{` için (düğüm no, fonksiyon no, blok derinliği, bilişsel blok mu)."""
        header = self.clean[self.boundary:pos]
        found = self.headers.classify(header)
        if found:
            kind, name, rel, params = found
            self.nodes.append({'kind': kind, 'name': name, 'start': self.boundary + rel, 'open': pos, 'close': None,
                               'owner': parent.owner, 'params': params, 'base_depth': parent.block_depth, 'max_nesting': 0})
            node_id = len(self.nodes) - 1
            return node_id, (node_id if kind == 'func' else parent.function_id), parent.block_depth, False
        control = self.headers.control_kind(header)
        if not control:
            return None, parent.function_id, parent.block_depth, False
        block_depth = parent.block_depth + 1
        if parent.function_id >= 0:
            function = self.nodes[parent.function_id]
            function['max_nesting'] = max(function['max_nesting'], block_depth - function['base_depth'])
        if control == 'cog':
            self.cognitive_opens.append(pos)
        return None, parent.function_id, block_depth, control == 'cog'

    def _close(self, pos: int) -> None:
        if self.stack:
            frame = self.stack.pop()
            self.paren_depth = frame.paren_depth
            if frame.node_id is not None:
                self.nodes[frame.node_id]['close'] = pos
            if frame.cognitive:
                self.cognitive_closes.append(pos)
        else:
            self.balanced = False
        if self.paren_depth == 0:
            self.boundary = pos + 1


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
        self._headers = HeaderClassifier(spec)
        self._refine = re.compile(spec.refine_pattern) if spec.refine_pattern else None
        self._cognitive_tokens = self._build_cognitive_tokens(spec)

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
            clean = blank_matches(_PREPROCESSOR_LINE, clean)

        blank_count, comment = self._classify_lines(original_lines, no_comments.split('\n'))
        metrics = SourceMetrics(
            language=self.id, total_lines=len(original_lines),
            code_lines=len(original_lines) - blank_count - comment,
            comment_lines=comment, blank_lines=blank_count, approximate=True,
        )
        metrics.imports = self._extract_imports(no_comments)
        metrics.functions, metrics.classes, metrics.parse_ok = self._scan_structure(clean)
        return metrics

    def stripped(self, text: str) -> Optional[StrippedSource]:
        """Yorum/string temizlenmiş görünüm. Satır sonları `\\n`e normalleştirilir (satır numaraları değişmez)."""
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        no_comments, clean = self._strip(text)
        if self.spec.preprocessor:
            clean = blank_matches(_PREPROCESSOR_LINE, clean)
        return StrippedSource(no_comments, clean)

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
            blanked = blank(token)
            clean.append(blanked)
            is_comment = match.group('bc') is not None or match.group('lc') is not None
            no_comments.append(blanked if is_comment else token)
            last = match.end()
        tail = text[last:]
        no_comments.append(tail)
        clean.append(tail)
        return ''.join(no_comments), ''.join(clean)

    @staticmethod
    def _classify_lines(original: List[str], without_comments: List[str]) -> Tuple[int, int]:
        blank_count = comment = 0
        for line, stripped in zip(original, without_comments):
            if not line.strip():
                blank_count += 1
            elif not stripped.strip():
                comment += 1
        return blank_count, comment

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
        scanner = _StructureScanner(self._headers, self.spec.family == 'go', clean)
        scanner.run()
        line_starts = [0] + [m.end() for m in re.finditer('\n', clean)]
        functions, classes = self._build_infos(clean, scanner.nodes, lambda offset: bisect_right(line_starts, offset),
                                               scanner.cognitive_opens, scanner.cognitive_closes)
        return functions, classes, scanner.balanced and not scanner.stack

    def _build_infos(self, clean: str, nodes: List[dict], line_of: Callable[[int], int],
                     cognitive_opens: List[int], cognitive_closes: List[int]):
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
                functions.append(FunctionInfo(
                    node['name'], start_line, end_line, 1 + inside, params=node['params'],
                    max_nesting=node['max_nesting'],
                    cognitive=self._cognitive(clean, node['open'], node['close'], cognitive_opens, cognitive_closes)))
        return functions, classes

    # ---- bilişsel karmaşıklık (yaklaşık, SonarSource kuralları) ----------------------------

    @staticmethod
    def _build_cognitive_tokens(spec: LanguageSpec) -> 're.Pattern':
        keywords = '|'.join(spec.structural_keywords)
        parts = [r'(?P<elseif>\belse\s+if\b)', r'(?P<else>\belse\b)',
                 rf'(?P<struct>(?<![.\w$])(?:{keywords})\b)']
        if spec.ternary_pattern:
            parts.append(f'(?P<ternary>{spec.ternary_pattern})')
        parts += [r'(?P<and>&&)', f'(?P<or>{spec.bool_or_pattern})', r'(?P<bound>[;{}])']
        return re.compile('|'.join(parts))

    def _cognitive(self, clean: str, open_pos: int, close_pos: int,
                   cognitive_opens: List[int], cognitive_closes: List[int]) -> int:
        """Yapısal belirteç +1 + iç içe seviye; else / else-if +1; her mantıksal operatör dizisi +1."""
        base = bisect_left(cognitive_opens, open_pos) - bisect_left(cognitive_closes, open_pos)
        total = 0
        last_operator = None
        for match in self._cognitive_tokens.finditer(clean, open_pos + 1, close_pos):
            group = match.lastgroup
            if group == 'bound':
                last_operator = None
            elif group in ('elseif', 'else'):
                total += 1
                last_operator = None
            elif group in ('struct', 'ternary'):
                position = match.start()
                nesting = bisect_left(cognitive_opens, position) - bisect_left(cognitive_closes, position) - base
                total += 1 + max(nesting, 0)
                last_operator = None
            elif group != last_operator:                        # and / or: operatör değişince yeni dizi
                total += 1
                last_operator = group
        return total
