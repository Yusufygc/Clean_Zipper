# 🚀 GitClean Archiver Pro

> **Profesyonel Proje Yönetim, Analiz ve Optimizasyon Aracı**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-2.0.0-orange.svg)]()
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

---

## 📋 İçindekiler

- [Genel Bakış](#-genel-bakış)
- [Özellikler](#-özellikler)
- [Ekran Görüntüleri](#-ekran-görüntüleri)
- [Mimari Yapı](#-mimari-yapı)
- [Kurulum](#-kurulum)
- [Kullanım Kılavuzu](#-kullanım-kılavuzu)
- [Modül Açıklamaları](#-modül-açıklamaları)
- [Sağlık Skorlama Sistemi](#-sağlık-skorlama-sistemi)
- [API Referansı](#-api-referansı)
- [Geliştirme](#-geliştirme)
- [Build ve Dağıtım](#-build-ve-dağıtım)
- [Sık Sorulan Sorular](#-sık-sorulan-sorular)
- [Lisans](#-lisans)

---

## 🎯 Genel Bakış

**GitClean Archiver Pro**, yazılım projelerinizi analiz eden, gereksiz dosyaları tespit eden, `.gitignore` kurallarına uygun arşivleme yapan ve proje sağlığınızı puanlayan kapsamlı bir proje yönetim aracıdır.

### 🎪 Kullanım Senaryoları

| Senaryo | Açıklama |
|---------|----------|
| 📦 **Dağıtım Öncesi Hazırlık** | Projenizi paylaşmadan önce gereksiz dosyalardan arındırın |
| 🔍 **Kod Teslimi** | Müşteriye sadece gerekli dosyaları içeren temiz bir paket sunun |
| 💾 **Yedekleme** | Sadece önemli dosyaları yedekleyerek alan tasarrufu yapın |
| 🧹 **Bakım** | Düzenli proje temizliği ile disk alanını optimize edin |
| 📊 **Analiz** | Projenizin sağlık durumunu düzenli olarak takip edin |
| 🔒 **Güvenlik** | Hassas dosyaların yanlışlıkla paylaşılmasını önleyin |

---

## ✨ Özellikler

### 🏥 Proje Doktoru
- **6 kategoride bulgu tabanlı sağlık analizi** (Güvenlik, Karmaşıklık, Çiftler, Boyut, Yapı, Bağımlılık)
- **A+ 'dan F' e kadar notlandırma** sistemi
- **Kritik sorunların otomatik tespiti**
- **İyileştirme önerileri** ve tahmini kazanç hesaplama

### 📦 Akıllı Arşivleme
- `.gitignore` kurallarına **tam uyumlu** zip oluşturma
- **Temiz dizin kopyası** oluşturma
- **Özel filtreleme** desteği
- **Sıkıştırma seviyesi** kontrolü (store/fast/normal/maximum)

### 🧹 Otomatik Temizlik
- **Kategorilere göre** temizlik (Python, JS, IDE, Genel)
- **Önizleme modu** ile silinecekleri görme
- **Geri alınamaz işlemler için onay** mekanizması
- **Güvenli mod** (sadece cache dosyaları)

### 💾 Versiyonlu Yedekleme
- **Otomatik isimlendirme** (proje_adı_tarih_saat)
- **Zip formatında** sıkıştırılmış yedek
- **Yedek listesi** görüntüleme
- **Eski yedekleri temizleme** (son N adet saklama)

### 📊 Görsel Dashboard
- **Dairesel sağlık skoru** göstergesi
- **İstatistik kartları** (dosya sayısı, boyut, klasör, sorunlar)
- **İnteraktif pasta grafiği** (dosya türü dağılımı)
- **Canlı öneri paneli**
- **Koyu/Açık tema** desteği

### 🔍 Analiz Motorları

| Analizör | Kategori | Açıklama |
|----------|----------|----------|
| `SizeAnalyzer` | size | Dosya/klasör boyut analizi, büyük dosya tespiti |
| `TypeAnalyzer` | type | Dosya türü dağılımı, eksik dosya kontrolü |
| `DuplicateFinder` | duplicate | Hash-bazlı çift dosya tespiti |
| `EmptyFolderFinder` | structure | Boş klasör bulma |
| `StructureAnalyzer` | structure | Proje yapısal analizi, derinlik kontrolü |

---

---

## 🏗️ Mimari Yapı

### SOLID Prensipleri ile Modüler Tasarım

```
gitclean-archiver-pro/
│
├── src/                          # Kaynak kod
│   ├── core/                     # 🏗️ Temel mimari (FAZ 1)
│   │   ├── interfaces.py         #    Abstract base class'lar
│   │   └── base_analyzer.py      #    Temel analizör sınıfı
│   │
│   ├── models/                   # 📊 Veri modelleri (FAZ 1)
│   │   └── analysis_models.py    #    Dataclass'lar ve Enum'lar
│   │
│   ├── analyzers/                # 🔍 Analiz motorları (FAZ 2)
│   │   ├── size_analyzer.py      #    Boyut analizi
│   │   ├── type_analyzer.py      #    Dosya türü analizi
│   │   ├── duplicate_finder.py   #    Çift dosya bulucu
│   │   ├── empty_folder_finder.py#    Boş klasör bulucu
│   │   └── structure_analyzer.py #    Yapı analizi
│   │
│   ├── doctors/                  # 🏥 Proje doktoru (FAZ 3)
│   │   ├── project_doctor.py     #    Ana doktor koordinatörü
│   │   ├── health_checker.py     #    Sağlık skoru hesaplama
│   │   └── recommendation_engine.py  # Öneri motoru
│   │
│   ├── services/                 # ⚙️ İş servisleri (FAZ 5)
│   │   ├── archive_service.py    #    Arşivleme (zip/kopyalama)
│   │   ├── cleanup_service.py    #    Temizlik servisi
│   │   ├── backup_service.py     #    Yedekleme servisi
│   │   └── project_service.py    #    Ana servis (Facade)
│   │
│   ├── ui/                       # 🎨 Kullanıcı arayüzü
│   │   ├── main_window.py        #    Ana pencere (FAZ 6)
│   │   ├── dashboard/            #    Dashboard paneli (FAZ 4)
│   │   │   └── dashboard_panel.py
│   │   ├── widgets/              #    UI bileşenleri (FAZ 4)
│   │   │   ├── stats_card.py     #    İstatistik kartı
│   │   │   ├── health_score_widget.py  # Sağlık skoru
│   │   │   ├── pie_chart_widget.py     # Pasta grafiği
│   │   │   └── progress_card.py  #    İlerleme kartı
│   │   └── themes/               #    Tema yönetimi
│   │       └── theme_manager.py
│   │
│   └── utils/                    # 🛠️ Yardımcı araçlar
│       └── gitignore_parser.py   #    .gitignore parser
│
├── tests/                        # 🧪 Testler
│   ├── unit/                     #    Birim testleri
│   ├── integration/              #    Entegrasyon testleri
│   └── fixtures/                 #    Test verileri
│
├── resources/                    # 📦 Kaynaklar
│   ├── icons/                    #    Uygulama ikonları
│   ├── templates/                #    Rapor şablonları
│   └── profiles/                 #    Hazır profiller
│
├── main.py                       # 🚀 Ana giriş noktası
├── build_exe.py                  # 🔨 Build script'i
├── requirements.txt              # 📋 Bağımlılıklar
├── setup.py                      # 📦 Pip kurulumu
└── README.md                     # 📖 Bu doküman
```

### Veri Akış Diyagramı

```
Kullanıcı → UI (main_window.py)
              ↓
         ProjectService (Facade)
              ↓
         ┌────┴────┐
         ↓         ↓
    Doctor    Services
         ↓         ↓
    Analyzers  Archive/Cleanup/Backup
         ↓
    AnalysisResult
         ↓
    Dashboard (Görselleştirme)
```

---

## 🔧 Kurulum

### Gereksinimler

- **Python** 3.8 veya üstü
- **pip** (Python paket yöneticisi)
- **İşletim Sistemi**: Windows 10/11, Linux, macOS

### Adım Adım Kurulum

```bash
# 1. Projeyi klonlayın veya indirin
git clone https://github.com/gitclean/archiver-pro.git
cd gitclean-archiver-pro

# 2. Sanal ortam oluşturun
python -m venv venv

# 3. Sanal ortamı aktifleştirin
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 4. Bağımlılıkları yükleyin
pip install -r requirements.txt

# 5. Uygulamayı başlatın
python main.py
```

### Tek Komutla Kurulum (Windows)

```batch
python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt && python main.py
```

---

## 📖 Kullanım Kılavuzu

### 1. Proje Açma

1. Uygulamayı başlatın
2. Sol üstteki **📁 Proje Aç** butonuna tıklayın
3. Analiz etmek istediğiniz proje dizinini seçin
4. Otomatik analiz başlayacaktır

### 2. Dashboard Kullanımı

- **Sağlık Skoru**: Projenizin genel durumunu gösterir (A+ en iyi, F en kötü)
- **İstatistik Kartları**: Dosya sayısı, boyut, klasör sayısı, sorun sayısı
- **Pasta Grafiği**: Dosya türlerinin dağılımını gösterir
- **Öneriler**: En önemli 5 iyileştirme önerisi

### 3. Arşivleme İşlemleri

**Zip Oluşturma:**
1. **📦 Arşivle** sekmesine geçin
2. Çıktı dosyası yolunu belirtin (veya varsayılanı kullanın)
3. **🚀 Zip Oluştur** butonuna tıklayın

**Temiz Kopya Oluşturma:**
1. Aynı sekmede **📋 Temiz Kopya Oluştur** butonuna tıklayın
2. `.gitignore` kurallarına uygun temiz bir kopya oluşturulur

### 4. Temizlik İşlemleri

1. **🧹 Temizlik** sekmesine geçin
2. **🔍 Temizlik Önizleme** ile silinecek dosyaları görün
3. Onay verdikten sonra **🧹 Temizliği Başlat** ile temizleyin

### 5. Yedekleme (Komut Satırı)

```python
from src.services.backup_service import BackupService
from pathlib import Path

service = BackupService()
result = service.create_backup(Path("/proje/yolu"))
print(f"Yedek adı: {result['backup_name']}")
```

---

## 📊 Sağlık Skorlama Sistemi

### Skor Kategorileri ve Ağırlıkları

Skor, analizörlerin ürettiği bulgulardan hesaplanır. Sabit değer yoktur.

| Kategori | Ağırlık | Kaynak |
|----------|---------|--------|
| **Güvenlik** | %25 | Sızan anahtar/şifre, açıkta `.env` gibi dosyalar |
| **Karmaşıklık** | %20 | Şişmiş dosya, God Object, yüksek siklomatik karmaşıklık |
| **Çiftler** | %15 | Tekrarlayan dosya grupları |
| **Boyut** | %15 | Toplam proje boyutu, büyük dosyalar |
| **Yapı** | %15 | Boş klasörler, klasör derinliği |
| **Bağımlılık** | %10 | Kullanılmayan kütüphaneler, eksik `requirements.txt` |

Dosya türü dağılımı bilgi amaçlıdır, puanlanmaz.

**Hesaplama:** her bulgunun şiddeti ceza puanı getirir (KRİTİK 40, YÜKSEK 15, ORTA 5, DÜŞÜK 1, BİLGİ 0). Kategori skoru `100 × e^(−ceza/60)` formülüyle bulunur. Genel skor, kategori skorlarının ağırlıklı ortalamasıdır. Çalışmayan veya hata veren analizörün kategorisi ağırlıktan çıkarılır; hiçbir analizör çalışmazsa skor 0 olur.

### Notlandırma Tablosu

| Skor Aralığı | Not | Durum | Renk |
|-------------|-----|-------|------|
| 95-100 | A+ | Mükemmel | 🟢 Koyu Yeşil |
| 85-94 | A | İyi | 🟢 Yeşil |
| 75-84 | B+ | Ortalama Üstü | 🟡 Sarı-Yeşil |
| 65-74 | B | Ortalama | 🟡 Sarı |
| 55-64 | C+ | Ortalama Altı | 🟠 Turuncu |
| 45-54 | C | Zayıf | 🟠 Koyu Turuncu |
| 35-44 | D | Kritik | 🔴 Kırmızı |
| 0-34 | F | Başarısız | 🔴 Koyu Kırmızı |

---

## 📚 Modül Açıklamaları

### Core Modülleri

#### `interfaces.py`
Tüm sistemin temelini oluşturan abstract base class'lar:
- `IAnalyzer`: Tüm analizörlerin uyması gereken arayüz
- `IHealthChecker`: Sağlık kontrolü arayüzü
- `IRecommendationEngine`: Öneri motoru arayüzü
- `IReporter`: Raporlama arayüzü

#### `base_analyzer.py`
Analizörler için temel sınıf. Ortak işlevleri sağlar:
- Dosya sistemi gezinme (`_walk_project`)
- Binary dosya tespiti (`_is_binary`)
- Standart sonuç oluşturma (`_create_result`)

### Analizörler

#### `SizeAnalyzer`
```python
from src.analyzers.size_analyzer import SizeAnalyzer

analyzer = SizeAnalyzer(large_file_threshold_mb=10)
results = analyzer.analyze(Path("/proje"))
# Sonuçlar: Büyük dosyalar, toplam boyut, boyut dağılımı
```

#### `DuplicateFinder`
```python
from src.analyzers.duplicate_finder import DuplicateFinder

finder = DuplicateFinder(min_file_size=1024)  # 1KB'dan küçükleri atla
results = finder.analyze(Path("/proje"))
# Sonuçlar: Hash-bazlı çift dosya grupları
```

### Servisler

#### `ArchiveService`
```python
from src.services.archive_service import ArchiveService
from src.utils.gitignore_parser import GitignoreParser

parser = GitignoreParser("/proje")
service = ArchiveService(parser=parser)

# Zip oluştur
result = service.create_zip(Path("/proje"), Path("/cikti.zip"))

# Temiz kopya
result = service.copy_project(Path("/proje"), Path("/temiz_kopya"))
```

#### `CleanupService`
```python
from src.services.cleanup_service import CleanupService

service = CleanupService()

# Önizleme
preview = service.preview_cleanup(Path("/proje"), categories=['python'])
print(f"Temizlenecek: {preview['total_files']} dosya, {preview['total_size']} byte")

# Gerçek temizlik
result = service.cleanup(Path("/proje"), dry_run=False)
```

---

## 🔌 API Referansı

### ProjectService (Ana Servis)

```python
from src.services.project_service import ProjectService

service = ProjectService()

# Proje ayarla
service.set_project(Path("/proje/yolu"))

# Analiz et
analysis = service.analyze_project()
# Dönen değer: {
#     'health_score': float,
#     'health_status': str,
#     'total_files': int,
#     'total_size_mb': float,
#     'issues_count': int,
#     'top_recommendations': list,
#     'file_type_distribution': dict
# }

# Arşiv oluştur
result = service.create_archive(Path("/cikti.zip"), archive_type='zip')
result = service.create_archive(Path("/cikti_klasor"), archive_type='copy')

# Yedek al
backup = service.create_backup(backup_name="manuel_yedek")
```

### ProjectDoctor (Analiz Motoru)

```python
from src.doctors.project_doctor import ProjectDoctor
from src.analyzers.size_analyzer import SizeAnalyzer

doctor = ProjectDoctor()
doctor.register_analyzer(SizeAnalyzer(large_file_threshold_mb=5))

# Tam analiz
analysis = doctor.diagnose(Path("/proje"))

# Hızlı tarama
scan = doctor.quick_scan(Path("/proje"))

# Analizörleri listele
analyzers = doctor.get_registered_analyzers()
```

---

## 🧪 Geliştirme

### Yeni Analizör Ekleme

```python
# 1. Yeni analizör sınıfı oluşturun
from src.core.base_analyzer import BaseAnalyzer
from src.models.analysis_models import AnalysisResult, Severity

class MyCustomAnalyzer(BaseAnalyzer):
    @property
    def name(self) -> str:
        return "Özel Analizör"
    
    @property
    def category(self) -> str:
        return "custom"
    
    def analyze(self, project_path: Path) -> List[AnalysisResult]:
        results = []
        # Analiz mantığınızı buraya yazın
        return results

# 2. Doktor'a kaydedin
doctor.register_analyzer(MyCustomAnalyzer(priority=25))
```

### Test Çalıştırma

```bash
# Tüm testler
python -m pytest tests/ -v

# Belirli bir test
python -m pytest tests/unit/test_phase3.py -v

# Coverage raporu
python -m pytest tests/ --cov=src --cov-report=html
```

---

## 📦 Build ve Dağıtım

### Exe Oluşturma

```bash
# Windows
python build_exe.py

# veya hazır script ile
build_exe.bat
```

**Çıktı:** `dist/GitCleanArchiverPro.exe`

### PyInstaller Parametreleri

Uygulamanın sorunsuz, taşınabilir ve güvenilir bir biçimde derlenmesi için aşağıdaki parametreler kullanılmaktadır:

| Parametre | Açıklama |
|-----------|----------|
| `--onefile` | Tüm uygulamayı tek bir bağımsız `.exe` dosyası haline getirir |
| `--windowed` | Arka planda konsol penceresinin açılmasını engeller |
| `--icon=...` | Uygulama exe'sine ve görev çubuğuna özel `app_icon.ico` ikonunu gömer |
| `--noupx` | UPX sıkıştırmasını devre dışı bırakarak yanlış pozitif virüs algılamalarını önler |
| `--version-file=...` | Telif hakkı ve sürüm (.exe içine) ekleyerek anti-virüs güvenilirliğini artırır |
| `--add-data=...` | Stil, ikon ve diğer gerekli kaynak klasörlerini derlenmiş dosyaya dâhil eder |

---

## ❓ Sık Sorulan Sorular

### S: Hangi dosyalar temizlenir?
**C:** Varsayılan olarak:
- Python: `__pycache__`, `*.pyc`, `*.pyo`
- Genel: `*.log`, `*.tmp`, `*.bak`
- IDE: `.idea/`, `.vscode/`, `.vs/`

### S: Temizlik geri alınabilir mi?
**C:** Hayır, bu yüzden önce **yedek almanız** önerilir. Önizleme modu ile silinecekleri görebilirsiniz.

### S: .gitignore nasıl kullanılır?
**C:** Proje kök dizinindeki `.gitignore` dosyası otomatik olarak okunur ve zip/kopyalama işlemlerinde bu kurallar uygulanır.

### S: Sağlık skoru nasıl hesaplanır?
**C:** 6 kategoride, bulguların şiddetine göre hesaplanan ağırlıklı ortalama ile. Detaylar için [Sağlık Skorlama Sistemi](#-sağlık-skorlama-sistemi) bölümüne bakın.

---

## 🤝 Katkıda Bulunma

1. Fork'layın
2. Feature branch oluşturun (`git checkout -b feature/amazing`)
3. Değişikliklerinizi commit edin (`git commit -m 'Harika özellik eklendi'`)
4. Branch'inizi push edin (`git push origin feature/amazing`)
5. Pull Request oluşturun

---

