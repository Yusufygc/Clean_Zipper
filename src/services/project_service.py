import itertools
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Dict, Iterable, Iterator, List, Optional
from src.core.errors import OperationBusyError, ProjectNotSelectedError
from src.core.registry import default_registry, load_builtin_analyzers
from src.core.thresholds import QualityThresholds
from src.doctors.project_doctor import ProjectDoctor
from src.models.analysis_models import ProjectAnalysis
from src.services.archive_service import ArchiveService
from src.services.cleanup_service import CleanupService
from src.services.recommendation_engine import RecommendationEngine
from src.services.backup_service import BackupService
from src.utils.gitignore_parser import GitignoreParser

ProgressCallback = Callable[[int, str], None]
FileProgressCallback = Callable[[int, int], None]
DEFAULT_PROFILE = "Geliştirici (Standart)"


class _CachedAnalysis:
    def __init__(self, doctor: ProjectDoctor, project: Path, started: int, analysis: ProjectAnalysis):
        self.doctor = doctor
        self.project = project
        self.started = started
        self.analysis = analysis


class ProjectService:
    """Arayüzün tek giriş noktası.

    Teşhis: aynı anda tek teşhis çalışır (analizör örnekleri paylaşılır, eşzamanlı çalışmaları güvenli değildir) ve sonuç
    önbelleğe alınır. Dashboard ile Sorunlar sayfası aynı teşhisi paylaşır. Önbellek proje, ayar (`doctor` değişince) ya
    da projeyi değiştiren bir işlem (temizlik, arşiv, kopya) sonrasında geçersizleşir.
    Projeyi değiştiren işlemler: aynı anda yalnızca biri; ikincisi beklemez, `OperationBusyError` alır.
    """

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
        self._diagnose_lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._running_write = ""
        self._cache: Optional[_CachedAnalysis] = None
        self._generation = 0                 # projeyi değiştiren her işlemde artar; eski teşhis önbelleğe yazılmaz
        # İstek ve teşhis başlangıçlarının sırası (saat değil: Windows'ta `monotonic` ~16 ms adımlıdır).
        self._sequence = itertools.count()

    @property
    def current_project(self) -> Optional[Path]:
        return self._current_project

    @property
    def busy_operation(self) -> str:
        """Süren yazma işleminin adı; yoksa boş."""
        return self._running_write

    def set_project(self, project_path: Path):
        self._current_project = Path(project_path).resolve()
        parser = GitignoreParser(str(self._current_project))
        self.archive_service.parser = parser
        self.invalidate()

    def invalidate(self):
        """Önbellekteki teşhisi geçersiz kılar (dışarıdan bilinen bir değişiklikten sonra)."""
        self._generation += 1
        self._cache = None

    def _require_project(self) -> Path:
        if not self._current_project:
            raise ProjectNotSelectedError()
        return self._current_project

    # ── Teşhis ─────────────────────────────────────────────────────────────

    def diagnose(self, progress: Optional[ProgressCallback] = None, refresh: bool = False) -> ProjectAnalysis:
        """Tam teşhis. `refresh=False`: geçerli önbellek varsa onu döner. `refresh=True`: bu çağrıdan sonra başlamış
        bir teşhis ister; aynı anda gelen yenileme istekleri (ör. proje açılınca Dashboard ve Sorunlar) tek teşhiste
        birleşir: sonra gelen, ilkinin bitmesini bekler ve onun sonucunu alır."""
        project = self._require_project()
        requested = next(self._sequence)
        with self._diagnose_lock:
            cached = self._valid_cache(project, None if not refresh else requested)
            if cached is not None:
                return cached
            doctor, generation, started = self.doctor, self._generation, next(self._sequence)
            analysis = doctor.diagnose(project, progress)
            if generation == self._generation and doctor is self.doctor and project == self._current_project:
                self._cache = _CachedAnalysis(doctor, project, started, analysis)
            return analysis

    def _valid_cache(self, project: Path, not_before: Optional[int]) -> Optional[ProjectAnalysis]:
        cache = self._cache
        if cache is None or cache.project != project or cache.doctor is not self.doctor:
            return None
        if not_before is not None and cache.started < not_before:
            return None
        return cache.analysis

    def analyze_project(self, progress: Optional[ProgressCallback] = None, refresh: bool = True) -> Dict:
        """Dashboard özeti ve öneriler; yeniden tarar (kullanıcı "Tara" dedi), eşzamanlı istekle birleşir."""
        analysis = self.diagnose(progress, refresh=refresh)
        summary = self.doctor.summarize(analysis)
        summary['top_recommendations'] = RecommendationEngine().get_top_recommendations(analysis)
        return summary

    # ── Projeyi değiştiren işlemler ───────────────────────────────────────

    @contextmanager
    def _exclusive(self, name: str, modifies_project: bool) -> Iterator[Path]:
        project = self._require_project()
        if not self._write_lock.acquire(blocking=False):
            raise OperationBusyError(self._running_write or name)
        self._running_write = name
        try:
            yield project
        finally:
            if modifies_project:
                self.invalidate()
            self._running_write = ""
            self._write_lock.release()

    def preview_cleanup(self, categories: Optional[List[str]] = None) -> Dict:
        """Salt okunur; kilit gerekmez."""
        return self.cleanup_service.preview_cleanup(self._require_project(), categories=categories)

    def cleanup(self, categories: Optional[List[str]] = None, dry_run: bool = True) -> Dict:
        with self._exclusive("temizlik", modifies_project=not dry_run) as project:
            return self.cleanup_service.cleanup(project, categories=categories, dry_run=dry_run)

    def create_zip(self, output_path: Path, profile_name: str = DEFAULT_PROFILE,
                   progress: Optional[FileProgressCallback] = None) -> Dict:
        # Çıktı proje içinde olabilir: sonraki teşhis yeni arşivi görmeli.
        with self._exclusive("arşiv", modifies_project=True) as project:
            return self.archive_service.create_zip(project, output_path, profile_name=profile_name,
                                                   progress_callback=progress)

    def copy_project(self, target_dir: Path, profile_name: str = DEFAULT_PROFILE,
                     progress: Optional[FileProgressCallback] = None) -> Dict:
        with self._exclusive("kopya", modifies_project=True) as project:
            return self.archive_service.copy_project(project, target_dir, profile_name=profile_name,
                                                     progress_callback=progress)

    def create_archive(self, output_path: Path, archive_type: str = 'zip') -> Dict:
        if archive_type == 'zip':
            return self.create_zip(output_path)
        return self.copy_project(output_path)

    def create_backup(self, backup_name: Optional[str] = None) -> Dict:
        # Yedek proje dışına (`~/.gitclean_backups`) yazılır; teşhis geçerli kalır.
        with self._exclusive("yedek", modifies_project=False) as project:
            return self.backup_service.create_backup(project, backup_name)

    # ── Dışa aktarma (son teşhisi kullanır) ───────────────────────────────

    def export_project_report(self, output_path: Path) -> bool:
        """Sağlık raporunu HTML olarak yazar."""
        from src.services.report_service import ReportService
        return ReportService().export_report(self.diagnose(), output_path)

    def export_agent_tasks(self, output_dir: Path, batch_size: int = 15) -> Dict:
        """Bulguları yapay zeka ajanının çalışabileceği görev dosyalarına yazar (`tasks.json`, `tasks/*.md`, `README.md`,
        `verify.py`); dalga sırası: sırlar (insan) -> güvenlik -> güvenilirlik -> temizlik -> hijyen -> test -> refactor."""
        from src.services.agent_task_export import write_agent_tasks
        return write_agent_tasks(self.diagnose(), Path(output_dir), batch_size)

    def verify_agent_tasks(self, tasks_dir: Path, only: Optional[Iterable[str]] = None) -> Dict:
        """Projeyi yeniden tarar (ajan dosyaları değiştirdi); `tasks.json` içindeki her görevin öğelerinin kapanıp
        kapanmadığını ve yeni çıkan bulguları döner."""
        project = self._require_project()
        import json
        from src.core.errors import GitCleanError
        from src.services.agent_tasks import SCHEMA_VERSION, verify
        path = Path(tasks_dir) / 'tasks.json'
        try:
            recorded = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as e:
            raise GitCleanError(f"Görev dosyası okunamadı: {path} ({e})") from e
        if recorded.get('version') != SCHEMA_VERSION:
            raise GitCleanError(f"Desteklenmeyen görev dosyası sürümü: {recorded.get('version')}")
        result = verify(self.diagnose(refresh=True), recorded, only)
        if Path(recorded.get('project', '')).resolve() != project:
            result['warning'] = f"Görevler başka bir proje için üretilmiş: {recorded.get('project')}"
        return result

    def export_audit_report(self, output_path: Path) -> bool:
        """V2 denetim şablonunda (A-F bölümleri) Markdown raporu yazar."""
        from src.services.audit_report_service import AuditReportService
        return AuditReportService().export_report(self.diagnose(), output_path)
