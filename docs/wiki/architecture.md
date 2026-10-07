# Mimari

Python 3.10, PySide6 6.6.1 masaüstü uygulaması. Giriş noktası `main.py`. Yol haritası için [[roadmap]], kurallar için [[rules]].

## Katmanlar
- `src/models/analysis_models.py`: `Severity`, `HealthStatus`, `AnalysisResult` (bulgu), `ProjectAnalysis`, `FileInfo`.
- `src/core/`: `constants.py` (`EXCLUDED_DIRS`), `IAnalyzer` ve diğer arayüzler, `BaseAnalyzer` (dizin gezme, bulgu üretme yardımcıları).
- `src/analyzers/`: 8 analizör (boyut, tür, çift dosya, boş klasör, yapı, güvenlik sızıntısı, bağımlılık, karmaşıklık). Her biri `analyze(project_path)` ile bulgu listesi döner.
- `src/doctors/`: `ProjectDoctor` analizörleri çalıştırır, bulguları şiddete göre `issues/warnings/suggestions` listelerine ayırır. `HealthChecker` bulgu şiddetinden kategori ve genel skor üretir (kategoriler: security, complexity, duplicate, size, structure, dependency), `RecommendationEngine` öneri üretir.
- `src/services/`: `ProjectService` (cephe), `ArchiveService`, `CleanupService` (kategori tabanlı, Geri Dönüşüm Kutusu'na taşır), `BackupService`, `ReportService` (HTML).
- `src/ui/`: `main_window.py`, `dashboard/`, `tabs/` (arşiv, temizlik), `widgets/`, `themes/style.qss`. Ağır işler `QThread` worker'larında.

## Veri akışı
UI → `ProjectService.analyze_project` → `ProjectDoctor.quick_scan` → her analizör kendi `os.walk` taramasını yapar → bulgular → `HealthChecker` → sözlük (`dict`) olarak dashboard'a.

## Bilinen sorunlar
Tam liste ve öncelik için [[roadmap]]. Özet: analizör kaydı `main_window.py` içinde, her analizör ayrı tarama yapıyor, yalnızca Python analiz ediliyor, test yok.

## Hedef yön
Çok dilli analiz, tek geçişli dosya indeksi, eklenti benzeri analizör kaydı, gerçek skorlama. CLI bilinçli olarak kapsam dışı: GUI çekirdeği tek tüketici olarak kalır.

## Ortam
`venv/` Python 3.10.11 ile yeniden kuruldu (2026-10-08). Bağımlılıklar `requirements.txt` içinde. Testler `pytest` ile, ayarlar `pytest.ini` içinde.
