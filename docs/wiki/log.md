# Değişiklik Günlüğü

## [2026-10-08] [REVIEW] | Bulgu 3: HTML raporda kaçış (escape) eklendi
- `ReportService`: bulgu başlığı/açıklaması/önerisi, dosya adı, proje yolu ve not metni `html.escape` ile kaçırılıyor (`_esc`). Rapora `Content-Security-Policy` meta etiketi (`default-src 'none'`) eklendi; kaçış gözden kaçsa bile betik çalışmaz.
- `export_report` hata durumunda artık `logging.exception` ile nedeni kaydediyor (eskiden sessizce `False` dönüyordu).
- Gerçek vektör: `requirements.txt` içeriği bulgu başlığına giriyordu (`x"onmouseover="...`); uçtan uca doğrulandı. Linux/macOS dosya adlarında `<` da mümkün.
- Testler: `tests/unit/test_report_service.py` (5 test, toplam 81). Önce kırmızı, sonra yeşil.
- Kapsam dışı: `src/ui/dashboard/dashboard_panel.py` içindeki HTML etiketleri (UI sıfırdan yazılacak, bkz. [[roadmap]] Kararlar). Bkz. [[roadmap]].

## [2026-10-08] [REVIEW] | Bulgu 4+5+9: tek geçişli ProjectIndex ve analizör registry
- `src/core/project_index.py`: dosya sistemi `os.scandir` ile bir kez taranır (`FileEntry`, `DirEntry`, toplamlar, `read_text` önbelleği, `hash_file`). Dışlanan klasörlere girilmez; okunamayan yollar `errors` listesine yazılır.
- `src/core/registry.py`: `@register_analyzer` + `load_builtin_analyzers()` (pkgutil). `ProjectService` analizörleri registry'den kurar; `main_window.py` artık hiçbir analizör bilmez.
- `IAnalyzer.analyze(index)`; `can_analyze(index)` artık çağrılıyor. `BaseAnalyzer`'dan `_walk_project`, `_is_binary`, `_get_file_info` kaldırıldı.
- 8 analizör indeks üzerine taşındı. `DuplicateFinder`: boyut, ilk 64 KB, tam özet (blake2b, parçalı okuma); kopyalar dosya yoluna göre sıralı. `CodeComplexityAnalyzer.analyze` parçalandı.
- `ProjectDoctor`: istatistikler indeksten (eski `rglob` kalktı); `diagnose(path, progress=None)`; ilerleme `AnalyzeWorker.progress` sinyaliyle dashboard ilerleme kartına ve durum çubuğuna bağlandı.
- Sayılar değişti: toplam dosya/boyut artık dışlanan klasörler hariç (bu projede 6997 dosya / 333.8 MB, yeni: 79 dosya / 0.6 MB). cp1254 kodlu dosyalar artık güvenlik taramasına giriyor.
- `build_exe.py`: `--collect-submodules=src.analyzers`. Donmuş (PyInstaller) uygulamada keşif, ayrı bir prob exe ile doğrulandı (8 analizör bulundu). Bayraksız kontrol denemesi çalıştırılamadı (izin hatası), bayrağın gerekliliği kanıtlanmadı.
- Davranış karşılaştırması (aynı çalışma ağacı): bulgular aynı; yalnızca yeniden yazılan iki fonksiyon (`_collect_all_imports`, `CodeComplexityAnalyzer.analyze`) artık karmaşıklık eşiğini aşmadığı için iki ORTA bulgu kayboldu.
- Testler: `test_project_index.py`, `test_registry.py`, `test_analyzers.py`, `test_project_doctor.py` genişletildi (76 test).
- Doğrulanamadı: dashboard ilerleme çubuğunun görsel davranışı; exe içinde analiz çalıştırma (GUI etkileşimi gerekir, yalnızca açılış ve keşif doğrulandı). Bkz. [[roadmap]].

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
