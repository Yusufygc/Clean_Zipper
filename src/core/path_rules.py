"""Yol adından çıkarılan kurallar (test dosyası, hassas dosya tanıma gibi); I/O yapmaz."""
import posixpath
import re
from typing import Optional, Set, Tuple

_TEST_DIRS = frozenset({'test', 'tests', '__tests__', 'spec', 'specs', 'testing', 'e2e', 'integration_tests'})
_TEST_NAME = re.compile(
    r'(?:^test_.*\.\w+$)|(?:_tests?\.\w+$)|(?:\.(?:test|spec)\.\w+$)|(?:^tests?\.\w+$)|(?:tests?\.(?:cs|java|kt)$)',
    re.IGNORECASE)


def is_test_path(rel: str) -> bool:
    """Test klasöründeki veya test adlandırma kuralına uyan dosya (`rel`: köke göre, '/' ayraçlı)."""
    parts = rel.replace('\\', '/').lower().split('/')
    return any(part in _TEST_DIRS for part in parts[:-1]) or bool(_TEST_NAME.search(parts[-1]))


_NON_ALNUM = re.compile(r'[^a-z0-9]')
_TEST_PREFIX = re.compile(r'^(?:(?i:tests?|spec)[_\-.]+|(?:Tests?|Spec)(?=[A-Z0-9]))')
_TEST_SUFFIX = re.compile(r'(?:[_\-.]+(?i:tests?|spec)|(?<=[a-z0-9])(?:Tests?|Spec))$')
_NEUTRAL_MODULES = frozenset({'__init__', '__main__', 'conftest', 'setup', 'manage', 'wsgi', 'asgi', 'index', 'mod'})


def module_key(rel: str, is_test: bool) -> str:
    """Kaynak dosya ile testini eşleştiren anahtar: `foo_bar.py`, `test_foo_bar.py`, `FooBarTests.cs` -> `foobar`.

    Uzantılar ve (yalnızca test dosyasında) `test`/`tests`/`spec` önek-sonekleri atılır, harf-rakam dışı karakterler silinir.
    """
    name = rel.replace('\\', '/').rsplit('/', 1)[-1]
    name = name.rsplit('.', 1)[0] if '.' in name else name
    if is_test:
        name = re.sub(r'\.(?:test|spec)$', '', name, flags=re.IGNORECASE)
        # Önek / sonek yalnızca ayraçta (`test_`, `_test`) ya da büyük harf sınırında (`TestFoo`, `FooTests`) atılır;
        # aksi hâlde `test_service` -> `testservice` -> `ervice` olurdu (`tests` öneki).
        stripped = _TEST_PREFIX.sub('', name, count=1)
        if stripped == name:
            stripped = _TEST_SUFFIX.sub('', name, count=1)
        key = _NON_ALNUM.sub('', stripped.lower())
        return key or _NON_ALNUM.sub('', name.lower())
    return _NON_ALNUM.sub('', name.lower())


def module_keys(rel: str, is_test: bool) -> Set[str]:
    """Eşleme anahtarları: dosya adı (`module_key`) ve üst klasörle birleşik ad.

    `auth/service.py` -> {`service`, `authservice`}: hem `test_service.py` hem `test_auth_service.py` hem de
    `tests/auth/test_service.py` eşleşir. Test klasörü adı (`tests/`, `spec/`) birleşik anahtara girmez.
    """
    key = module_key(rel, is_test)
    parts = rel.replace('\\', '/').lower().split('/')[:-1]
    parent = next((p for p in reversed(parts) if p not in _TEST_DIRS), None)
    if parent is None:
        return {key}
    return {key, _NON_ALNUM.sub('', parent) + key}


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


# `git log -- <pathspec>` için; `**/` kökü de kapsar
SECRET_PATHSPECS = tuple(f':(glob)**/{pattern}' for pattern in (
    '.env', '.env.*', 'credentials.json', 'secrets.yaml', 'secrets.yml', 'secrets.json',
    'id_rsa', 'id_dsa', 'id_ecdsa', 'id_ed25519',
    '*.pem', '*.key', '*.p12', '*.pfx', '*.jks', '*.keystore'))
_EXACT_KINDS = {
    '.env': 'env', 'credentials.json': 'credentials', 'secrets.yaml': 'credentials', 'secrets.yml': 'credentials',
    'secrets.json': 'credentials', 'id_rsa': 'private-key', 'id_dsa': 'private-key', 'id_ecdsa': 'private-key',
    'id_ed25519': 'private-key'}
_KEY_EXTENSIONS = ('.pem', '.key', '.p12', '.pfx', '.jks', '.keystore')
_PUBLIC_ENV_SUFFIXES = ('.example', '.sample', '.template', '.dist', '.tpl')
_UNVERIFIED_EXTENSIONS = ('.pem', '.key')      # içerik doğrulanmadığı için ortak sertifika olabilir


def secret_kind(rel: str) -> Optional[str]:
    """Dosya adından hassas dosya türü (`env`, `credentials`, `private-key`); hassas değilse None."""
    name = posixpath.basename(rel).lower()
    if name in _EXACT_KINDS:
        return _EXACT_KINDS[name]
    if name.startswith('.env.'):
        return None if name.endswith(_PUBLIC_ENV_SUFFIXES) else 'env'
    return 'private-key' if name.endswith(_KEY_EXTENSIONS) else None


def is_unverified_secret(rel: str) -> bool:
    """Adı yalnızca olası bir sırrı gösteren dosya (`.pem`, `.key`): ortak sertifika da olabilir."""
    return rel.lower().endswith(_UNVERIFIED_EXTENSIONS)
