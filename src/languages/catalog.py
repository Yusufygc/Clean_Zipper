"""Desteklenen dillerin kaydı. Yeni dil eklemek: burada bir LanguageSpec ve bir kayıt satırı."""
from src.languages import brace as b
from src.languages.brace import BraceLanguage, LanguageSpec
from src.languages.python_lang import PythonLanguage
from src.languages.registry import default_languages

# ---- ortak parçalar ---------------------------------------------------------

_C_LIKE_KEYWORDS = frozenset({
    'if', 'for', 'while', 'switch', 'catch', 'return', 'sizeof', 'else', 'do', 'try', 'using', 'lock',
    'foreach', 'fixed', 'synchronized', 'constexpr', 'delegate', 'typeof', 'throw', 'new', 'unchecked',
    'checked', 'unsafe', 'when', 'elif', 'alignof', 'decltype', 'static_assert', 'defined',
})
_JS_KEYWORDS = frozenset({
    'if', 'for', 'while', 'switch', 'catch', 'function', 'return', 'else', 'do', 'try', 'with', 'typeof',
    'await', 'new', 'throw', 'super',
})

# Üçlü ifade `?`: boşluk/`)`/`]` sonrası, `?.` `??` `?:` `?>` ve `? extends` hariç.
_TERNARY = r'(?<=[\s)\]])\?(?![?.:>])(?!\s*(?:extends|super)\b)'
_WORDS_C = r'(?<![.\w$])(?:if|for|while|case|catch)\b'

_C_DECISION = _WORDS_C + r'|&&|\|\||' + _TERNARY
_CSHARP_DECISION = r'(?<![.\w$])(?:if|for|foreach|while|case|catch)\b|&&|\|\||' + _TERNARY
_JS_DECISION = _C_DECISION
_GO_DECISION = r'(?<![.\w$])(?:if|for|case)\b|&&|\|\|'
_RUST_DECISION = r'(?<![.\w$])(?:if|for|while|loop)\b|&&|(?<!\bmove)(?<=[\w)\]])\s*\|\||=>'

_C_INCLUDE = r'(?m)^[ \t]*#[ \t]*include[ \t]*[<"]([^>"\n]+)[>"]'
_JS_IMPORTS = (
    r'''(?m)^[ \t]*import\s+(?:type\s+)?(?:[\w$*{}\s,]+?\s+from\s+)?['"]([^'"\n]+)['"]''',
    r'''\brequire\s*\(\s*['"]([^'"\n]+)['"]\s*\)''',
    r'''\bimport\s*\(\s*['"]([^'"\n]+)['"]\s*\)''',
    r'''(?m)^[ \t]*export\s+(?:type\s+)?(?:\*|\{[^}]*\})\s*(?:as\s+\w+\s+)?from\s+['"]([^'"\n]+)['"]''',
)
_JS_CLEANERS = (r'@[\w$.]+(?:\([^()]*\))?',)     # dekoratörler

# ---- diller -----------------------------------------------------------------

