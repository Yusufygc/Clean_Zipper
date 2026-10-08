from pathlib import Path
from typing import List
from src.core.base_analyzer import BaseAnalyzer
from src.core.project_index import ProjectIndex
from src.core.registry import register_analyzer
from src.languages import parse_file
from src.languages.base import ClassInfo, FunctionInfo, SourceMetrics
from src.models.analysis_models import AnalysisResult, Severity


@register_analyzer
class CodeComplexityAnalyzer(BaseAnalyzer):
    """God Object, Bloated File ve Siklomatik Karmaşıklık analizlerini yapan dil bağımsız motor."""

    def __init__(self, priority: int = 12):
        super().__init__(priority)
        # Kurumsal temiz kod limitleri (Clean Code Guidelines)
        self.bloated_file_threshold = 400       # Dosya satır limiti (LOC)
        self.god_class_method_limit = 12        # Sınıf içi metot limiti
        self.god_class_loc_limit = 250          # Sınıf satır limiti
        self.complexity_limit = 10              # Metot karmaşıklık limiti

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

        # 1. Aşırı Şişmiş Dosya (Bloated File) Kontrolü
        if metrics.total_lines > self.bloated_file_threshold:
            results.append(self._create_result(
                title=f"Aşırı Şişmiş Dosya: {file_path.name}",
                description=f"Dosya toplamda {metrics.total_lines} satır kod içeriyor (Limit: {self.bloated_file_threshold}).",
                severity=Severity.HIGH,
                file_path=file_path,
                recommendation="Bu dosyayı mantıksal olarak daha küçük, tek sorumluluğa (SRP) sahip modüllere veya alt sınıflara parçalayın.",
                **extra
            ))

        for cls in metrics.classes:
            results.extend(self._check_class(file_path, cls, extra))
        for func in metrics.functions:
            results.extend(self._check_function(file_path, func, extra))
        return results

    def _check_class(self, file_path: Path, cls: ClassInfo, extra: dict) -> List[AnalysisResult]:
        """Sınıf Bazlı Analiz (God Class / God Object)."""
        if cls.method_count <= self.god_class_method_limit and cls.lines <= self.god_class_loc_limit:
            return []
        return [self._create_result(
            title=f"Tanrı Sınıf (God Object) Riski: {cls.name}",
            description=f"'{cls.name}' sınıfı {cls.method_count} metoda ve yaklaşık {cls.lines} satır koda sahip. Bu sınıf sistemde çok fazla sorumluluk üstleniyor.",
            severity=Severity.HIGH,
            file_path=file_path,
            recommendation="Sınıfı SOLID prensiplerine uygun olarak parçalayın. Sınıfın sadece tek bir aktöre veya amaca hizmet etmesini sağlayın.",
            **extra
        )]

    def _check_function(self, file_path: Path, func: FunctionInfo, extra: dict) -> List[AnalysisResult]:
        """Metot/Fonksiyon Bazlı Karmaşıklık Analizi (McCabe)."""
        if func.complexity <= self.complexity_limit:
            return []
        return [self._create_result(
            title=f"Yüksek Karmaşıklık Saptandı: {func.name}()",
            description=f"Metodun siklomatik karmaşıklık skoru {func.complexity} olarak hesaplandı (Önerilen Sınır: {self.complexity_limit}). Çok fazla dallanma (if, loop) var.",
            severity=Severity.MEDIUM,
            file_path=file_path,
            recommendation="Metodu alt metotlara bölün (Extract Method). İç içe if-else bloklarını 'Guard Clauses' yöntemiyle düzleştirin.",
            **extra
        )]
