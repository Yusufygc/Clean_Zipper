"""Yol adından çıkarılan kurallar (test dosyası tanıma gibi); I/O yapmaz."""
import re

_TEST_DIRS = frozenset({'test', 'tests', '__tests__', 'spec', 'specs', 'testing', 'e2e', 'integration_tests'})
_TEST_NAME = re.compile(
    r'(?:^test_.*\.\w+$)|(?:_tests?\.\w+$)|(?:\.(?:test|spec)\.\w+$)|(?:^tests?\.\w+$)|(?:tests?\.(?:cs|java|kt)$)',
    re.IGNORECASE)


def is_test_path(rel: str) -> bool:
    """Test klasöründeki veya test adlandırma kuralına uyan dosya (`rel`: köke göre, '/' ayraçlı)."""
    parts = rel.replace('\\', '/').lower().split('/')
    return any(part in _TEST_DIRS for part in parts[:-1]) or bool(_TEST_NAME.search(parts[-1]))
