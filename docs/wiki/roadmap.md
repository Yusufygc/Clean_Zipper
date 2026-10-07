# Yol Haritası

Kaynak: 2026-10-08 sistem denetimi. Mimari bağlam için [[architecture]], çalışma düzeni için [[rules]].

| # | Bulgu | Öncelik | Durum |
|---|-------|---------|-------|
| 1 | `CleanupService` `venv`/`node_modules` içinde de siliyor, yedek yok | 🔴 | Tamamlandı (2026-10-08) |
| 2 | Sağlık skoru sabit değerlere dayanıyor, alanlar doldurulmuyor | 🔴 | Tamamlandı (2026-10-08) |
| 3 | HTML raporda escape yok | 🟠 | Bekliyor |
| 4 | Tarama 9 kez tekrarlanıyor, `rglob` dışlamaları yok sayıyor | 🟠 | Bekliyor |
| 5 | Analizör kaydı UI içinde, arayüzler yarım uygulanmış | 🟠 | Bekliyor |
| 6 | Sadece Python ve `requirements.txt` destekleniyor | 🟠 | Bekliyor |
| 7 | Hatalar sessizce yutuluyor, logger yok | 🟠 | Kısmen (`ProjectDoctor` loglıyor ve `failed_analyzers` tutuyor; analizörlerin içindeki `except` blokları bekliyor) |
| 8 | Test yok | 🟠 | Başladı (pytest altyapısı, 35 test) |
| 9 | Çift dosya bulucu tüm dosyayı belleğe okuyor | 🟠 | Bekliyor |
| 10 | Dışlama listesi birden fazla yerde tekrarlanıyor | 🟡 | Kısmen (`EXCLUDED_DIRS`: `CleanupService` ve `BaseAnalyzer` bağlı, `ArchiveService`/`BackupService` bekliyor) |
| 11 | Arşiv profil regex'leri iç içe klasörleri kaçırıyor | 🟡 | Bekliyor |
| 12 | Karmaşıklık analizörü eksikleri | 🟡 | Bekliyor |
| 13 | Build ve bağımlılık hijyeni | 🟡 | Bekliyor |

## Kararlar
- Kapsam: çok dilli analiz hedefi, CLI şart değil.
- Sıra: önce 1 ve 2, sonra adım adım.
- Silme güvenliği: kalıcı silme yerine Geri Dönüşüm Kutusu (`send2trash`).
- Kapsam dışı bu turda: `ArchiveService`/`BackupService` dışlama birleştirme, `FileIndex`, registry.

## Yeni bulgu
- `RecommendationEngine` ve `ProjectDoctor._collect_stats` boyutu `rglob` ile hesaplıyor; `venv` ve `.git` dahil. "Büyük proje boyutu 335 MB" önerisi bu yüzden şişiyor. Bulgu 4 ile birlikte çözülecek.
