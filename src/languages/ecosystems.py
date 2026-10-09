"""Bağımlılık ekosistemleri: manifest dosyasını okur, bağımlılığın kodda kullanılıp kullanılmadığını söyler.

Kapsam: Python (requirements.txt, pyproject.toml), npm (package.json), Go (go.mod), Rust (Cargo.toml).
Maven/NuGet bilerek yok: paket adı ile namespace arasında güvenilir eşleme olmadığından yanlış pozitif üretirdi.
"""
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Pattern, Set


@dataclass(frozen=True)
class Dependency:
    name: str
    dev: bool = False            # True ise kullanılmayan bağımlılık raporlanmaz
    spec: Optional[str] = None   # sürüm kısıtı (ör. '==1.2', '^4.0'); None: ekosistem pinleme denetlemiyor


@dataclass
class ParsedManifest:
    dependencies: List[Dependency] = field(default_factory=list)
    usage_text: str = ''         # kod dışı kullanım ipuçları (ör. package.json scripts)


class SourceScope:
    """Bir manifestin kapsamındaki kaynak dosyalar: içe aktarmalar ve (nadiren) ham metin araması."""

    def __init__(self, imports: Set[str], texts):
        self.imports = imports
        self._texts = texts                        # çağrılınca metin üreten callable

    def mentions(self, pattern: Pattern) -> bool:
        return any(pattern.search(text) for text in self._texts())


class Ecosystem(ABC):
    id: str
    manifest_names: tuple
    source_languages: tuple                      # içe aktarmaları sayılacak dil kimlikleri

    @abstractmethod
    def parse(self, text: str) -> ParsedManifest: ...

    @abstractmethod
    def is_used(self, dep: Dependency, scope: SourceScope, manifest: ParsedManifest) -> bool: ...

    def is_unpinned(self, dep: Dependency) -> bool:
        """Sürümü belirsiz (derleme tekrarlanamaz / tedarik zinciri riski) bağımlılık; denetlenmiyorsa False."""
        return False


# --------------------------------------------------------------------------- #
#  Python                                                                      #
# --------------------------------------------------------------------------- #

class PythonEcosystem(Ecosystem):
    id = 'python'
    manifest_names = ('requirements.txt',)
    source_languages = ('python',)

    # pip adı -> import adı (farklı olanlar)
    COMMON_MAPPINGS = {
        "pyside6-essentials": "pyside6", "pyside6-addons": "pyside6", "pillow": "pil", "pyyaml": "yaml",
        "scikit-learn": "sklearn", "beautifulsoup4": "bs4", "opencv-python": "cv2", "python-docx": "docx",
        "python-dotenv": "dotenv", "python-socketio": "socketio", "authlib": "authlib", "pyjwt": "jwt",
        "paho-mqtt": "paho", "websocket-client": "websocket",
    }
    # Geliştirme / paketleme araçları import edilmez; "kullanılmıyor" diye raporlanmaz.
    TOOLING = frozenset({
        "pytest", "pytest-cov", "pyinstaller", "black", "flake8", "mypy", "ruff", "pylint", "isort", "tox",
        "coverage", "pre-commit", "wheel", "setuptools", "pip", "twine", "build", "sphinx", "bandit",
    })
    _NAME = re.compile(r'^([A-Za-z0-9][A-Za-z0-9._-]*)')
    _EXACT = re.compile(r'(?:^|,)\s*===?\s*[\w.+!-]+\s*(?:,|$)')       # `==1.2.3` (joker `==1.*` değil)

    def parse(self, text: str) -> ParsedManifest:
        found: Dict[str, str] = {}
        for raw in text.splitlines():
            line = raw.split('#', 1)[0].strip()
            if not line or line.startswith('-') or '://' in line:
                continue                                  # -r, -e, --index-url, URL satırları
            match = self._NAME.match(line)
            if match:
                spec = line[match.end():].split(';', 1)[0].replace(' ', '')
                spec = re.sub(r'^\[[^\]]*\]', '', spec)    # ekstralar: requests[security]==2.0
                found.setdefault(match.group(1), spec)
        return ParsedManifest([Dependency(n, dev=self.is_tooling(n), spec=spec) for n, spec in found.items()])

    @classmethod
    def is_tooling(cls, name: str) -> bool:
        """Test / paketleme aracı; pytest eklentileri (`pytest-qt`, `pytest-mock` ...) fikstürle kullanılır, import edilmez."""
        name = name.lower()
        return name in cls.TOOLING or name.startswith('pytest-')

    def is_unpinned(self, dep: Dependency) -> bool:
        return not dep.dev and dep.spec is not None and not self._EXACT.search(dep.spec)

    def is_used(self, dep: Dependency, scope: SourceScope, manifest: ParsedManifest) -> bool:
        key = dep.name.lower()
        mapped = self.COMMON_MAPPINGS.get(key, key)
        candidates = {mapped, mapped.replace('-', '_'), mapped.replace('.', '_')}
        for imported in scope.imports:
            imported = imported.lower()
            if any(imported == c or imported.startswith(c + '.') for c in candidates):
                return True
        return False


