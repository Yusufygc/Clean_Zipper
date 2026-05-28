import re
from pathlib import Path
from typing import List, Set, Dict
from src.core.base_analyzer import BaseAnalyzer
from src.models.analysis_models import AnalysisResult, Severity

class DeadWeightAnalyzer(BaseAnalyzer):
    """Projedeki gereksiz/kullanılmayan kütüphaneleri (bağımlılıkları) tespit eden analizör."""

    # Popüler kütüphanelerin requirements.txt ismi ile koddaki import ismi arasındaki eşleşme haritası
    COMMON_MAPPINGS = {
        "pyside6-essentials": "pyside6",
        "pyside6-addons": "pyside6",
        "pillow": "pil",
        "pyyaml": "yaml",
        "scikit-learn": "sklearn",
        "beautifulsoup4": "bs4",
        "opencv-python": "cv2",
        "python-docx": "docx",
        "python-dotenv": "dotenv",
        "python-socketio": "socketio",
        "authlib": "authlib",
        "pyjwt": "jwt",
        "paho-mqtt": "paho",
        "websocket-client": "websocket"
    }

    def __init__(self, priority: int = 25):
        super().__init__(priority)

    @property
    def name(self) -> str:
        return "Bağımlılık ve Ölü Kod Analizörü"

    @property
    def category(self) -> str:
        return "quality"

    def analyze(self, project_path: Path) -> List[AnalysisResult]:
        results = []
        
        # 1. Projedeki requirements.txt dosyasını bul ve bağımlılıkları oku
        req_file = project_path / "requirements.txt"
        if not req_file.exists():
            # Eğer requirements.txt yoksa bir bilgi uyarısı verelim
            results.append(self._create_result(
                title="Gereksinim Dosyası Eksik (requirements.txt)",
                description="Projede requirements.txt bulunamadı. Bağımlılık yönetimi için eklemeniz önerilir.",
                severity=Severity.INFO,
                recommendation="Proje kök dizininde pip bağımlılıklarını içeren bir requirements.txt oluşturun."
            ))
            return results

        dependencies = self._parse_requirements(req_file)
        if not dependencies:
            return results

        # 2. Tüm Python dosyalarındaki import ifadelerini tara
        imported_modules = self._collect_all_imports(project_path)

        # 3. Bağımlılıkları karşılaştır ve kullanılmayanları bul
        unused_deps = []
        for dep in dependencies:
            # Standart karşılaştırma için isimleri normalize et
            normalized_dep = dep.lower()
            
            # Özel eşleşme haritasından kontrol et (örn: pillow -> pil)
            mapped_name = self.COMMON_MAPPINGS.get(normalized_dep, normalized_dep)
            
            # Alt modül veya doğrudan modül adı eşleşiyor mu kontrol et
            is_used = False
            for imp in imported_modules:
                if imp == mapped_name or imp.startswith(mapped_name + "."):
                    is_used = True
                    break
            
            if not is_used:
                unused_deps.append(dep)

        # 4. Bulguları raporla
        for unused in unused_deps:
            results.append(self._create_result(
                title=f"Kullanılmayan Kütüphane Tespit Edildi: {unused}",
                description=f"'{unused}' kütüphanesi requirements.txt içinde tanımlı fakat kodda import edilmemiş.",
                severity=Severity.MEDIUM,
                file_path=req_file,
                recommendation=f"Eğer bu kütüphaneyi kullanmıyorsanız requirements.txt dosyasından silerek bağımlılıkları temizleyin."
            ))

        return results

    def _parse_requirements(self, filepath: Path) -> Set[str]:
        """requirements.txt dosyasını temizleyerek kütüphane isimlerini ayrıştırır."""
        deps = set()
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    # Boş satırları ve yorumları atla
                    if not line or line.startswith('#'):
                        continue
                    
                    # Versiyon belirteçlerini temizle (==, >=, <=, ~=, >, <)
                    # Örn: PySide6-Essentials==6.6.1 -> PySide6-Essentials
                    parts = re.split(r'==|>=|<=|~=|>|<', line)
                    dep_name = parts[0].strip()
                    if dep_name:
                        deps.add(dep_name)
        except Exception:
            pass
        return deps

    def _collect_all_imports(self, project_path: Path) -> Set[str]:
        """Projedeki tüm .py dosyalarını tarayarak import edilen ana modül isimlerini toplar."""
        imports = set()
        
        # 'import x' veya 'from x import y' ifadelerini yakalayan regex şablonları
        import_pattern = re.compile(r'^\s*import\s+([a-zA-Z0-9_.,\s]+)')
        from_pattern = re.compile(r'^\s*from\s+([a-zA-Z0-9_]+)')

        for root_path, _, filenames in self._walk_project(project_path):
            for filename in filenames:
                file_path = Path(root_path) / filename
                if file_path.suffix.lower() != '.py':
                    continue

                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            # 1. 'import x, y' yapısı
                            imp_match = import_pattern.match(line)
                            if imp_match:
                                # Virgülle ayrılmış çoklu importları ayır
                                modules = imp_match.group(1).split(',')
                                for mod in modules:
                                    # Alt paketleri temizle (örn: os.path -> os)
                                    main_mod = mod.strip().split('.')[0]
                                    if main_mod:
                                        imports.add(main_mod.lower())
                            
                            # 2. 'from x import y' yapısı
                            from_match = from_pattern.match(line)
                            if from_match:
                                main_mod = from_match.group(1).strip().split('.')[0]
                                if main_mod:
                                    imports.add(main_mod.lower())
                except Exception:
                    pass
        return imports