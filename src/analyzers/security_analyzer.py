import re
from pathlib import Path
from typing import List
from src.core.base_analyzer import BaseAnalyzer
from src.core.project_index import ProjectIndex
from src.core.registry import register_analyzer
from src.models.analysis_models import AnalysisResult, Severity
from src.utils.gitignore_parser import GitignoreMatcher

SENSITIVE_FILE_NAMES = frozenset({'.env', 'credentials.json', 'secrets.yaml'})

@register_analyzer
class SecurityLeakAnalyzer(BaseAnalyzer):
    def __init__(self, priority: int = 15):
        super().__init__(priority)
        # Yaygın sızıntı kelimeleri yakalamak için hassas regex şablonları
        self.secret_patterns = {
            "API Anahtarı / Şifre": re.compile(r'(key|secret|password|passwd|token)\s*=\s*[\'"][A-Za-z0-9_\-]{8,}[\'"]', re.IGNORECASE),
            # Kendi kodumuzu yanlışlıkla sızıntı olarak işaretlememesi (False Positive) için
            # regex şablonlarını parçalayarak (concatenation) birleştiriyoruz.
            "Veritabanı URL Sızıntısı": re.compile(r'mongo' + r'db(\+srv)?://|post' + r'gres://|my' + r'sql://', re.IGNORECASE)
        }

    @property
    def name(self) -> str:
        return "Güvenlik Sızıntısı Analizörü"

    @property
    def category(self) -> str:
        return "security"

    def analyze(self, index: ProjectIndex) -> List[AnalysisResult]:
        results = []
        tracked = index.git_tracked          # None: git yok / depo değil (izleme bilinmiyor)

        for entry in index.files:
            file_path = entry.path

            # Riskli dosya adı (.env veya credentials kontrolü)
            if file_path.name in SENSITIVE_FILE_NAMES:
                results.append(self._sensitive_file_result(index, entry.rel, file_path, tracked))
                continue

            # Kod içi tarama mantığı (ikilik ve çok büyük dosyalar atlanır)
            text = index.read_text(entry)
            if text is None:
                continue
            for line_num, line in enumerate(text.splitlines(), 1):
                for pattern_name, regex in self.secret_patterns.items():
                    if regex.search(line):
                        results.append(self._create_result(
                            title=f"Açık Şifreleme/Key Sızıntısı ({file_path.name})",
                            description=f"Satır {line_num}: Kod içinde sertifikasız '{pattern_name}' algılandı.",
                            severity=Severity.HIGH,
                            file_path=file_path,
                            recommendation="Şifre ve anahtarları doğrudan kod içine yazmak yerine çevre değişkenlerinden (.env) çağırın."
                        ))

        results.extend(self._tracked_but_ignored(index, tracked))
        return results

    def _sensitive_file_result(self, index: ProjectIndex, rel: str, file_path, tracked) -> AnalysisResult:
        """İndekste kalan hassas dosya: git'e commit edilmiş mi, yoksa yalnızca .gitignore'a eklenmemiş mi."""
        tracking_known = tracked is not None
        if tracking_known and rel in tracked:
            # İzlenen dosya kurala uysa bile indekste kalır; "zaten .gitignore'da" bilgisini kurallardan öğren.
            matches_rules = GitignoreMatcher(str(index.root)).is_ignored(file_path)
            return self._committed_result(rel, file_path, ignored=matches_rules)
        note = "" if tracking_known else " (git bilgisi alınamadı: dosyanın zaten commit edilip edilmediği bilinmiyor)"
        return self._create_result(
            title=f"Kritik Güvenlik Riski: {file_path.name}",
            description=f"'{rel}' hassas yapılandırma dosyası .gitignore'a eklenmemiş; commit edilme riski var.{note}",
            severity=Severity.CRITICAL,
            file_path=file_path,
            recommendation="Bu dosyayı hemen .gitignore içerisine ekleyin ve sunucuda ortam değişkeni (env) olarak tanımlayın.",
            kind='sensitive_file', committed=False, tracking_known=tracking_known,
        )

    def _committed_result(self, rel: str, file_path, ignored: bool) -> AnalysisResult:
        reason = " ve .gitignore'da olmasına rağmen" if ignored else ""
        return self._create_result(
            title=f"Kritik Güvenlik Riski: {file_path.name} git'e commit edilmiş",
            description=(f"'{rel}' hassas dosyası git tarafından izleniyor{reason}. "
                         ".gitignore izlenen dosyayı depodan ve geçmişten silmez; içindeki sırlar ele geçmiş sayılmalı."),
            severity=Severity.CRITICAL,
            file_path=file_path,
            recommendation=(f"'git rm --cached {rel}' ile izlemeden çıkarın, içindeki sırları değiştirin (rotate) "
                            "ve gerekirse geçmişi temizleyin."),
            kind='sensitive_file', committed=True, tracking_known=True, gitignored=ignored,
        )

    def _tracked_but_ignored(self, index: ProjectIndex, tracked) -> List[AnalysisResult]:
        """.gitignore'a eklenmiş ama git'in hâlâ izlediği hassas dosyalar (indekste yoklar; git'ten bulunur)."""
        if not tracked:
            return []
        in_index = {f.rel for f in index.files}
        return [
            self._committed_result(rel, index.root / rel, ignored=True)
            for rel in sorted(tracked)
            if rel.rsplit('/', 1)[-1] in SENSITIVE_FILE_NAMES and rel not in in_index
        ]