class PyprojectEcosystem(PythonEcosystem):
    """`pyproject.toml`: PEP 621 `[project].dependencies` ve Poetry `[tool.poetry.dependencies]`.

    Yalnızca çalışma zamanı bağımlılıkları okunur. Geliştirme grupları (`optional-dependencies`, Poetry grupları,
    `dependency-groups`, `tool.pdm/uv` dev) bilinçli olarak atlanır: araçlar import edilmez, "kullanılmıyor" diye
    raporlanırdı. Sürüm sabitleme denetlenmez: pyproject aralık bildirir, sabitleme kilit dosyasının işidir
    (`missing-lockfile`).
    """
    manifest_names = ('pyproject.toml',)

    def parse(self, text: str) -> ParsedManifest:
        data = _load_toml(text)
        unique = dict.fromkeys(self._pep621_names(data) + self._poetry_names(data))
        return ParsedManifest([Dependency(n, dev=self.is_tooling(n)) for n in unique])

    def _pep621_names(self, data: dict) -> List[str]:
        """`[project].dependencies`: PEP 508 dizeleri (`requests[socks]>=2 ; python_version<'4'`)."""
        requirements = (data.get('project') or {}).get('dependencies') or []
        matches = (self._NAME.match(str(r).strip()) for r in requirements)
        return [m.group(1) for m in matches if m]

    @staticmethod
    def _poetry_names(data: dict) -> List[str]:
        poetry = ((data.get('tool') or {}).get('poetry') or {}).get('dependencies') or {}
        return [name for name in poetry if name.lower() != 'python']

    def is_unpinned(self, dep: Dependency) -> bool:
        return False


def _load_toml(text: str) -> dict:
    """TOML ayrıştırma; hatalı belge `ValueError` (TOMLDecodeError) fırlatır."""
    try:
        import tomllib                                       # Python 3.11+
    except ModuleNotFoundError:                              # Python 3.10: aynı API'li tomli
        import tomli as tomllib
    return tomllib.loads(text)


# --------------------------------------------------------------------------- #
#  npm                                                                         #
# --------------------------------------------------------------------------- #

