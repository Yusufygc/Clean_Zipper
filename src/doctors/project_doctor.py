from pathlib import Path
from typing import List, Dict
from datetime import datetime
from collections import defaultdict
from src.doctors.health_checker import HealthChecker
from src.doctors.recommendation_engine import RecommendationEngine
from src.models.analysis_models import ProjectAnalysis, AnalysisResult, Severity, FileInfo

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
        for analyzer in self._analyzers:
            try:
                results = analyzer.analyze(project_path)
                all_results.extend(results)
            except Exception as e:
                print(f"Analizor hatasi ({analyzer.name}): {e}")
        
        for result in all_results:
            if result.severity in [Severity.CRITICAL, Severity.HIGH]:
                analysis.issues.append(result)
            elif result.severity == Severity.MEDIUM:
                analysis.warnings.append(result)
            else:
                analysis.suggestions.append(result)
        
        self._collect_stats(project_path, analysis)
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