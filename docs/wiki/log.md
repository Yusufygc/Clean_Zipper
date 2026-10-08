# Değişiklik Günlüğü

## [2026-10-08] [REVIEW] | `.gitignore` duyarlılığı: iç içe kurallar, izlenen dosyalar, güvenlik analizi
- `GitignoreMatcher` (`src/utils/gitignore_parser.py`): her klasörün `.gitignore`'u tembel yüklenir (+ `.git/info/exclude`), git önceliği (derindeki kural kazanır, `!` geri alır), ignore'lu klasörün içi geri eklenemez, okunamayan dosya `load_errors`. `GitignoreParser` eski API'yi korur (kök dosya erken yüklenir). Gerçek `git check-ignore` ile 25 yolda çapraz doğrulandı (test olarak duruyor).
- `ProjectIndex.build(respect_gitignore=True)`: ignore'lu dosya/klasör indekse girmez ve `gitignored` sayaçlarına yazılır; ignore'lu dosyası olan klasör "boş" sayılmaz. `ProjectAnalysis.gitignore_applied` / `ignored_by_gitignore`, `quick_scan` alanları, `ProjectService(respect_gitignore=)`.
- `src/utils/git_info.py` `tracked_paths()`: `git ls-files -z` (salt-okunur: `GIT_OPTIONAL_LOCKS=0`, `core.fsmonitor=false`, istem yok, zaman aşımı, Windows'ta konsol penceresi yok); git yoksa/depo değilse `None`, asla fırlatmaz.
- **Git semantiği düzeltmesi (gerçek veriyle bulundu):** izlenen dosya ignore kuralına uysa bile ignore sayılmaz. P005'in `.gitignore`'u kendi adını içeriyordu; ilk sürüm onu arşivden eliyordu. Matcher artık izlenen kümeyi alır (`set_tracked`); izlenen dosyası olan klasör budanmaz.
- `SecurityLeakAnalyzer` hassas dosyalar için üç durum: izlenen (ignore'lu olsa bile) → KRİTİK "git'e commit edilmiş" (+ "zaten .gitignore'da" bilgisi); izlenmeyen ve ignore'sız → KRİTİK "commit edilme riski"; izlenmeyen ve ignore'lu → bulgu yok. Eski mesajdaki yanlış "proje kökünde" ifadesi kalktı. Ignore'lu dosyalarda anahtar/şifre regex taraması artık yapılmıyor. Gerileme önlemi: commit edilmiş sonra ignore'lanmış `.env` sessizliğe düşmüyor (gerçek git deposuyla test).
- `ArchiveService`: iç içe `.gitignore` (eskiden yalnızca kök), ignore'lu klasör budama, arşiv anında izlenen dosya kümesi yenilenir, iç içe `.gitignore` okunamazsa çıktı oluşmadan reddedilir.
- **Doğrulama (gerçek veri):** 23 git deposunda arşiv (Standart profil) dosya kümesi `git ls-files --cached --others --exclude-standard` ile birebir: zip-fazla 0, açıklanamayan eksik 0 (tek fark P005'te 381 izlenen `bin/obj` derleme çıktısı, bilinçli dışlama). 14 depoda indekste kalan her dosya `git ls-files` içinde; P009 1495 → 91, P017 746 → 29 dosya. `.env` bulgusu çıkan depo yok.
- Yan bulgu: P005 deposunda 381 derleme çıktısı (`bin/obj`) git'e commit edilmiş; bunu tespit eden bir analizör yok (roadmap'te fikir).
- Testler: `test_gitignore_matcher.py` (14, gerçek `git check-ignore` ve `git ls-files` oracle'ları dahil), `test_git_info.py` (9), güvenlik, indeks, doktor ve arşiv testleri genişletildi; toplam 276 test (git yoksa git'li olanlar atlanır).
- Doğrulanamadı: çok büyük depolarda `git ls-files` süresi (yalnızca küçük/orta depolar denendi, 15 sn zaman aşımı var). Bkz. [[roadmap]].

## [2026-10-08] [REVIEW] | Bulgu 11 (+ Bulgu 10'un arşiv kısmı): arşiv profilleri gitignore sözdizimiyle
- Sorun (konsolda doğrulandı): `re.match` yalnızca yol başında eşleştiğinden temiz profillerde `src/tests/a.py`, `pkg/test/b.py`, `src/test_x.py`, `*.test.ts` sızıyordu; Minimal profilde `backend/.env` (gizli dosya) arşive giriyordu; Standart profilde `.venv`/`myenv` giriyordu; bilinmeyen profil adı sessizce "hiçbir şeyi eleme" oluyordu.
- Profiller artık `resources/profiles/*.json` (`01-standart`, `02-musteri-teslimi`, `03-yayinlama`; `extends` desteği) ve `~/.gitclean/profiles/*.json` (geçersiz kılma/ekleme). `src/services/archive_profiles.py`: yükleme, doğrulama, döngü korumalı `extends`, bozuk dosya atlama + loglama, hiç profil yoksa eleme yapmayan varsayılan, PyInstaller `_MEIPASS` yolu.
- Desenler gitignore sözdizimi (pathspec): klasör adları her derinlikte (`tests/`), dosya adı kuralları kökte (`/README*`), `.env*` her derinlikte. `make_pathspec` yardımcı: `'gitignore'` fabrikası, eski pathspec'te `'gitwildmatch'` (DeprecationWarning kalktı).
- `src/core/exclusions.py` (`is_excluded_dir`): `ProjectIndex` ve `ArchiveService` aynı klasör dışlamasını kullanıyor (EXCLUDED_DIRS + bağlamsal `target`/`bin`/`obj` + `pyvenv.cfg`).
- `ArchiveService`: `profiles` enjekte edilebilir, `PROFILES` özelliği UI uyumlu sözlük; bilinmeyen profil `success=False` ve "Geçerli profiller: ..." mesajı.
- Gerçek proje ölçümü (eski/yeni kod, aynı proje): C# projesi (P005) 383 dosya / 23.2 MB → 58 dosya / 0.05 MB (`bin/obj` derleme çıktısı artık girmiyor); TS/Rust projesi (P023) temiz profillerde 4 `*.test.ts` sızıntısı → 0; bu repo Standart 104 → 99 (araç önbellekleri).
- Testler: `test_archive_profiles.py` (40), `test_exclusions.py`, `test_archive_service.py` genişletildi, `tests/conftest.py` (kullanıcı profil klasörü yalıtımı); toplam 234 test.
- Kullanıcı kararı: "Müşteri Teslimi (Temiz)" profiline `.env*` eklendi (her derinlikte); Minimal bunu `extends` ile devralıyor, kendi listesinden kaldırıldı.
- Doğrulanamadı: donmuş exe içinde profil yükleme (Uygulama Denetimi imzasız exe'yi engelliyor); `_MEIPASS` yolu birim testle doğrulandı. Bkz. [[roadmap]].

## [2026-10-08] [REVIEW] | Bulgu 7: hata yönetimi ve loglama
- `src/utils/logging_config.py`: `setup_logging()` (dönen dosya `~/.gitclean/logs/gitclean.log`, `GITCLEAN_LOG_LEVEL`, idempotent) ve `sys.excepthook` / `threading.excepthook` ile yakalanmayan istisnaların kaydı. `main.py` çağırıyor. Gerçek bir alt süreçte doğrulandı: yakalanmayan `RuntimeError` log dosyasında traceback ile görünüyor.
- `src/core/errors.py`: `GitCleanError`, `ProjectNotSelectedError(ValueError)`; `ProjectService` düz `ValueError` yerine bunu fırlatıyor.
- `GitignoreParser`: `utf-8-sig` + `errors='replace'` (BOM'lu / cp1254 `.gitignore` artık okunuyor); `OSError` → `load_error`. `ArchiveService` `load_error` doluysa arşivi reddediyor (gizli dosya sızıntısı önlemi).
- `ArchiveService` (ortak `_collect_files` ile iki kopya döngü birleşti), `BackupService`: dosya başına hata `failed_files`'a yazılıp devam ediliyor, `complete` bayrağı; ölümcül hatada yarım zip siliniyor ve `logger.exception`. Eski bir hata da düzeldi: kaynak dışına işaret eden symlink `relative_to` ile `ValueError` fırlatıyordu.
- `ProjectIndex.skipped` + `mark_skipped`: `too_large`, `unreadable`, `parse_error`, `minified`; `ProjectAnalysis.skipped_files` (okunamayan klasörler `unreadable_dir`) ve `quick_scan['skipped_files']`. `DuplicateFinder` ve `CleanupService` hataları loglanıyor.
- Gerileme koruması: `test_skipped_and_hygiene.py` içindeki AST testi `src/` (UI hariç) altında çıplak `except:` ve loglamayan/yeniden fırlatmayan `except Exception` bloklarını yasaklıyor (dedektörün sessiz bloğu yakaladığı ayrıca doğrulandı).
- Konsol doğrulaması: Windows'ta `CreateFileW` paylaşım modu 0 ile gerçek dosya kilidi → `create_zip` `success=True`, `complete=False`, `failed_files=[locked.txt]`, log satırı yazıldı. 2,4 MB dosya `skipped_files={'too_large': 1}`; bu repo için `{}`.
- Testler: `test_logging_config.py` (9), `test_archive_service.py` (13), `test_skipped_and_hygiene.py` (10); toplam 183 test.
- Doğrulanamadı: UI'nın `complete=False` durumunu göstermesi (UI yeniden yazılacak; not edildi). Bkz. [[roadmap]].

## [2026-10-08] [REVIEW] | Bulgu 6 tamamlandı: ekosistemler, dil istatistikleri, bağlamsal dışlama
- `src/languages/ecosystems.py`: Python (`requirements.txt`), npm (`package.json` `dependencies`, `scripts` içindeki CLI kullanımı sayılır), Go (`go.mod`, `// indirect` atlanır), Rust (`Cargo.toml`, `use` ve `crate::` tam yol kullanımı). Manifestin klasör alt ağacı kapsamdır. `DeadWeightAnalyzer` buna bağlandı; "requirements.txt eksik" bildirimi artık yalnızca Python kaynağı olup hiçbir Python manifesti (`requirements.txt`, `pyproject.toml`, `Pipfile`, `setup.py`, `setup.cfg`) olmayan projelerde.
- Davranış değişikliği: Python araç paketleri (pytest, pyinstaller, black, ...) artık "kullanılmayan" diye raporlanmıyor.
- `LanguageStatsAnalyzer` (kategori `type`, puanlanmaz) ve `ProjectAnalysis.language_stats`; `quick_scan` çıktısında `language_stats`. Kayıtlı analizör sayısı 8 → 9.
- Bağlamsal dışlama (`ProjectIndex`): yanında `Cargo.toml`/`pom.xml`/`build.gradle` olan `target`, yanında `.csproj` olan `bin`/`obj`, `pyvenv.cfg` içeren her klasör (örn. `myenv`) taranmıyor. Tauri projesinde 5672 → 80 dosya, 10.6 sn → 0.14 sn.
- Gerçek proje denemeleri: Tauri (TS+Rust) projesinde `clsx`, `tailwind-merge` (package.json) ve `serde_json` (Cargo.toml) gerçekten kullanılmıyordu (grep ile doğrulandı); C# projesi (26 dosya) ve bu repo hatasız analiz edildi, `failed_analyzers` boş.
- Testler: `test_ecosystems.py` (14), `test_project_index.py` ve `test_analyzers.py` genişletildi (toplam 151 test).
- Paketleme: prob exe derlendi, PYZ içeriğinde `src.languages.*` ve 9 analizör modülünün tamamı var. **Exe çalıştırılamadı:** Windows "Uygulama Denetimi" ilkesi imzasız prob exe'yi engelledi (aşılmadı). Donmuş uygulamada uçtan uca analiz doğrulanmadı; yalnızca daha önceki prob ile analizör keşfi doğrulanmıştı.
- Java ve Go için diskte gerçek kod olmadığından yalnızca örnek kodla doğrulandı. Bkz. [[roadmap]].

## [2026-10-08] [INGEST] | Bulgu 6 (çok dilli analiz) yarım: adım 1-3 bitti, 4-6 sırada
- Yeni `src/languages/` katmanı: `base.py` (FunctionInfo/ClassInfo/SourceMetrics), `registry.py` (`parse_file`, indekste önbellekli, üretilmiş dosyaları atlar), `python_lang.py` (ast; `async` artık sayılıyor, içe aktarmalar ast'ten), `brace.py` (sözcük tabanlı motor), `catalog.py` (C, C++, C#, Java, JS, TS, Go, Rust tanımları).
- `ProjectIndex.memo(...)` eklendi. `CodeComplexityAnalyzer` dil bağımsız hale geldi (eşikler aynı; bulgulara `language`, `approximate` metadata).
- Testler: `test_language_registry.py`, `test_brace_lexer.py`, `test_languages.py` (toplam 131 test yeşil). Beklenen değerler örnek kodda elle sayıldı.
- Commit edilmedi (çalışma ağacında).
- **Kalan adımlar:** (4) `src/languages/ecosystems.py` + `DeadWeightAnalyzer` (requirements.txt, package.json, go.mod, Cargo.toml; "requirements eksik" uyarısı yalnızca Python projesinde), (5) `LanguageStatsAnalyzer` + `ProjectAnalysis.language_stats` + kayıt sayısı testleri 8 → 9, (6) gerçek kod doğrulaması ve belgeler (README, architecture, roadmap).
- **Gerçek kod doğrulaması (C:\2UYGULAMALAR, 34 bin dosya):** çökme yok, dengesiz parantez 0. İlk koşuda `.next` derleme çıktıları ve küçültülmüş paketler 52 sn sürdü ve 4584 gibi anlamsız karmaşıklıklar üretti. Düzeltmeler: `EXCLUDED_DIRS`'e `.next`, `.nuxt`, `.svelte-kit`, `.turbo`, `.parcel-cache`, `.gradle`, `.tox`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `coverage`, `htmlcov` eklendi; `looks_minified` (satır uzunluğu) ile paketlenmiş dosyalar atlanıyor. Sonuç: 17 sn (çoğu 5489 Python dosyası), JS 1289 → 117 dosya.
- **Elle örnekleme (bağımsız grep sayımı):** TS `drawComposition` 51 ✓, Rust `run_ffmpeg_export` 11 ✓, C# `Edit` 21 (grep 22 saydı; fark satır sonu yorumundaki "for" kelimesi, motor doğru). Java ve Go için diskte gerçek kod yok; yalnızca örneklerle doğrulandı.
- Yeni bulgu: `myenv` gibi `venv` adı taşımayan sanal ortamlar Python sayılarını şişiriyor. `pyvenv.cfg` içeren klasörleri otomatik dışlamak sonraki iyileştirme (bkz. [[roadmap]]).
- Bilinen sınırlar: makro benzeri `FOREACH(x) {`, template literal içi iç içe `${ }`, Rust iç içe blok yorum, ifade gövdeli üyeler.

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
