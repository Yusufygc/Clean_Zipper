# 🚀 GitClean Archiver

> **Profesyonel Proje Yönetim, Analiz ve Optimizasyon Aracı**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![CI](https://github.com/Yusufygc/Clean_Zipper/actions/workflows/ci.yml/badge.svg)](https://github.com/Yusufygc/Clean_Zipper/actions/workflows/ci.yml)
[![Version](https://img.shields.io/badge/Version-2.1.0-orange.svg)]()
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)]()

---

## 📋 İçindekiler

- [Genel Bakış](#-genel-bakış)
- [Özellikler](#-özellikler)
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

**GitClean Archiver**, yazılım projelerinizi analiz eden, gereksiz dosyaları tespit eden, `.gitignore` kurallarına uygun arşivleme yapan ve proje sağlığınızı puanlayan kapsamlı bir proje yönetim aracıdır.

### 🎪 Kullanım Senaryoları

| Senaryo | Açıklama |
|---------|----------|
| 📦 **Dağıtım Öncesi Hazırlık** | Projenizi paylaşmadan önce gereksiz dosyalardan arındırın |
| 🔍 **Kod Teslimi** | Müşteriye sadece gerekli dosyaları içeren temiz bir paket sunun |
| 💾 **Yedekleme** | Yeniden üretilebilir klasörleri (venv, node_modules ...) atlayıp geri getirilemeyen dosyaları (.env, veritabanı, model) korur |
| 🧹 **Bakım** | Düzenli proje temizliği ile disk alanını optimize edin |
| 📊 **Analiz** | Projenizin sağlık durumunu düzenli olarak takip edin |
| 🔒 **Güvenlik** | Hassas dosyaların yanlışlıkla paylaşılmasını önleyin |

---

## ✨ Özellikler

### 🏥 Proje Doktoru
- **11 kategoride bulgu tabanlı sağlık analizi** (Güvenlik, Karmaşıklık, Çiftler, Boyut, Yapı, Bağımlılık, Ölü kod, Mimari, Güvenilirlik, Test, Hijyen)
- **A+ 'dan F' e kadar notlandırma** sistemi
- **Kritik sorunların otomatik tespiti**
- **İyileştirme önerileri** (kural başına, şiddete göre en önemli 5) ve tahmini kazanç hesaplama

### 📦 Akıllı Arşivleme
- `.gitignore` kurallarına **tam uyumlu** zip oluşturma
- **Temiz dizin kopyası** oluşturma
- **Arşiv profilleri** (Geliştirici / Müşteri Teslimi / Yayınlama; kendi profilinizi JSON ile ekleyebilirsiniz)
- **Proje dışına taşmaz:** sembolik bağ ve junction klasörlere girilmez, dosya bağlarının hedefi arşive konmaz

### 🧹 Otomatik Temizlik
- **Kategorilere göre** temizlik: Python önbelleği ve geçici dosyalar (varsayılan açık), log ve `.bak` dosyaları (varsayılan kapalı: kullanıcı verisi içerebilir)
- **Önizleme modu** ile silinecekleri görme
- **Kalıcı silme yok:** her şey Geri Dönüşüm Kutusu'na taşınır
- **Güvenli sınır:** sanal ortam, `node_modules`, derleme çıktıları, bağ / junction klasörler ve proje dışı yollar asla temizlenmez

### 💾 Versiyonlu Yedekleme
- **Otomatik isimlendirme** (proje_adı_tarih_saat)
- **Zip formatında** sıkıştırılmış yedek
- **Felaket kurtarma odaklı dışlama:** `.git`, `venv`/`.venv` (ve `pyvenv.cfg` içeren her klasör), `node_modules`, `__pycache__`, `dist`, `build`, araç önbellekleri ve derleme çıktıları (`.next`, `target` + `Cargo.toml` gibi) yedeğe girmez. **`.gitignore` uygulanmaz**: `.env`, yerel veritabanları, model ve veri dosyaları genellikle ignore'dadır ve git'ten geri getirilemez, bu yüzden yedekte kalır (arşiv ise paylaşım içindir ve `.gitignore`'u uygular). Fark gerçek projelerde büyüktür: 30 depoda `.git` dışında her şey 36,1 GB, bu kural 3,8 GB, `.gitignore` de uygulansaydı 69 MB olurdu ve yaklaşık 0,9 GB veritabanı, 11 `.env` dosyası kaybolurdu.
- **Sessiz dışlama yok:** sonuçta `excluded_dirs` (proje köküne göre, en çok 100) ve `excluded_dir_count` döner. Yedek klasörü proje içindeyse zip kendini içermez.
- **Yedek listesi** görüntüleme
- **Eski yedekleri temizleme:** proje başına en yeni 5 otomatik yedek saklanır (arşiv sayfasında "Saklanan yedek", 0 = sınırsız); fazlası Geri Dönüşüm Kutusu'na taşınır. Elle adlandırılmış yedeklere dokunulmaz.

### 📊 Görsel Dashboard
- **Dairesel sağlık skoru** göstergesi
- **İstatistik kartları** (dosya sayısı, boyut, klasör, sorunlar)
- **Dosya türü ve dil dağılımı**
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
| `CodeComplexityAnalyzer` | complexity | V2 eşikleri: karmaşıklık, uzunluk, derinlik, parametre, God Object |
| `DeadCodeAnalyzer` | deadcode | Kullanılmayan import, ulaşılamaz kod, kullanılmayan yerel değişken |
| `MagicNumberAnalyzer` | deadcode | Fonksiyon gövdelerindeki adsız sayısal sabitler |
| `CloneAnalyzer` | duplicate | Kopyala-yapıştır kod blokları (dosyalar arası ve dosya içi) |
| `ArchitectureAnalyzer` | architecture | Dosya bağımlılık grafiği: döngüsel bağımlılık, en çok kullanılan dosyalar |
| `CodeSecurityAnalyzer` | security | SAST-lite: 39 kuralla tehlikeli API ve kalıp taraması (CWE etiketli) |
| `ReliabilityAnalyzer` | reliability | Yutulan hatalar, kodlamasız dosya açma, saat dilimsiz tarih, DEBUG, konsol çıktısı, TODO envanteri |
| `TestingAnalyzer` | testing | Test yok, düşük test/kaynak oranı, testi olmayan modüller, kararsız test işaretleri |
| `ProjectHygieneAnalyzer` | hygiene | README, LICENSE, .gitignore, CI, kilit dosyası, .env.example kontrol listesi |
| `GitHistoryAnalyzer` | git (+ security) | Geçmişte commit edilmiş sır dosyaları, sık değişen karmaşık dosyalar, birlikte değişen dosyalar |

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
│   │   ├── brace_headers.py      #    `{` öncesi başlık sınıflama (sınıf / fonksiyon / kontrol bloğu, parametre sayısı)
│   │   ├── catalog.py            #    Dil tanımları (yeni dil = bir LanguageSpec)
│   │   ├── registry.py           #    parse_file: önbellekli, üretilmiş/küçültülmüş dosyaları atlar
│   │   └── ecosystems.py         #    requirements.txt, pyproject.toml, package.json, go.mod, Cargo.toml
│   │
│   ├── doctors/                  # 🏥 Proje doktoru (FAZ 3)
│   │   ├── project_doctor.py     #    Ana doktor koordinatörü
│   │   ├── health_checker.py     #    Sağlık skoru hesaplama
│   │
│   ├── services/                 # ⚙️ İş servisleri (FAZ 5)
│   │   ├── archive_service.py    #    Arşivleme (zip/kopyalama)
│   │   ├── cleanup_service.py    #    Temizlik servisi
│   │   ├── backup_service.py     #    Yedekleme servisi
│   │   ├── report_service.py     #    HTML raporu (kategori puanları dahil)
│   │   ├── audit_report_service.py # V2 formatında Markdown denetim raporu
│   │   ├── audit_catalog.py      #    Rapor sabitleri: etiket, efor, etki tabloları
│   │   ├── audit_evidence.py     #    Bulgu konumu ve kanıt (kod parçası)
│   │   ├── recommendation_engine.py # Dashboard önerileri (kural başına, şiddete göre)
│   │   └── project_service.py    #    Ana servis (Facade)
│   │
│   ├── qml_ui/                   # 🎨 Kullanıcı arayüzü (QML)
│   │   ├── app.py                #    Uygulama kurulumu, ViewModel bağlantıları, kapanış sırası
│   │   ├── viewmodels/           #    QML köprüleri (QThread worker'ları ProjectService'i çağırır)
│   │   ├── qml/                  #    MainView.qml, views/, components/, singletons/ (tema, metinler)
│   │   └── resources/icons/      #    Arayüz simgeleri (SVG)
│   │
│   └── utils/                    # 🛠️ Yardımcı araçlar
│       └── gitignore_parser.py   #    .gitignore parser
│
├── docs/wiki/                    # 📚 Proje wiki'si (kurallar, kararlar, analizör kataloğu, backend arayüzü)
│
├── tests/                        # 🧪 Testler (790+)
│   ├── unit/                     #    Birim testleri
│   ├── integration/              #    Entegrasyon testleri
│   └── fixtures/                 #    Test verileri
│
├── resources/                    # 📦 Kaynaklar
│   ├── icons/                    #    Uygulama ikonu (app.svg kaynak, app.png, app_icon.ico)
│   ├── templates/                #    Rapor şablonları
│   └── profiles/                 #    Arşiv profilleri (JSON, gitignore sözdizimi)
│
├── main.py                       # 🚀 Ana giriş noktası (QML arayüzü)
├── build_exe.py                  # 🔨 Build script'i
├── build_installer.py            # 📦 EXE (onedir) + Inno Setup sihirbazı; bu makinede dener, engellenirse yeniden derler (dist/installer)
├── build_verify.py               # ✅ Derleme sonrası deneme: exe açılıyor mu, kurulum dosyası sessizce kurulup kaldırılıyor mu
├── packaging/                    # 📦 Inno Setup betiği (GitCleanArchiver.iss) ve sihirbaz görselleri
├── tools/release.py              # 🏷️ Sürüm yükseltme + etiket (tag) aracı
├── build_icons.py                # 🎨 Uygulama ikonunu vektörden (app.svg) üretir: app.png + çok boyutlu app_icon.ico
├── requirements.txt              # 📋 Çalışma zamanı bağımlılıkları (tam sabit sürümler)
├── requirements-dev.txt          # 🧪 + test ve lint (pytest, ruff)
├── ruff.toml                     # 🧹 Lint ayarı (yalnızca kesin hatalar)
├── .github/workflows/ci.yml      # 🤖 CI: Windows'ta ruff, pytest, pip-audit
├── .github/workflows/release.yml # 🚀 vX.Y.Z etiketinde: test, kurulum dosyası, GitHub Release
├── requirements-build.txt        # 🔨 + EXE derleme (pyinstaller)
├── .gitattributes / .editorconfig # ↩️ Satır sonu (LF) ve kodlama (UTF-8) politikası
└── README.md                     # 📖 Bu doküman
```

### Veri Akış Diyagramı

```
Kullanıcı → QML arayüzü (MainView.qml + ViewModel'ler)
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

- **Python** 3.10 veya üstü
- **pip** (Python paket yöneticisi)
- **İşletim Sistemi**: Windows 10/11 (CI ve elle test bu platformda yapılır; Linux ve macOS doğrulanmadı, bağ / junction denetimi Windows'a özgü ayrıntılar içerir)

### Adım Adım Kurulum

```bash
# 1. Projeyi klonlayın veya indirin
git clone https://github.com/Yusufygc/Clean_Zipper.git
cd Clean_Zipper

# 2. Sanal ortam oluşturun
python -m venv venv

# 3. Sanal ortamı aktifleştirin
# Windows:
venv\Scripts\activate
# Linux/Mac (doğrulanmadı):
source venv/bin/activate

# 4. Bağımlılıkları yükleyin
pip install -r requirements.txt          # yalnızca çalıştırmak için
pip install -r requirements-dev.txt      # + testler ve lint (python -m pytest, python -m ruff check .)
pip install -r requirements-build.txt    # + EXE derleme (python build_exe.py)

# 5. Uygulamayı başlatın
python main.py
```

### Kurulum Sihirbazı (önerilen, Windows)

[Releases](https://github.com/Yusufygc/Clean_Zipper/releases) sayfasından `GitCleanArchiver-Setup-X.Y.Z.exe` dosyasını indirip çalıştırın. Yönetici hakkı gerekmez (varsayılan: kullanıcıya özel kurulum); Başlat menüsü kısayolu, isteğe bağlı masaüstü kısayolu ve kaldırıcı eklenir. Yeni sürümün üstüne kurulum eski sürümü günceller; ayarlarınız (`~/.gitclean`) korunur. Dosyanın yanındaki `.sha256` ile özetini doğrulayabilirsiniz. Kurulum dosyası imzasızdır: SmartScreen uyarısında **Ek bilgi → Yine de çalıştır**. Windows 11 **Akıllı Uygulama Denetimi** imzasız dosyaları dosya başına rastgele engelleyebilir ("Uygulama Denetimi ilkesi bu dosyayı engelledi"); nedenleri, teşhisi ve alınacak önlemler: [`docs/wiki/windows-exe-dagitim.md`](docs/wiki/windows-exe-dagitim.md).

Uygulama açılışta GitHub'a yalnızca "en son sürüm nedir" diye sorar; daha yeni bir sürüm varsa sürüm notlarıyla bir pencere açar (**İndir** kurulum dosyasını tarayıcıda açar, **Sonra**, **Bu Sürümü Atla**). Hiçbir şey kendiliğinden indirilip çalıştırılmaz, proje ya da kişisel veri gönderilmez. Kapatmak için **Ayarlar → Güncellemeler** ya da ortam değişkeni `GITCLEAN_NO_UPDATE_CHECK=1`.

### Tek Komutla Kurulum (Windows)

```batch
python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt && python main.py
```

---

## 📖 Kullanım Kılavuzu

### 1. Proje Açma

1. Uygulamayı başlatın (`python main.py` ya da `GitCleanArchiver.exe`)
2. Sağ üstteki **Proje Dizini Aç** düğmesine tıklayın
3. Analiz etmek istediğiniz proje dizinini seçin
4. Gösterge Paneli ve Sorunlar sayfası otomatik olarak tek bir teşhisle dolar

### 2. Dashboard Kullanımı

- **Sağlık Skoru**: Projenizin genel durumunu gösterir (A+ en iyi, F en kötü)
- **İstatistik Kartları**: Dosya sayısı, boyut, klasör sayısı, sorun sayısı
- **Dosya Türü ve Dil Dağılımı**: Dosya türleri ve dillere göre satır dağılımı
- **Öneriler**: En önemli 5 iyileştirme önerisi

### 3. Arşivleme İşlemleri

**Zip Oluşturma:**
1. **Arşivleme ve Dağıtım** sekmesine geçin, **Zip Arşivi** modunu seçin
2. **Sıkıştırma & Temizleme Profili**'ni seçin
3. **Zip Konumu Seç ve Arşivle** ile çıktı dosyasını belirleyin

**Temiz Kopya Oluşturma:**
1. Aynı sekmede **Temiz Kopya** modunu seçin
2. **Hedef Klasör Seç ve Kopyala** ile `.gitignore` ve profil kurallarına uygun temiz bir kopya oluşturun (hedef kaynağın kendisi ya da üst klasörü olamaz)

**Yedek:** **Proje Yedeği** modunda **Hızlı Yedek Al**; proje başına saklanan yedek sayısı aynı kartta ayarlanır.

### 4. Temizlik İşlemleri

1. **Proje Temizliği** sekmesine geçin ve kategorileri seçin
2. **Önizleme (Tara)** ile taşınacak dosyaları görün
3. **Temizliği Başlat** ile dosyaları Geri Dönüşüm Kutusu'na taşıyın (aynı anda yalnızca bir temizlik / arşiv / yedek işlemi çalışır)

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
| **Güvenlik** | %20 | Sızan anahtar/şifre, `.env`, commit edilmiş hassas dosya |
| **Karmaşıklık** | %16 | V2 eşikleri: karmaşıklık, uzunluk, derinlik, parametre, God Object, dosya boyutu |
| **Çiftler** | %10 | Tekrarlayan dosya grupları ve kod klonları |
| **Boyut** | %8 | Toplam proje boyutu, büyük dosyalar |
| **Yapı** | %8 | Boş klasörler, klasör derinliği |
| **Bağımlılık** | %8 | Kullanılmayan kütüphaneler, eksik `requirements.txt` |
| **Ölü Kod** | %6 | Kullanılmayan import / değişken, ulaşılamaz kod, sihirli sayı |
| **Mimari** | %6 | Döngüsel bağımlılıklar |
| **Güvenilirlik** | %8 | Yutulan hatalar, kodlamasız dosya açma, DEBUG, konsol çıktısı |
| **Test** | %6 | Test yok, düşük test oranı, kararsız test işaretleri |
| **Hijyen** | %4 | README, LICENSE, .gitignore, CI, kilit dosyası, .env.example |

Ağırlıklar çalışan analizörlerin kategorilerine göre yeniden normalize edilir; çalışmayan veya hata veren analizörün kategorisi hesaba katılmaz. Dosya türü dağılımı ve `git` kategorisi (sıcak nokta, birlikte değişim) bilgi amaçlıdır, puanlanmaz.

**Hesaplama:** her bulgunun şiddeti ceza puanı getirir (KRİTİK 40, YÜKSEK 15, ORTA 5, DÜŞÜK 1, BİLGİ 0). Kategori skoru `100 × e^(−ceza/60)` formülüyle bulunur. Genel skor, kategori skorlarının ağırlıklı ortalamasıdır. Hiçbir analizör çalışmazsa skor 0 olur.

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
| Python | `.py` | `ast` (kesin) | `requirements.txt`, `pyproject.toml` |
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
result = service.copy_project(Path("/proje"), Path("/temiz_kopya"))   # hedef kaynağın kendisi / üst klasörü olamaz
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

# Analiz et (yeniden tarar; diagnose() son teşhisi önbellekten verir)
analysis = service.analyze_project()
# Dönen değer: {
#     'health_score': float,
#     'health_status': str,
#     'total_files': int,
#     'total_size_mb': float,
#     'issues_count': int,
#     'top_recommendations': list,   # (başlık, açıklama, 'KRİTİK' | 'YÜKSEK' | 'ORTA'), en çok 5
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

### Kalite Eşikleri (V2)

`QualityThresholds` (`src/core/thresholds.py`) V2 denetim şablonunun ölçüm eşiklerini taşır; bir değer eşiği **aşarsa** (`>`) bulgu üretilir, eşiğin 2 katı ve üstü bir seviye yukarı raporlanır. `ProjectService(thresholds=QualityThresholds(parameters=7))` ile geçersiz kılınır.

| Metrik | Eşik | Öncelik |
|--------|------|---------|
| Siklomatik karmaşıklık | > 10 | ORTA |
| Bilişsel karmaşıklık | > 15 | ORTA |
| İç içe blok derinliği | > 4 | ORTA |
| Fonksiyon uzunluğu | > 50 satır | DÜŞÜK |
| Parametre sayısı | > 5 | DÜŞÜK |
| Sınıf uzunluğu / sınıf metodu | > 300 satır / > 20 metot | YÜKSEK (God Object) |
| Dosya uzunluğu | > 500 satır | ORTA |
| Dosya başına benzersiz import | > 25 | DÜŞÜK |

Bir fonksiyon birden çok eşiği aşarsa **tek** bulgu üretilir (aşılan metrikler birlikte listelenir). Python metrikleri `ast` ile kesindir: siklomatik karmaşıklık `radon` kurallarıyla, bilişsel karmaşıklık SonarSource kurallarıyla hesaplanır (gerçek kodda `radon` ile %100, `cognitive_complexity` paketiyle %99 uyum doğrulandı). Diğer dillerde parametre sayısı, iç içe derinlik ve bilişsel karmaşıklık sözcük tabanlı çözümlemeyle **yaklaşık** hesaplanır; süslü parantezsiz tek satırlık `if` gibi yapılar iç içe sayılamaz.

### Ölü Kod, Sihirli Sayı ve Kod Klonu

| Kural | Kapsam | Doğruluk | Öncelik |
|-------|--------|----------|---------|
| `unused-import` | Python (`ast`), JS/TS, Java | Python kesin; JS/TS/Java yaklaşık | DÜŞÜK (dosya başına tek bulgu) |
| `unreachable-code` | Python; C, C++, Java, C#, JS, TS | Python kesin (ORTA); diğerleri yaklaşık (DÜŞÜK) | ORTA / DÜŞÜK |
| `unused-variable` | yalnızca Python | kesin | DÜŞÜK (fonksiyon başına tek bulgu) |
| `magic-numbers` | 9 dil | Python kesin, diğerleri yaklaşık | DÜŞÜK (dosya başına tek bulgu, eşik > 10) |
| `code-clone` | `CloneAnalyzer`: 9 dil | birebir eşleşme (Tip-1) | DÜŞÜK; ≥ 20 satır ORTA |

- **Kullanılmayan import:** Ad tabanlıdır. Aynı adlı bir yerel değişken/parametre kullanım sayılır; bu yüzden `pyflakes`'tan daha tutucudur. `__init__.py`, `from __future__`, `*`, `import x as x`, `__all__` içindekiler ve `# noqa` / `# noqa: F401` satırları atlanır. Go ve Rust derleyici zaten reddettiği için, C# ve C/C++ içe aktarmaları kullanım ile eşlenemediği için kapsam dışıdır.
- **Ulaşılamaz kod:** `return/raise/break/continue` sonrası aynı blokta kalan ifade. Brace dillerinde süslü parantezsiz `if (x) return;`, `#if/#else` dalları, JS `function` bildirimleri ve JSX metni yanlış pozitif üretmez.
- **Sihirli sayı:** `{0, 1, 2, -1, 0.5}`, adlandırılmış atamalar (`retries = 3`, `const`), adlı argümanlar, indeksler ve sabit veri tabloları sayılmaz. Test dosyaları atlanır. Eşik `QualityThresholds.magic_numbers`.
- **Kod klonu:** En az `clone_lines` (varsayılan 8) ardışık anlamlı satır; yorum ve boşluk farkı yok sayılır, string ve sayı değerleri birebir aynı olmalıdır. Tamamen aynı dosyalar `DuplicateFinder`'a bırakılır. En büyük 50 grup ayrı bulgu, ayrıca tek bir özet bulgusu (tekrarlanan satır oranı) üretilir.

### Mimari: Döngüsel Bağımlılık

`ArchitectureAnalyzer` her dil ailesi (Python, JS/TS) için dosya düzeyinde bir içe aktarma grafiği kurar ve Tarjan algoritmasıyla (yinelemeli, derin zincirlerde güvenli) döngüleri bulur.

| Kural | Açıklama | Öncelik |
|-------|----------|---------|
| `import-cycle` | Birbirini doğrudan/dolaylı içe aktaran ≥ 2 dosya; en kısa döngü yolu gösterilir | ORTA; ≥ 4 dosyalık döngü YÜKSEK |
| `dependency-graph` | Dosya/kenar/döngü sayısı, en çok kullanılan ve en çok bağımlılığı olan 5 dosya | BİLGİ |

- **Python:** mutlak ve göreli importlar proje dosyalarına çözülür (`from . import x` alt modülü, `from p import Name` paketi bağlar). Kaynak kökü, içe aktaranın klasörü veya atası olmalıdır (`sys.path[0]` anlambilimi). Standart kütüphane adlarını gölgeleyen iç içe dosyalar çözülmez. Yalnızca modül yüklenirken çalışan importlar sayılır: **fonksiyon içi importlar ve `if TYPE_CHECKING:` blokları döngü değildir** (çalışma zamanında hata vermezler).
- **JS/TS (yaklaşık):** göreli yollar (`./x`, uzantısız, `index`, TS'te `.js` -> `.ts`) ile `@/` ve `~/` takma adları (kök ve `src/` denenir). `import type` ve harici paketler grafiğe girmez. `tsconfig` `paths` ayarı okunmaz.
- Java, C#, Go, Rust ve C/C++ için döngü tespiti yoktur: namespace/paket ile dosya eşlemesi güvenilir değil.

### Güvenlik: SAST-lite, Sağlayıcı Sırları, Sürüm Sabitleme

**`CodeSecurityAnalyzer`** `resources/rules/security_rules.json` içindeki kuralları kaynak kodda arar. Kural başına dosya başına tek bulgu; satırlar ve CWE numarası bulguda yer alır. Yorumlar taranmaz, test dosyaları atlanır. Regex tabanlıdır: veri akışı bilinmediği için sonuçlar **ipucudur** (`approximate=True`).

| Dil | Kurallar (örnek) |
|-----|------------------|
| Python | `eval`/`exec`, `pickle`/`marshal` yükleme, `yaml.load`, `subprocess(... shell=True)`, `os.system`, `hashlib.md5/sha1`, `verify=False`, `tempfile.mktemp`, SQL'e f-string/`%`/`+`, Flask `debug=True` |
| JS/TS | `eval`, `new Function`, `setTimeout("...")`, dinamik `innerHTML`, `document.write`, `dangerouslySetInnerHTML`, `child_process.exec`, `rejectUnauthorized: false`, `createHash('md5')`, SQL birleştirme |
| Java | `Runtime.exec`, `MessageDigest MD5/SHA-1`, `ObjectInputStream`, SQL birleştirme, DES/RC4/ECB |
| C# | `BinaryFormatter`, `MD5/SHA1.Create`, SQL birleştirme/enterpolasyon, sertifika doğrulamasını kapatma |
| C/C++ | `gets`, `strcpy/strcat`, `sprintf`, `system`, sınırsız `scanf("%s")` |
| Go / Rust | `InsecureSkipVerify`, `md5/sha1`, `sh -c`; Rust `unsafe` (bilgi) |

- **Kural biçimi:** `{id, title, severity, languages, scope, pattern, flags, cwe, advice}`. `scope`: `code` (yorum ve string silinmiş) veya `text` (string içeriği durur, ör. `createHash('md5')`). Kullanıcı kuralları `~/.gitclean/rules/*.json` içine konur; aynı `id` paketliyi geçersiz kılar. Bozuk kural atlanır ve loglanır.
- **Kural kapatma:** `ProjectService(disabled_rules=["py-os-system"])`.
- **SQL kuralları** ORTA öncelikli: tablo adı gibi parametrelenemeyen yerlerde f-string kaçınılmaz olabilir.

**Test dosyaları:** `password = '...'` gibi genel kalıplar test klasörlerinde DÜŞÜK öncelikli raporlanır (çoğu sahte örnek değerdir, `in_tests=True`); sağlayıcı biçimli anahtarlar testte de aynı öncelikle raporlanır.

**`SecurityLeakAnalyzer`** sağlayıcı biçimli sırları da yakalar: AWS erişim anahtarı, PEM özel anahtar, GitHub, Slack, Google API, Stripe canlı anahtar ve JWT. Bulguya **değer yazılmaz** (yalnızca 4 karakterlik maskeli önek ve uzunluk). Satırında `example` geçenler (belge örnekleri) atlanır.

**Çalışma zamanı / geliştirme ayrımı:** Python'da `requirements.txt` içindeki test ve paketleme araçları (`pytest`, `pyinstaller`, `mypy`, `ruff`, `black` ...) manifest başına tek DÜŞÜK bulgu üretir (`dev-dependency-in-runtime`); `requirements-dev.txt`, `requirements-build.txt` gibi adlarda (`dev`, `test`, `build`, `lint`, `doc`) araçlar serbesttir.

**Sürüm sabitleme:** `DeadWeightAnalyzer` manifest başına tek DÜŞÜK bulgu üretir (`unpinned-dependencies`). Python `requirements.txt`: `==` olmayan her satır. npm: `*`, `latest`, boş, `>=` gibi açık uçlu aralıklar ve git/URL bağımlılıkları (`^`/`~` normal sayılır). Go ve Cargo denetlenmez.

### Güvenilirlik ve Üretim Hijyeni

`ReliabilityAnalyzer` kural başına dosya başına tek bulgu üretir (test dosyaları hariç). Python `ast` ile kesindir, diğer diller sözcük tabanlıdır.

| Kural | Kapsam | Öncelik |
|-------|--------|---------|
| `bare-except` | Python: çıplak `except:` (içinde `raise` yoksa) | YÜKSEK |
| `swallowed-exception` | Python: `except Exception/BaseException` gövdesi yalnızca `pass`, `...`, `continue`, `break`, `return`/`return None` | ORTA |
| `empty-catch` | JS/TS/Java/C#/C++: boş `catch {}` ve `.catch(() => {})` | ORTA |
| `open-without-encoding` | Python: metin kipinde `open()`, `Path.read_text/write_text` kodlamasız (Windows'ta cp1254/cp1252'ye bağımlı) | ORTA |
| `debug-flag` | Python: modül düzeyi `DEBUG = True` | ORTA |
| `debugger-statement` | JS/TS: `debugger;` | ORTA |
| `naive-datetime` | Python: `datetime.now()` (argümansız), `utcnow()`, `today()` | DÜŞÜK |
| `print-density` | `print` / `console.log` / `System.out` / `Console.Write` / `fmt.Print` / `println!` dosya başına > 5 (`QualityThresholds.print_calls`) | DÜŞÜK |
| `todo-inventory` | Yorumlardaki `TODO` `FIXME` `HACK` `XXX`; projede tek bulgu, liste metadata'da | BİLGİ |

- **Bilinçli yutma sayılmaz:** gövdesinde açıklama yorumu olan `except Exception: pass  # neden` ve `catch { /* neden */ }` raporlanmaz; `return False` / `return 0` gibi değer döndürenler de yutma değil geri dönüş değeri sayılır.
- **Atlananlar:** `if __name__ == "__main__":` içindeki `print`, `datetime.now().astimezone()` (saat dilimi eklenir), C/C++ konsol çıktısı (konsol programı olduğundan), `encoding=` veya ikilik kip (`'rb'`) verilen `open`.
- **Sınırlar:** `.read_text()`/`.write_text()` yöntem adına bakılır (nesne türü bilinmez); `datetime` yalnızca `datetime` adıyla tanınır (`import datetime as dt` takma adı atlanır). TODO işaretleri yalnızca yorumlarda aranır (docstring içindeki `TODO` sayılmaz).

### Test Sağlığı ve Proje Hijyeni

**`TestingAnalyzer`** test dosyasını klasör (`tests`, `__tests__`, `spec`, `e2e`, `src/test` ...) veya adlandırma kuralıyla (`test_x.py`, `x_test.go`, `x.test.ts`, `XTests.cs`) tanır. Test işlevleri: Python `def test*` (`ast`), JS/TS `it(`/`test(`, Java `@Test`, C# `[Fact]`/`[Test]`, Go `func Test*`, Rust `#[test]` (birim testler kaynak dosyasında olduğundan her dosyada sayılır), C/C++ `TEST(`.

| Kural | Koşul | Öncelik |
|-------|-------|---------|
| `no-tests` | ≥ 100 kaynak satırı var, test yok | ORTA; > 500 satır YÜKSEK |
| `low-test-ratio` | test/kaynak kod satırı oranı < 0.3 (`test_ratio_low`) | DÜŞÜK; < 0.1 (`test_ratio_severe`) ORTA |
| `untested-modules` | adına karşılık gelen test dosyası olmayan ≥ 30 satırlık modüller (ilk 50 metadata'da) | BİLGİ |
| `test-sleep` / `test-real-network` | test dosyasında gerçek `sleep`, yerel olmayan gerçek HTTP çağrısı (kararsız test göstergesi) | DÜŞÜK |
| `test-summary` | test dosyası / işlevi sayısı, atlanmış-koşullu atlanan işaretler, oran | BİLGİ |

Eşleşme ada bakar (`foo_bar.py` ↔ `test_foo_bar.py`, `FooBarTests.cs`); farklı adla yazılmış test "testsiz" görünür, bu yüzden bulgu bilgi amaçlıdır. `skipif` gibi koşullu atlamalar da işaret olarak sayılır.

**`ProjectHygieneAnalyzer`** kök dizinde kontrol listesi çalıştırır; eksik her madde DÜŞÜK bulgudur (`missing-readme`, `missing-license`, `missing-gitignore`, `missing-ci`, `missing-lockfile`, `missing-env-example`). Ayrıca tek bir BİLGİ özeti (`hygiene-summary`) mevcut iyi pratikleri (`present`) ve eksikleri (`missing`) listeler; denetim raporu bunu "iyi pratikler" bölümünde kullanır.

- README/LICENSE yalnızca ≥ 100 kaynak satırı olan projelerde, `.gitignore` yalnızca git deposunda, CI yalnızca testi olan projelerde beklenir (`.github/workflows`, `.gitlab-ci.yml`, `Jenkinsfile`, `azure-pipelines.yml`, `.circleci`, `bitbucket-pipelines.yml`, `.travis.yml` ...).
- **Kilit dosyası:** bağımlılığı olan her manifest için aynı veya üst klasörde aranır (monorepo kökündeki kilit dosyası sayılır): `package.json` -> `package-lock.json`/`yarn.lock`/`pnpm-lock.yaml`/`bun.lock*`, `go.mod` -> `go.sum`, `Cargo.toml` (yalnızca `src/main.rs` olan uygulama crate'i) -> `Cargo.lock`, `Pipfile` -> `Pipfile.lock`, `pyproject.toml` (yalnızca poetry/uv/pdm kullanıyorsa) -> `poetry.lock`/`uv.lock`/`pdm.lock`.
- **Sürüm kontrolündeki üretilmiş içerik (`tracked-artifacts`):** git'in izlediği `node_modules`, `venv`/`.venv`, `__pycache__` ve araç önbellekleri, `*.pyc`, `dist`/`build` klasörleri kök başına bir bulgudur (en çok dosyası olan 10 kök). Bağımlılık klasörleri ORTA, önbellek / bytecode / derleme çıktısı DÜŞÜK; `dist`/`build` adı belirsiz olduğundan `approximate=True` (`lib/`, `vendor/`, `third_party/` altındaki üçüncü taraf paketleri sayılmaz). Temiz depo `hygiene-summary.present` içinde `clean-repo` olur. `.gitignore`'a eklenmiş ama hâlâ izlenen dosyalar da yakalanır, çünkü `git ls-files` esas alınır.
- **`.env.example`:** `.env` varsa (kök dizinde, `.gitignore`'da olsa bile) `.env.example`/`.env.sample`/`.env.template` aranır.

### Git Geçmişi

**`GitHistoryAnalyzer`** yalnızca git deposunda çalışır (git yoksa, depo değilse ya da zaman aşımında sessizce bulgu üretmez). Çağrıların hepsi salt-okunurdur (`GIT_OPTIONAL_LOCKS=0`, `core.fsmonitor=false`, etkileşimli soru yok, 30 sn zaman aşımı); `--all` yerine `--branches --tags --remotes` kullanılır, stash taranmaz.

| Kural | Koşul | Öncelik |
|-------|-------|---------|
| `secret-in-history` | Hassas bir dosya (`.env`, `.env.*` (örnek/şablon hariç), `credentials.json`, `secrets.{yaml,yml,json}`, `id_rsa`/`id_dsa`/`id_ecdsa`/`id_ed25519`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.jks`, `*.keystore`) geçmişte eklenmiş ama **artık izlenmiyor** | YÜKSEK; test klasöründeyse ORTA |
| `hotspot` | Son 500 commit'te ≥ 5 kez değişen kaynak dosya; sıralama = değişim sayısı × işlev siklomatik toplamı, ilk 10 | BİLGİ; ≥ 20 değişim ve siklomatik eşiği aşan işlev varsa DÜŞÜK |
| `co-change` | İki kaynak dosya ≥ 5 ortak commit'te değişmiş, güven ≥ 0.6, ilk 10 | BİLGİ |

- `secret-in-history` bulgusu **`security`** kategorisinde puanlanır ("sır geçmişte duruyor, anahtarı döndürün"); hâlâ izlenen sır dosyalarını `SecurityLeakAnalyzer` bildirir. `.pem`/`.key` içeriği doğrulanmadığı için (ortak sertifika olabilir) `approximate=True` işaretlenir.
- `hotspot` ve `co-change` bilgi amaçlı **`git`** kategorisindedir ve puana girmez (`HealthChecker.WEIGHTS` içinde yoktur).
- Güven = ortak commit sayısı / iki dosyadan çok değişenin commit sayısı. Bir dosya ile kendi testi (`foo.py` / `test_foo.py`) birlikte değişir; bu beklenen durum olduğu için çift sayılmaz.
- 30'dan fazla dosya içeren commit'ler (toplu biçimlendirme, taşıma) ve merge commit'leri her iki analizde de atlanır; geçmişi 20 commit'ten kısa depolarda sıcak nokta / birlikte değişim üretilmez.

### Denetim Raporu (V2 Formatı)

`ProjectService.export_audit_report(yol)` tam teşhisi çalıştırır ve `V2-GenelSablon.md` yapısında bir **Markdown** raporu yazar (`AuditReportService`, `IReporter`). Bölümler sabittir:

| Bölüm | İçerik |
|-------|--------|
| **A. Yönetici özeti** | Genel not, öncelik sayıları (🔴 KRİTİK, 🟠 YÜKSEK, 🟡 ORTA, 🟢 DÜŞÜK), kategori puanları ve `# \| Bulgu \| Öncelik \| Boyut \| Efor \| Etki` tablosu (en fazla 15 grup) |
| **B. İyi pratikler** | `hygiene-summary.present` maddeleri, test özeti ve "olumsuz bulgu yok" tespitleri (yalnızca ilgili analizör çalışmışsa: döngü yok, klon yok, yüksek güvenlik bulgusu yok, bağımlılıklar sabit, hata yutulmuyor) |
| **C. İncelenmedi** | Analize girmeyen dosyalar (çok büyük, okunamayan, minify, ayrıştırılamayan), hata veren analizörler, `.gitignore` ile dışarıda kalanlar, yaklaşık (sözcük tabanlı) diller, git bulgusu yokluğu ve aracın kapsam dışı konuları (CVE, lisans uyumu, çalışma zamanı performansı) |
| **D. Ayrıntılı bulgular** | Dosya / Konum, Kategori, Sorun, Etki, Kanıt (ilk 3 kaynak satırı), Çözüm, Efor, Bağımlılık; öncelik sırasıyla, kuraldan en fazla 3, toplam en fazla 25 |
| **E. Aksiyon planı** | KRİTİK -> 24 saat içinde, YÜKSEK -> bu hafta, ORTA -> bu ay; `Eylem \| Beklenen sonuç \| Bağımlılık \| Risk` tabloları; DÜŞÜK bulgular "fırsat oldukça" |
| **F. Sonraki adım** | En yüksek öncelikli grup için bir soru |

- Bulgular `kural + öncelik` ile gruplanır (910 benzer işlev bulgusu raporu boğmaz); tabloda grup başına sayı görünür.
- **Boyut** kategoriden türetilir (Kod Kalitesi, Mimari, Güvenlik, Test, Production). **Efor** (S/M/L/XL) kural tablosundan gelir ve bulgu sayısı arttıkça bir-iki basamak yükselir (`audit_catalog.effort_of`); bu bir tahmindir.
- **Sır güvenliği:** `hardcoded-secret`, `provider-secret`, `secret-in-history` bulgularında, `kind=sensitive_file` bulgularında ve `.env`, `*.pem`, `*.key`, `id_rsa` gibi dosyalarda kaynak satırı rapora **asla yazılmaz**.
- Tablo hücreleri ve satır içi metinler Markdown'ı bozmayacak biçimde kaçışlanır (`|`, satır sonu, ters tırnak); kanıt bloğunun çiti içindeki en uzun ``` dizisinden uzundur.
- HTML rapor (`export_project_report`) artık kategori puanlarını (güvenlik, mimari, test, hijyen ...) en düşükten başlayarak kartlar olarak gösterir.

### Ajan Görevleri (bulguları yapay zeka ajanına çözdürmek)

`ProjectService.export_agent_tasks(klasör, batch_size=15)` tüm bulguları bir yapay zeka ajanının (Claude Code ya da herhangi biri) sırayla çözebileceği görevlere yazar. `verify_agent_tasks(klasör)` ajanın çalışmasından sonra hangi bulguların kapandığını ve yeni bulgu çıkıp çıkmadığını söyler.

```
agent-tasks/
  README.md      # ajana giriş talimatı, dalga tablosu, ilk görevler, insan aksiyonu bekleyenler
  tasks.json     # tüm öğeler, makine okunur (kararlı parmak izi, dalga, kural, risk)
  verify.py      # kapanış doğrulaması: python verify.py [görev kimliği ...]
  tasks/
    W3-004-unused-import.md   # her biri en fazla 15 öğelik bir parti
```

| Dalga | İçerik | Yapan |
|---|---|---|
| 0 | Sırlar (`hardcoded-secret`, `provider-secret`, `secret-in-history`), `.env`, `tracked-artifacts`, LICENSE | **İnsan**: görev dosyasında kaynak satırı ve sır yok |
| 1 | Güvenlik (SAST kuralları) | Ajan, dikkatli |
| 2 | Güvenilirlik (`bare-except`, `swallowed-exception`, kodlamasız `open` ...) | Ajan |
| 3 | Mekanik temizlik (kullanılmayan import / değişken, ulaşılamaz kod, sihirli sayı, `print`, saat dilimsiz tarih) | Ajan, düşük risk |
| 4 | Bağımlılık ve hijyen (sürüm sabitleme, eksik README / CI / kilit dosyası ...) | Ajan |
| 5 | Test (`no-tests`, `low-test-ratio`, `test-sleep` ...) | Ajan, refactor'dan önce |
| 6 | Refactor (`function-metrics`, `class-size`, `file-length`, `code-clone`, `import-cycle`) | Ajan, testler geçmeli |

- **Görev dosyası:** kural bazlı "ne yapılacak / neleri yapma", genel kısıtlar (davranışı değiştirme, testler geçmeli, emin olmadığını atla), `dosya:satır` + parmak izi + kanıt satırları (aynı satır bir kez), doğrulama komutu, commit önerisi. Yaklaşık (sözcük tabanlı) bulgularda "önce doğrula, yanlış pozitifse atla ve nedenini yaz" uyarısı.
- **Parti:** aynı dosyanın öğeleri aynı görevde kalır; tek dosya sınırı aşarsa bölünür. Görev kimliği `W<dalga>-<sıra>`.
- **Parmak izi:** `kural + yol + ayırt edici ad (işlev, sınıf, import adı, bağımlılık ...) + sıra`; satır numarasına bağlı değildir, bu yüzden ajanın düzeltmeleri satırları kaydırsa da aynı bulgu aynı kimliği taşır.
- **Sır güvenliği:** sır değeri ve sır dosyalarının kaynak satırı hiçbir çıktıya yazılmaz; Dalga 0 görevleri kaynak satırı içermez ve ajana "yapma" der.
- **Yeniden çalıştırma** yalnızca önceki `W*-*.md` görev dosyalarını ve üç sabit dosyayı (`tasks.json`, `README.md`, `verify.py`) değiştirir; klasördeki diğer dosyalara dokunmaz.
- **`verify`:** projeyi yeniden tarar; görev başına `closed` (kapanan), `reduced` (aynı satırda tekrar sayısı azalan), `open`, ayrıca ajanın yeni çıkardığı bulgular (`new_findings`).

### `.gitignore` ve Git Duyarlılığı

Analiz ve arşivleme projenin `.gitignore` kurallarını **git ile aynı öncelikle** uygular: kökteki ve alt klasörlerdeki tüm `.gitignore` dosyaları, `.git/info/exclude`, `!` ile geri alma, ignore'lu klasörün içine girilmeyişi. Git deposunda `git ls-files` ile **izlenen** dosyalar (kendi adını içeren `.gitignore`, `git add -f` ile eklenenler) kurala uysa bile dahil edilir.

- Analizde ignore'lu dosyalar (derleme çıktısı, yerel veri, `*.log`) boyut, dil istatistiği, karmaşıklık, çift dosya ve bağımlılık sayılarına girmez. `quick_scan` çıktısında `gitignore_applied` ve `ignored_by_gitignore` (`files`/`dirs`; budanan klasörün içi sayılmaz) görünür. Kapatmak için `ProjectService(respect_gitignore=False)`.
- `git` kurulu değilse ya da klasör bir depo değilse yalnızca `.gitignore` kuralları uygulanır.
- Güvenlik: `.gitignore`'daki izlenmeyen `.env` doğru uygulamadır ve bulgu üretmez. `.gitignore`'a eklenmemiş hassas dosyalar (`.env`, `.env.*` (örnek/şablon hariç), `credentials.json`, `secrets.{yaml,yml,json}`, `id_rsa`/`id_dsa`/`id_ecdsa`/`id_ed25519`, `*.pem`, `*.key`, `*.p12`, `*.pfx`, `*.jks`, `*.keystore`; yalnızca sertifika içeren `.pem` hariç) "commit edilme riski"; **git'e commit edilmiş** olanlar (sonradan `.gitignore`'a eklenmiş olsa bile) KRİTİK "commit edilmiş" bulgusudur: `.gitignore` izlenen dosyayı geçmişten silmez (`git rm --cached` + sırları değiştirin).
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

### Dokümantasyon (wiki)

Projenin kararları, analizör kataloğu, backend arayüzü ve çalışma kuralları `docs/wiki/` altındadır. Başlangıç noktası `docs/wiki/index.md`; yeni arayüzü yazacak olan için `docs/wiki/backend-api.md`.

### Test Çalıştırma

```bash
# Önce test bağımlılığı: pip install -r requirements-dev.txt

# Tüm testler (790'dan fazla, yaklaşık 90-100 sn)
# Lint (CI ile aynı): python -m ruff check .
python -m pytest tests/ -v

# Belirli bir test dosyası
python -m pytest tests/unit/test_audit_report.py -v

# Wiki bütünlüğü (kırık link, öksüz sayfa)
python -m pytest tests/unit/test_wiki.py -v

# Coverage raporu için ayrıca: pip install pytest-cov
python -m pytest tests/ --cov=src --cov-report=html

Doğrulama yöntemi (bağımsız araçlarla karşılaştırma, refactor öncesi/sonrası karşılaştırma, kendi kendini tarama) `docs/wiki/testing.md` içinde anlatılır.
```

---

## 📦 Build ve Dağıtım

### Exe Oluşturma

```bash
# Önce: pip install -r requirements-build.txt
python build_exe.py
```

**Çıktı:** `dist/GitCleanArchiver/` klasörü (`GitCleanArchiver.exe` + `_internal`)

### Kurulum Sihirbazı (Inno Setup)

```bash
# Önce: Inno Setup 6 (https://jrsoftware.org/isdl.php) ve pip install -r requirements-build.txt
python build_installer.py                 # EXE'yi derler, bu makinede dener (Akıllı Uygulama Denetimi engellerse en çok 6 kez yeniden derler), sonra dist/installer/GitCleanArchiver-Setup-<sürüm>.exe + .sha256
python build_installer.py --no-verify     # denemeden (CI'da `CI` ortam değişkeniyle otomatik)
python build_installer.py --skip-build    # dist/GitCleanArchiver/ hazırsa yalnızca sihirbaz (tek deneme)
```

Sürüm tek kaynaktan gelir: `src/version.py`. Sihirbaz Türkçe ve İngilizcedir; `AppId` sabittir (sürümler birbirinin üstüne kurulur, değiştirmeyin).

### Sürüm Yayınlama (etiket)

```bash
python tools/release.py 2.1.0             # src/version.py, version_info.txt, README rozetini yükseltir; "chore(release): v2.1.0" commit'i ve v2.1.0 etiketi
git push origin main
git push origin v2.1.0                    # etiket itilince Release iş akışı çalışır
```

`.github/workflows/release.yml`: etiket sürümle uyumlu mu denetler, `ruff` + `pytest` koşar, kurulum dosyasını derler ve GitHub Release olarak yayınlar (sürüm notları otomatik üretilir; `v2.1.0-rc1` gibi etiketler ön sürüm olur ve güncelleme denetimi onları yok sayar). Uygulamanın güncelleme penceresi en son **yayınlanmış, ön sürüm olmayan** Release'i kullanır.

### PyInstaller Parametreleri

Uygulamanın sorunsuz, taşınabilir ve güvenilir bir biçimde derlenmesi için aşağıdaki parametreler kullanılmaktadır:

| Parametre | Açıklama |
|-----------|----------|
| `--onedir` | exe + `_internal` klasörü üretir; Inno Setup tüm klasörü paketler (kurulum dosyası ~40 MB, her açılışta `%TEMP%`'e açma yok) |
| `--windowed` | Arka planda konsol penceresinin açılmasını engeller |
| `--icon=...` | Uygulama exe'sine ve görev çubuğuna özel `app_icon.ico` ikonunu gömer |
| `--noupx` | UPX sıkıştırmasını devre dışı bırakarak yanlış pozitif virüs algılamalarını önler |
| `--version-file=...` | Telif hakkı ve sürüm (.exe içine) ekleyerek anti-virüs güvenilirliğini artırır |
| `--add-data=...` | QML arayüz dosyaları (`src/qml_ui/qml`), arayüz simgeleri ve `resources/` (kurallar, profiller, ikon); eksik klasör derlemeyi durdurur |
| `--collect-submodules=src.analyzers` | Kendini kaydeden analizörlerin pakete girmesini sağlar |

EXE ve kurulum dosyası imzasızdır: Windows SmartScreen "tanınmayan uygulama" uyarısı gösterebilir (**Ek bilgi → Yine de çalıştır**) ve Windows 11 Akıllı Uygulama Denetimi bazı derlemeleri tümüyle engelleyebilir; bu yüzden dağıtımdan önce `build_installer.py` dosyayı dener. Kalıcı çözüm kod imzalamadır ([rehber](docs/wiki/windows-exe-dagitim.md)).

---

## ❓ Sık Sorulan Sorular

### S: Hangi dosyalar temizlenir?
**C:** Varsayılan olarak:
- Python önbelleği: `__pycache__`, `*.pyc`, `*.pyo` (varsayılan açık)
- Geçici dosyalar: `*.tmp` (varsayılan açık)
- Log `*.log` ve yedek `*.bak` dosyaları (varsayılan kapalı; kullanıcı verisi içerebilir)

Sanal ortamlar, `node_modules`, derleme çıktıları, sembolik bağ / junction klasörler ve proje dışındaki yollar hiçbir zaman temizlenmez.

### S: Temizlik geri alınabilir mi?
**C:** Evet. Temizlik kalıcı silme yapmaz, dosyaları Geri Dönüşüm Kutusu'na taşır; oradan geri yüklenebilir. Önizleme modu ile taşınacakları önceden görebilirsiniz.

### S: .gitignore nasıl kullanılır?
**C:** Kökteki ve alt klasörlerdeki tüm `.gitignore` dosyaları ile `.git/info/exclude` git ile aynı öncelikle okunur; analiz, zip ve temiz kopyada uygulanır (git'in izlediği dosyalar yine dahil edilir). Yedek bilinçli olarak `.gitignore` uygulamaz.

### S: Sağlık skoru nasıl hesaplanır?
**C:** 11 kategoride, bulguların şiddetine göre hesaplanan ağırlıklı ortalama ile. Detaylar için [Sağlık Skorlama Sistemi](#-sağlık-skorlama-sistemi) bölümüne bakın.

---

## 📄 Lisans

Depoda henüz bir `LICENSE` dosyası yok; lisans seçimi depo sahibine aittir. Lisans eklenene kadar tüm hakları saklıdır.

---

## 🤝 Katkıda Bulunma

1. Fork'layın
2. Feature branch oluşturun (`git checkout -b feature/amazing`)
3. Değişikliklerinizi commit edin (`git commit -m 'Harika özellik eklendi'`)
4. Branch'inizi push edin (`git push origin feature/amazing`)
5. Pull Request oluşturun

---

