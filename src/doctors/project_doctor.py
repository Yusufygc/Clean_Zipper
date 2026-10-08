import logging
from collections import Counter
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple
from datetime import datetime
from src.core.interfaces import IAnalyzer
from src.core.project_index import ProjectIndex
from src.core.thresholds import QualityThresholds
from src.doctors.health_checker import HealthChecker
from src.doctors.recommendation_engine import RecommendationEngine
from src.models.analysis_models import ProjectAnalysis, AnalysisResult, Severity, FileInfo

logger = logging.getLogger(__name__)

# (yüzde 0-100, kullanıcıya gösterilecek metin)
ProgressCallback = Callable[[int, str], None]

INDEX_PROGRESS_SHARE = 10   # yüzdenin ilk %10'u dosya taramasına ayrılır
ANALYZER_PROGRESS_SHARE = 85


class ProjectDoctor:
    def __init__(self, analyzers: Optional[Iterable[IAnalyzer]] = None, respect_gitignore: bool = True,
                 thresholds: Optional[QualityThresholds] = None):
        self.respect_gitignore = respect_gitignore
        self.thresholds = thresholds
        self._analyzers: List[IAnalyzer] = []
        self._health_checker = HealthChecker()
        self._recommendation_engine = RecommendationEngine()
        for analyzer in analyzers or ():
            self.register_analyzer(analyzer)

    def register_analyzer(self, analyzer: IAnalyzer):
        if self.thresholds is not None and hasattr(analyzer, 'thresholds'):
            analyzer.thresholds = self.thresholds
        self._analyzers.append(analyzer)
        self._analyzers.sort(key=lambda a: a.get_priority())

    def get_registered_analyzers(self) -> List[str]:
        return [a.name for a in self._analyzers]

    def diagnose(self, project_path: Path, progress: Optional[ProgressCallback] = None) -> ProjectAnalysis:
        project_path = Path(project_path).resolve()
        analysis = ProjectAnalysis(project_path=project_path, analysis_time=datetime.now())
        report = progress or (lambda pct, text: None)

        report(0, "Dosyalar taranıyor…")
        index = ProjectIndex.build(
            project_path,
            progress=lambda n: report(INDEX_PROGRESS_SHARE // 2, f"Dosyalar taranıyor… ({n} dosya)"),
            respect_gitignore=self.respect_gitignore,
        )
        analysis.gitignore_applied = index.gitignore_applied
        analysis.ignored_by_gitignore = dict(index.gitignored)
        for path, error in index.errors:
            logger.warning("Okunamayan yol atlandı: %s (%s)", path, error)

        all_results, ran_categories = self._run_analyzers(index, analysis, report)
        self._collect_skipped(index, analysis)

        for result in all_results:
            if result.severity in [Severity.CRITICAL, Severity.HIGH]:
                analysis.issues.append(result)
            elif result.severity == Severity.MEDIUM:
                analysis.warnings.append(result)
            else:
                analysis.suggestions.append(result)

        report(INDEX_PROGRESS_SHARE + ANALYZER_PROGRESS_SHARE, "Skor hesaplanıyor…")
        self._collect_stats(index, analysis)
        self._populate_from_findings(analysis)
        analysis.category_scores = self._health_checker.calculate_category_scores(all_results, ran_categories)
        analysis.health_score = self._health_checker.calculate_score(analysis)
        analysis.health_status = self._health_checker.get_health_status(analysis.health_score)
        return analysis

    @staticmethod
    def _collect_skipped(index: ProjectIndex, analysis: ProjectAnalysis):
        """Analizörler çalıştıktan sonra: hangi dosya/klasörler neden dışarıda kaldı."""
        counts = Counter(index.skipped.values())
        if index.errors:
            counts['unreadable_dir'] = len(index.errors)
        analysis.skipped_files = dict(counts)
        if counts:
            logger.info("Analize girmeyen öğeler: %s", dict(counts))

    def _run_analyzers(self, index: ProjectIndex, analysis: ProjectAnalysis,
                       report: ProgressCallback) -> Tuple[List[AnalysisResult], Set[str]]:
        all_results: List[AnalysisResult] = []
        ran_categories: Set[str] = set()
        total = len(self._analyzers)
        for i, analyzer in enumerate(self._analyzers):
            report(INDEX_PROGRESS_SHARE + ANALYZER_PROGRESS_SHARE * i // max(total, 1),
                   f"{analyzer.name} çalışıyor…")
            try:
                if not analyzer.can_analyze(index):
                    continue
                all_results.extend(analyzer.analyze(index))
                ran_categories.add(analyzer.category)
            except Exception:
                logger.exception("Analizor hatasi (%s)", analyzer.name)
                analysis.failed_analyzers.append(analyzer.name)
        return all_results, ran_categories

    def quick_scan(self, project_path: Path, progress: Optional[ProgressCallback] = None) -> Dict:
        analysis = self.diagnose(project_path, progress)

        # Sadece gerçek kod kalitesi sorunları ve uyarıları sayılıyor (INFO düzeyindeki loglar hariç)
        actual_issues_count = len(analysis.issues) + len(analysis.warnings)

        return {
            'health_score': analysis.health_score,
            'health_status': analysis.health_status.value,
            'category_scores': analysis.category_scores,
            'failed_analyzers': analysis.failed_analyzers,
            'total_size_mb': analysis.total_size_mb,
            'total_files': analysis.total_files,
            'total_dirs': analysis.total_dirs,
            'issues_count': actual_issues_count, # Karttaki sayı artık listedeki eleman sayısıyla tam uyumlu
            'potential_savings_mb': analysis.potential_savings_mb,
            'file_type_distribution': analysis.file_type_distribution,
            'language_stats': analysis.language_stats,
            'skipped_files': analysis.skipped_files,
            'gitignore_applied': analysis.gitignore_applied,
            'ignored_by_gitignore': analysis.ignored_by_gitignore,
            'top_recommendations': self._recommendation_engine.get_top_recommendations(analysis),
            'project_path': str(project_path),
            'all_issues': analysis.issues + analysis.warnings # Sadece gerçek hatalar ve uyarılar listeleniyor
        }

    def _populate_from_findings(self, analysis: ProjectAnalysis):
        """Bulgu metadata'sındaki 'kind' alanından özet listeleri doldurur."""
        for finding in analysis.all_findings:
            kind = finding.metadata.get('kind')
            if kind == 'empty_dir' and finding.file_path:
                analysis.empty_dirs.append(finding.file_path)
            elif kind == 'duplicate_group':
                analysis.duplicate_files.append(list(finding.metadata.get('paths', [])))
            elif kind == 'language_stats':
                analysis.language_stats[finding.metadata['language']] = {
                    key: finding.metadata[key]
                    for key in ('files', 'total_lines', 'code_lines', 'comment_lines', 'blank_lines')}
            elif kind == 'large_file' and finding.file_path:
                try:
                    modified = datetime.fromtimestamp(finding.file_path.stat().st_mtime)
                except OSError:
                    modified = analysis.analysis_time
                analysis.largest_files.append(FileInfo(
                    path=finding.file_path, size_bytes=finding.size_impact or 0,
                    extension=finding.file_path.suffix.lower(), last_modified=modified
                ))
        analysis.largest_files.sort(key=lambda f: f.size_bytes, reverse=True)

    @staticmethod
    def _collect_stats(index: ProjectIndex, analysis: ProjectAnalysis):
        analysis.total_files = index.total_files
        analysis.total_dirs = index.total_dirs
        analysis.total_size = index.total_size
        analysis.file_type_distribution = dict(index.ext_counts)
        analysis.file_type_sizes = dict(index.ext_sizes)
