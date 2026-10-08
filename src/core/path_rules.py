"""Yol adından çıkarılan kurallar (test dosyası tanıma gibi); I/O yapmaz."""
import re
from typing import Optional, Tuple

_TEST_DIRS = frozenset({'test', 'tests', '__tests__', 'spec', 'specs', 'testing', 'e2e', 'integration_tests'})
_TEST_NAME = re.compile(
    r'(?:^test_.*\.\w+$)|(?:_tests?\.\w+$)|(?:\.(?:test|spec)\.\w+$)|(?:^tests?\.\w+$)|(?:tests?\.(?:cs|java|kt)$)',
    re.IGNORECASE)


def is_test_path(rel: str) -> bool:
    """Test klasöründeki veya test adlandırma kuralına uyan dosya (`rel`: köke göre, '/' ayraçlı)."""
    parts = rel.replace('\\', '/').lower().split('/')
    return any(part in _TEST_DIRS for part in parts[:-1]) or bool(_TEST_NAME.search(parts[-1]))


_NON_ALNUM = re.compile(r'[^a-z0-9]')
_TEST_WORDS = ('tests', 'test', 'spec')
_NEUTRAL_MODULES = frozenset({'__init__', '__main__', 'conftest', 'setup', 'manage', 'wsgi', 'asgi', 'index', 'mod'})


def module_key(rel: str, is_test: bool) -> str:
    """Kaynak dosya ile testini eşleştiren anahtar: `foo_bar.py`, `test_foo_bar.py`, `FooBarTests.cs` -> `foobar`.

    Uzantılar ve (yalnızca test dosyasında) `test`/`tests`/`spec` önek-sonekleri atılır, harf-rakam dışı karakterler silinir.
    """
    name = rel.replace('\\', '/').rsplit('/', 1)[-1].lower()
    name = name.rsplit('.', 1)[0] if '.' in name else name
    if is_test:
        name = re.sub(r'\.(?:test|spec)$', '', name)
        key = _NON_ALNUM.sub('', name)
        for word in _TEST_WORDS:
            if key.startswith(word) and len(key) > len(word):
                return key[len(word):]
            if key.endswith(word) and len(key) > len(word):
                return key[:-len(word)]
        return key
    return _NON_ALNUM.sub('', name)


def is_neutral_module(rel: str) -> bool:
    """Kendi başına test beklenmeyen giriş / yapılandırma dosyaları (`__init__`, `conftest`, `index` ...)."""
    name = rel.replace('\\', '/').rsplit('/', 1)[-1].lower().rsplit('.', 1)[0]
    return name in _NEUTRAL_MODULES


# Sürüm kontrolüne girmemesi gereken klasörler -> tür
_ARTIFACT_DIRS = {
    'node_modules': 'dependencies', 'venv': 'dependencies', '.venv': 'dependencies',
    '__pycache__': 'cache', '.pytest_cache': 'cache', '.mypy_cache': 'cache', '.ruff_cache': 'cache', '.tox': 'cache',
    'htmlcov': 'cache', '.next': 'cache', '.nuxt': 'cache', '.svelte-kit': 'cache', '.gradle': 'cache',
    'dist': 'build', 'build': 'build',
}


# Bu klasörlerin altındaki `dist` / `build` üçüncü taraf paketidir (libman, vendor); bilinçli olarak commit edilir.
_VENDOR_DIRS = frozenset({'lib', 'libs', 'vendor', 'vendors', 'third_party', 'third-party', 'external'})


def artifact_root(rel: str) -> Optional[Tuple[str, str]]:
    """Üretilmiş içerik yolu için (kök, tür): `web/node_modules/x/y.js` -> ('web/node_modules', 'dependencies').

    Tür: 'dependencies' | 'cache' | 'build' | 'bytecode' (`.pyc`). Normal kaynak yolu için None.
    `dist` / `build` ad olarak belirsizdir (kaynak da olabilir); çağıran bunu yaklaşık saymalıdır. `lib/`, `vendor/` gibi
    üçüncü taraf klasörlerinin altındakiler sayılmaz.
    """
    parts = rel.replace('\\', '/').split('/')
    for position, part in enumerate(parts[:-1]):
        kind = _ARTIFACT_DIRS.get(part)
        if kind == 'build' and _VENDOR_DIRS.intersection(parts[:position]):
            continue
        if kind:
            return '/'.join(parts[:position + 1]), kind
    if parts[-1].lower().endswith('.pyc'):
        return '/'.join(parts[:-1] + ['*.pyc']), 'bytecode'
    return None
