import posixpath
import time
from collections import Counter
from itertools import combinations
from typing import Dict, List, Optional, Sequence, Tuple

from src.core.base_analyzer import BaseAnalyzer
from src.core.path_rules import is_test_path, module_key
from src.core.project_index import FileEntry, ProjectIndex
from src.core.registry import register_analyzer
from src.languages import parse_file
from src.models.analysis_models import AnalysisResult, Severity
from src.utils import git_info
from src.utils.git_info import Commit

COMMIT_LIMIT = 500                # incelenen son commit sayısı
MIN_COMMITS = 20                  # bundan kısa geçmişte sıcak nokta / birlikte değişim anlamsız
MAX_FILES_PER_COMMIT = 30         # daha geniş commit'ler (toplu biçimlendirme, taşıma) atlanır
MIN_HOTSPOT_CHANGES = 5
HOTSPOT_LIMIT = 10
HOTSPOT_WARN_CHANGES = 20         # bu kadar değişen VE eşiği aşan işlevi olan dosya DÜŞÜK
MIN_SHARED_COMMITS = 5
MIN_CONFIDENCE = 0.6
CO_CHANGE_LIMIT = 10
SECRET_LIMIT = 25

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


@register_analyzer
class GitHistoryAnalyzer(BaseAnalyzer):
    """Git geçmişinden bulgular: geçmişte commit edilmiş sırlar, sıcak noktalar, birlikte değişen dosyalar.

    Hepsi salt-okunurdur ve zaman aşımlıdır; git yoksa ya da klasör depo değilse analizör bulgu üretmez.
    Sır bulgusu `security` kategorisinde puanlanır, diğerleri bilgi amaçlı `git` kategorisindedir.
    """

    def __init__(self, priority: int = 50):
        super().__init__(priority)

    @property
    def name(self) -> str:
        return "Git Geçmişi Analizörü"

    @property
    def category(self) -> str:
        return "git"

    def analyze(self, index: ProjectIndex) -> List[AnalysisResult]:
        tracked = index.git_tracked
        if tracked is None:
            return []
        results = self._secrets_in_history(index, tracked)
        commits = git_info.recent_commits(index.root, COMMIT_LIMIT)
        if commits and len(commits) >= MIN_COMMITS:
            focused = [c for c in commits if len(c.files) <= MAX_FILES_PER_COMMIT]
            by_rel = {f.rel: f for f in index.files if parse_file(index, f) is not None}
            results.extend(self._hotspots(index, focused, by_rel, len(commits)))
            results.extend(self._co_changes(index, focused, by_rel))
        return results

    # ---- geçmişteki sırlar ---------------------------------------------------------------------------

    def _secrets_in_history(self, index: ProjectIndex, tracked) -> List[AnalysisResult]:
        found = git_info.history_paths(index.root, SECRET_PATHSPECS)
        if not found:
            return []
        gone = sorted((rel for rel in found if secret_kind(rel) and rel not in tracked),
                      key=lambda rel: -found[rel].time)
        return [self._secret_result(index, rel, found[rel]) for rel in gone[:SECRET_LIMIT]]

    def _secret_result(self, index: ProjectIndex, rel: str, entry) -> AnalysisResult:
        kind = secret_kind(rel)
        when = time.strftime('%Y-%m-%d', time.gmtime(entry.time))
        in_tests = is_test_path(rel)
        result = self._create_result(
            title=f"Geçmişte Commit Edilmiş Sır Dosyası: {rel}",
            description=(f"'{rel}' ({kind}) {when} tarihli {entry.sha} commit'inde eklenmiş; artık izlenmiyor ama git geçmişinde "
                         "hâlâ okunabilir. Depoya erişen herkes içeriği geri alabilir."),
            severity=Severity.MEDIUM if in_tests else Severity.HIGH,
            file_path=index.root / rel,
            recommendation="İçindeki anahtar/parolaları geçersiz kılıp yenileyin (rotate). Geçmişten silmek gerekirse git filter-repo veya BFG kullanın.",
            rule='secret-in-history', kind=kind, commit=entry.sha, committed_at=when, in_tests=in_tests,
            approximate=rel.lower().endswith(_UNVERIFIED_EXTENSIONS), history_scanned=True)
        result.category = 'security'              # puanlanan kategori; analizörün kendi kategorisi (`git`) bilgi amaçlıdır
        return result

    # ---- sıcak noktalar -----------------------------------------------------------------------------

    def _hotspots(self, index: ProjectIndex, commits: Sequence[Commit], by_rel: Dict[str, FileEntry],
                  window: int) -> List[AnalysisResult]:
        changes = Counter(rel for c in commits for rel in c.files if rel in by_rel)
        ranked: List[Tuple[int, str, int, int]] = []
        for rel, count in changes.items():
            if count < MIN_HOTSPOT_CHANGES:
                continue
            complexity, worst = self._complexity(index, by_rel[rel])
            ranked.append((count * complexity, rel, count, worst))
        ranked.sort(key=lambda item: (-item[0], item[1]))
        return [self._hotspot_result(by_rel[rel], (score, count, worst, window))
                for score, rel, count, worst in ranked[:HOTSPOT_LIMIT] if score > 0]

    @staticmethod
    def _complexity(index: ProjectIndex, entry: FileEntry) -> Tuple[int, int]:
        """(işlev karmaşıklıkları toplamı, en karmaşık işlev); işlevsiz dosyada satır sayısı kaba ölçüdür."""
        metrics = parse_file(index, entry)
        if metrics is None:
            return 0, 0
        if not metrics.functions:
            return max(1, metrics.code_lines // 50), 0
        values = [f.complexity for f in metrics.functions]
        return sum(values), max(values)

    def _hotspot_result(self, entry: FileEntry, stats: Tuple[int, int, int, int]) -> AnalysisResult:
        score, count, worst, window = stats
        risky = count >= HOTSPOT_WARN_CHANGES and worst > self.thresholds.cyclomatic
        return self._create_result(
            title=f"Sık Değişen Karmaşık Dosya: {entry.rel}",
            description=(f"Son {window} commit'te {count} kez değişti; en karmaşık işlevinin siklomatik değeri {worst}. "
                         "Sık değişen ve karmaşık kod hata ve bakım maliyetinin yoğunlaştığı yerdir."),
            severity=Severity.LOW if risky else Severity.INFO, file_path=entry.path,
            recommendation="Önce bu dosyaya test yazın, sonra karmaşık işlevlerini küçültün." if risky else None,
            rule='hotspot', changes=count, max_complexity=worst, score=score, window=window, approximate=False)

    # ---- birlikte değişen dosyalar ------------------------------------------------------------------------

    def _co_changes(self, index: ProjectIndex, commits: Sequence[Commit],
                    by_rel: Dict[str, FileEntry]) -> List[AnalysisResult]:
        counts, pairs = self._count_pairs(commits, by_rel)
        ranked = []
        for (first, second), shared in pairs.items():
            if shared < MIN_SHARED_COMMITS or self._counterparts(first, second):
                continue
            confidence = shared / max(counts[first], counts[second])
            if confidence >= MIN_CONFIDENCE:
                ranked.append((shared, confidence, first, second))
        ranked.sort(key=lambda item: (-item[0], -item[1], item[2], item[3]))
        return [self._co_change_result(index, first, second, shared, confidence)
                for shared, confidence, first, second in ranked[:CO_CHANGE_LIMIT]]

    @staticmethod
    def _count_pairs(commits: Sequence[Commit], by_rel: Dict[str, FileEntry]) -> Tuple[Counter, Counter]:
        """(dosya başına commit sayısı, dosya çifti başına ortak commit sayısı); yalnızca kaynak dosyalar."""
        counts: Counter = Counter()
        pairs: Counter = Counter()
        for commit in commits:
            files = sorted({rel for rel in commit.files if rel in by_rel})
            counts.update(files)
            pairs.update(combinations(files, 2))
        return counts, pairs

    @staticmethod
    def _counterparts(first: str, second: str) -> bool:
        """Bir dosya ile kendi testi birlikte değişir; bu beklenen durumdur, bulgu değildir."""
        return module_key(first, is_test_path(first)) == module_key(second, is_test_path(second))

    def _co_change_result(self, index: ProjectIndex, first: str, second: str, shared: int,
                          confidence: float) -> AnalysisResult:
        return self._create_result(
            title=f"Birlikte Değişen Dosyalar: {first} ↔ {second}",
            description=(f"İki dosya {shared} ortak commit'te değişti (güven {confidence:.0%}: ikisinden birinin "
                         "değiştiği commit'lerin bu orandaki payı ikisini de içeriyor). Gizli bir bağımlılık olabilir."),
            severity=Severity.INFO, file_path=index.root / first,
            rule='co-change', files=[first, second], shared_commits=shared, confidence=round(confidence, 2),
            same_directory=posixpath.dirname(first) == posixpath.dirname(second), approximate=False)
