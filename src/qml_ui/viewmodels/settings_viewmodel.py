import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from PySide6.QtCore import QObject, Signal, Slot, Property
from src.core.registry import default_registry, load_builtin_analyzers
from src.core.thresholds import QualityThresholds
from src.doctors.project_doctor import ProjectDoctor
from src.services.project_service import ProjectService

logger = logging.getLogger(__name__)

ANALYZER_METADATA: Dict[str, tuple[str, str]] = {
    "ArchitectureAnalyzer": ("Mimari ve Katman Analizi", "Ters bağımlılıkları ve katman ihlallerini denetler."),
    "CloneAnalyzer": ("Kod Klonu ve Tekrar Analizi", "Tekrarlanan kod bloklarını tespit eder."),
    "CodeComplexityAnalyzer": ("Karmaşıklık Analizi", "Döngüsel ve bilişsel karmaşıklık sınırlarını ölçer."),
    "CodeSecurityAnalyzer": ("Kod Güvenlik Taraması", "Güvenlik açıkları ve riskli API çağrılarını denetler."),
    "DeadCodeAnalyzer": ("Ölü ve Atıl Kod Analizi", "Kullanılmayan fonksiyon ve sınıfları tespit eder."),
    "DeadWeightAnalyzer": ("Gereksiz Ağırlık Tespiti", "Gereksiz büyük ve hantal dosyaları belirler."),
    "DuplicateFinder": ("Kopya Dosya Tespiti", "Birebir aynı dosya içeriklerini yakalar."),
    "EmptyFolderFinder": ("Boş Klasör Tespiti", "Gereksiz boş dizinleri listeler."),
    "GitHistoryAnalyzer": ("Git Geçmişi Analizi", "Commit geçmişi ve büyük git nesnelerini denetler."),
    "LanguageStatsAnalyzer": ("Dil ve Satır Dağılımı", "Programlama dilleri ve satır istatistiklerini hesaplar."),
    "MagicNumberAnalyzer": ("Sihirli Sayı Denetimi", "Sabit yerine doğrudan kodlanan sayıları inceler."),
    "ProjectHygieneAnalyzer": ("Proje Hijyen Taraması", "TODO, geçici dosyalar ve şablon kalıntılarını inceler."),
    "ReliabilityAnalyzer": ("Güvenilirlik ve Hata Analizi", "Hata yakalama ve sessiz istisna yakalamalarını inceler."),
    "SecurityLeakAnalyzer": ("Sır ve Anahtar Sızıntıları", "API anahtarları, şifreler ve .env sızıntılarını arar."),
    "SizeAnalyzer": ("Boyut ve Alan Analizi", "Büyük dosyalar ve disk kullanımını analiz eder."),
    "StructureAnalyzer": ("Yapı ve Modül Mimarisi", "Dizin hiyerarşisi ve modül düzenini inceler."),
    "TestingAnalyzer": ("Test Kapsam Analizi", "Test dosyalarının varlığını ve oranını denetler."),
    "TypeAnalyzer": ("Tip İpuçları ve Tür Analizi", "Python type hint kullanım oranını analiz eder."),
}


