# Değişiklik Günlüğü

## [2026-10-08] [REVIEW] | Bulgu 2: Sağlık skoru bulgu tabanlı hale getirildi
- `HealthChecker` yeniden yazıldı: sabit `types=80` / `organization=85` kalktı. Kategori skoru `100*exp(-ceza/60)`, ceza şiddetten (KRİTİK 40, YÜKSEK 15, ORTA 5, DÜŞÜK 1). Genel skor, çalışmış kategorilerin ağırlığı yeniden normalize edilerek hesaplanıyor. `IHealthChecker` artık miras alınıyor.
- Analizör kategorileri: `SecurityLeakAnalyzer` → `security`, `CodeComplexityAnalyzer` → `complexity`, `DeadWeightAnalyzer` → `dependency`.
- `ProjectAnalysis`: `category_scores`, `failed_analyzers`, `all_findings` eklendi. `empty_dirs`, `duplicate_files`, `largest_files` artık bulgu `metadata['kind']` üzerinden doldurulur.
- Hata düzeltildi: toplam proje boyutu "tahmini kazanç" sayılıyordu (bu projede 68 MB). Artık yalnızca `metadata['reclaimable']` olan bulgular (çift dosyalar) sayılır.
- `ProjectDoctor`: çöken analizör `failed_analyzers`'a yazılır ve skordan çıkar; `print` yerine `logging`.
- Bu proje üzerinde önce/sonra: 84.4 (B+) → 88.6 (A); kazanç 68.16 MB → 0 MB; `complexity` alt skoru 47.
- Testler: `test_health_checker.py`, `test_project_doctor.py` (toplam 35 test). README skor bölümü güncellendi.
- Doğrulanamadı: dashboard'un görsel çıktısı. `update_dashboard` çağrısı hatasız çalıştı, ekran kontrolü elle gerekir. Bkz. [[roadmap]].

## [2026-10-08] [REVIEW] | Bulgu 1: CleanupService güvenli hale getirildi
- `src/core/constants.py` (`EXCLUDED_DIRS`) eklendi. `BaseAnalyzer` buna bağlandı; analizörler artık `dist`, `build`, `env`, `ENV` klasörlerini de gezmiyor.
- `CleanupService` yeniden yazıldı: `venv`/`node_modules`/`.git` taranmıyor, `__pycache__` klasörü tek öğe, kategori seçimi gerçekten uygulanıyor, silme `send2trash` ile Geri Dönüşüm Kutusu'na, hatalar `failed` listesinde.
- `.log` ve `.bak` kategorileri varsayılan kapalı. Temizlik sekmesine kategori kutuları eklendi.
- Testler: `tests/unit/test_cleanup_service.py` (9 test). Gerçek `send2trash` ile geçici klasörde elle doğrulandı.
- Doğrulanamadı: GUI görsel düzeni ve PyInstaller build'inde `send2trash` paketlenmesi (elle kontrol gerekir). Bkz. [[roadmap]].

## [2026-10-08] [INGEST] | Wiki, pytest altyapısı ve `send2trash` bağımlılığı kuruldu
- `docs/wiki/` (rules, index, architecture, roadmap, log) ve `CLAUDE.md` eklendi.
- `pytest.ini` eklendi, `send2trash>=1.8.3` `requirements.txt`'e girdi.
- Eski bozuk `venv` (başka makinenin Python yolu) silinip Python 3.10.11 ile yeniden kuruldu.
