from pathlib import Path
from typing import List, Tuple
from src.core.base_analyzer import BaseAnalyzer
from src.core.project_index import ProjectIndex
from src.core.registry import register_analyzer
from src.languages import parse_file
from src.languages.base import ClassInfo, FunctionInfo, SourceMetrics
from src.models.analysis_models import AnalysisResult, Severity

# Tek fonksiyon bulgusu için metrik tanımları: (anahtar, etiket, taban öncelik, öneri)
SEVERITY_ORDER = [Severity.INFO, Severity.LOW, Severity.MEDIUM, Severity.HIGH, Severity.CRITICAL]

ADVICE = {
    'cyclomatic': "Metodu alt metotlara bölün (Extract Method); çok dallı koşulları sadeleştirin.",
    'cognitive': "İç içe if/döngü zincirlerini 'Guard Clause' ve erken dönüşle düzleştirin; karar mantığını ayrı fonksiyonlara taşıyın.",
    'nesting': "İç içe blokları erken dönüş / 'continue' ile düzleştirin veya iç bloğu ayrı bir fonksiyona çıkarın.",
    'length': "Fonksiyonu tek sorumluluğa sahip daha küçük fonksiyonlara bölün.",
    'params': "İlgili parametreleri bir nesnede toplayın (Introduce Parameter Object).",
}


def _escalate(severity: Severity) -> Severity:
    return SEVERITY_ORDER[min(SEVERITY_ORDER.index(severity) + 1, SEVERITY_ORDER.index(Severity.HIGH))]