class SettingsViewModel(QObject):
    """QML Yapılandırma, Kalite Eşikleri ve Ajan Görevleri köprüsü."""

    settingsChanged = Signal()
    taskExportFinished = Signal(dict)
    taskExportError = Signal(str)

    def __init__(self, project_service: ProjectService, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.service = project_service
        load_builtin_analyzers()

        self._respect_gitignore = True
        self._disabled_analyzers: Set[str] = set()

        # Eşikler
        self._cyclomatic = 10
        self._cognitive = 15
        self._function_lines = 50
        self._class_lines = 300
        self._file_lines = 500

        # Ajan parti büyüklüğü
        self._agent_batch_size = 15
        self._last_agent_result: Dict[str, Any] = {}

    # ── Properties ──

    @Property(bool, notify=settingsChanged)
    def respectGitignore(self) -> bool:
        return self._respect_gitignore

    @Property(int, notify=settingsChanged)
    def cyclomatic(self) -> int:
        return self._cyclomatic

    @Property(int, notify=settingsChanged)
    def cognitive(self) -> int:
        return self._cognitive

    @Property(int, notify=settingsChanged)
    def functionLines(self) -> int:
        return self._function_lines

    @Property(int, notify=settingsChanged)
    def classLines(self) -> int:
        return self._class_lines

    @Property(int, notify=settingsChanged)
    def fileLines(self) -> int:
        return self._file_lines

    @Property(int, notify=settingsChanged)
    def agentBatchSize(self) -> int:
        return self._agent_batch_size

    @Property("QVariantList", notify=settingsChanged)
    def analyzersList(self) -> List[Dict[str, Any]]:
        """18 analizörün aktif/pasif ve meta veri listesi."""
        items = []
        for name in default_registry.ids():
            meta = ANALYZER_METADATA.get(name, (name, "Statik kod analiz motoru."))
            items.append({
                "id": name,
                "name": meta[0],
                "description": meta[1],
                "enabled": name not in self._disabled_analyzers
            })
        return items

    @Property("QVariantMap", notify=settingsChanged)
    def lastAgentResult(self) -> Dict[str, Any]:
        return self._last_agent_result

    # ── Slots ──

    @Slot(bool)
    def setRespectGitignore(self, value: bool):
        self._respect_gitignore = value
        self.settingsChanged.emit()

    @Slot(str, bool)
    def toggleAnalyzer(self, name: str, enabled: bool):
        if enabled:
            self._disabled_analyzers.discard(name)
        else:
            self._disabled_analyzers.add(name)
        self.settingsChanged.emit()

    @Slot()
    def enableAllAnalyzers(self):
        """Tüm analizörleri etkinleştirir."""
        self._disabled_analyzers.clear()
        self.settingsChanged.emit()

    @Slot()
    def disableAllAnalyzers(self):
        """Tüm analizörleri devre dışı bırakır."""
        for name in default_registry.ids():
            self._disabled_analyzers.add(name)
        self.settingsChanged.emit()

    @Slot(int)
    def setCyclomatic(self, val: int):
        self._cyclomatic = max(val, 1)
        self.settingsChanged.emit()

    @Slot(int)
    def setCognitive(self, val: int):
        self._cognitive = max(val, 1)
        self.settingsChanged.emit()

    @Slot(int)
    def setFunctionLines(self, val: int):
        self._function_lines = max(val, 5)
        self.settingsChanged.emit()

    @Slot(int)
    def setClassLines(self, val: int):
        self._class_lines = max(val, 20)
        self.settingsChanged.emit()

    @Slot(int)
    def setFileLines(self, val: int):
        self._file_lines = max(val, 50)
        self.settingsChanged.emit()

    @Slot(int)
    def setAgentBatchSize(self, val: int):
        self._agent_batch_size = max(val, 1)
        self.settingsChanged.emit()

    @Slot()
    def resetToDefaults(self):
        """Tüm ayarları ve eşikleri V2 varsayılanlarına döndürür."""
        self._respect_gitignore = True
        self._disabled_analyzers.clear()
        self._cyclomatic = 10
        self._cognitive = 15
        self._function_lines = 50
        self._class_lines = 300
        self._file_lines = 500
        self._agent_batch_size = 15
        self.applySettings()

    @Slot()
    def applySettings(self):
        """Ayarları ProjectService ve Doctor'a uygular."""
        try:
            thresholds = QualityThresholds(
                cyclomatic=self._cyclomatic,
                cognitive=self._cognitive,
                function_lines=self._function_lines,
                class_lines=self._class_lines,
                file_lines=self._file_lines
            )

            analyzers = default_registry.create_all(disabled=tuple(self._disabled_analyzers))
            self.service.doctor = ProjectDoctor(
                analyzers=analyzers,
                respect_gitignore=self._respect_gitignore,
                thresholds=thresholds,
            )
            self.settingsChanged.emit()
            logger.info("Yeni ayarlar ve kalite eşikleri başarıyla uygulandı.")
        except Exception as e:
            logger.error("Ayarlar uygulanırken hata: %s", e, exc_info=True)

    @Slot(str)
    def exportAgentTasks(self, output_dir_str: str):
        """Bulguları yapay zeka görev dosyalarına yazar."""
        if not self.service._current_project:
            self.taskExportError.emit("Ajan görevleri üretmek için önce bir proje seçilmelidir.")
            return

        if output_dir_str.startswith("file:///"):
            output_dir_str = output_dir_str[8:]
        target_dir = Path(output_dir_str).resolve()

        try:
            res = self.service.export_agent_tasks(target_dir, batch_size=self._agent_batch_size)
            self._last_agent_result = {
                "success": True,
                "verified": False,
                "totalTasks": int(res.get("tasks", 0)),
                "totalItems": int(res.get("items", 0)),
                "outputDir": str(target_dir),
            }
            self.settingsChanged.emit()
            self.taskExportFinished.emit(self._last_agent_result)
        except Exception as e:
            logger.error("Ajan görevleri dışa aktarılırken hata: %s", e, exc_info=True)
            self.taskExportError.emit(str(e))

    @Slot(str)
    def verifyAgentTasks(self, tasks_dir_str: str):
        """Üretilen ajan görevlerinin projeyi tekrar tarayarak tamamlanıp tamamlanmadığını doğrular."""
        if not self.service._current_project:
            self.taskExportError.emit("Ajan görevlerini doğrulamak için önce bir proje seçilmelidir.")
            return

        if tasks_dir_str.startswith("file:///"):
            tasks_dir_str = tasks_dir_str[8:]
        target_dir = Path(tasks_dir_str).resolve()

        try:
            res = self.service.verify_agent_tasks(target_dir)
            closed_cnt = len(res.get("closed_items", [])) if "closed_items" in res else int(res.get("closed_count", 0))
            remaining_cnt = len(res.get("remaining_items", [])) if "remaining_items" in res else int(res.get("remaining_count", 0))
            self._last_agent_result = {
                "success": True,
                "verified": True,
                "closed": closed_cnt,
                "remaining": remaining_cnt,
                "tasksDir": str(target_dir),
                "warning": res.get("warning", "")
            }
            self.settingsChanged.emit()
            self.taskExportFinished.emit(self._last_agent_result)
        except Exception as e:
            logger.error("Ajan görevleri doğrulanırken hata: %s", e, exc_info=True)
            self.taskExportError.emit(str(e))
