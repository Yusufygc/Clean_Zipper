import json
import logging
import posixpath
from typing import List, Set

from src.core.base_analyzer import BaseAnalyzer
from src.core.path_rules import is_test_path
from src.core.project_index import FileEntry, ProjectIndex
from src.core.registry import register_analyzer
from src.languages import parse_file
from src.languages.ecosystems import ECOSYSTEMS
from src.models.analysis_models import AnalysisResult, Severity

logger = logging.getLogger(__name__)

README_PREFIXES = ('readme',)
LICENSE_PREFIXES = ('license', 'licence', 'copying', 'unlicense')
CI_FILES = frozenset({'.gitlab-ci.yml', 'jenkinsfile', 'azure-pipelines.yml', 'bitbucket-pipelines.yml',
                      '.travis.yml', 'appveyor.yml', '.drone.yml', 'cloudbuild.yaml', 'buildkite.yml'})
ENV_EXAMPLES = frozenset({'.env.example', '.env.sample', '.env.template', '.env.dist', 'example.env', 'env.example',
                          'sample.env'})
# manifest -> bu klasörde veya üst klasörlerinde aranacak kilit dosyaları
LOCK_FILES = {
    'package.json': ('package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'bun.lockb', 'bun.lock', 'npm-shrinkwrap.json'),
    'Cargo.toml': ('Cargo.lock',),
    'go.mod': ('go.sum',),
    'Pipfile': ('Pipfile.lock',),
    'pyproject.toml': ('poetry.lock', 'uv.lock', 'pdm.lock', 'Pipfile.lock'),
}
_LOCKING_TOOLS = ('[tool.poetry', '[tool.uv', '[tool.pdm')       # kilit dosyası üreten pyproject araçları


@register_analyzer
class ProjectHygieneAnalyzer(BaseAnalyzer):
    """Proje hijyeni kontrol listesi: README, LICENSE, .gitignore, CI, kilit dosyası, .env.example.

    Eksik her madde ayrı DÜŞÜK bulgudur. Ayrıca tek bir BİLGİ özeti (`hygiene-summary`) hangi iyi pratiklerin bulunduğunu
    (`present`) ve eksik olanları (`missing`) listeler; denetim raporu bunu "iyi pratikler" bölümünde kullanır.
    """

    def __init__(self, priority: int = 45):
        super().__init__(priority)

    @property
    def name(self) -> str:
        return "Proje Hijyeni Analizörü"

    @property
    def category(self) -> str:
        return "hygiene"

    def analyze(self, index: ProjectIndex) -> List[AnalysisResult]:
        rels = {f.rel for f in index.files}
        root_names = {rel.lower() for rel in rels if '/' not in rel}
        present: List[str] = []
        results = self._basic_checks(index, rels, root_names, present)
        results.extend(self._lockfiles(index, rels, present))
        results.extend(self._env_example(index, rels, present))
        if any(n == 'dockerfile' or n.startswith('dockerfile.') for n in root_names):
            present.append('dockerfile')
        if present or results:
            results.append(self._summary(present, results))
        return results

    def _basic_checks(self, index: ProjectIndex, rels: Set[str], root_names: Set[str],
                      present: List[str]) -> List[AnalysisResult]:
        has_code = self._source_lines(index) >= self.thresholds.test_min_source_lines
        # (anahtar, var mı, başlık, öneri, kontrol geçerli mi)
        checks = (
            ('readme', any(n.startswith(README_PREFIXES) for n in root_names), "README Eksik",
             "Projeyi, kurulumu ve kullanımı anlatan bir README ekleyin.", has_code),
            ('license', any(n.startswith(LICENSE_PREFIXES) for n in root_names), "LICENSE Eksik",
             "Lisans dosyası ekleyin (lisanssız kod varsayılan olarak başkalarınca kullanılamaz).", has_code),
            ('gitignore', '.gitignore' in root_names, ".gitignore Eksik",
             "Derleme çıktıları, sanal ortamlar ve gizli dosyalar için kök .gitignore ekleyin.",
             (index.root / '.git').exists()),
            ('ci', self._has_ci(rels, root_names), "CI Yapılandırması Yok",
             "Testleri her değişiklikte çalıştıran bir CI iş akışı ekleyin (GitHub Actions, GitLab CI ...).",
             has_code and self._has_tests(index)),
        )
        results = []
        for key, ok, title, advice, applies in checks:
            if not applies:
                continue
            if ok:
                present.append(key)
            else:
                results.append(self._missing(index, key, title, advice))
        return results

    # ---- yardımcılar -------------------------------------------------------------------------------

    @staticmethod
    def _source_lines(index: ProjectIndex) -> int:
        total = 0
        for entry in index.files:
            if is_test_path(entry.rel):
                continue
            metrics = parse_file(index, entry)
            if metrics is not None:
                total += metrics.code_lines
        return total

    @staticmethod
    def _has_tests(index: ProjectIndex) -> bool:
        return any(is_test_path(f.rel) for f in index.files)

    @staticmethod
    def _has_ci(rels: Set[str], root_names: Set[str]) -> bool:
        if any(rel.startswith('.github/workflows/') and rel.endswith(('.yml', '.yaml')) for rel in rels):
            return True
        return '.circleci/config.yml' in rels or bool(root_names & CI_FILES)

    def _missing(self, index: ProjectIndex, key: str, title: str, advice: str) -> AnalysisResult:
        return self._create_result(
            title=title, description=f"Proje kökünde beklenen '{key}' bulunamadı.",
            severity=Severity.LOW, file_path=index.root, recommendation=advice,
            rule=f'missing-{key}', approximate=False)

    # ---- kilit dosyaları ------------------------------------------------------------------------------

    def _lockfiles(self, index: ProjectIndex, rels: Set[str], present: List[str]) -> List[AnalysisResult]:
        results = []
        checked = ok = 0
        for entry in index.files:
            candidates = LOCK_FILES.get(entry.path.name)
            if candidates is None or not self._needs_lock(index, entry, rels):
                continue
            checked += 1
            if self._lock_nearby(entry.rel, candidates, rels):
                ok += 1
                continue
            results.append(self._create_result(
                title=f"Kilit Dosyası Yok: {entry.rel}",
                description=f"'{entry.rel}' bağımlılık tanımlıyor ama yanında/üstünde kilit dosyası ({', '.join(candidates[:3])}) yok; kurulumlar tekrarlanamaz.",
                severity=Severity.LOW, file_path=entry.path,
                recommendation="Kilit dosyasını üretin ve sürüm kontrolüne ekleyin (npm install, poetry lock, cargo build, go mod tidy).",
                rule='missing-lockfile', manifest=entry.rel, approximate=False))
        if checked and ok == checked:
            present.append('lockfile')
        return results

    @staticmethod
    def _lock_nearby(manifest_rel: str, candidates, rels: Set[str]) -> bool:
        directory = posixpath.dirname(manifest_rel)
        while True:
            if any(posixpath.join(directory, name) in rels for name in candidates):
                return True
            if not directory:
                return False
            directory = posixpath.dirname(directory)              # monorepo: kilit dosyası kökte olabilir

    def _needs_lock(self, index: ProjectIndex, entry: FileEntry, rels: Set[str]) -> bool:
        text = index.read_text(entry)
        if text is None:
            return False
        name = entry.path.name
        if name == 'pyproject.toml':
            return any(tool in text for tool in _LOCKING_TOOLS)
        if name == 'Pipfile':
            return '[packages]' in text
        if name == 'Cargo.toml':
            directory = posixpath.dirname(entry.rel)                # kütüphane crate'leri kilit dosyasını sürmez
            return posixpath.join(directory, 'src/main.rs') in rels and self._has_dependencies(name, text)
        return self._has_dependencies(name, text)

    @staticmethod
    def _has_dependencies(manifest_name: str, text: str) -> bool:
        ecosystem = next((e for e in ECOSYSTEMS if manifest_name in e.manifest_names), None)
        if ecosystem is None:
            return False
        try:
            return bool(ecosystem.parse(text).dependencies)
        except (ValueError, json.JSONDecodeError):
            logger.warning("Manifest ayrıştırılamadı, kilit dosyası denetimi atlandı: %s", manifest_name)
            return False

    # ---- .env.example ----------------------------------------------------------------------------------

    def _env_example(self, index: ProjectIndex, rels: Set[str], present: List[str]) -> List[AnalysisResult]:
        names = {posixpath.basename(rel).lower() for rel in rels}
        uses_env = '.env' in {posixpath.basename(rel) for rel in rels} or (index.root / '.env').is_file()
        if not uses_env:
            return []
        if names & ENV_EXAMPLES:
            present.append('env-example')
            return []
        return [self._missing(index, 'env-example', ".env.example Eksik",
                              ".env dosyasının değerleri boş/örnek hâliyle bir .env.example olarak commit edin; yeni geliştirici hangi değişkenlerin gerektiğini bilsin.")]

    # ---- özet -------------------------------------------------------------------------------------------------

    def _summary(self, present: List[str], missing: List[AnalysisResult]) -> AnalysisResult:
        missing_keys = [r.metadata['rule'].replace('missing-', '') for r in missing]
        total = len(present) + len(missing_keys)
        return self._create_result(
            title=f"Proje Hijyeni: {len(present)}/{total} kontrol tamam",
            description=f"Mevcut: {', '.join(present) or '-'}. Eksik: {', '.join(missing_keys) or '-'}.",
            severity=Severity.INFO,
            rule='hygiene-summary', present=present, missing=missing_keys, approximate=False)