class NpmEcosystem(Ecosystem):
    id = 'npm'
    manifest_names = ('package.json',)
    source_languages = ('javascript', 'typescript')

    def parse(self, text: str) -> ParsedManifest:
        data = json.loads(text)
        deps = data.get('dependencies') or {}
        scripts = data.get('scripts') or {}
        return ParsedManifest(
            # devDependencies okunmaz; @types/* derleyici tarafından kullanılır, import edilmez.
            [Dependency(name, dev=name.startswith('@types/'), spec=str(spec)) for name, spec in deps.items()],
            usage_text='\n'.join(str(v) for v in scripts.values()),
        )

    _FLOATING = re.compile(r'^\s*(?:|\*|x|latest|next|[<>]=?.*|(?:git\+|https?:|github:|git:|ssh:).*)\s*$', re.IGNORECASE)

    def is_unpinned(self, dep: Dependency) -> bool:
        """`*`, `latest`, boş, açık uçlu aralık (`>=1`) ve git/URL bağımlılıkları; `^`/`~` normal sayılır."""
        return not dep.dev and dep.spec is not None and bool(self._FLOATING.match(dep.spec))

    def is_used(self, dep: Dependency, scope: SourceScope, manifest: ParsedManifest) -> bool:
        if any(s == dep.name or s.startswith(dep.name + '/') for s in scope.imports):
            return True
        # `scripts` içinde CLI olarak kullanılan paketler (rimraf, cross-env, ...)
        return re.search(r'(?<![\w@/.-])' + re.escape(dep.name) + r'(?![\w-])', manifest.usage_text) is not None


# --------------------------------------------------------------------------- #
#  Go                                                                          #
# --------------------------------------------------------------------------- #

class GoEcosystem(Ecosystem):
    id = 'go'
    manifest_names = ('go.mod',)
    source_languages = ('go',)

    def parse(self, text: str) -> ParsedManifest:
        deps: List[Dependency] = []
        in_block = False
        for raw in text.splitlines():
            line = raw.strip()
            if in_block:
                if line.startswith(')'):
                    in_block = False
                else:
                    self._add(deps, line)
            elif re.match(r'require\s*\($', line):
                in_block = True
            elif re.match(r'require\s+\S', line):
                self._add(deps, line[len('require'):].strip())
        return ParsedManifest(deps)

    @staticmethod
    def _add(deps: List[Dependency], spec: str):
        if not spec or spec.startswith('//') or '// indirect' in spec:
            return                                         # dolaylı bağımlılıklar import edilmez
        deps.append(Dependency(spec.split()[0]))

    def is_used(self, dep: Dependency, scope: SourceScope, manifest: ParsedManifest) -> bool:
        return any(s == dep.name or s.startswith(dep.name + '/') for s in scope.imports)


# --------------------------------------------------------------------------- #
#  Rust                                                                        #
# --------------------------------------------------------------------------- #

class RustEcosystem(Ecosystem):
    id = 'cargo'
    manifest_names = ('Cargo.toml',)
    source_languages = ('rust',)

    _SECTION = re.compile(r'^\[\s*(?P<name>[^\]]+?)\s*\]$')
    _DEPS_SECTION = re.compile(r'^(?:target\..+\.)?dependencies$')
    _DEPS_TABLE = re.compile(r'^(?:target\..+\.)?dependencies\.(?P<crate>[^.]+)$')

    def parse(self, text: str) -> ParsedManifest:
        names: List[str] = []
        in_deps = False
        for raw in text.splitlines():
            line = re.sub(r'\s+#.*$', '', raw).strip()
            if not line or line.startswith('#'):
                continue
            section = self._SECTION.match(line)
            if section:
                name = section.group('name').replace('"', '').replace("'", '')
                table = self._DEPS_TABLE.match(name)
                in_deps = bool(self._DEPS_SECTION.match(name))
                if table:
                    names.append(table.group('crate'))
                continue
            if in_deps and '=' in line:
                names.append(line.split('=', 1)[0].strip().strip('"').split('.')[0])
        return ParsedManifest([Dependency(n) for n in dict.fromkeys(names)])

    def is_used(self, dep: Dependency, scope: SourceScope, manifest: ParsedManifest) -> bool:
        crate = dep.name.replace('-', '_')
        if any(s.split('::')[0] == crate for s in scope.imports):
            return True
        # `serde_json::from_str(..)` gibi use olmadan tam yolla kullanım
        return scope.mentions(re.compile(r'\b' + re.escape(crate) + r'::'))


ECOSYSTEMS: List[Ecosystem] = [PythonEcosystem(), PyprojectEcosystem(), NpmEcosystem(), GoEcosystem(), RustEcosystem()]
