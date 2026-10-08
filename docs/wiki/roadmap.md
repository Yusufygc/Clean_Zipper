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
| 8 | Test yok | 🟠 | Backend için tamamlandı (635 test, bkz. [[testing]]); GUI testi bilinçli kapsam dışı |
| 9 | Çift dosya bulucu tüm dosyayı belleğe okuyor | 🟠 | Tamamlandı (2026-10-08, parçalı hash) |
| 10 | Dışlama listesi birden fazla yerde tekrarlanıyor | 🟡 | Tamamlandı (2026-10-09): analiz, temizlik, arşiv ve yedek `exclusions.py` kullanır; yedek `.gitignore` uygulamaz ([[decisions]]) |
| 11 | Arşiv profil regex'leri iç içe klasörleri kaçırıyor | 🟡 | Tamamlandı (2026-10-08) |
| 12 | Karmaşıklık analizörü eksikleri | 🟡 | Tamamlandı (2026-10-08): Aşama 0-7, bkz. aşağıdaki plan ve [[analyzers]] |
| 13 | Build ve bağımlılık hijyeni | 🟡 | Tamamlandı (2026-10-09) |

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
