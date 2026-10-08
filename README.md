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
│   │   ├── base_analyzer.py      #    Temel analizör sınıfı
│   │   ├── project_index.py      #    Tek geçişli dosya indeksi (tüm analizörler bunu kullanır)
│   │   ├── registry.py           #    Analizör kayıt defteri ve otomatik keşif
│   │   └── constants.py          #    Ortak sabitler (EXCLUDED_DIRS)
│   │
│   ├── models/                   # 📊 Veri modelleri (FAZ 1)
│   │   └── analysis_models.py    #    Dataclass'lar ve Enum'lar
│   │
│   ├── analyzers/                # 🔍 Analiz motorları (FAZ 2)
│   │   ├── size_analyzer.py      #    Boyut analizi
│   │   ├── type_analyzer.py      #    Dosya türü analizi
│   │   ├── duplicate_finder.py   #    Çift dosya bulucu
│   │   ├── empty_folder_finder.py#    Boş klasör bulucu
│   │   ├── structure_analyzer.py #    Yapı analizi
│   │   ├── security_analyzer.py  #    Güvenlik sızıntısı analizi
│   │   ├── dead_weight_analyzer.py#   Kullanılmayan bağımlılıklar
│   │   ├── code_complexity_analyzer.py # Karmaşıklık / God Object (tüm diller)
│   │   └── language_stats_analyzer.py  # Dil başına dosya / satır dağılımı
│   │
│   ├── languages/                # 🌐 Çok dilli kaynak kod çözümleme
│   │   ├── base.py               #    FunctionInfo / ClassInfo / SourceMetrics
│   │   ├── python_lang.py        #    Python (ast, kesin sonuç)
│   │   ├── brace.py              #    C ailesi, Java, C#, JS/TS, Go, Rust (sözcük tabanlı, yaklaşık)
│   │   ├── catalog.py            #    Dil tanımları (yeni dil = bir LanguageSpec)
│   │   ├── registry.py           #    parse_file: önbellekli, üretilmiş/küçültülmüş dosyaları atlar
│   │   └── ecosystems.py         #    requirements.txt, package.json, go.mod, Cargo.toml
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
│   └── profiles/                 #    Arşiv profilleri (JSON, gitignore sözdizimi)
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

