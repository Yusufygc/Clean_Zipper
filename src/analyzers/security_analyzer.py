import re
from pathlib import Path
from typing import List
from src.core.base_analyzer import BaseAnalyzer
from src.core.project_index import ProjectIndex
from src.core.registry import register_analyzer
from src.models.analysis_models import AnalysisResult, Severity

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

        for entry in index.files:
            file_path = entry.path

            # Riskli dosya adı (.env veya credentials kontrolü)
            if file_path.name in SENSITIVE_FILE_NAMES:
                results.append(self._create_result(
                    title=f"Kritik Güvenlik Riski: {file_path.name}",
                    description=f"Hassas yapılandırma dosyası proje kökünde açıkta bırakılmış!",
                    severity=Severity.CRITICAL,
                    file_path=file_path,
                    recommendation="Bu dosyayı hemen .gitignore içerisine ekleyin ve sunucuda ortam değişkeni (env) olarak tanımlayın."
                ))
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

        return results
