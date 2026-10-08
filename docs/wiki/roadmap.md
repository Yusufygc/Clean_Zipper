# Yol Haritası

Kaynak: 2026-10-08 sistem denetimi. Mimari bağlam için [[architecture]], çalışma düzeni için [[rules]].

| # | Bulgu | Öncelik | Durum |
|---|-------|---------|-------|
| 1 | `CleanupService` `venv`/`node_modules` içinde de siliyor, yedek yok | 🔴 | Tamamlandı (2026-10-08) |
| 2 | Sağlık skoru sabit değerlere dayanıyor, alanlar doldurulmuyor | 🔴 | Tamamlandı (2026-10-08) |
| 3 | HTML raporda escape yok | 🟠 | Tamamlandı (2026-10-08) |
| 4 | Tarama 9 kez tekrarlanıyor, `rglob` dışlamaları yok sayıyor | 🟠 | Tamamlandı (2026-10-08) |
| 5 | Analizör kaydı UI içinde, arayüzler yarım uygulanmış | 🟠 | Tamamlandı (2026-10-08) |
| 6 | Sadece Python ve `requirements.txt` destekleniyor | 🟠 | Sürüyor: motor ve 8 dil hazır, ekosistemler/istatistik sırada |
| 7 | Hatalar sessizce yutuluyor, logger yok | 🟠 | Kısmen (`ProjectDoctor` loglıyor ve `failed_analyzers` tutuyor; analizörlerin içindeki `except` blokları bekliyor) |
| 8 | Test yok | 🟠 | Başladı (131 test) |
| 9 | Çift dosya bulucu tüm dosyayı belleğe okuyor | 🟠 | Tamamlandı (2026-10-08, parçalı hash) |
| 10 | Dışlama listesi birden fazla yerde tekrarlanıyor | 🟡 | Kısmen (`EXCLUDED_DIRS`: `CleanupService` ve `BaseAnalyzer` bağlı, `ArchiveService`/`BackupService` bekliyor) |
| 11 | Arşiv profil regex'leri iç içe klasörleri kaçırıyor | 🟡 | Bekliyor |
| 12 | Karmaşıklık analizörü eksikleri | 🟡 | Bekliyor |
| 13 | Build ve bağımlılık hijyeni | 🟡 | Bekliyor |

## Kararlar
- UI (`src/ui`) kullanıcı tarafından sonradan sıfırdan yazılacak. Önce backend; doğrulama pytest ve konsol ile, GUI testi yok.
- Kapsam: çok dilli analiz hedefi, CLI şart değil.
- Sıra: önce 1 ve 2, sonra adım adım.
- Silme güvenliği: kalıcı silme yerine Geri Dönüşüm Kutusu (`send2trash`).
- Kapsam dışı bu turda: `ArchiveService`/`BackupService` dışlama birleştirme, `FileIndex`, registry.

## Açık notlar
- Analiz `.gitignore`'u dikkate almıyor. `.env` dosyası `.gitignore`'da olsa bile KRİTİK bulgu üretiyor (yanlış pozitif). Ayrı karar gerektirir.
- Analizör içinde kalan geniş `except` blokları (Bulgu 7) bekliyor.
- Analiz iptal edilemiyor (UI'da iptal düğmesi yok).
- `read_text` 2 MB üstü dosyaları atlıyor: büyük kaynak dosyalar karmaşıklık ve sızıntı taramasına girmez.
- `venv` adı taşımayan sanal ortamlar (ör. `myenv`) taranıyor: `pyvenv.cfg` içeren klasörleri `ProjectIndex` içinde dışlamak gerekir.
- Bir sonraki adım: Bulgu 6 (çok dilli analiz) bu indeks ve registry üzerine kurulacak.
