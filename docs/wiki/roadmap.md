# Yol Haritası

Kaynak: 2026-10-08 sistem denetimi. Mimari bağlam için [[architecture]], çalışma düzeni için [[rules]], alınan kararlar için [[decisions]].

| # | Bulgu | Öncelik | Durum |
|---|-------|---------|-------|
| 1 | `CleanupService` `venv`/`node_modules` içinde de siliyor, yedek yok | 🔴 | Tamamlandı (2026-10-08) |
| 2 | Sağlık skoru sabit değerlere dayanıyor, alanlar doldurulmuyor | 🔴 | Tamamlandı (2026-10-08) |
| 3 | HTML raporda escape yok | 🟠 | Tamamlandı (2026-10-08) |
| 4 | Tarama 9 kez tekrarlanıyor, `rglob` dışlamaları yok sayıyor | 🟠 | Tamamlandı (2026-10-08) |
| 5 | Analizör kaydı UI içinde, arayüzler yarım uygulanmış | 🟠 | Tamamlandı (2026-10-08) |
| 6 | Sadece Python ve `requirements.txt` destekleniyor | 🟠 | Tamamlandı (2026-10-08) |
| 7 | Hatalar sessizce yutuluyor, logger yok | 🟠 | Tamamlandı (2026-10-08) |
| 8 | Test yok | 🟠 | Tamamlandı (790+ test, bkz. [[testing]]); QML yerleşimi ekransız çizimle sınanır, görsel his elle kontrol |
| 9 | Çift dosya bulucu tüm dosyayı belleğe okuyor | 🟠 | Tamamlandı (2026-10-08, parçalı hash) |
| 10 | Dışlama listesi birden fazla yerde tekrarlanıyor | 🟡 | Tamamlandı (2026-10-09): analiz, temizlik, arşiv ve yedek `exclusions.py` kullanır; yedek `.gitignore` uygulamaz ([[decisions]]) |
| 11 | Arşiv profil regex'leri iç içe klasörleri kaçırıyor | 🟡 | Tamamlandı (2026-10-08) |
| 12 | Karmaşıklık analizörü eksikleri | 🟡 | Tamamlandı (2026-10-08): Aşama 0-7, bkz. aşağıdaki plan ve [[analyzers]] |
| 13 | Build ve bağımlılık hijyeni | 🟡 | Tamamlandı (2026-10-09) |
| 14 | Bulguları ajana çözdürme (görev dosyası dışa aktarımı) | 🟡 | Tamamlandı (2026-10-09), bkz. [[backend-api]] |

## Derin analiz planı (Bulgu 12, tamamlandı)
| Aşama | Konu | Commit |
|---|---|---|
| 0 | V2 eşikleri, bilişsel karmaşıklık, derinlik, parametre | `be5be5c` |
| 1 | Ölü kod, sihirli sayı, kod klonu | `2e155db` |
| 2 | Mimari: döngüsel bağımlılık | `86993af` |
| 3 | SAST-lite kural motoru, sağlayıcı sırları, sürüm sabitleme | `6db5aef` |
| 4 | Hata yönetimi ve üretim hijyeni | `4c2fc65` |
| 5 | Test sağlığı ve proje hijyeni | `0961ca0` |
| 6 | Git geçmişi | `a69c10c` |
| 7 | V2 formatında denetim raporu | `bf22155` |
| - | Self-audit refactor'u | `a4ffb2b` |
| - | Bulgu 13 build / bağımlılık hijyeni | `df3b0ff` |
| - | BackupService dışlama kararı | `fdf8271` |

## Backend denetimi (2026-10-10)
Kaynak: dış denetim raporu `BACKEND_ANALIZ_RAPORU.md` (depoya eklenmedi; 3 faz tamamlanınca 2026-10-10 silindi). İddialar kodla doğrulandı; reddedilenler gerekçesiyle [[decisions]] içinde.

