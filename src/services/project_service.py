from pathlib import Path
from typing import Dict, Optional
from src.doctors.project_doctor import ProjectDoctor
from src.services.archive_service import ArchiveService
from src.services.cleanup_service import CleanupService
from src.services.backup_service import BackupService
from src.utils.gitignore_parser import GitignoreParser

class ProjectService:
    def __init__(self):
        self.doctor = ProjectDoctor()
        self.archive_service = ArchiveService()
        self.cleanup_service = CleanupService()
        self.backup_service = BackupService()
        self._current_project: Optional[Path] = None
    
    def set_project(self, project_path: Path):
        self._current_project = Path(project_path)
        parser = GitignoreParser(str(self._current_project))
        self.archive_service.parser = parser
    
    def analyze_project(self) -> Dict:
        if not self._current_project:
            raise ValueError("Once bir proje secin!")
        return self.doctor.quick_scan(self._current_project)
    
    def create_archive(self, output_path: Path, archive_type: str = 'zip') -> Dict:
        if not self._current_project:
            raise ValueError("Once bir proje secin!")
        if archive_type == 'zip':
            return self.archive_service.create_zip(self._current_project, output_path)
        else:
            return self.archive_service.copy_project(self._current_project, output_path)
    
    def create_backup(self, backup_name: Optional[str] = None) -> Dict:
        if not self._current_project:
            raise ValueError("Once bir proje secin!")
        return self.backup_service.create_backup(self._current_project, backup_name)
