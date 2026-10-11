# Test ve Doğrulama

Çalışma düzeni için [[rules]], analizör ayrıntıları için [[analyzers]], alınan kararlar için [[decisions]].

## Komutlar
```bash
./venv/Scripts/python.exe -m pytest                       # 790+ test (yetkiye bağlı 1-2 atlanır), yaklaşık 90-100 sn
./venv/Scripts/python.exe -m pytest tests/unit/test_x.py  # tek dosya
./venv/Scripts/python.exe -m ruff check .                 # lint (ruff.toml: E9, F)
./venv/Scripts/python.exe -m py_compile <dosya>
```
CI (`.github/workflows/ci.yml`) aynı üç adımı Windows'ta koşar ve `pip-audit -r requirements.txt` ekler; yerelde ekransız çalıştırmak için `QT_QPA_PLATFORM=offscreen`. Dosya sembolik bağı testi Windows'ta Geliştirici Modu / yönetici yoksa atlanır; junction testleri yetki gerektirmez (`_winapi.CreateJunction`).
Bağımlılıklar `requirements-dev.txt` ile kurulur. Ayarlar `pytest.ini` (`testpaths = tests`, `pythonpath = .`). Git gerektiren testler `git` yoksa atlanır (`skipif`). QML yerleşimi ekransız çizimle sınanır (`test_qml_layout`); görsel his elle kontrol edilir. Katman yönü `test_layering` ile zorunludur.

## Test dosyaları (`tests/unit/`)
| Konu | Dosyalar |
|---|---|
| Çekirdek | `test_project_index`, `test_exclusions`, `test_gitignore_matcher`, `test_git_info`, `test_registry`, `test_logging_config`, `test_skipped_and_hygiene` |
| Dil motoru | `test_languages`, `test_language_registry`, `test_brace_lexer`, `test_metrics` (karmaşıklık, derinlik, parametre) |
| Kalite | `test_python_usage`, `test_brace_usage`, `test_clones`, `test_quality_analyzers`, `test_analyzers`, `test_reliability` |
| Mimari | `test_import_graph`, `test_architecture_analyzer` |
| Güvenlik / bağımlılık | `test_security_rules`, `test_ecosystems`, `test_build_hygiene` |
| Proje sağlığı | `test_testing_and_hygiene`, `test_git_history`, `test_health_checker`, `test_project_doctor` |
| Servisler / raporlar | `test_archive_service`, `test_archive_profiles`, `test_cleanup_service`, `test_backup_service`, `test_report_service`, `test_audit_report` |
| Ajan görevleri | `test_agent_tasks` (dalga / parmak izi / parti / dışa aktarma / sır sızıntısı / verify / `verify.py` uçtan uca) |
| Ayarlar | `test_app_settings` (kalıcılık, bozuk dosya, sınır), `test_settings_viewmodel` (9 eşik, kural kapatma, kalıcılık, ajan dışa aktarma / doğrulama) |
| QML yerleşim | `test_qml_layout` (kart boyutu / üst üste binme, arayüz veri köprüsü); ekran görüntüsü yöntemi aşağıda |
| Wiki | `test_wiki` (kırık link, öksüz sayfa, indeks, `CLAUDE.md` giriş noktaları) |

