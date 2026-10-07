import logging
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from collections import defaultdict
from src.doctors.health_checker import HealthChecker
from src.doctors.recommendation_engine import RecommendationEngine
from src.models.analysis_models import ProjectAnalysis, AnalysisResult, Severity, FileInfo

logger = logging.getLogger(__name__)

class ProjectDoctor:
    def __init__(self):
        self._analyzers = []
        self._health_checker = HealthChecker()
        self._recommendation_engine = RecommendationEngine()
    
    def register_analyzer(self, analyzer):
        self._analyzers.append(analyzer)
        self._analyzers.sort(key=lambda a: a.get_priority())
    
    def get_registered_analyzers(self) -> List[str]:
        return [a.name for a in self._analyzers]
    
    def diagnose(self, project_path: Path) -> ProjectAnalysis:
        project_path = Path(project_path).resolve()
        analysis = ProjectAnalysis(project_path=project_path, analysis_time=datetime.now())
        all_results = []
        ran_categories = set()
        for analyzer in self._analyzers:
            try:
                results = analyzer.analyze(project_path)
                all_results.extend(results)
                ran_categories.add(analyzer.category)
            except Exception:
                logger.exception("Analizor hatasi (%s)", analyzer.name)
                analysis.failed_analyzers.append(analyzer.name)
        
        for result in all_results:
            if result.severity in [Severity.CRITICAL, Severity.HIGH]:
                analysis.issues.append(result)
            elif result.severity == Severity.MEDIUM:
                analysis.warnings.append(result)
            else:
                analysis.suggestions.append(result)
        
        self._collect_stats(project_path, analysis)
        self._populate_from_findings(analysis)
        analysis.category_scores = self._health_checker.calculate_category_scores(all_results, ran_categories)
        analysis.health_score = self._health_checker.calculate_score(analysis)
        analysis.health_status = self._health_checker.get_health_status(analysis.health_score)
        return analysis
    
    def quick_scan(self, project_path: Path) -> Dict:
        analysis = self.diagnose(project_path)
        
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

    def _collect_stats(self, project_path: Path, analysis: ProjectAnalysis):
        total_files, total_dirs, total_size = 0, 0, 0
        ext_dist = defaultdict(int)
        try:
            for item in project_path.rglob('*'):
                if item.is_file():
                    try:
                        total_size += item.stat().st_size
                        ext_dist[item.suffix.lower()] += 1
                        total_files += 1
                    except (OSError, PermissionError):
                        pass
                elif item.is_dir():
                    total_dirs += 1
        except:
            pass
        analysis.total_files = total_files
        analysis.total_dirs = total_dirs
        analysis.total_size = total_size
        analysis.file_type_distribution = dict(ext_dist)