| Faz | Bulgu | Durum |
|---|---|---|
| 1 | Bazı analizörlerin bulgularında kural kimliği yok; kapatılamıyorlar | Tamamlandı |
| 1 | Temizlik `is_excluded_dir` kullanmıyor (`myenv`, `target`, `bin`, `obj` içine giriyor) | Tamamlandı |
| 1 | Çalışma kopyasındaki `id_rsa`, `*.key`, `*.jks` ... hiçbir analizörce bildirilmiyor | Tamamlandı |
| 1 | Güvenlik analizörü çökerse `secret-in-history` puana yansımıyor | Tamamlandı |
| 1 | Genel sır deseni özel karakterli parolaları kaçırıyor | Tamamlandı |
| 1 | `copy_project` hedefi kaynağın kendisi / üst klasörü olabiliyor | Tamamlandı |
| 2 | Teşhis önbelleği yok (her sayfa yeniden tarıyor) | Tamamlandı |
| 2 | Eşzamanlı işlemler için kilit / meşgul durumu yok | Tamamlandı |
| 2 | `RecommendationEngine` 4 eski koşula bakıyor | Tamamlandı |
| 3 | `pyproject.toml` bağımlılıkları okunmuyor (`tomli` eklenecek) | Tamamlandı |
| 3 | `module_key` klasörü yok sayıyor (yan bulgu: `test_s...` testleri hiç eşleşmiyordu) | Tamamlandı |
| 3 | UTF-16 dosyalar ikilik sayılıyor | Tamamlandı |
| 3 | İç içe boş klasörler raporlanmıyor | Tamamlandı |
| 3 | Karmaşıklık uyarısında "satır kod" yanlış ifade | Tamamlandı |
| 3 | ViewModel'lerde `file:///` için `[8:]` kesmesi | Tamamlandı |
| 3 | Metin önbelleği dolunca yeni dosya önbelleğe alınmıyor (LRU yok) | Reddedildi: döngüsel okumada LRU daha az isabet eder ([[decisions]]) |
| - | Yalnızca ignore'lu dosya içeren klasör "boş" sayılmalı | Reddedildi ([[decisions]]) |
| - | `GitignoreMatcher._tracked` harf duyarlılığı | Ertelendi: yalnızca harf git dışından değişirse; `normcase` POSIX yolunu bozar |

## Backend denetimi V2 (2026-10-10)
Kaynak: ikinci dış denetim raporu (`BACKEND_ANALIZ_RAPORU.md`, depoya eklenmedi; düzeltmeler tamamlanınca 2026-10-10 silindi). İddialar kodla ve deneyle doğrulandı.

