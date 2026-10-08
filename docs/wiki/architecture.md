# Mimari

Python 3.10, PySide6 6.6.1 masaüstü uygulaması. Giriş noktası `main.py`. Yol haritası için [[roadmap]], kurallar için [[rules]].

## Katmanlar
- `src/models/analysis_models.py`: `Severity`, `HealthStatus`, `AnalysisResult` (bulgu), `ProjectAnalysis`, `FileInfo`.
- `src/core/`: `constants.py` (`EXCLUDED_DIRS`), `project_index.py` (tek geçişli `ProjectIndex`: dosya/klasör listesi, toplamlar, `read_text`, `hash_file`), `registry.py` (`@register_analyzer`, `load_builtin_analyzers`), `IAnalyzer` ve diğer arayüzler, `BaseAnalyzer` (bulgu üretme yardımcısı).
- `src/analyzers/`: 8 analizör (boyut, tür, çift dosya, boş klasör, yapı, güvenlik sızıntısı, bağımlılık, karmaşıklık). Her biri `@register_analyzer` ile kendini kaydeder ve `analyze(index)` ile bulgu listesi döner. Yeni analizör = tek dosya.
- `src/doctors/`: `ProjectDoctor` analizörleri çalıştırır, bulguları şiddete göre `issues/warnings/suggestions` listelerine ayırır. `HealthChecker` bulgu şiddetinden kategori ve genel skor üretir (kategoriler: security, complexity, duplicate, size, structure, dependency), `RecommendationEngine` öneri üretir.
- `src/services/`: `ProjectService` (cephe), `ArchiveService`, `CleanupService` (kategori tabanlı, Geri Dönüşüm Kutusu'na taşır), `BackupService`, `ReportService` (HTML).
- `src/ui/`: `main_window.py`, `dashboard/`, `tabs/` (arşiv, temizlik), `widgets/`, `themes/style.qss`. Ağır işler `QThread` worker'larında.

## Veri akışı
UI (`AnalyzeWorker`, QThread) → `ProjectService.analyze_project(progress)` → `ProjectDoctor.quick_scan` → `ProjectIndex.build` (tek tarama) → kayıtlı analizörler sırayla `can_analyze(index)` + `analyze(index)` → bulgular → `HealthChecker` → sözlük (`dict`) olarak dashboard'a. İlerleme `progress(yüzde, metin)` ile sinyal üzerinden döner.

## Bilinen sorunlar
Tam liste ve öncelik için [[roadmap]]. Özet: yalnızca Python analiz ediliyor, analizör içlerinde geniş `except` blokları var, analiz `.gitignore`'a duyarsız.

## Hedef yön
Çok dilli analiz (indeks ve registry hazır, dil eklentileri sırada). CLI bilinçli olarak kapsam dışı: GUI çekirdeği tek tüketici olarak kalır.

## Ortam
`venv/` Python 3.10.11 ile yeniden kuruldu (2026-10-08). Bağımlılıklar `requirements.txt` içinde. Testler `pytest` ile, ayarlar `pytest.ini` içinde.
