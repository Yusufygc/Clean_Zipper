import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Signal, Slot, Property
from src.core.errors import GitCleanError
from src.core.registry import default_registry, load_builtin_analyzers
from src.doctors.project_doctor import ProjectDoctor
from src.services import app_settings
from src.services.app_settings import AppSettings, THRESHOLD_LIMITS, default_thresholds
from src.services.audit_catalog import RULE_LABELS
from src.services.project_service import ProjectService
from src.qml_ui.viewmodels.paths import local_path

logger = logging.getLogger(__name__)

ANALYZER_METADATA: Dict[str, tuple] = {
    "ArchitectureAnalyzer": ("Mimari ve Katman Analizi", "Döngüsel bağımlılıkları ve bağımlılık grafiğini denetler."),
    "CloneAnalyzer": ("Kod Klonu ve Tekrar Analizi", "Tekrarlanan kod bloklarını tespit eder."),
    "CodeComplexityAnalyzer": ("Karmaşıklık Analizi", "Döngüsel ve bilişsel karmaşıklık sınırlarını ölçer."),
    "CodeSecurityAnalyzer": ("Kod Güvenlik Taraması", "Güvenlik açıkları ve riskli API çağrılarını denetler."),
    "DeadCodeAnalyzer": ("Ölü Kod Analizi", "Kullanılmayan import, değişken ve ulaşılamaz kodu bulur."),
    "DeadWeightAnalyzer": ("Bağımlılık Analizi", "Kullanılmayan ve sabitlenmemiş bağımlılıkları bulur."),
    "DuplicateFinder": ("Kopya Dosya Tespiti", "Birebir aynı dosya içeriklerini yakalar."),
    "EmptyFolderFinder": ("Boş Klasör Tespiti", "Gereksiz boş dizinleri listeler."),
    "GitHistoryAnalyzer": ("Git Geçmişi Analizi", "Geçmişte commit edilmiş sırları, sık değişen ve birlikte değişen dosyaları bulur."),
    "LanguageStatsAnalyzer": ("Dil ve Satır Dağılımı", "Programlama dilleri ve satır istatistiklerini hesaplar."),
    "MagicNumberAnalyzer": ("Sihirli Sayı Denetimi", "Sabit yerine doğrudan kodlanan sayıları inceler."),
    "ProjectHygieneAnalyzer": ("Proje Hijyeni", "README, LICENSE, CI, kilit dosyası ve sürüm kontrolündeki üretilmiş içeriği denetler."),
    "ReliabilityAnalyzer": ("Güvenilirlik ve Hata Analizi", "Hata yakalama ve sessiz istisna yakalamalarını inceler."),
    "SecurityLeakAnalyzer": ("Sır ve Anahtar Sızıntıları", "API anahtarları, şifreler ve .env sızıntılarını arar."),
    "SizeAnalyzer": ("Boyut ve Alan Analizi", "Büyük dosyalar ve disk kullanımını analiz eder."),
    "StructureAnalyzer": ("Yapı ve Modül Mimarisi", "Dizin hiyerarşisi ve modül düzenini inceler."),
    "TestingAnalyzer": ("Test Kapsam Analizi", "Test dosyalarının varlığını ve oranını denetler."),
    "TypeAnalyzer": ("Dosya Türü Analizi", "Dosya türü dağılımını hesaplar."),
}

THRESHOLD_LABELS: Dict[str, str] = {
    "cyclomatic": "Döngüsel karmaşıklık", "cognitive": "Bilişsel karmaşıklık", "function_lines": "İşlev satırı",
    "class_lines": "Sınıf satırı", "file_lines": "Dosya satırı", "parameters": "İşlev parametresi",
    "nesting": "İç içe blok derinliği", "class_methods": "Sınıf metodu", "module_imports": "Dosya başına import",
}


