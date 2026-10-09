from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from src.core.base_analyzer import BaseAnalyzer
from src.core.path_rules import is_neutral_module, is_test_path, module_keys
from src.core.project_index import FileEntry, ProjectIndex
from src.core.registry import register_analyzer
from src.languages import parse_file, testing_patterns
from src.languages.base import SourceMetrics
from src.languages.registry import get_stripped
from src.models.analysis_models import AnalysisResult, Severity

MIN_UNTESTED_LINES = 30           # bundan küçük modüllerin ayrı testi beklenmez
MAX_LISTED = 10
NO_TESTS_HIGH_LINES = 500         # bu kadar kaynak satırı olup hiç testi olmayan proje YÜKSEK


@dataclass
class _Scan:
    source_lines: int = 0
    test_lines: int = 0
    test_files: int = 0
    test_functions: int = 0
    skipped: int = 0
    sources: Dict[str, int] = field(default_factory=dict)         # rel -> kod satırı (test olmayanlar)
    test_keys: Set[str] = field(default_factory=set)
    sleeps: Dict[str, Tuple[str, List[int]]] = field(default_factory=dict)
    networks: Dict[str, Tuple[str, List[int]]] = field(default_factory=dict)


@register_analyzer
class TestingAnalyzer(BaseAnalyzer):
    """Test sağlığı: test yok, düşük test/kaynak satır oranı, testi olmayan modüller, kararsız (flaky) test işaretleri.

    Test dosyası: test klasörü veya adlandırma kuralı (`path_rules.is_test_path`). Rust'ta birim testler kaynak dosyasının
    içinde olduğundan `#[test]` her dosyada sayılır. Test işlevi sayısı ve oran bilgi amaçlıdır; sonuçlar sözcük tabanlıdır.
    """
    __test__ = False                  # pytest bu sınıfı test sınıfı sanıp toplamasın

    def __init__(self, priority: int = 40):
        super().__init__(priority)

    @property
    def name(self) -> str:
        return "Test Sağlığı Analizörü"

    @property
    def category(self) -> str:
        return "testing"

    def analyze(self, index: ProjectIndex) -> List[AnalysisResult]:
        scan = self._scan(index)
        if not scan.sources and not scan.test_files and not scan.test_functions:
            return []
        results = self._coverage_findings(index, scan)
        results.extend(self._flaky_findings(index, scan))
        if scan.test_files or scan.test_functions:
            results.append(self._summary(scan))
        return results

    # ---- tarama ------------------------------------------------------------------------------------

    def _scan(self, index: ProjectIndex) -> _Scan:
        scan = _Scan()
        for entry in index.files:
            metrics = parse_file(index, entry)
            if metrics is None:
                continue
            stripped = get_stripped(index, entry)
            if stripped is None:
                continue
            is_test = is_test_path(entry.rel)
            python_tests = sum(1 for f in metrics.functions if f.name.startswith('test')) \
                if metrics.language == 'python' and is_test else 0
            count = testing_patterns.count_tests(
                metrics.language, stripped.clean, stripped.no_comments, python_tests)
            if is_test:
                self._add_test_file(scan, entry, metrics, stripped, count)
            else:
                scan.sources[entry.rel] = metrics.code_lines
                scan.source_lines += metrics.code_lines
                if metrics.language == 'rust':
                    scan.test_functions += count                  # birim testler kaynak dosyasında
                    scan.skipped += testing_patterns.find_skipped('rust', stripped.clean)
        return scan

    @staticmethod
    def _add_test_file(scan: _Scan, entry: FileEntry, metrics: SourceMetrics, stripped, count: int):
        scan.test_lines += metrics.code_lines
        scan.test_functions += count
        if is_neutral_module(entry.rel):
            return                                          # __init__.py / conftest.py test dosyası sayılmaz
        scan.test_files += 1
        scan.test_keys.update(module_keys(entry.rel, True))
        scan.skipped += testing_patterns.find_skipped(metrics.language, stripped.clean)
        sleeps = testing_patterns.find_sleeps(metrics.language, stripped.clean)
        if sleeps:
            scan.sleeps[entry.rel] = (metrics.language, sleeps)
        networks = testing_patterns.find_network_calls(metrics.language, stripped.no_comments, stripped.clean)
        if networks:
            scan.networks[entry.rel] = (metrics.language, networks)

    # ---- bulgular ------------------------------------------------------------------------------------

    def _coverage_findings(self, index: ProjectIndex, scan: _Scan) -> List[AnalysisResult]:
        t = self.thresholds
        has_tests = scan.test_files > 0 or scan.test_functions > 0
        if not has_tests:
            if scan.source_lines < t.test_min_source_lines:
                return []
            severity = Severity.HIGH if scan.source_lines > NO_TESTS_HIGH_LINES else Severity.MEDIUM
            return [self._create_result(
                title="Projede Test Yok",
                description=f"{scan.source_lines} satır kaynak kod var, hiç test dosyası veya test işlevi bulunamadı.",
                severity=severity, file_path=index.root,
                recommendation="Kritik iş mantığı için birim testleri ekleyin (Python: pytest, JS/TS: vitest/jest, Java: JUnit ...).",
                rule='no-tests', source_lines=scan.source_lines, approximate=True)]
        results = []
        if scan.test_files and scan.source_lines >= t.test_min_source_lines:
            ratio = scan.test_lines / scan.source_lines
            if ratio < t.test_ratio_low:
                severity = Severity.MEDIUM if ratio < t.test_ratio_severe else Severity.LOW
                results.append(self._create_result(
                    title=f"Düşük Test Oranı: %{ratio * 100:.0f}",
                    description=(f"Test kodu / kaynak kod satır oranı {ratio:.2f} ({scan.test_lines} / {scan.source_lines}); "
                                 f"hedef en az {t.test_ratio_low:.1f}."),
                    severity=severity, file_path=index.root,
                    recommendation="Testsiz kalan modüllere öncelikle karmaşık ve sık değişen kodlardan başlayarak test ekleyin.",
                    rule='low-test-ratio', ratio=ratio, test_lines=scan.test_lines,
                    source_lines=scan.source_lines, approximate=True))
        results.extend(self._untested(index, scan))
        return results

    def _untested(self, index: ProjectIndex, scan: _Scan) -> List[AnalysisResult]:
        if not scan.test_files:
            return []
        untested = sorted(
            ((rel, lines) for rel, lines in scan.sources.items()
             if lines >= MIN_UNTESTED_LINES and not is_neutral_module(rel)
             and not module_keys(rel, False) & scan.test_keys),
            key=lambda item: (-item[1], item[0]))
        if not untested:
            return []
        shown = ", ".join(f"{rel} ({lines})" for rel, lines in untested[:MAX_LISTED])
        more = f" ... (+{len(untested) - MAX_LISTED})" if len(untested) > MAX_LISTED else ""
        return [self._create_result(
            title=f"Eşleşen Testi Olmayan Modüller: {len(untested)}",
            description=f"Adına karşılık gelen test dosyası bulunamayan, en az {MIN_UNTESTED_LINES} satırlık modüller (kod satırı): {shown}{more}.",
            severity=Severity.INFO, file_path=index.root,
            recommendation="Adlandırma kuralıyla (test_<modül>.py, <modül>.test.ts ...) eşleşen test dosyaları ekleyin; farklı adla test varsa bu yalnızca ipucudur.",
            rule='untested-modules', count=len(untested),
            modules=[{'path': rel, 'code_lines': lines} for rel, lines in untested[:50]], approximate=True)]

    def _flaky_findings(self, index: ProjectIndex, scan: _Scan) -> List[AnalysisResult]:
        results = []
        for rule, title, found, advice in (
                ('test-sleep', "Testte Gerçek Bekleme (sleep)", scan.sleeps,
                 "Zamanı sahtelemek (fake timers / freezegun) veya olay beklemek için yoklama (polling) kullanın."),
                ('test-real-network', "Testte Gerçek Ağ Çağrısı", scan.networks,
                 "Dış servisleri sahteleyin (mock / yerel sahte sunucu); testler ağdan bağımsız olmalı.")):
            for rel, (language, lines) in sorted(found.items()):
                shown = ", ".join(str(n) for n in lines[:MAX_LISTED])
                results.append(self._create_result(
                    title=f"{title}: {rel.rsplit('/', 1)[-1]}",
                    description=f"{title}, kararsız (flaky) test göstergesi. Satır: {shown}.",
                    severity=Severity.LOW, file_path=index.root / rel, recommendation=advice,
                    rule=rule, lines=lines, count=len(lines), language=language, approximate=True))
        return results

    def _summary(self, scan: _Scan) -> AnalysisResult:
        ratio = scan.test_lines / scan.source_lines if scan.source_lines else 0.0
        return self._create_result(
            title=f"Test Özeti: {scan.test_functions} test işlevi, {scan.test_files} test dosyası",
            description=(f"{scan.test_files} test dosyası, {scan.test_functions} test işlevi, "
                         f"{scan.skipped} atlanmış / koşullu atlanan test işareti; test/kaynak satır oranı {ratio:.2f}."),
            severity=Severity.INFO,
            rule='test-summary', test_files=scan.test_files, test_functions=scan.test_functions,
            skipped=scan.skipped, test_lines=scan.test_lines, source_lines=scan.source_lines, ratio=ratio,
            approximate=True)