@register_analyzer
class CodeComplexityAnalyzer(BaseAnalyzer):
    """V2 ölçüm eşiklerine göre karmaşıklık / boyut analizi (tüm diller).

    Fonksiyon başına tek bulgu: aşılan bütün metrikler birlikte listelenir. Eşiklerin `severe_factor` katı
    ve üstü bir seviye yukarı raporlanır. Eşikler `self.thresholds` (varsayılan V2 tablosu) ile ayarlanır.
    """

    def __init__(self, priority: int = 12):
        super().__init__(priority)

    @property
    def name(self) -> str:
        return "Kod Karmaşıklığı ve Tasarım Analizörü"

    @property
    def category(self) -> str:
        return "complexity"

    def analyze(self, index: ProjectIndex) -> List[AnalysisResult]:
        results = []
        for entry in index.files:
            metrics = parse_file(index, entry)
            if metrics is not None:
                results.extend(self._analyze_metrics(entry.path, metrics))
        return results

    def _analyze_metrics(self, file_path: Path, metrics: SourceMetrics) -> List[AnalysisResult]:
        extra = {'language': metrics.language, 'approximate': metrics.approximate}
        results = []
        results.extend(self._check_file(file_path, metrics, extra))
        for cls in metrics.classes:
            results.extend(self._check_class(file_path, cls, extra))
        for func in metrics.functions:
            results.extend(self._check_function(file_path, func, extra))
        return results

    # ---- dosya ----------------------------------------------------------------------

    def _check_file(self, file_path: Path, metrics: SourceMetrics, extra: dict) -> List[AnalysisResult]:
        t = self.thresholds
        results = []
        if metrics.total_lines > t.file_lines:
            severity = Severity.HIGH if t.is_severe(metrics.total_lines, t.file_lines) else Severity.MEDIUM
            results.append(self._create_result(
                title=f"Aşırı Şişmiş Dosya: {file_path.name}",
                description=f"Dosya toplam {metrics.total_lines} satır (boş ve yorum satırları dahil; {metrics.code_lines} kod satırı). Eşik: {t.file_lines} toplam satır.",
                severity=severity, file_path=file_path,
                recommendation="Bu dosyayı mantıksal olarak daha küçük, tek sorumluluğa (SRP) sahip modüllere veya alt sınıflara parçalayın.",
                rule='file-length', **extra))
        imports = len(set(metrics.imports))
        if imports > t.module_imports:
            severity = Severity.MEDIUM if t.is_severe(imports, t.module_imports) else Severity.LOW
            results.append(self._create_result(
                title=f"Çok Fazla Import: {file_path.name}",
                description=f"Dosya {imports} farklı modül içe aktarıyor (Eşik: {t.module_imports}); yüksek bağımlılık (fan-out).",
                severity=severity, file_path=file_path,
                recommendation="Sorumlulukları ayırın; bağımlılıkları bir cephe (facade) arkasında toplayın.",
                rule='module-imports', imports=imports, **extra))
        return results

    # ---- sınıf ----------------------------------------------------------------------

    def _check_class(self, file_path: Path, cls: ClassInfo, extra: dict) -> List[AnalysisResult]:
        """Sınıf Bazlı Analiz (God Class / God Object)."""
        t = self.thresholds
        # Ölçülerden biri eşiği aşması yeter (ikisi de eşik içindeyse bulgu yok).
        exceeded = [label for label, value, limit in (
            (f"{cls.method_count} metot (eşik {t.class_methods})", cls.method_count, t.class_methods),
            (f"yaklaşık {cls.lines} satır (eşik {t.class_lines})", cls.lines, t.class_lines)) if value > limit]
        if not exceeded:
            return []
        return [self._create_result(
            title=f"Tanrı Sınıf (God Object) Riski: {cls.name}",
            description=(f"'{cls.name}' sınıfı eşiği aşıyor: {' ve '.join(exceeded)}; {cls.method_count} metot, "
                         f"{cls.lines} satır. Bu sınıf sistemde çok fazla sorumluluk üstleniyor."),
            severity=Severity.HIGH, file_path=file_path,
            recommendation="Sınıfı SOLID prensiplerine uygun olarak parçalayın. Sınıfın sadece tek bir aktöre veya amaca hizmet etmesini sağlayın.",
            rule='class-size', class_name=cls.name, start_line=cls.start_line, **extra)]

    # ---- fonksiyon ------------------------------------------------------------------

    def _violations(self, func: FunctionInfo) -> List[Tuple[str, str, int, int, Severity]]:
        """(anahtar, etiket, değer, eşik, öncelik) listesi; yalnızca eşiği aşanlar."""
        t = self.thresholds
        checks = [
            ('cyclomatic', 'siklomatik karmaşıklık', func.complexity, t.cyclomatic, Severity.MEDIUM),
            ('cognitive', 'bilişsel karmaşıklık', func.cognitive, t.cognitive, Severity.MEDIUM),
            ('nesting', 'iç içe blok derinliği', func.max_nesting, t.nesting, Severity.MEDIUM),
            ('length', 'satır sayısı', func.lines, t.function_lines, Severity.LOW),
            ('params', 'parametre sayısı', func.params, t.parameters, Severity.LOW),
        ]
        found = []
        for key, label, value, threshold, base in checks:
            if value > threshold:
                severity = _escalate(base) if t.is_severe(value, threshold) else base
                found.append((key, label, value, threshold, severity))
        return found

    def _check_function(self, file_path: Path, func: FunctionInfo, extra: dict) -> List[AnalysisResult]:
        """Metot/Fonksiyon Bazlı Analiz: tek bulguda aşılan tüm eşikler."""
        violations = self._violations(func)
        if not violations:
            return []
        severity = max((v[4] for v in violations), key=SEVERITY_ORDER.index)
        details = "; ".join(f"{label} {value} (Eşik: {threshold})" for _, label, value, threshold, _ in violations)
        advice = " ".join(dict.fromkeys(ADVICE[key] for key, *_ in violations))
        return [self._create_result(
            title=f"Karmaşık Fonksiyon: {func.name}()",
            description=f"{func.name}() eşikleri aşıyor: {details}.",
            severity=severity, file_path=file_path, recommendation=advice,
            rule='function-metrics', function=func.name, start_line=func.start_line,
            violations={key: value for key, _, value, _, _ in violations}, **extra)]
