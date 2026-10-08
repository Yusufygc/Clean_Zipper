# Mimari

Python 3.10, PySide6 6.6.1 masaüstü uygulaması. Giriş noktası `main.py`. Yol haritası için [[roadmap]], kurallar için [[rules]].

## Katmanlar
- `src/models/analysis_models.py`: `Severity`, `HealthStatus`, `AnalysisResult` (bulgu), `ProjectAnalysis`, `FileInfo`.
- `src/core/`: `constants.py` (`EXCLUDED_DIRS`, bağlamsal dışlamalar), `exclusions.py` (`is_excluded_dir`: analiz ve arşiv ortak), `project_index.py` (tek geçişli `ProjectIndex`: dosya/klasör listesi, toplamlar, `read_text`, `hash_file`), `registry.py` (`@register_analyzer`, `load_builtin_analyzers`), `IAnalyzer` ve diğer arayüzler, `BaseAnalyzer` (bulgu üretme yardımcısı).
- `src/languages/`: çok dilli çözümleme. `parse_file(index, entry)` dosya başına `SourceMetrics` (satırlar, fonksiyon/sınıf, karmaşıklık, içe aktarmalar) üretir ve indekste önbelleğe alır. Python `ast` ile (kesin), 8 dil `brace.py` sözcük tabanlı motoruyla (yaklaşık). `catalog.py` dil tanımları, `ecosystems.py` bağımlılık manifestleri.
- `src/analyzers/`: 9 analizör (boyut, tür, dil istatistikleri, çift dosya, boş klasör, yapı, güvenlik sızıntısı, bağımlılık, karmaşıklık). Her biri `@register_analyzer` ile kendini kaydeder ve `analyze(index)` ile bulgu listesi döner. Yeni analizör = tek dosya.
- `src/doctors/`: `ProjectDoctor` analizörleri çalıştırır, bulguları şiddete göre `issues/warnings/suggestions` listelerine ayırır. `HealthChecker` bulgu şiddetinden kategori ve genel skor üretir (kategoriler: security, complexity, duplicate, size, structure, dependency), `RecommendationEngine` öneri üretir.
- `src/services/`: `ProjectService` (cephe), `ArchiveService` (profil tabanlı; `archive_profiles.py` JSON profilleri yükler), `CleanupService` (kategori tabanlı, Geri Dönüşüm Kutusu'na taşır), `BackupService`, `ReportService` (HTML).
- `src/utils/`: `gitignore_parser.py` (okunamazsa `load_error`), `logging_config.py` (`setup_logging`, istisna kancaları). `src/core/errors.py`: `GitCleanError`, `ProjectNotSelectedError`.
- `src/ui/`: `main_window.py`, `dashboard/`, `tabs/` (arşiv, temizlik), `widgets/`, `themes/style.qss`. Ağır işler `QThread` worker'larında.

## Veri akışı
UI (`AnalyzeWorker`, QThread) → `ProjectService.analyze_project(progress)` → `ProjectDoctor.quick_scan` → `ProjectIndex.build` (tek tarama) → kayıtlı analizörler sırayla `can_analyze(index)` + `analyze(index)` → bulgular → `HealthChecker` → sözlük (`dict`) olarak dashboard'a. İlerleme `progress(yüzde, metin)` ile sinyal üzerinden döner.

## Bilinen sorunlar
Tam liste ve öncelik için [[roadmap]]. Özet: analiz `.gitignore`'a duyarsız.

## Hedef yön
Çok dilli analiz tamam (9 dil). Sıradaki: eşik genişletme, `.gitignore` duyarlılığı. CLI bilinçli olarak kapsam dışı: GUI çekirdeği tek tüketici olarak kalır.

## Ortam
`venv/` Python 3.10.11 ile yeniden kuruldu (2026-10-08). Bağımlılıklar `requirements.txt` içinde. Testler `pytest` ile, ayarlar `pytest.ini` içinde.

## Hata yönetimi
Sessiz yutma yok: geniş `except` yalnızca loglayıp yeniden fırlatarak ya da sonucu `failed_*` alanlarına yazarak kullanılır (AST testiyle zorunlu). Kullanıcıya görünen işaretler: `failed_analyzers`, `skipped_files`, arşiv/yedek `failed_files` + `complete`. Loglar `~/.gitclean/logs/`.
