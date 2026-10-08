# Mimari

Python 3.10, PySide6 6.6.1 masaüstü uygulaması. Giriş noktası `main.py`. Yol haritası için [[roadmap]], kurallar için [[rules]].

## Katmanlar
- `src/models/analysis_models.py`: `Severity`, `HealthStatus`, `AnalysisResult` (bulgu), `ProjectAnalysis`, `FileInfo`.
- `src/core/`: `constants.py` (`EXCLUDED_DIRS`, bağlamsal dışlamalar), `thresholds.py` (`QualityThresholds`, V2 eşikleri), `exclusions.py` (`is_excluded_dir`: analiz ve arşiv ortak), `project_index.py` (tek geçişli `ProjectIndex`: dosya/klasör listesi, toplamlar, `read_text`, `hash_file`), `registry.py` (`@register_analyzer`, `load_builtin_analyzers`), `IAnalyzer` ve diğer arayüzler, `BaseAnalyzer` (bulgu üretme yardımcısı).
- `src/languages/`: çok dilli çözümleme. `parse_file(index, entry)` dosya başına `SourceMetrics` (satırlar, fonksiyon/sınıf, karmaşıklık, içe aktarmalar) üretir ve indekste önbelleğe alır. Python `ast` ile (kesin; siklomatik `radon`, bilişsel Sonar kurallarıyla), 8 dil `brace.py` sözcük tabanlı motoruyla (yaklaşık). Her fonksiyon için karmaşıklık, bilişsel karmaşıklık, iç içe derinlik, parametre sayısı; `stripped()` ile yorum/string temizlenmiş görünüm (`registry.get_stripped`, bütçeli önbellek). `catalog.py` dil tanımları, `ecosystems.py` bağımlılık manifestleri.
- `src/analyzers/`: 18 analizör (boyut, tür, dil istatistikleri, çift dosya, boş klasör, yapı, güvenlik sızıntısı, bağımlılık, karmaşıklık, ölü kod, sihirli sayı, kod klonu, mimari bağımlılık, SAST-lite kod güvenliği, güvenilirlik ve üretim hijyeni, test sağlığı, proje hijyeni, git geçmişi). Kural verisi `resources/rules/*.json` (+ `~/.gitclean/rules`), yükleyici `src/core/security_rules.py`. Dile özgü saf analiz kodu `src/languages/` altındadır (`python_usage.py`, `brace_usage.py`, `clones.py`, `import_graph.py`, `python_reliability.py`, `brace_reliability.py`, `todo_markers.py`, `testing_patterns.py`); brace motoru iki dosyadır: `brace.py` (temizleme, yapı tarayıcısı `_StructureScanner`, ölçüm) ve `brace_headers.py` (`HeaderClassifier`: `{` öncesi başlık sınıflama); analizörler yalnızca bulgu üretir. Her biri `@register_analyzer` ile kendini kaydeder ve `analyze(index)` ile bulgu listesi döner. Yeni analizör = tek dosya.
- `src/doctors/`: `ProjectDoctor` analizörleri çalıştırır, bulguları şiddete göre `issues/warnings/suggestions` listelerine ayırır. `HealthChecker` bulgu şiddetinden kategori ve genel skor üretir (kategoriler: security, complexity, duplicate, size, structure, dependency), `RecommendationEngine` öneri üretir.
- `src/services/`: `ProjectService` (cephe), `ArchiveService` (profil tabanlı; `archive_profiles.py` JSON profilleri yükler), `CleanupService` (kategori tabanlı, Geri Dönüşüm Kutusu'na taşır), `BackupService`, `ReportService` (HTML, kategori puanları dahil), `AuditReportService` (V2 formatında Markdown denetim raporu; sabitler `audit_catalog.py`, kanıt / konum `audit_evidence.py`).
- `src/utils/`: `gitignore_parser.py` (`GitignoreMatcher`: iç içe `.gitignore`, git önceliği, izlenen dosya farkındalığı; `GitignoreParser` eski API), `git_info.py` (salt-okunur git: `tracked_paths`, `recent_commits`, `history_paths`; hepsi zaman aşımlı, hata olursa `None`), `logging_config.py` (`setup_logging`, istisna kancaları). `src/core/errors.py`: `GitCleanError`, `ProjectNotSelectedError`.
- `src/ui/`: `main_window.py`, `dashboard/`, `tabs/` (arşiv, temizlik), `widgets/`, `themes/style.qss`. Ağır işler `QThread` worker'larında.

## Veri akışı
UI (`AnalyzeWorker`, QThread) → `ProjectService.analyze_project(progress)` → `ProjectDoctor.quick_scan` → `ProjectIndex.build` (tek tarama; `.gitignore` uygulanır, izlenen dosyalar korunur) → kayıtlı analizörler sırayla `can_analyze(index)` + `analyze(index)` → bulgular → `HealthChecker` → sözlük (`dict`) olarak dashboard'a. İlerleme `progress(yüzde, metin)` ile sinyal üzerinden döner.

## Bilinen sorunlar
Tam liste ve öncelik için [[roadmap]]. Özet: analiz sınırları (2 MB üstü dosya vb.) `skipped_files` ile görünür.

## Hedef yön
Çok dilli analiz tamam (9 dil). Sıradaki: eşik genişletme, `.gitignore` duyarlılığı. CLI bilinçli olarak kapsam dışı: GUI çekirdeği tek tüketici olarak kalır.

## Ortam
`venv/` Python 3.10.11 ile yeniden kuruldu (2026-10-08). Çalışma zamanı bağımlılıkları `requirements.txt` (tam sabit sürüm), test `requirements-dev.txt`, EXE derleme `requirements-build.txt`. Testler `pytest` ile, ayarlar `pytest.ini` içinde. Satır sonu politikası `.gitattributes` (depo ve çalışma kopyası LF) ve `.editorconfig`.

## Hata yönetimi
Sessiz yutma yok: geniş `except` yalnızca loglayıp yeniden fırlatarak ya da sonucu `failed_*` alanlarına yazarak kullanılır (AST testiyle zorunlu). Kullanıcıya görünen işaretler: `failed_analyzers`, `skipped_files`, arşiv/yedek `failed_files` + `complete`. Loglar `~/.gitclean/logs/`.
