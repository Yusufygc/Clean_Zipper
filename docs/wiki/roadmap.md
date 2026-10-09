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
| 8 | Test yok | 🟠 | Backend için tamamlandı (680+ test, bkz. [[testing]]); GUI testi bilinçli kapsam dışı |
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
Kaynak: `BACKEND_ANALIZ_RAPORU.md` (işler bitince silinecek). İddialar kodla doğrulandı; reddedilenler gerekçesiyle [[decisions]] içinde.

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
| 3 | `pyproject.toml` bağımlılıkları okunmuyor (`tomli` eklenecek) | Planlandı |
| 3 | `module_key` klasörü yok sayıyor | Planlandı |
| 3 | UTF-16 dosyalar ikilik sayılıyor | Planlandı |
| 3 | İç içe boş klasörler raporlanmıyor | Planlandı |
| 3 | Karmaşıklık uyarısında "satır kod" yanlış ifade | Planlandı |
| 3 | ViewModel'lerde `file:///` için `[8:]` kesmesi | Planlandı |
| 3 | Metin önbelleği dolunca yeni dosya önbelleğe alınmıyor (LRU yok) | Planlandı |
| - | Yalnızca ignore'lu dosya içeren klasör "boş" sayılmalı | Reddedildi ([[decisions]]) |
| - | `GitignoreMatcher._tracked` harf duyarlılığı | Ertelendi: yalnızca harf git dışından değişirse; `normcase` POSIX yolunu bozar |

## Kararlar
Tam liste ve gerekçeler: [[decisions]]. Özet: önce backend (UI sonradan sıfırdan), çok dilli analiz, CLI yok, silme kalıcı değil (Geri Dönüşüm Kutusu), kendi kodumuz kendi taramamızdan geçer.

## Açık notlar
- Analiz iptal edilemiyor (UI'da iptal düğmesi yok).
- `read_text` 2 MB üstü dosyaları atlıyor: büyük kaynak dosyalar karmaşıklık ve sızıntı taramasına girmez (`skipped_files` ile görünür).
- Java/Go yalnızca örnek kodla doğrulandı (diskte gerçek kod yoktu); C#, JS/TS ve Rust gerçek projelerde doğrulandı. Kotlin/PHP/Swift: yalnızca yeni bir `LanguageSpec` gerekir.
- Donmuş exe içinde analiz çalıştırılamadı (Windows Uygulama Denetimi imzasız exe'yi engelliyor); paket içeriği doğrulandı.
- UI yazılırken: arşiv/yedek sonucunda `complete=False` ve `failed_files` kullanıcıya gösterilmeli; `skipped_files` ve `failed_analyzers` "analiz tam mı" göstergesi olmalı ([[backend-api]]).
- Kendi taramamızın bilinçli bırakılan bulguları: 4 UI işlevi (yeniden yazılacak) ve `BaseAnalyzer._create_result` (7 parametreli genel API).
- Geçişli bağımlılıklar için kilit dosyası (`pip freeze` türevi) üretilmedi; yalnızca doğrudan bağımlılıklar tam sabit.
- README'deki "son N yedeği saklama" ifadesinin kodda karşılığı yok.

## Sonraki adaylar (onay bekliyor, öncelik sırasız)
- `.gitignore` önerisi üretme (`tracked-artifacts` bulgusundan türetilmiş kural listesi).
- Analiz iptali (`ProjectDoctor` döngüsünde iptal belirteci).
- Yeni diller (Kotlin, PHP, Swift) için `LanguageSpec`.
- Yedekte eski yedekleri temizleme (son N saklama) ya da README'den kaldırma.
- Kayıtlı kullanıcı kural paketleri için örnek `~/.gitclean/rules` dosyası ve belge.
