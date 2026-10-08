"""Dil bazlı test kalıpları: test işlevi sayısı, atlanmış testler, kararsızlık (flaky) işaretleri. Sözcük tabanlı."""
import re
from typing import Dict, List, Pattern

# Test işlevi tanımları. `strings`: True ise string içeriği korunan metinde (it('...') gibi) aranır.
_TEST_DEFINITIONS: Dict[str, tuple] = {
    'javascript': (re.compile(r'(?<![\w$.])(?:it|test)(?:\.(?:only|skip|concurrent))?\s*\(\s*["\'`]'), True),
    'typescript': (re.compile(r'(?<![\w$.])(?:it|test)(?:\.(?:only|skip|concurrent))?\s*\(\s*["\'`]'), True),
    'java': (re.compile(r'@(?:Test|ParameterizedTest|RepeatedTest)\b'), False),
    'csharp': (re.compile(r'\[(?:Fact|Theory|Test|TestCase|TestMethod)\b'), False),
    'go': (re.compile(r'(?m)^func\s+(?:Test|Benchmark|Example)\w*\s*\('), False),
    'rust': (re.compile(r'#\[(?:\w+::)?test\b'), False),
    'c': (re.compile(r'\b(?:TEST|TEST_F|TEST_P|TEST_CASE|START_TEST)\s*\('), False),
    'cpp': (re.compile(r'\b(?:TEST|TEST_F|TEST_P|TEST_CASE|BOOST_AUTO_TEST_CASE)\s*\('), False),
}

# Atlanmış / devre dışı testler.
_SKIP_PATTERNS: Dict[str, Pattern] = {
    'python': re.compile(r'@(?:pytest\.mark\.skip(?:if)?|unittest\.skip(?:If|Unless)?)\b|\bpytest\.skip\s*\(|\bself\.skipTest\s*\('),
    'javascript': re.compile(r'(?<![\w$.])(?:it|test|describe)\.skip\s*\(|(?<![\w$.])(?:xit|xdescribe|xtest)\s*\('),
    'typescript': re.compile(r'(?<![\w$.])(?:it|test|describe)\.skip\s*\(|(?<![\w$.])(?:xit|xdescribe|xtest)\s*\('),
    'java': re.compile(r'@(?:Disabled|Ignore)\b'),
    'csharp': re.compile(r'\bSkip\s*=\s*"|\[Ignore\b'),
    'go': re.compile(r'\bt\.Skip(?:Now|f)?\s*\('),
    'rust': re.compile(r'#\[ignore\b'),
}

_LOCAL = r'(?:localhost|127\.0\.0\.1|0\.0\.0\.0|testserver|example\.(?:com|org|net))'

# Kararsızlık işaretleri: gerçek bekleme ve gerçek ağ çağrısı.
_SLEEP_PATTERNS: Dict[str, Pattern] = {
    'python': re.compile(r'(?<![\w.])(?:time|asyncio)\.sleep\s*\('),
    'javascript': re.compile(r'(?<![\w$.])sleep\s*\(|new\s+Promise\s*\(\s*\(?\s*\w+\s*\)?\s*=>\s*setTimeout\s*\('),
    'typescript': re.compile(r'(?<![\w$.])sleep\s*\(|new\s+Promise\s*\(\s*\(?\s*\w+\s*\)?\s*=>\s*setTimeout\s*\('),
    'java': re.compile(r'\bThread\.sleep\s*\('),
    'csharp': re.compile(r'\bThread\.Sleep\s*\(|\bTask\.Delay\s*\('),
    'go': re.compile(r'\btime\.Sleep\s*\('),
    'rust': re.compile(r'\bthread::sleep\s*\('),
    'cpp': re.compile(r'\bstd::this_thread::sleep_for\s*\(|\busleep\s*\('),
}
_NETWORK_PATTERNS: Dict[str, Pattern] = {
    'python': re.compile(r'\b(?:requests|httpx)\.(?:get|post|put|delete|patch|head)\s*\(\s*f?["\']https?://(?!' + _LOCAL
                         + r'\b)|\burlopen\s*\(\s*["\']https?://(?!' + _LOCAL + r'\b)'),
    'javascript': re.compile(r'\b(?:fetch|axios(?:\.\w+)?)\s*\(\s*["\'`]https?://(?!' + _LOCAL + r'\b)'),
    'typescript': re.compile(r'\b(?:fetch|axios(?:\.\w+)?)\s*\(\s*["\'`]https?://(?!' + _LOCAL + r'\b)'),
}


def _lines(pattern: Pattern, text: str) -> List[int]:
    return sorted({text.count('\n', 0, m.start()) + 1 for m in pattern.finditer(text)})


def count_tests(language: str, clean: str, no_comments: str, python_test_functions: int = 0) -> int:
    """Dosyadaki test işlevi sayısı. Python için `def test*` sayısı çağıran tarafından verilir (ast)."""
    if language == 'python':
        return python_test_functions
    entry = _TEST_DEFINITIONS.get(language)
    if entry is None:
        return 0
    pattern, needs_strings = entry
    return len(pattern.findall(no_comments if needs_strings else clean))


def find_skipped(language: str, clean: str) -> int:
    pattern = _SKIP_PATTERNS.get(language)
    return len(pattern.findall(clean)) if pattern is not None else 0


def find_sleeps(language: str, clean: str) -> List[int]:
    pattern = _SLEEP_PATTERNS.get(language)
    return _lines(pattern, clean) if pattern is not None else []


def find_network_calls(language: str, no_comments: str) -> List[int]:
    pattern = _NETWORK_PATTERNS.get(language)
    return _lines(pattern, no_comments) if pattern is not None else []
