import json
import logging
from typing import List

from src.core.base_analyzer import BaseAnalyzer
from src.core.project_index import FileEntry, ProjectIndex
from src.core.registry import register_analyzer
from src.languages import default_languages, parse_file
from src.languages.ecosystems import ECOSYSTEMS, Ecosystem, SourceScope
from src.models.analysis_models import AnalysisResult, Severity

logger = logging.getLogger(__name__)

# Bunlardan herhangi biri varsa Python projesi için bağımlılık yönetimi var sayılır.
MAX_LISTED_UNPINNED = 8
DEV_MANIFEST_WORDS = ('dev', 'test', 'build', 'lint', 'doc')
PYTHON_MANIFEST_NAMES =frozenset({'requirements.txt', 'pyproject.toml', 'Pipfile', 'setup.py', 'setup.cfg'})


@register_analyzer
class DeadWeightAnalyzer(BaseAnalyzer):
    """Projedeki gereksiz/kullanılmayan kütüphaneleri (bağımlılıkları) tespit eden analizör.

    Manifest bulunan her ekosistem için (requirements.txt, package.json, go.mod, Cargo.toml) manifestin
    klasörü ve alt klasörlerindeki kaynak dosyaların içe aktarmalarıyla karşılaştırır.
    """

    def __init__(self, priority: int = 25):
        super().__init__(priority)

    @property
    def name(self) -> str:
        return "Bağımlılık ve Ölü Kod Analizörü"

    @property
    def category(self) -> str:
        return "dependency"

    def analyze(self, index: ProjectIndex) -> List[AnalysisResult]:
        results: List[AnalysisResult] = []
        for ecosystem in ECOSYSTEMS:
            for manifest_entry in index.files:
                if manifest_entry.path.name in ecosystem.manifest_names:
                    results.extend(self._analyze_manifest(index, ecosystem, manifest_entry))
        results.extend(self._missing_python_manifest(index))
        return results

    def _analyze_manifest(self, index: ProjectIndex, ecosystem: Ecosystem,
                          manifest_entry: FileEntry) -> List[AnalysisResult]:
        text = index.read_text(manifest_entry)
        if text is None:
            return []
        try:
            manifest = ecosystem.parse(text)
        except (ValueError, json.JSONDecodeError):
            logger.warning("Manifest ayrıştırılamadı, atlandı: %s", manifest_entry.rel)
            return []

        scope = self._build_scope(index, ecosystem, manifest_entry)
        results = []
        for dep in manifest.dependencies:
            if dep.dev or ecosystem.is_used(dep, scope, manifest):
                continue
            results.append(self._create_result(
                title=f"Kullanılmayan Kütüphane Tespit Edildi: {dep.name}",
                description=f"'{dep.name}' kütüphanesi {manifest_entry.path.name} içinde tanımlı fakat kodda import edilmemiş.",
                severity=Severity.MEDIUM,
                file_path=manifest_entry.path,
                recommendation=f"Eğer bu kütüphaneyi kullanmıyorsanız {manifest_entry.path.name} dosyasından silerek bağımlılıkları temizleyin.",
                ecosystem=ecosystem.id, rule='unused-dependency', dependency=dep.name,
            ))
        results.extend(self._unpinned(ecosystem, manifest, manifest_entry))
        results.extend(self._dev_in_runtime(ecosystem, manifest, manifest_entry))
        return results

    @staticmethod
    def _is_runtime_manifest(name: str) -> bool:
        """`requirements.txt` çalışma zamanı listesidir; `requirements-dev.txt` gibi adlar geliştirme listesidir."""
        return not any(word in name.lower() for word in DEV_MANIFEST_WORDS)

    def _dev_in_runtime(self, ecosystem: Ecosystem, manifest, manifest_entry: FileEntry) -> List[AnalysisResult]:
        """Python: test / paketleme araçları çalışma zamanı bağımlılık listesinde (kurulum gereksiz şişer)."""
        if ecosystem.id != 'python' or not self._is_runtime_manifest(manifest_entry.path.name):
            return []
        tools = [d.name for d in manifest.dependencies if d.dev]
        if not tools:
            return []
        return [self._create_result(
            title=f"Geliştirme Araçları Çalışma Zamanı Listesinde: {manifest_entry.path.name}",
            description=(f"{', '.join(tools)} test / paketleme aracıdır ama {manifest_entry.path.name} içinde. "
                         "Uygulamayı yalnızca çalıştıran herkes bunları da kurar."),
            severity=Severity.LOW, file_path=manifest_entry.path,
            recommendation="Araçları requirements-dev.txt (test) ve requirements-build.txt (paketleme) gibi ayrı dosyalara taşıyın.",
            ecosystem=ecosystem.id, rule='dev-dependency-in-runtime', count=len(tools), dependencies=tools)]

    def _unpinned(self, ecosystem: Ecosystem, manifest, manifest_entry: FileEntry) -> List[AnalysisResult]:
        """Sürümü sabitlenmemiş bağımlılıklar: manifest başına tek bulgu (tedarik zinciri / tekrarlanabilirlik)."""
        unpinned = [d for d in manifest.dependencies if ecosystem.is_unpinned(d)]
        if not unpinned:
            return []
        listed = ", ".join(f"{d.name}{d.spec}" if d.spec else d.name for d in unpinned[:MAX_LISTED_UNPINNED])
        more = f" ... (+{len(unpinned) - MAX_LISTED_UNPINNED})" if len(unpinned) > MAX_LISTED_UNPINNED else ""
        return [self._create_result(
            title=f"Sabitlenmemiş Bağımlılıklar: {manifest_entry.path.name}",
            description=(f"{len(unpinned)} bağımlılığın sürümü sabit değil: {listed}{more}. "
                         "Her kurulumda farklı sürüm gelebilir (tekrarlanamayan derleme, tedarik zinciri riski)."),
            severity=Severity.LOW, file_path=manifest_entry.path,
            recommendation="Sürümleri tam sürüme sabitleyin (==, ^/~ aralığı) ve kilit dosyası (lock) kullanın.",
            ecosystem=ecosystem.id, rule='unpinned-dependencies', count=len(unpinned),
            dependencies=[{'name': d.name, 'spec': d.spec} for d in unpinned])]

    @staticmethod
    def _build_scope(index: ProjectIndex, ecosystem: Ecosystem, manifest_entry: FileEntry) -> SourceScope:
        manifest_dir = manifest_entry.rel.rsplit('/', 1)[0] + '/' if '/' in manifest_entry.rel else ''
        imports = set()
        entries = []
        for entry in index.files:
            language = default_languages.for_extension(entry.ext)
            if language is None or language.id not in ecosystem.source_languages:
                continue
            if manifest_dir and not entry.rel.startswith(manifest_dir):
                continue
            metrics = parse_file(index, entry)
            if metrics is not None:
                imports.update(metrics.imports)
                entries.append(entry)

        def texts():
            return (t for t in (index.read_text(e) for e in entries) if t is not None)

        return SourceScope(imports, texts)

    def _missing_python_manifest(self, index: ProjectIndex) -> List[AnalysisResult]:
        has_python = next(index.files_with_ext('.py'), None) is not None
        has_manifest = any(f.path.name in PYTHON_MANIFEST_NAMES for f in index.files)
        if not has_python or has_manifest:
            return []
        return [self._create_result(
            title="Gereksinim Dosyası Eksik (requirements.txt)",
            description="Projede requirements.txt bulunamadı. Bağımlılık yönetimi için eklemeniz önerilir.",
            severity=Severity.INFO,
            recommendation="Proje kök dizininde pip bağımlılıklarını içeren bir requirements.txt oluşturun.",
            ecosystem='python',
        )]