class SettingsViewModel(QObject):
    """QML Yapılandırma, Kalite Eşikleri ve Ajan Görevleri köprüsü. Ayarlar `~/.gitclean/settings.json` içinde kalıcıdır."""

    settingsChanged = Signal()
    settingsApplied = Signal(str)
    rulesChanged = Signal()                      # kural açıp kapatınca: görünümler analizi yenilemeli
    taskExportFinished = Signal(dict)
    taskExportError = Signal(str)

    def __init__(self, project_service: ProjectService, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.service = project_service
        load_builtin_analyzers()
        self._settings: AppSettings = app_settings.load_settings()
        self._last_agent_result: Dict[str, Any] = {}
        self._build_doctor()                     # kayıtlı ayarlar uygulama açılışında da geçerli olsun

    # ── Uygulama ──

    def _build_doctor(self) -> None:
        s = self._settings
        analyzers = default_registry.create_all(disabled=tuple(s.disabled_analyzers))
        self.service.doctor = ProjectDoctor(analyzers=analyzers, respect_gitignore=s.respect_gitignore,
                                            thresholds=s.quality_thresholds(), disabled_rules=s.disabled_rules)
        self.service.backup_service.max_backups = s.max_backups

    def _apply(self, message: str) -> bool:
        """Doctor'ı yeniden kurar ve ayarları diske yazar."""
        try:
            self._build_doctor()
        except Exception as e:
            logger.error("Ayarlar uygulanırken hata: %s", e, exc_info=True)
            self.settingsApplied.emit(f"Ayarlar uygulanamadı: {e}")
            return False
        saved = app_settings.save_settings(self._settings)
        self.settingsChanged.emit()
        self.settingsApplied.emit(message if saved else message + " (diske kaydedilemedi)")
        return True

    # ── Properties ──

    @Property(bool, notify=settingsChanged)
    def respectGitignore(self) -> bool:
        return self._settings.respect_gitignore

    @Property("QVariantList", notify=settingsChanged)
    def thresholds(self) -> List[Dict[str, Any]]:
        defaults = default_thresholds()
        return [{"key": key, "label": THRESHOLD_LABELS[key], "value": self._settings.thresholds[key],
                 "default": defaults[key], "step": step} for key, (_, step) in THRESHOLD_LIMITS.items()]

    @Property("QVariantList", notify=settingsChanged)
    def analyzersList(self) -> List[Dict[str, Any]]:
        items = []
        for name in default_registry.ids():
            meta = ANALYZER_METADATA.get(name, (name, "Statik kod analiz motoru."))
            items.append({"id": name, "name": meta[0], "description": meta[1],
                          "enabled": name not in self._settings.disabled_analyzers})
        return items

    @Property("QVariantList", notify=settingsChanged)
    def disabledRules(self) -> List[Dict[str, str]]:
        return [{"id": rule, "title": RULE_LABELS.get(rule, rule)} for rule in self._settings.disabled_rules]

    @Property(int, notify=settingsChanged)
    def maxBackups(self) -> int:
        """Proje başına saklanan otomatik yedek sayısı; 0 = sınırsız."""
        return self._settings.max_backups

    @Property(int, notify=settingsChanged)
    def agentBatchSize(self) -> int:
        return self._settings.agent_batch_size

    @Property(str, notify=settingsChanged)
    def agentOutputDir(self) -> str:
        """Seçilen ya da (boşsa) varsayılan çıktı klasörü; varsayılan projenin dışındadır."""
        if self._settings.agent_output_dir:
            return self._settings.agent_output_dir
        return str(app_settings.default_agent_dir(self.service._current_project))

    @Property(bool, notify=settingsChanged)
    def agentOutputDirIsCustom(self) -> bool:
        return bool(self._settings.agent_output_dir)

    @Property("QVariantMap", notify=settingsChanged)
    def lastAgentResult(self) -> Dict[str, Any]:
        return self._last_agent_result

    # ── Slots: genel ayarlar ──

    @Slot(bool)
    def setRespectGitignore(self, value: bool):
        self._settings.respect_gitignore = value
        self.settingsChanged.emit()

    @Slot(str, int)
    def adjustThreshold(self, key: str, delta: int):
        if key not in THRESHOLD_LIMITS:
            return
        self._settings.set_threshold(key, self._settings.thresholds[key] + delta)
        self.settingsChanged.emit()

    @Slot(str, bool)
    def toggleAnalyzer(self, name: str, enabled: bool):
        names = set(self._settings.disabled_analyzers)
        if enabled:
            names.discard(name)
        else:
            names.add(name)
        self._settings.disabled_analyzers = sorted(names)
        self.settingsChanged.emit()

    @Slot()
    def enableAllAnalyzers(self):
        self._settings.disabled_analyzers = []
        self.settingsChanged.emit()

    @Slot()
    def disableAllAnalyzers(self):
        self._settings.disabled_analyzers = sorted(default_registry.ids())
        self.settingsChanged.emit()

    @Slot()
    def resetToDefaults(self):
        """Tüm ayarları (eşikler, analizörler, kapatılan kurallar, ajan ayarları) varsayılana döndürür ve uygular."""
        self._settings = AppSettings()
        if self._apply("Ayarlar varsayılana döndürüldü."):
            self.rulesChanged.emit()                  # eşikler değişti: sonuçlar yeniden hesaplanır

    @Slot()
    def applySettings(self):
        refresh = " Analiz yenileniyor." if self.service.current_project else ""
        if self._apply("Ayarlar kaydedildi ve uygulandı." + refresh):
            self.rulesChanged.emit()                  # eşikler / .gitignore / analizörler değişti: sonuçlar yeniden hesaplanır

    # ── Slots: kural açma / kapama ──

    @Slot(str)
    def disableRule(self, rule: str):
        """Bir kuralı (yanlış pozitif) kapatır; hemen uygulanır ve kaydedilir."""
        if not rule or rule in self._settings.disabled_rules:
            return
        self._settings.disabled_rules = sorted(self._settings.disabled_rules + [rule])
        if self._apply(f"'{RULE_LABELS.get(rule, rule)}' kuralı kapatıldı."):
            self.rulesChanged.emit()

    @Slot(str)
    def enableRule(self, rule: str):
        if rule not in self._settings.disabled_rules:
            return
        self._settings.disabled_rules = [r for r in self._settings.disabled_rules if r != rule]
        if self._apply(f"'{RULE_LABELS.get(rule, rule)}' kuralı yeniden etkinleştirildi."):
            self.rulesChanged.emit()

    # ── Slots: yedek ──

    @Slot(int)
    def adjustMaxBackups(self, delta: int):
        """Hemen uygulanır ve kaydedilir (teşhisi etkilemez, analiz yenilenmez)."""
        value = min(max(self._settings.max_backups + delta, 0), app_settings.MAX_KEPT_BACKUPS)
        if value == self._settings.max_backups:
            return
        self._settings.max_backups = value
        self.service.backup_service.max_backups = value
        app_settings.save_settings(self._settings)
        self.settingsChanged.emit()

    # ── Slots: ajan görevleri ──

    @Slot(int)
    def adjustAgentBatchSize(self, delta: int):
        self._settings.agent_batch_size = min(max(self._settings.agent_batch_size + delta, 1), app_settings.MAX_BATCH_SIZE)
        self.settingsChanged.emit()

    @Slot(str)
    def setAgentOutputDir(self, path_str: str):
        """Boş metin varsayılan klasöre döner."""
        path_str = local_path(path_str)
        self._settings.agent_output_dir = str(Path(path_str)) if path_str else ""
        self.settingsChanged.emit()

    @Slot()
    def onProjectChanged(self):
        """Varsayılan ajan klasörü proje adına bağlıdır."""
        self.settingsChanged.emit()

    @Slot()
    def exportAgentTasks(self):
        """Bulguları yapay zeka görev dosyalarına yazar."""
        if not self.service._current_project:
            self.taskExportError.emit("Ajan görevleri üretmek için önce bir proje seçilmelidir.")
            return
        target = Path(self.agentOutputDir)
        try:
            summary = self.service.export_agent_tasks(target, batch_size=self._settings.agent_batch_size)
        except Exception as e:
            logger.error("Ajan görevleri dışa aktarılırken hata: %s", e, exc_info=True)
            self.taskExportError.emit(str(e))
            return
        self._publish_agent_result({
            "kind": "export", "success": True, "totalTasks": int(summary.get("tasks", 0)),
            "totalItems": int(summary.get("items", 0)), "outputDir": str(target),
            "waves": [{"wave": wave, "tasks": info["tasks"], "items": info["items"]}
                      for wave, info in summary.get("waves", {}).items()]})

    @Slot()
    def verifyAgentTasks(self):
        """Projeyi yeniden tarayıp üretilmiş görevlerin kapanıp kapanmadığını doğrular."""
        if not self.service._current_project:
            self.taskExportError.emit("Ajan görevlerini doğrulamak için önce bir proje seçilmelidir.")
            return
        target = Path(self.agentOutputDir)
        try:
            result = self.service.verify_agent_tasks(target)
        except Exception as e:
            logger.warning("Ajan görevleri doğrulanamadı: %s", e, exc_info=not isinstance(e, GitCleanError))
            self.taskExportError.emit(f"Doğrulama yapılamadı: {e}")
            return
        totals = result.get("totals", {})
        self._publish_agent_result({
            "kind": "verify", "success": True, "verified": True, "tasksDir": str(target), "outputDir": str(target),
            "total": int(totals.get("total", 0)), "closed": int(totals.get("closed", 0)),
            "reduced": int(totals.get("reduced", 0)), "open": int(totals.get("open", 0)),
            "newCount": int(result.get("new_count", 0)), "warning": result.get("warning", "")})

    def _publish_agent_result(self, result: Dict[str, Any]) -> None:
        self._last_agent_result = result
        self.settingsChanged.emit()
        self.taskExportFinished.emit(result)