#### `project_index.py`
Proje klasörü bir kez taranır; tüm analizörler `analyze(index)` ile bu indeksi kullanır:
- Dosya ve klasör listesi (`index.files`, `index.dirs`), toplam boyut, uzantı dağılımı, en büyük derinlik
- Dışlanan klasörler (`EXCLUDED_DIRS`: `.git`, `venv`, `node_modules`, `dist`, `build` ...) hiç taranmaz
- `read_text(entry)`: UTF-8 (BOM'lu), cp1254 ve latin-1 dener; ikilik veya 2 MB'tan büyük dosyada `None` döner; içerik önbelleğe alınır
- `hash_file(entry, partial=False)`: parçalı okuma ile özet

#### `registry.py`
`@register_analyzer` dekoratörü ile işaretlenen analizörler `src/analyzers/` altından otomatik bulunur (`load_builtin_analyzers()`).

#### `base_analyzer.py`
Analizörler için temel sınıf: standart sonuç oluşturma (`_create_result`), `name`, `category`, öncelik.

### Dil Desteği

| Dil | Uzantılar | Çözümleme | Bağımlılık manifesti |
|-----|-----------|-----------|----------------------|
| Python | `.py` | `ast` (kesin) | `requirements.txt` |
| JavaScript | `.js .jsx .mjs .cjs` | sözcük tabanlı (yaklaşık) | `package.json` |
| TypeScript | `.ts .tsx .mts .cts` | sözcük tabanlı (yaklaşık) | `package.json` |
| Java | `.java` | sözcük tabanlı (yaklaşık) | yok |
| C# | `.cs` | sözcük tabanlı (yaklaşık) | yok |
| C | `.c .h` | sözcük tabanlı (yaklaşık) | yok |
| C++ | `.cpp .cc .cxx .hpp .hh .hxx` (`.h` içinde C++ işareti varsa) | sözcük tabanlı (yaklaşık) | yok |
| Go | `.go` | sözcük tabanlı (yaklaşık) | `go.mod` |
| Rust | `.rs` | sözcük tabanlı (yaklaşık) | `Cargo.toml` |

Her dosya için satır dağılımı (kod/yorum/boş), fonksiyon ve sınıf listesi, siklomatik karmaşıklık ve içe aktarmalar çıkarılır.
Python dışındaki diller gerçek ayrıştırıcıyla değil, yorum/string temizleme + süslü parantez eşleme ile çözümlenir; sonuçlar **yaklaşıktır** ve bulgularda `approximate=True` işaretlenir.
Bilinen sınırlar: fonksiyon benzeri makrolar (`FOREACH(x) {`), template literal içinde iç içe `${ }`, Rust iç içe blok yorumları, ifade gövdeli (süslü parantezsiz) üyeler.
Küçültülmüş / paketlenmiş (`.min.js`, webpack parçaları) ve üretilmiş dosyalar (`*.g.cs`, `*.pb.go`, `*_pb2.py`) ölçüme girmez.
Derleme çıktıları ve sanal ortamlar taranmaz: `node_modules`, `dist`, `build`, `.next`, `coverage`, `venv` ve `pyvenv.cfg` içeren her klasör; ayrıca yanında `Cargo.toml`/`pom.xml` varsa `target`, yanında `.csproj` varsa `bin`/`obj`.

Kullanılmayan bağımlılık tespiti manifestin klasörü ve alt klasörlerindeki kaynaklara bakar (monorepo uyumlu). `devDependencies`, `@types/*`, Go `// indirect` ve Python araç paketleri (pytest, pyinstaller, black ...) raporlanmaz. Maven/NuGet desteklenmez: paket adı ile namespace arasında güvenilir eşleme olmadığından yanlış pozitif üretirdi.

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

# Tam analiz (isteğe bağlı ilerleme: progress(yüzde, metin))
analysis = doctor.diagnose(Path("/proje"))

# Hızlı tarama
scan = doctor.quick_scan(Path("/proje"))

# Analizörleri listele
analyzers = doctor.get_registered_analyzers()
```

---

## 🧪 Geliştirme

### Yeni Analizör Ekleme

`src/analyzers/` altına tek bir dosya eklemek yeterlidir; UI veya başka bir dosyada değişiklik gerekmez.

```python
# src/analyzers/my_custom_analyzer.py
from typing import List
from src.core.base_analyzer import BaseAnalyzer
from src.core.project_index import ProjectIndex
from src.core.registry import register_analyzer
from src.models.analysis_models import AnalysisResult, Severity

@register_analyzer
class MyCustomAnalyzer(BaseAnalyzer):
    def __init__(self, priority: int = 25):
        super().__init__(priority)

    @property
    def name(self) -> str:
        return "Özel Analizör"

    @property
    def category(self) -> str:
        # Puanlanan kategoriler: security, complexity, duplicate, size, structure, dependency
        return "custom"

    def analyze(self, index: ProjectIndex) -> List[AnalysisResult]:
        results = []
        for entry in index.files_with_ext('.py'):
            text = index.read_text(entry)   # None: ikilik veya çok büyük
            # Analiz mantığınızı buraya yazın
        return results
```

Başka bir sınıf adıyla çakışma `ValueError` verir. Bir analizörü kapatmak için `ProjectService(disabled_analyzers=["MyCustomAnalyzer"])`.
Not: yeni bir kategori puanlanmaz; puanlanması için `HealthChecker.WEIGHTS` güncellenmelidir.

### `.gitignore` ve Git Duyarlılığı

Analiz ve arşivleme projenin `.gitignore` kurallarını **git ile aynı öncelikle** uygular: kökteki ve alt klasörlerdeki tüm `.gitignore` dosyaları, `.git/info/exclude`, `!` ile geri alma, ignore'lu klasörün içine girilmeyişi. Git deposunda `git ls-files` ile **izlenen** dosyalar (kendi adını içeren `.gitignore`, `git add -f` ile eklenenler) kurala uysa bile dahil edilir.

- Analizde ignore'lu dosyalar (derleme çıktısı, yerel veri, `*.log`) boyut, dil istatistiği, karmaşıklık, çift dosya ve bağımlılık sayılarına girmez. `quick_scan` çıktısında `gitignore_applied` ve `ignored_by_gitignore` (`files`/`dirs`; budanan klasörün içi sayılmaz) görünür. Kapatmak için `ProjectService(respect_gitignore=False)`.
- `git` kurulu değilse ya da klasör bir depo değilse yalnızca `.gitignore` kuralları uygulanır.
- Güvenlik: `.gitignore`'daki izlenmeyen `.env` doğru uygulamadır ve bulgu üretmez. `.gitignore`'a eklenmemiş `.env` / `credentials.json` / `secrets.yaml` "commit edilme riski"; **git'e commit edilmiş** olanlar (sonradan `.gitignore`'a eklenmiş olsa bile) KRİTİK "commit edilmiş" bulgusudur: `.gitignore` izlenen dosyayı geçmişten silmez (`git rm --cached` + sırları değiştirin).
- Okunamayan bir `.gitignore` arşivlemeyi reddeder (gizli dosya sızıntısı önlemi); analiz ignore'suz sürer ve hata `index.errors`'a yazılır.
- `CleanupService` bilerek `.gitignore`'a bakmaz: temizlediği önbellek ve geçici dosyalar zaten ignore'ludur.

### Arşiv Profilleri

Arşivlemede hangi dosyaların elendiği **profil** dosyalarıyla belirlenir: paketli `resources/profiles/*.json` ve kullanıcının `~/.gitclean/profiles/*.json` dosyaları (aynı adlı kullanıcı profili paketliyi geçersiz kılar, yeni adlar eklenir). Dosya adı sırası listeleme sırasıdır; bozuk dosya atlanır ve loglanır.

```json
{
  "name": "Benim Profilim",
  "description": "Kısa açıklama",
  "extends": "Müşteri Teslimi (Temiz)",
  "exclude": ["*.bak", "/scripts/", "!tests/keep.py"]
}
```

Desenler **gitignore sözdizimidir**: `tests/` her derinlikte klasör, `/README*` yalnızca kökte, `*.test.*` her derinlikte dosya, `!` ile istisna. `extends` ile başka profilin desenleri devralınır.

| Profil | Eler |
|--------|------|
| Geliştirici (Standart) | yalnızca `.gitignore` kuralları |
| Müşteri Teslimi (Temiz) | her derinlikte `tests/ test/ __tests__/ benchmarks/` ve test dosyaları (`test_*.py`, `*_test.py`, `conftest.py`, `*.test.*`, `*.spec.*`), kökte `/docs/ /doc/ /.github/`, her derinlikte `.env*` |
| Yayınlama / Dağıtım (Minimal) | Temiz'in hepsi + kökte `README*`, `LICENSE*`, `CONTRIBUTING*`, `pytest.ini`, `tox.ini`, `requirements-dev.txt`, `.gitattributes` |

Her profilde ayrıca analizle aynı klasör dışlaması geçerlidir: `venv`, `.venv`, `node_modules`, `dist`, `build`, `.next`, `coverage` ..., yanında `Cargo.toml`/`pom.xml` olan `target`, yanında `.csproj` olan `bin`/`obj` ve `pyvenv.cfg` içeren her sanal ortam. Bilinmeyen profil adı hata verir (sessizce "hiçbir şeyi eleme" olmaz).

### Loglama ve Hata Yönetimi

`main.py` açılışta `setup_logging()` çağırır. Loglar `~/.gitclean/logs/gitclean.log` dosyasına yazılır (1 MB × 3 dönen dosya). Seviye `GITCLEAN_LOG_LEVEL` ortam değişkeniyle ayarlanır (varsayılan `INFO`; `DEBUG` okunamayan dosya ayrıntılarını da yazar). Konsolsuz (windowed) exe'de yakalanmayan istisnaların traceback'i de bu dosyaya düşer.

- Arşiv, kopya ve yedek işlemleri tek dosya hatasında durmaz: sonuç sözlüğünde `failed_files` (yol, hata) dolar, `complete` `False` olur, `success` yine `True` kalır. Ölümcül hatada (disk dolu vb.) yarım çıktı silinir, `success=False` ve `error` döner.
- `.gitignore` okunamıyorsa arşiv/kopya **reddedilir** (gizli dosyaların sızmaması için); analiz etkilenmez.
- Analize girmeyen dosyalar sessiz kalmaz: `quick_scan` çıktısındaki `skipped_files` neden başına sayı verir (`too_large`: 2 MB üstü, `unreadable`, `parse_error`, `minified`, `unreadable_dir`). Çöken analizör `failed_analyzers` listesine yazılır ve skordan çıkarılır.
- Proje seçilmeden işlem istenirse `ProjectNotSelectedError` (`ValueError` alt sınıfı) fırlatılır.

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