## Test kuralları
- Her kuralın en az bir olumlu ve bir olumsuz fixture testi vardır (örn. SAST kurallarının 39'u için ikişer).
- Kayıt sayıları `test_registry.py` ve `test_project_doctor.py` içinde sabittir: yeni analizör eklenince güncellenir.
- Git senaryoları geçici gerçek depoda kurulur (silinmiş `.env`, sıcak dosya, birlikte değişim); sahte çıktı kullanılmaz.
- Güvenlik testleri sızıntıyı doğrudan sınar: sır değeri raporda geçmemelidir (`test_audit_report`).
- Testler kullanıcının gerçek klasörlerine yazmaz: `tests/conftest.py` ayarları (`settings_path`), kullanıcı profillerini ve yedek kökünü (`backup_service.default_backup_root`) geçici klasöre yönlendirir. Yedek yalıtımı 2026-10-10'da eklendi: `test_archive_viewmodel` her çalışmada `~/.gitclean_backups/test_backup_qml` yazıyordu.
- Kendi test fixture'ları kendi taramamıza takılabilir (örn. test dosyasındaki sahte anahtar); bu kasıtlı olarak testlerde DÜŞÜK öncelikli raporlanır ([[decisions]]).

## Bağımsız doğrulama (oracle) yöntemi
Birim testleri tek başına yetmez: her aşamada sonuçlar, **farklı bir araçla ya da farklı bir kod yoluyla** gerçek veri üzerinde karşılaştırıldı. Araçlar yalnızca geçici sanal ortamda kuruldu; projenin `venv`'i ve `requirements.txt` dosyası değişmedi.

| Alan | Oracle | Sonuç |
|---|---|---|
| Siklomatik / bilişsel karmaşıklık | `radon`, `cognitive_complexity` | fark yok / belgelenmiş farklar |
| Kullanılmayan import / değişken, klon | `pyflakes`, bağımsız klon karşılaştırması | 525 ortak import, bizde fazla 0; 46/46 değişken; 59/59 klon çifti |
| Döngü / bağımlılık grafiği | `grimp` (Python), `madge` (JS) | 134/135 ve 95/96 kenar, hayalet kenar 0; JS değer kenarları 111/111 |
| Güvenilirlik | `ruff` (çıplak except, print, datetime), `tokenize` (TODO) | birebir / eşleşti |
| Test sayımı | `grep '^\s*def test'`, `find` | 373 / 27 ve 105 / 26 birebir |
| Git geçmişi | `git log --name-only` + `awk`, `grep` | sıcak nokta sayıları ve birlikte değişim güveni birebir |
| Üretilmiş içerik, araçlar | `git ls-files` + ayrı regex, `grep requirements.txt` | 29/30 (fark bilinçli istisna), 7/7 |
| Yedek içeriği | ayrı kod yolu `ProjectIndex(respect_gitignore=False)`, `git ls-files --ignored` | 8/8 |
| Ajan görevleri | öğe sayısı = bulgu kalemleri toplamı (30 depo, 379 görev, 1911 öğe); kopya projede 29 basit import elle silinip `verify` ile kapanış; sır değeri sızıntısı taraması | 0 uyuşmazlık, 29/29 kapandı, yeni bulgu 0, gerçek sızıntı 0 |
| Rapor sayıları | analiz bulgularının `Counter`'ı, 44 sır bulgusunun kaynak satırı | birebir; 0 sızıntı |

## Uçtan uca QA ve erişilebilirlik
- Gerçek QML penceresi + `QTest.mouseClick` ile uçtan uca denetim yapıldı (2026-10-11); rapor (`QA_RAPORU.md`) ve ekran görüntüleri (`docs/qa/`) 2026-10-12'de kullanıcı kararıyla silindi, git geçmişinde durur. Düzeltmelerin gerileme testleri `tests/unit/test_qa_fixes.py` içindedir.
- **QML ekli özellikleri (`Accessible.name`) `item.property(...)` ile okunamaz;** ölçüm için `QAccessible.setActive(True)` + `QAccessible.queryAccessibleInterface(item).text(QAccessible.Text.Name)` kullanılır. İlk QA turunda yanlış yöntemle "0 öğe" sayılmıştı (kaynakta gerçekten `Accessible` yoktu, sonuç doğru çıktı, yöntem yanlıştı).
- Pencere nesnesi `contentItem()` / `grabWindow` gibi `QQuickWindow` yöntemlerini yalnızca `QtQuick` modülü uygulamadan **önce** içe aktarılmışsa sunar (aksi hâlde `QWindow` olarak çözülür).
- Ekransız (`offscreen`) modda SVG simgeleri boş çizilir ve Qt, stil özelleştirmesi hakkında uyarı verir; görsel ve uyarı kontrolü gerçek platformda (`QT_QPA_PLATFORM=windows`) yapılır. İlk QA turundaki 48 uyarı yalnızca ekransız ortam artefaktıydı.
- "Kaldı" çıkan bir kontrol hata sayılmadan önce bağımsız bir kaynakla doğrulanır: ilk turdaki 15 başarısızlığın 6'sı test düzeneğinin hatası ya da beklenen davranıştı.

## Davranış korunumu (refactor oracle)
Refactor öncesi commit `git worktree` ile ayrı bir klasöre alınır; aynı betik iki kod tabanında 8 gerçek projede çalıştırılır ve tam teşhis çıktısı (her bulgunun kategori, öncelik, başlık, dosya, açıklama, tüm metadata'sı, skorlar, dil istatistikleri, atlananlar) anahtarları sıralanmış JSON olarak `cmp` ile karşılaştırılır. Her adımdan sonra tekrarlanır; sonuç 8/8 birebir olmalıdır. `build_exe.py` gibi dış araca bağlı betikler sahte modülle (örn. sahte `PyInstaller`) eski ve yeni sürümde çalıştırılıp argüman ve çıktı karşılaştırılır.

## Dogfooding (kendi kendini tarama)
Her aşamanın yeni kodu, aracın kendi `CodeComplexityAnalyzer` eşiklerinden (V2) geçmelidir: yeni dosyalarda bulgu kalmayana dek fonksiyonlar bölünür. Bu repo skoru: 83,1 → 88,3 → 89,1; kalan bulgular: QML ViewModel'lerinin `class-size` bulguları (`ScanViewModel`, `SettingsViewModel`, `FindingsViewModel`: her `@Property` / `@Slot` bir metot sayılır, sınıf QML'e açılan yüzeydir) ve `BaseAnalyzer._create_result` (7 parametreli genel API). Eski arayüz kaldırıldıktan sonra (2026-10-10) skor 85,7.

## Performans bütçesi
Tüm `C:\2UYGULAMALAR` (yaklaşık 5.900 dosya, 30 depo): hedef < 60 sn, ölçülen 30-35 sn. Tek bir analizör pahalıysa (örn. sağlayıcı sırları regex'i bir ara 70 sn'ye çıkmıştı) `analizör başına süre` ölçülür ve anchor + alt dizgi ipucuyla hızlandırılır (2,6 sn). Git tabanlı analizörler 29 depoda toplam 14,6 sn.

## QML arayüzünü kodla görmek
`QT_QPA_PLATFORM=offscreen QT_QUICK_BACKEND=software QT_QPA_FONTDIR=C:/Windows/Fonts` ile `create_qml_app()` çalıştırılır, `appVM.setProjectPath(...)` ile proje yüklenir, `window.setProperty("currentTab", n)` ile sekme değiştirilir ve `window.screen().grabWindow(window.winId())` ile PNG alınır. Yerleşim bozuklukları (üst üste binme, taşma) bu görüntülerde ve `qInstallMessageHandler` ile toplanan QML uyarılarında (`Unable to assign [undefined] to ...`) görünür. Çevrimdışı çizimde SVG ikonlar görünmez; gerçek pencerede elle kontrol gerekir.

## Araç tuzakları (oturumlardan öğrenilenler)
- Bash heredoc içindeki kaçış dizileri bozulur: `\n` gerçek satır sonuna, `\b` 0x08 karakterine, `'\\'` `'\'`ya dönüşebilir. Kod yazarken `Write`/`Edit` aracı ya da betik dosyası kullanılır; sonra kontrol karakteri taraması (`[\x00-\x08\x0b\x0c\x0e-\x1f]`) yapılır.
- Windows Python, Git Bash'in `/tmp` ve `/c/...` yollarını göremez: betik dosyaları oturum scratchpad klasörüne `C:/...` yoluyla yazılır.
- Konsol cp1254 olduğu için betiklerde `PYTHONIOENCODING=utf-8` kullanılır (örn. `↔` yazdırmak).
- **Kodlamasız dosya yazma / okuma yerel ayara bağlıdır:** Türkçe Windows'ta varsayılan cp1254 `ı`, `ş` yazabilir, GitHub runner'ında cp1252 yazamaz (`UnicodeEncodeError`; ilk CI koşusunda 2 test böyle kırıldı). Testler ve kod her zaman `encoding="utf-8"` verir. Koruma: `pytest.ini` `EncodingWarning`'i hataya çevirir, CI `PYTHONWARNDEFAULTENCODING=1` ile çalışır; yerelde aynısı `python -X warn_default_encoding -m pytest`.
- `.gitattributes` eklenince `git status` satır sonu önbelleği yüzünden dosyaları "değişmiş" gösterebilir; gerçek farkı `git diff` ve `git add -A --dry-run` verir.
- `test_` ile başlayan analizör dosyası test sayılır ve kurallardan muaf kalır; bu yüzden `testing_analyzer.py` / `testing_patterns.py`.
