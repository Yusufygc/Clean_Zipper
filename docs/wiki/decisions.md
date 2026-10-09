# Kararlar

Her karar: ne seçildi, neden, nasıl uygulanır. Bulgu durumları için [[roadmap]], kataloglar için [[analyzers]], tarih sırası için [[log]].

## Kapsam ve yaklaşım
- **Önce backend, UI sonra.** `src/ui` kullanıcı tarafından sıfırdan yazılacak. Doğrulama pytest ve konsolla yapılır; GUI testi yok. Uygulama: UI dosyalarına dokunulmaz (kendi taramamızın UI bulguları bilinçli bırakıldı). Tüketici yüzeyi: [[backend-api]].
- **CLI şart değil.** GUI çekirdeği tek tüketici; ayrı bir komut satırı arayüzü yazılmaz.
- **Çok dilli, hafif sözcük tabanlı çözümleyici.** Python `ast` ile kesin; JS, TS, Java, C#, C, C++, Go, Rust sözcük tabanlı (`brace.py` + `brace_headers.py`). Neden: yüzlerce MB gramer / ayrıştırıcı bağımlılığı olmadan, ek kurulum istemeden çalışması; bedeli yaklaşık sonuçtur, bu yüzden Python dışı bulgular `approximate=True` taşır. Yeni dil = yeni `LanguageSpec` (`catalog.py`).
- **Kapsam dışı (gerekçeli):** bilinen zafiyet (CVE) taraması (ağ / veritabanı gerekir), lisans uyumu (paket metaverisi gerekir), Maven / NuGet kullanılmayan bağımlılık ve Java / C# / Go / Rust namespace tabanlı döngü tespiti (paket adı ile namespace arasında güvenilir eşleme yok, yanlış pozitif üretir), "Feature Envy" / "Primitive Obsession" (tür bilgisi gerekir), çalışma zamanı performansı, analiz iptali.

## Ölçüm ve skor
- **Eşikler V2 şablonuna hizalı** (`V2-GenelSablon.md`), tek yerde (`QualityThresholds`); eşik aşılırsa (`>`) bulgu, 2 katında bir seviye yukarı. Üst düzey yapılandırma `ProjectService(thresholds=...)`.
- **Gürültü azaltma:** bir fonksiyon birden çok eşiği aşarsa tek bulgu; dosya başına toplulaştırma (sihirli sayı, `print`, TODO); raporda `kural + öncelik` ile gruplama.
- **Skor bulgu tabanlıdır** (`100 × exp(-ceza/60)`), sabit değer değil. Çalışmayan analizörün kategorisi hesaba katılmaz. `git` ve `type` kategorileri puanlanmaz (bilgi amaçlı); tek istisna `secret-in-history`, bulgusu `security` kategorisinde puanlanır.
- **Kural kimliği + `disabled_rules`:** her bulguda `metadata['rule']`; yanlış pozitif kapatma tek yerden.
- **Klon tespiti yalnızca Tip-1** (birebir aynı satırlar). Dize ve sayıları normalleştiren sürüm sahte klon üretti, vazgeçildi.
- **Test eşleme ada bakar.** Farklı adla yazılmış test "testsiz" görünür; bu yüzden `untested-modules` yalnızca BİLGİ.
- **Yorumla gerekçelendirilmiş hata yutma bulgu sayılmaz** (`swallowed-exception`); gerekçesiz yutma sayılır.
- **Test dosyalarındaki genel `password = '...'` kalıpları DÜŞÜK**, sağlayıcı biçimli anahtarlar testte de aynı öncelikte (gerçek anahtar testte de sızıntıdır).
- **`dist` / `build` adı belirsiz:** `tracked-artifacts` bunları `approximate=True` verir; `lib/`, `vendor/`, `third_party/` altındakiler üçüncü taraf paketi sayılır, bulgu olmaz.

