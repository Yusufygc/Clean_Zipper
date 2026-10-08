# Analizör Kataloğu

18 analizör, 11 puanlanan kategori. Katman bağlamı için [[architecture]], tüketici arayüzü için [[backend-api]], doğrulama yöntemleri için [[testing]], alınan kararlar için [[decisions]].

Her analizör `src/analyzers/` altında tek dosyadır, `@register_analyzer` ile kendini kaydeder (`src/core/registry.py`, `pkgutil` ile otomatik keşif) ve `analyze(index) -> List[AnalysisResult]` döner. `ProjectIndex` tek tarama yapar; dosya başına ölçüm `parse_file(index, entry)` ile bir kez üretilir ve paylaşılır.

## Bulgu sözleşmesi
- `AnalysisResult`: `analyzer_name`, `category`, `severity` (`INFO` < `LOW` < `MEDIUM` < `HIGH` < `CRITICAL`), `title`, `description`, `file_path`, `size_impact`, `recommendation`, `metadata`.
- `metadata['rule']`: kural kimliği (kapatmak için `disabled_rules`). `approximate`: sonuç sözcük tabanlıysa `True`. `language`, satır bilgisi (`line`, `start_line` ya da `lines`) ve kurala özgü alanlar.
- Aynı kuraldan çok sayıda bulgu üretilen yerde bulgu dosya başına / fonksiyon başına birleştirilir (gürültü azaltma).
- Python dışındaki 8 dil (JS, TS, Java, C#, C, C++, Go, Rust) `brace.py` sözcük tabanlı motoruyla çözümlenir: sonuçlar yaklaşıktır ve bulguda `approximate=True` olur.

## Katalog
Sıra, çalışma önceliğidir (küçük önce). `*` ile işaretli kategori puanlanmaz (bilgi amaçlı).

| Öncelik | Analizör | Kategori | Kurallar (`metadata['rule']` / `kind`) |
|---|---|---|---|
| 10 | `SizeAnalyzer` | size | `large_file`, `total_size` |
| 12 | `CodeComplexityAnalyzer` | complexity | `function-metrics`, `class-size`, `file-length`, `module-imports` |
| 14 | `DeadCodeAnalyzer` | deadcode | `unused-import`, `unused-variable`, `unreachable-code` |
| 15 | `SecurityLeakAnalyzer` | security | `hardcoded-secret`, `provider-secret`, `sensitive_file` |
| 16 | `CodeSecurityAnalyzer` | security | SAST-lite: `resources/rules/security_rules.json` (39 kural: `py-*`, `js-*`, `java-*`, `cs-*`, `c-*`, `go-*`, `rust-*`) |
| 16 | `MagicNumberAnalyzer` | deadcode | `magic-numbers` |
| 18 | `CloneAnalyzer` | duplicate | `code-clone`, `clone-summary` |
| 20 | `TypeAnalyzer` | type* | dosya türü dağılımı |
| 22 | `LanguageStatsAnalyzer` | type* | `language_stats` (satır / dosya sayıları) |
| 25 | `DeadWeightAnalyzer` | dependency | `unused-dependency`, `unpinned-dependencies`, `dev-dependency-in-runtime` |
| 30 | `ArchitectureAnalyzer` | architecture | `import-cycle`, `dependency-graph` |
| 30 | `DuplicateFinder` | duplicate | `duplicate_group` (aynı içerikli dosyalar) |
| 35 | `ReliabilityAnalyzer` | reliability | `bare-except`, `swallowed-exception`, `empty-catch`, `open-without-encoding`, `naive-datetime`, `debug-flag`, `debugger-statement`, `print-density`, `todo-inventory` |
| 40 | `EmptyFolderFinder` | structure | `empty_dir` |
| 40 | `TestingAnalyzer` | testing | `no-tests`, `low-test-ratio`, `untested-modules`, `test-sleep`, `test-real-network`, `test-summary` |
| 45 | `ProjectHygieneAnalyzer` | hygiene | `missing-readme/license/gitignore/ci/lockfile/env-example`, `tracked-artifacts`, `hygiene-summary` |
| 50 | `GitHistoryAnalyzer` | git* (+ security) | `secret-in-history` (security), `hotspot`, `co-change` |
| 50 | `StructureAnalyzer` | structure | klasör yapısı denetimi |

## Önemli kural ayrıntıları
- **`function-metrics`:** tek fonksiyon birden çok eşiği aşarsa tek bulgu. Siklomatik, bilişsel ve iç içe derinlik ORTA; uzunluk ve parametre DÜŞÜK; eşiğin 2 katı bir seviye yukarı. Python'da kesin (`ast`; siklomatik `radon`, bilişsel Sonar kurallarıyla), diğer dillerde yaklaşık. `class-size` YÜKSEK (God Object), `file-length` ORTA (2 katı YÜKSEK), `module-imports` DÜŞÜK.
- **Ölü kod:** `unused-import` DÜŞÜK (`# noqa` ve `__all__` dikkate alınır), `unused-variable` DÜŞÜK, `unreachable-code` ORTA (Python) / DÜŞÜK (brace). `magic-numbers` dosya başına tek DÜŞÜK bulgu.
- **Klon:** Tip-1 (birebir aynı satırlar, yorumlar hariç), 8 satırlık pencere; ≥ 20 satır ORTA, daha kısası DÜŞÜK.
- **Mimari:** Python (mutlak + göreli) ve JS/TS için dosya grafiği, Tarjan SCC. `import-cycle` ORTA, ≥ 4 dosya YÜKSEK. `if TYPE_CHECKING` ve fonksiyon içi import grafiğe girmez.
- **Güvenlik:** `hardcoded-secret` YÜKSEK (test klasöründe DÜŞÜK); sağlayıcı anahtarları (AWS, GitHub, Slack, Google, Stripe, JWT, PEM) sağlayıcıya göre; bulguya **değer yazılmaz**, yalnızca maskeli önek. `sensitive_file` KRİTİK (`.env`, `credentials.json`, `secrets.yaml`). Kullanıcı kuralları `~/.gitclean/rules`.
- **Güvenilirlik:** `bare-except` YÜKSEK; `swallowed-exception`, `empty-catch`, `open-without-encoding`, `debug-flag`, `debugger-statement` ORTA; `naive-datetime`, `print-density` DÜŞÜK; `todo-inventory` BİLGİ. Yorumla gerekçelendirilmiş yutma bulgu sayılmaz.
- **Test:** `no-tests` (≥ 100 kaynak satırı, ORTA; > 500 YÜKSEK), `low-test-ratio` (< 0,3 DÜŞÜK, < 0,1 ORTA), `untested-modules`, `test-summary` BİLGİ. Kaynak-test eşleme ada bakar, bu yüzden `untested-modules` yalnızca bilgidir.
- **Hijyen:** eksik madde DÜŞÜK; `tracked-artifacts` bağımlılık klasörü ORTA, diğerleri DÜŞÜK (`dist`/`build` `approximate`; `lib/`, `vendor/` altı sayılmaz). `hygiene-summary` BİLGİ `present` / `missing` listeleri ([[backend-api]] denetim raporunun "iyi pratikler" bölümünü besler).
- **Bağımlılık:** `unused-dependency` ORTA, `unpinned-dependencies` ve `dev-dependency-in-runtime` DÜŞÜK; Python, npm, Go, Rust manifestleri.
- **Git:** salt-okunur, zaman aşımlı; git yoksa sessizce atlanır. `secret-in-history` YÜKSEK (test klasöründe ORTA) ve `security` kategorisinde puanlanır; `hotspot` / `co-change` `git` kategorisinde bilgi amaçlıdır. 30'dan fazla dosyalı commit'ler ve 20'den kısa geçmişler atlanır.

## Eşikler (`QualityThresholds`, `src/core/thresholds.py`)
Varsayılanlar `V2-GenelSablon.md` "Ölçüm Eşikleri" tablosudur; eşik AŞILIRSA (`>`) bulgu üretilir. `ProjectService(thresholds=...)` ile geçersiz kılınır.

| Eşik | Değer | Eşik | Değer |
|---|---|---|---|
| siklomatik | 10 | sınıf metodu | 20 |
| bilişsel | 15 | dosya başına import | 25 |
| fonksiyon satırı | 50 | sihirli sayı (dosya başına) | 10 |
| sınıf satırı | 300 | `print` çağrısı (dosya başına) | 5 |
| dosya satırı | 500 | klon uzunluğu / ağır klon | 8 / 20 satır |
| parametre | 5 | test oranı (düşük / ağır) | 0,3 / 0,1 |
| iç içe derinlik | 4 | `severe_factor` | 2,0 |

## Skor
- Kategori puanı: `100 × exp(-ceza / 60)`; ceza: KRİTİK 40, YÜKSEK 15, ORTA 5, DÜŞÜK 1, BİLGİ 0.
- Genel skor: kategori puanlarının ağırlıklı ortalaması; çalışmayan analizörün kategorisi hesaba katılmaz ve ağırlıklar yeniden normalleştirilir.
- Ağırlıklar: security .20, complexity .16, duplicate .10, size .08, structure .08, dependency .08, reliability .08, deadcode .06, architecture .06, testing .06, hygiene .04.
- Notlar (`HealthStatus`): A+ ≥ 95, A ≥ 85, B+ ≥ 75, B ≥ 65, C+ ≥ 55, C ≥ 45, D ≥ 35, F < 35.

## Yeni analizör eklemek
1. `src/analyzers/<ad>_analyzer.py`, `BaseAnalyzer` türet, `@register_analyzer` ekle, `name` ve `category` ver.
2. Bulgulara `rule=` ver; sözcük tabanlıysa `approximate=True`.
3. Dosya adı `test_` ile başlamasın (test sayılır); bkz. [[decisions]].
4. `tests/unit/test_registry.py` ve `test_project_doctor.py` içindeki analizör sayılarını güncelle.
5. Yeni kategori puanlanacaksa `HealthChecker.WEIGHTS`, `audit_catalog.CATEGORY_NAMES` ve `DIMENSIONS` güncellenir.
6. Kendi kodunu kendi taramanla çalıştır (dogfooding), bulgusuz olmalı; bkz. [[rules]].