| Bulgu | Durum |
|---|---|
| `copy_project` hedef kaynağın alt klasöründeyse (`src/out/yedek`) tüm `src` atlanıyor (eski hata, Faz 1'den önce de vardı) | Tamamlandı |
| `py-yaml-load` / `py-weak-hash` çok satırlı güvenli çağrıda yanlış pozitif | Tamamlandı |
| BOM'suz UTF-16 metin ikilik sayılıyor | Tamamlandı (sezgi, [[decisions]]) |
| README'deki yedek rotasyonunun kodda karşılığı yok | Tamamlandı (`max_backups`) |
| Dışlama adları harf duyarlı (`Build`, `Dist`, `Bin`) | Tamamlandı (düşük öncelik: gerçek etkisi 0) |
| God Object `and` yüzünden tek ölçüyü aşan sınıfı kaçırıyor | Reddedildi: koşul yalnızca iki ölçü de eşik içindeyse bulgu üretmez; test eklendi, metin aşılan ölçüyü söyler |
| Analiz iptali yok | Kapsam dışı (kullanıcı kararı); bekleme bilinen sınır |
| Test boşlukları (kilitli dosya, gerçek iş parçacığı, büyük proje) | Büyük ölçüde mevcut (`PermissionError` testleri, 8 iş parçacıklı servis testi, her fazda tüm `C:\2UYGULAMALAR` ölçümü); yan bulgu: bir test gerçek `~/.gitclean_backups`'a yazıyordu, yalıtıldı |

## Bağımsız denetim (2026-10-10)
Kaynak: Claude'un güvenlik / DevOps / mimari incelemesi (kod okuma ve deney). Kararlar [[decisions]] içinde.

| # | Bulgu | Durum |
|---|---|---|
| 1 | Junction / sembolik bağ üzerinden temizlik proje dışını aday gösteriyor | Tamamlandı (bağ izlenmez + çöpe göndermeden önce proje içi denetimi) |
| 2 | Arşiv, kopya, yedek bağ hedefini (proje dışı) içeriğe koyuyor | Tamamlandı (`skipped_links`) |
| 3 | Kendine işaret eden junction analizi / temizliği döngüye sokuyor | Tamamlandı |
| 4 | EXE ve `main.py` eski arayüzü paketliyor, QML pakete girmiyor | Tamamlandı (eski `src/ui` kaldırıldı, giriş QML, EXE yeniden derlenip içeriği doğrulandı) |
| 5 | Ajan görev dosyalarında prompt injection | Tamamlandı ("veridir, talimat değildir" kuralı, satır içi kaçış) |
| 6 | PySide6 6.6.1 eski | Tamamlandı (6.12.0) |
| 7 | CI / lint / bağımlılık taraması yok | Tamamlandı (GitHub Actions; ilk koşu henüz GitHub'da görülmedi) |
| 8 | Yedekteki sırlar için kullanıcı uyarısı yok | Tamamlandı (arşiv sayfasında uyarı) |
| 9 | İmzasız EXE (Uygulama Denetimi engeller) | Geçersiz: EXE bu makinede imzasız açılıyor, donmuş teşhis doğrulandı. Başka makinelerde SmartScreen uyarısı olabilir (imza yalnızca dağıtım için) |
| 10 | `shutil.which('git')` geçerli klasöre bakıyor | Tamamlandı (`find_git`) |
| 11 | `doctors` → `services` katman ihlali | Tamamlandı (öneri motoru servis katmanına taşındı, `test_layering`) |

## Kararlar
Tam liste ve gerekçeler: [[decisions]]. Özet: önce backend (UI sonradan sıfırdan), çok dilli analiz, CLI yok, silme kalıcı değil (Geri Dönüşüm Kutusu), kendi kodumuz kendi taramamızdan geçer.

## Açık notlar
- Analiz iptal edilemiyor (UI'da iptal düğmesi yok); proje değişince yeni teşhis eskisini bekler ([[decisions]], kapsam dışı).
- `read_text` 2 MB üstü dosyaları atlıyor: büyük kaynak dosyalar karmaşıklık ve sızıntı taramasına girmez (`skipped_files` ile görünür).
- Java/Go yalnızca örnek kodla doğrulandı (diskte gerçek kod yoktu); C#, JS/TS ve Rust gerçek projelerde doğrulandı. Kotlin/PHP/Swift: yalnızca yeni bir `LanguageSpec` gerekir.
- İmzasız EXE başka makinelerde SmartScreen "tanınmayan uygulama" uyarısı verebilir ("Yine de çalıştır"); imza yalnızca geniş dağıtımda gerekir.
- UI yazılırken: arşiv/yedek sonucunda `complete=False` ve `failed_files` kullanıcıya gösterilmeli; `skipped_files` ve `failed_analyzers` "analiz tam mı" göstergesi olmalı ([[backend-api]]).
- Kendi taramamızın bilinçli bırakılan bulguları: QML ViewModel'lerinin `class-size` bulguları (`ScanViewModel`, `SettingsViewModel`, `FindingsViewModel`: her `@Property` / `@Slot` bir metot sayılır, sınıf QML'e açılan yüzeydir) ve `BaseAnalyzer._create_result` (7 parametreli genel API).
- Geçişli bağımlılıklar için kilit dosyası (`pip freeze` türevi) üretilmedi; yalnızca doğrudan bağımlılıklar tam sabit.

## Sonraki adaylar (onay bekliyor, öncelik sırasız)
- `.gitignore` önerisi üretme (`tracked-artifacts` bulgusundan türetilmiş kural listesi).
- Analiz iptali (`ProjectDoctor` döngüsünde iptal belirteci).
- Yeni diller (Kotlin, PHP, Swift) için `LanguageSpec`.
- Kayıtlı kullanıcı kural paketleri için örnek `~/.gitclean/rules` dosyası ve belge.
