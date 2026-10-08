# Yol Haritası

Kaynak: 2026-10-08 sistem denetimi. Mimari bağlam için [[architecture]], çalışma düzeni için [[rules]].

| # | Bulgu | Öncelik | Durum |
|---|-------|---------|-------|
| 1 | `CleanupService` `venv`/`node_modules` içinde de siliyor, yedek yok | 🔴 | Tamamlandı (2026-10-08) |
| 2 | Sağlık skoru sabit değerlere dayanıyor, alanlar doldurulmuyor | 🔴 | Tamamlandı (2026-10-08) |
| 3 | HTML raporda escape yok | 🟠 | Tamamlandı (2026-10-08) |
| 4 | Tarama 9 kez tekrarlanıyor, `rglob` dışlamaları yok sayıyor | 🟠 | Tamamlandı (2026-10-08) |
| 5 | Analizör kaydı UI içinde, arayüzler yarım uygulanmış | 🟠 | Tamamlandı (2026-10-08) |
| 6 | Sadece Python ve `requirements.txt` destekleniyor | 🟠 | Tamamlandı (2026-10-08) |
| 7 | Hatalar sessizce yutuluyor, logger yok | 🟠 | Tamamlandı (2026-10-08) |
| 8 | Test yok | 🟠 | Başladı (585 test) |
| 9 | Çift dosya bulucu tüm dosyayı belleğe okuyor | 🟠 | Tamamlandı (2026-10-08, parçalı hash) |
| 10 | Dışlama listesi birden fazla yerde tekrarlanıyor | 🟡 | Kısmen (`exclusions.py`: analiz, temizlik ve arşiv ortak; `BackupService` bilerek yalnızca `.git` dışlıyor, karar bekliyor) |
| 11 | Arşiv profil regex'leri iç içe klasörleri kaçırıyor | 🟡 | Tamamlandı (2026-10-08) |
| 12 | Karmaşıklık analizörü eksikleri | 🟡 | Tamam (2026-10-08): Aşama 0-7: V2 eşikleri, ölü kod, sihirli sayı, klon, döngü, SAST-lite, pinleme, güvenilirlik, test/hijyen, git geçmişi, V2 denetim raporu |
| 13 | Build ve bağımlılık hijyeni | 🟡 | Bekliyor |

## Kararlar
- UI (`src/ui`) kullanıcı tarafından sonradan sıfırdan yazılacak. Önce backend; doğrulama pytest ve konsol ile, GUI testi yok.
- Kapsam: çok dilli analiz hedefi, CLI şart değil.
- Sıra: önce 1 ve 2, sonra adım adım.
- Silme güvenliği: kalıcı silme yerine Geri Dönüşüm Kutusu (`send2trash`).
- Kapsam dışı bu turda: `ArchiveService`/`BackupService` dışlama birleştirme, `FileIndex`, registry.

## Açık notlar
- Analiz iptal edilemiyor (UI'da iptal düğmesi yok).
- `read_text` 2 MB üstü dosyaları atlıyor: büyük kaynak dosyalar karmaşıklık ve sızıntı taramasına girmez.
- Java/Go yalnızca örnek kodla doğrulandı (diskte gerçek kod yoktu). Kotlin/PHP/Swift: yalnızca yeni bir `LanguageSpec` gerekir.
- Donmuş exe içinde analiz çalıştırılamadı (Windows Uygulama Denetimi imzasız exe'yi engelliyor); paket içeriği doğrulandı.
- UI yazılırken: arşiv/yedek sonucunda `complete=False` ve `failed_files` kullanıcıya gösterilmeli; `skipped_files` ve `failed_analyzers` "analiz tam mı" göstergesi olmalı.
- Karar bekliyor (kullanıcı "sonra konuşalım" dedi): `BackupService` yedeği "olduğu gibi" mi kalsın, ortak dışlama mı uygulansın. Bulgu 12 unutulmayacak.
- **Derin analiz planı (onaylı, aşama aşama):** 1 kod kalitesi (ölü kod, klon, sihirli sayı), 2 mimari (döngüsel bağımlılık), 3 SAST-lite + pinleme, 4 hata yönetimi/üretim hijyeni, 5 test + proje hijyeni, 6 git geçmişi, 7 V2 formatında denetim raporu. Aşama 0-7 bitti. Sonra Bulgu 13.
- Refactor adayları (kendi kodumuz, V2 eşiklerine göre): `brace.py:_scan_structure`, `_count_params`, `project_index.py:_scan_directory`, `build_exe.py:build_executable`.
- Fikir: git'e commit edilmiş derleme çıktısı / bağımlılık klasörü tespiti (P005'te 381 `bin/obj` dosyası izleniyor), `.gitignore` önerisi üretme.