C = LanguageSpec(
    id='c', display_name='C', extensions=('.c', '.h'), family='c_like',
    string_patterns=(b.DOUBLE_QUOTED,), char_literal=True, preprocessor=True,
    decision_pattern=_C_DECISION, import_patterns=(_C_INCLUDE,), keywords=_C_LIKE_KEYWORDS,
    class_kinds=('struct',), header_cleaners=(r'__attribute__\s*\(\(.*?\)\)', r'__declspec\s*\([^)]*\)'),
    # .h dosyası C++ işaretleri taşıyorsa C++ sayılır
    refine_pattern=r'(?m)^\s*(?:template\s*<|namespace\s+\w+|class\s+\w+\s*[:{;]|public\s*:|private\s*:|protected\s*:)|\bstd::',
    refine_to='cpp',
)
CPP = LanguageSpec(
    id='cpp', display_name='C++', extensions=('.cc', '.cpp', '.cxx', '.c++', '.hpp', '.hh', '.hxx', '.ipp', '.tpp'),
    family='c_like', string_patterns=(b.CPP_RAW_STRING, b.DOUBLE_QUOTED), char_literal=True, preprocessor=True,
    decision_pattern=_C_DECISION, import_patterns=(_C_INCLUDE,), keywords=_C_LIKE_KEYWORDS,
    class_kinds=('class', 'struct'), new_guard=True,
    header_cleaners=(r'\[\[[^\]]*\]\]', r'__attribute__\s*\(\(.*?\)\)', r'__declspec\s*\([^)]*\)'),
)
JAVA = LanguageSpec(
    id='java', display_name='Java', extensions=('.java',), family='c_like',
    string_patterns=(b.TRIPLE_QUOTED, b.DOUBLE_QUOTED), char_literal=True,
    decision_pattern=_C_DECISION,
    import_patterns=(r'(?m)^[ \t]*import\s+(?:static\s+)?([\w.]+?)(?:\.\*)?\s*;',), keywords=_C_LIKE_KEYWORDS,
    class_kinds=('class', 'interface', 'record'), new_guard=True,
    header_cleaners=(r'@[\w.]+(?:\s*\((?:[^()]|\([^()]*\))*\))?',),
)
CSHARP = LanguageSpec(
    id='csharp', display_name='C#', extensions=('.cs',), family='c_like',
    string_patterns=(b.TRIPLE_QUOTED, b.CSHARP_VERBATIM, b.CSHARP_INTERPOLATED, b.DOUBLE_QUOTED),
    char_literal=True, preprocessor=True,
    decision_pattern=_CSHARP_DECISION,
    import_patterns=(r'(?m)^[ \t]*(?:global\s+)?using\s+(?:static\s+)?(?:\w+\s*=\s*)?([\w.]+)\s*;',),
    keywords=_C_LIKE_KEYWORDS, class_kinds=('class', 'interface', 'record', 'struct'),
    class_header_parens=True, new_guard=True,
    header_cleaners=(r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]',),
)
JAVASCRIPT = LanguageSpec(
    id='javascript', display_name='JavaScript', extensions=('.js', '.jsx', '.mjs', '.cjs'), family='js',
    string_patterns=(b.DOUBLE_QUOTED, b.SINGLE_QUOTED, b.TEMPLATE_LITERAL), regex_literal=True,
    decision_pattern=_JS_DECISION, import_patterns=_JS_IMPORTS, keywords=_JS_KEYWORDS,
    class_kinds=('class',), class_header_parens=True, new_guard=True, header_cleaners=_JS_CLEANERS,
)
TYPESCRIPT = LanguageSpec(
    id='typescript', display_name='TypeScript', extensions=('.ts', '.tsx', '.mts', '.cts'), family='js',
    string_patterns=(b.DOUBLE_QUOTED, b.SINGLE_QUOTED, b.TEMPLATE_LITERAL), regex_literal=True,
    decision_pattern=_JS_DECISION, import_patterns=_JS_IMPORTS, keywords=_JS_KEYWORDS,
    class_kinds=('class', 'interface'), class_header_parens=True, new_guard=True, header_cleaners=_JS_CLEANERS,
)
GO = LanguageSpec(
    id='go', display_name='Go', extensions=('.go',), family='go',
    string_patterns=(b.GO_RAW_STRING, b.DOUBLE_QUOTED), char_literal=True,
    decision_pattern=_GO_DECISION,
    import_patterns=(r'(?m)^[ \t]*import\s+(?:[\w.]+\s+)?"([^"\n]+)"',), keywords=frozenset(),
)
RUST = LanguageSpec(
    id='rust', display_name='Rust', extensions=('.rs',), family='rust',
    string_patterns=(b.RUST_RAW_STRING, b.DOUBLE_QUOTED), char_literal=True,
    decision_pattern=_RUST_DECISION,
    import_patterns=(r'(?m)^[ \t]*(?:pub(?:\([^)]*\))?\s+)?use\s+(?:::)?([\w:]+)',
                     r'(?m)^[ \t]*(?:pub\s+)?extern\s+crate\s+(\w+)'),
    keywords=frozenset(),
)

default_languages.register(PythonLanguage())
for _spec in (C, CPP, JAVA, CSHARP, JAVASCRIPT, TYPESCRIPT, GO, RUST):
    default_languages.register(BraceLanguage(_spec))