## Güvenlik
- **Sır değeri asla yazılmaz:** bulguda yalnızca maskeli önek ve uzunluk; denetim raporunda sır içerebilecek bulguların ve dosyaların (`.env`, `*.pem`, `*.key`, `id_rsa`) kaynak satırı gösterilmez. Test: 44 sır bulgusu, 0 sızıntı.
- **Silme kalıcı değil:** temizlik Geri Dönüşüm Kutusu'na taşır (`send2trash`); `venv`, `node_modules` gibi klasörlerin içine girilmez; `cleanup` varsayılanı `dry_run=True`.
- **Git erişimi salt-okunur ve zaman aşımlıdır** (`GIT_OPTIONAL_LOCKS=0`, `core.fsmonitor=false`, etkileşimli soru yok); git yoksa `None` ve sessiz atlama. `--all` yerine `--branches --tags --remotes` (stash taranmaz).
- **Okunamayan `.gitignore` varken arşiv reddedilir:** gizli dosyalar sızabilirdi.

## Dosya seçimi (arşiv / yedek / analiz)
- **Analiz ve arşiv `.gitignore` uygular, izlenen dosyalar korunur** (git semantiği: izlenen dosya sonradan ignore'a girse de dışlanmaz). Dışarıda kalan sayılar görünür (`ignored_by_gitignore`).
- **Yedek `.gitignore` uygulamaz** (2026-10-09): yedek felaket kurtarma içindir, `.env`, yerel veritabanı, model gibi git'ten geri getirilemeyen dosyalar çoğunlukla ignore'dadır. Yalnızca yeniden üretilebilir klasörler (`EXCLUDED_DIRS`, koşullu `target`/`bin`/`obj`, `pyvenv.cfg` içeren klasör) dışlanır. Ölçüm (30 depo): eski davranış 36,1 GB, seçilen 3,8 GB, `.gitignore` de uygulansaydı 69 MB ve ~0,9 GB veritabanı kaybolurdu. Dışlananlar sonuçta bildirilir (sessiz dışlama yok).
- **Tek dışlama kaynağı:** `src/core/exclusions.py` (`is_excluded_dir`); analiz, temizlik, arşiv ve yedek ortak kullanır.

## Ajan görevleri (2026-10-09)
- **Bulgular ajana görev olarak verilir; sırlar verilmez.** Dalga 0 (sır yenileme, LICENSE kararı, git izleme) insan aksiyonudur: görev dosyasında kaynak satırı ve değer yoktur, ajana "yapma" denir.
- **Dalga sırası bilinçli:** güvenlik -> güvenilirlik -> mekanik temizlik -> hijyen -> **test -> refactor**. Testsiz refactor davranışı bozar, bu yüzden test dalgası refactor'dan önce gelir.
- **Parti: görev başına en fazla 15 öğe** (ayarlanabilir), aynı dosyanın öğeleri bir arada. Neden: ajanın bağlamını doldurmadan tek turda bitirebileceği, tek commit'lik iş.
- **Tüm bulgular göreve girer, BİLGİ düzeyindekiler girmez** (`hotspot`, `co-change`, özetler ve `todo-inventory` yalnızca bilgi). Önceliklendirme dalga ve öncelikle yapılır, kapsam daraltılmaz.
- **Kararlı parmak izi:** `kural + yol + ayırt edici ad + sıra`, satır numarası yok. Neden: ajan düzeltme yaparken satırlar kayar; kapanışı satıra bağlamak yanlış "açık" ya da "kapandı" üretir.
- **Doğrulama dahil:** ajan kendi işini `verify.py` ile doğrular; ajanın yeni çıkardığı bulgular (`new_findings`) ayrıca raporlanır.
- **Genel (ajan bağımsız) çıktı:** Claude Code için optimize edilmiş ama araç adı geçen ya da araca özgü bir biçim yok; Markdown + JSON.

## Arayüz ve ayarlar (2026-10-09)
- **Ayarlar kalıcıdır ve geneldir** (`~/.gitclean/settings.json`, proje başına değil). "Kaydet ve Uygula" gerçekten kaydeder; kural kapatma / açma anında kaydedilir ve analizi yeniler.
- **Ajan görev klasörü varsayılanı projenin dışındadır** (`~/.gitclean/agent-tasks/<proje>`); aksi hâlde sonraki analiz görev dosyalarını (`verify.py`, `.md`) bulgu sayardı.
- **Arayüze yalnızca verimli backend özellikleri eklendi:** dil dağılımı, atlanan dosya nedenleri, kategori süzgeci, göreli yol / satır / kaynak kodu, kural kapatma, 9 eşik (V2 tablosunun ayarlanabilir olanları), ajan doğrulama sayıları. **Eklenmeyenler (bilinçli):** denetim raporu önizlemesi, kalan 8 nadir eşik (test oranı, `print`, klon uzunluğu, sihirli sayı ...; `QualityThresholds` varsayılanları geçerli), analiz iptali.
- **Arayüzden ulaşılamayan ViewModel üyeleri:** eski arayüzle ilgisiz olanlar arayüze bağlandı (kategori süzgeci, dil dağılımı, analizörleri toplu aç / kapat, varsayılana dön, ajan sonucu), işlevsizler silindi (`clearProject`, `errorMessage` sinyali, `scanVM.allIssues`, `findingsVM.searchQuery`, 29 kullanılmayan metin, 4 kullanılmayan tema sabiti). `src/ui` (eski arayüz) ayrıca durmaktadır, dokunulmadı.
- **Kural kapatma güvenli:** sır içeren bulgularda "Bu Kuralı Kapat" ve kaynak gösterimi sunulmaz.
- **ViewModel'ler Python'da referansla canlı tutulur:** QML context property'leri zayıf referanstır; aksi hâlde `archiveVM` / `cleanupVM` / `settingsVM` null kalır (test: `test_qml_layout`).

- **Arayüz metni Türkçedir ve okunaklıdır:** koyu temada ikincil metin de parlak (en az `#CBD5E1`), en küçük yazı 12 px; arayüzde kural kimliği ve şiddet adı gösterilmez (`RULE_LABELS`, `ruleLabel`); yaygın teknik terimler (God Object, SOLID, Extract Method, Agent, LLM ...) İngilizce kalabilir (kullanıcı kararı).

- **Sorunlar sayfasında süzgeç tek satırdadır:** şiddet bitişik seçenekler, kategori açılır liste (kategori sayısı arttıkça ekran kalabalıklaşmasın); gösterge panelinde her satır eşit sütunlu ve eşit yüksekliklidir.

## Depo ve build
- **Satır sonu LF:** `.gitattributes` (`* text=auto eol=lf`; `.bat/.cmd/.ps1` CRLF) ve `.editorconfig`; kaynak dosyalarda UTF-8 BOM yok (testle zorunlu).
- **Bağımlılıklar ayrık ve tam sabit:** `requirements.txt` yalnızca çalışma zamanı; `requirements-dev.txt` (pytest), `requirements-build.txt` (pyinstaller). Sürümler venv'de test edilen sürümlerdir. Kullanılmayan `pillow` kaldırıldı. Geçişli bağımlılıklar için kilit dosyası üretilmedi.
- **Analizör dosyası `test_` ile başlamaz** (test sayılır, kurallardan muaf kalır); sınıf adı `Test...` ise `__test__ = False`.
- **Python 3.10 hedefi;** donmuş exe içinde analiz doğrulanamadı (Windows Uygulama Denetimi imzasız exe'yi engelliyor), paket içeriği doğrulandı.

## Kalite güvencesi
- **Kendi kodumuz kendi taramamızdan geçer** (dogfooding). Bilinçli istisnalar: UI dosyaları (yeniden yazılacak) ve `BaseAnalyzer._create_result` (7 parametreli, 18 dosyanın kullandığı genel API).
- **Her aşama bağımsız oracle ile doğrulanır** (başka araç ya da başka kod yolu), sonuç raporda dürüstçe belirtilir; doğrulanamayan şey açıkça "doğrulanmadı" denir. Ayrıntı: [[testing]].
