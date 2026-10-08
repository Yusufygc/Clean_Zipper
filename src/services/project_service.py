from pathlib import Path
from typing import Callable, Dict, Iterable, Optional
from src.core.errors import ProjectNotSelectedError
from src.core.registry import default_registry, load_builtin_analyzers
from src.core.thresholds import QualityThresholds
from src.doctors.project_doctor import ProjectDoctor
from src.services.archive_service import ArchiveService
from src.services.cleanup_service import CleanupService
from src.services.backup_service import BackupService
from src.utils.gitignore_parser import GitignoreParser

class ProjectService:
    def __init__(self, disabled_analyzers=(), respect_gitignore: bool = True,
                 thresholds: Optional[QualityThresholds] = None, disabled_rules: Iterable[str] = ()):
        load_builtin_analyzers()
        self.doctor = ProjectDoctor(default_registry.create_all(disabled=disabled_analyzers),
                                    respect_gitignore=respect_gitignore, thresholds=thresholds,
                                    disabled_rules=disabled_rules)
        self.archive_service = ArchiveService()
        self.cleanup_service = CleanupService()
        self.backup_service = BackupService()
        self._current_project: Optional[Path] = None
    
    def set_project(self, project_path: Path):
        self._current_project = Path(project_path).resolve()
        parser = GitignoreParser(str(self._current_project))
        self.archive_service.parser = parser
    
    def analyze_project(self, progress: Optional[Callable[[int, str], None]] = None) -> Dict:
        if not self._current_project:
            raise ProjectNotSelectedError()
        return self.doctor.quick_scan(self._current_project, progress)
    
    def create_archive(self, output_path: Path, archive_type: str = 'zip') -> Dict:
        if not self._current_project:
            raise ProjectNotSelectedError()
        if archive_type == 'zip':
            return self.archive_service.create_zip(self._current_project, output_path)
        else:
            return self.archive_service.copy_project(self._current_project, output_path)
    
    def create_backup(self, backup_name: Optional[str] = None) -> Dict:
        if not self._current_project:
            raise ProjectNotSelectedError()
        return self.backup_service.create_backup(self._current_project, backup_name)

    # ── YENİ: Kritik Sorunları ve Sağlık Analizini HTML Olarak Dışa Aktarma ──
    def export_project_report(self, output_path: Path) -> bool:
        if not self._current_project:
            raise ProjectNotSelectedError()
        
        # Tam teşekküllü teşhis analizi çalıştırılıyor
        analysis = self.doctor.diagnose(self._current_project)
        
        # Raporlama servisi çağrılarak HTML raporu diske yazılıyor
        from src.services.report_service import ReportService
        reporter = ReportService()
        return reporter.export_report(analysis, output_path)

    def export_audit_report(self, output_path: Path) -> bool:
        """V2 denetim şablonunda (A-F bölümleri) Markdown raporu yazar."""
        if not self._current_project:
            raise ProjectNotSelectedError()
        from src.services.audit_report_service import AuditReportService
        analysis = self.doctor.diagnose(self._current_project)
        return AuditReportService().export_report(analysis, output_path)