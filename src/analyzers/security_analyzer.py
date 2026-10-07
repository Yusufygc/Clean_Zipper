import re
from pathlib import Path
from typing import List
from src.core.base_analyzer import BaseAnalyzer
from src.models.analysis_models import AnalysisResult, Severity

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

    def analyze(self, project_path: Path) -> List[AnalysisResult]:
        results = []
        
        for root_path, _, filenames in self._walk_project(project_path):
            for filename in filenames:
                file_path = Path(root_path) / filename
                
                # Sadece text/kod tabanlı dosyaları oku, binary dosyaları atla
                if self._is_binary(file_path):
                    continue
                    
                # Riskli uzantı veya doğrudan isim eşleşmesi (.env veya config kontrolü)
                if file_path.name in ['.env', 'credentials.json', 'secrets.yaml']:
                    results.append(self._create_result(
                        title=f"Kritik Güvenlik Riski: {file_path.name}",
                        description=f"Hassas yapılandırma dosyası proje kökünde açıkta bırakılmış!",
                        severity=Severity.CRITICAL,
                        file_path=file_path,
                        recommendation="Bu dosyayı hemen .gitignore içerisine ekleyin ve sunucuda ortam değişkeni (env) olarak tanımlayın."
                    ))
                    continue

                # Kod içi tarama mantığı
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            for pattern_name, regex in self.secret_patterns.items():
                                if regex.search(line):
                                    results.append(self._create_result(
                                        title=f"Açık Şifreleme/Key Sızıntısı ({file_path.name})",
                                        description=f"Satır {line_num}: Kod içinde sertifikasız '{pattern_name}' algılandı.",
                                        severity=Severity.HIGH,
                                        file_path=file_path,
                                        recommendation="Şifre ve anahtarları doğrudan kod içine yazmak yerine çevre değişkenlerinden (.env) çağırın."
                                    ))
                except Exception:
                    pass # Okuma hatalarını güvenle yut
                    
        return results