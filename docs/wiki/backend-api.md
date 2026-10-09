# Backend Arayüzü (UI için)

`src/ui` sıfırdan yazılacak; bu sayfa yeni arayüzün tüketeceği backend yüzeyini özetler. Katmanlar için [[architecture]], bulgu ve kural ayrıntıları için [[analyzers]], bilinen sınırlar için [[roadmap]].

Tek giriş noktası `ProjectService` (`src/services/project_service.py`). Arayüz doğrudan analizör ya da `ProjectIndex` kullanmamalıdır.

## ProjectService
```python
service = ProjectService(disabled_analyzers=(), respect_gitignore=True, thresholds=None, disabled_rules=())
service.set_project(path)
```
| Yöntem | Ne yapar | Dönüş |
|---|---|---|
| `analyze_project(progress=None)` | Hızlı tarama (UI panosu için) | `dict` (aşağıda) |
| `create_archive(output, archive_type='zip')` | Profil tabanlı zip ya da kopya | sonuç sözlüğü |
| `create_backup(name=None)` | Zip yedeği | sonuç sözlüğü |
| `export_project_report(path)` | HTML rapor | `bool` |
| `export_audit_report(path)` | V2 formatında Markdown denetim raporu | `bool` |
| `export_agent_tasks(klasör, batch_size=15)` | Bulguları yapay zeka ajanı için görev dosyalarına yazar | özet sözlüğü (aşağıda) |
| `verify_agent_tasks(klasör, only=None)` | Görevlerin kapanışını doğrular | sözlük (aşağıda) |
| `service.doctor.diagnose(path, progress)` | Tüm bulgularla `ProjectAnalysis` | `ProjectAnalysis` |
| `service.cleanup_service.preview_cleanup / cleanup` | Temizlik önizleme / Geri Dönüşüm Kutusu'na taşıma | `dict` |

Proje seçilmeden çağrılırsa `ProjectNotSelectedError` (`ValueError` türevi). `progress(yüzde, metin)` çağrıları iş parçacığından gelir; UI'da sinyalle taşıyın (`QThread` worker).

## `analyze_project` sözlüğü
`health_score` (0-100), `health_status` (A+...F), `category_scores` (kategori -> puan), `failed_analyzers`, `total_size_mb`, `total_files`, `total_dirs`, `issues_count`, `potential_savings_mb`, `file_type_distribution`, `language_stats`, `skipped_files`, `gitignore_applied`, `ignored_by_gitignore`, `top_recommendations`, `project_path`, `all_issues`.

- **`all_issues` yalnızca KRİTİK, YÜKSEK ve ORTA bulguları içerir.** DÜŞÜK ve BİLGİ bulgular (hijyen özeti, test özeti, sıcak noktalar, bağımlılık grafiği) için `service.doctor.diagnose()` çağırıp `analysis.all_findings` kullanın.
- `analysis.issues` (KRİTİK + YÜKSEK), `analysis.warnings` (ORTA), `analysis.suggestions` (DÜŞÜK + BİLGİ).
- `category_scores` yalnızca çalışan analizörlerin kategorilerini içerir; `git` ve `type` kategorileri puanlanmaz ve burada görünmez.

## "Analiz tam mı?" göstergeleri
UI bunları kullanıcıya göstermelidir (sessiz kısmi sonuç yok):
- `failed_analyzers`: hata veren analizörler, sonuçları eksik.
- `skipped_files`: neden -> dosya sayısı (`too_large` 2 MB üstü, `unreadable`, `parse_error`, `minified`, `unreadable_dir`).
- `gitignore_applied` / `ignored_by_gitignore`: `.gitignore` ile dışarıda kalan dosya ve klasör sayısı.
- Python dışı diller `approximate` bulgu üretir; bulgu metadata'sında işaretlidir.

## Arşiv, kopya, yedek sonucu
Üçü de aynı sözleşmeyi izler; tek dosya hatasında durmazlar.
- Ortak: `success`, `complete` (`False` ise bazı dosyalar işlenemedi), `failed_files` (liste: `(yol, hata)`), `error`.
- Arşiv: `total_files`, `added_files`, `skipped_files`; kopya: `copied_files`, `skipped_files`; arşiv ve kopya `profile_name` alır (`resources/profiles/*.json`, gitignore sözdizimi, `extends` ile kalıtım).
- Yedek: `backup_name`, `size`, `excluded_dirs` (en çok 100) ve `excluded_dir_count`. Yedek `.gitignore` uygulamaz, yalnızca yeniden üretilebilir klasörleri dışlar ([[decisions]]).
- Arşiv, `.gitignore` okunamıyorsa gizli dosyaları sızdırmamak için işlemi reddeder (`error` dolu, `success=False`).
- Kopya, hedef kaynağın kendisi ya da üst klasörüyse hiçbir dosyaya dokunmadan reddeder (`error` dolu, `success=False`).
- UI `complete=False` ve `failed_files`'ı kullanıcıya göstermelidir.

## Temizlik
`CleanupService.scan / preview_cleanup / cleanup(dry_run=True)`: kategoriler `python_cache`, `temp_files` (varsayılan açık), `logs`, `backups` (varsayılan kapalı). Dışlanan klasörlerin içine girilmez; kural analizle aynıdır (`is_excluded_dir`: `venv`, `node_modules`, adı ne olursa olsun `pyvenv.cfg` içeren sanal ortam, derleme dosyası yanındaki `target` / `bin` / `obj`). Silme kalıcı değildir: Geri Dönüşüm Kutusu (`send2trash`). `cleanup` varsayılanı `dry_run=True`.

## Denetim raporu
`AuditReportService` (Markdown) bölümleri: A yönetici özeti, B iyi pratikler, C incelenmedi, D ayrıntılı bulgular, E aksiyon planı, F sonraki adım. Kurallar:
- Bulgular `kural + öncelik` ile gruplanır; D bölümünde kuraldan en fazla 3, toplam en fazla 25 bulgu.
- Sır içerebilecek bulgularda ve dosyalarda (`hardcoded-secret`, `provider-secret`, `secret-in-history`, `kind=sensitive_file`, `.env`, `*.pem`, `*.key`, `id_rsa`) kaynak satırı **asla** yazılmaz.
- "Şu sorun yok" iddiası yalnızca ilgili analizör çalışmışsa yapılır.
- Efor (S/M/L/XL) kural tablosundan gelen bir tahmindir (`audit_catalog.py`).
HTML `ReportService` kategori puanı kartlarını ve tüm bulguları gösterir; çıktı `html.escape` ile kaçışlıdır ve CSP başlığı taşır.

## Ajan görevleri
`export_agent_tasks(klasör)` dönüşü: `{'output_dir', 'tasks', 'items', 'waves': {dalga: {'tasks', 'items'}}, 'readme', 'tasks_json'}`. Klasör içeriği: `README.md` (ajan talimatı), `tasks.json`, `verify.py`, `tasks/W<dalga>-<sıra>-<kural>.md`. Dalga sırası: 0 insan (sırlar, LICENSE, git izleme) -> 1 güvenlik -> 2 güvenilirlik -> 3 mekanik temizlik -> 4 bağımlılık / hijyen -> 5 test -> 6 refactor. Kural -> dalga ve kural başına talimat metinleri `src/services/agent_guidance.py` içindedir.

`tasks.json` (`version: 1`): `{version, generated, project, tool_root, batch_size, health_score, tasks: [{id, wave, rule, label, risk, file, items: [{fingerprint, rule, severity, category, path, line, lines, title, message, recommendation, approximate, count}]}]}`. Kaynak satırları JSON'a yazılmaz (yalnızca `.md` dosyalarında; sır dosyalarında hiç yok).

`verify_agent_tasks` dönüşü: `{'tasks': [{id, wave, rule, total, closed, reduced, open, open_fingerprints}], 'totals': {total, closed, reduced, open}, 'new_count', 'new_findings': [{fingerprint, rule, severity, path, line, title}] (en çok 50), 'warning'?}`. `warning` görevler başka bir proje için üretildiyse gelir. Geçersiz / eksik / desteklenmeyen sürümlü `tasks.json` için `GitCleanError`.

Arayüz: bir "ajan görevleri olarak dışa aktar" düğmesi yalnızca `export_agent_tasks`'ı çağırır; ilerleme için `ProjectService` içinde ayrı bir `progress` yoktur (tarama `doctor.diagnose` ile yapılır, uzun sürebilir: bir `QThread` worker kullanın). "Doğrula" düğmesi `verify_agent_tasks`'ı çağırır.

## Kalıcı ayarlar
`src/services/app_settings.py`: `AppSettings` (`respect_gitignore`, `disabled_analyzers`, `disabled_rules`, 9 eşik, `agent_batch_size`, `agent_output_dir`) `~/.gitclean/settings.json` dosyasında saklanır (`load_settings`, `save_settings`, atomik yazım). Bozuk / eksik dosya, bilinmeyen anahtar ve sınır dışı değer güvenle varsayılana döner (uygulama açılışı bozulmaz). Eşik varsayılanları `QualityThresholds`'tan gelir (tek kaynak), en küçük değerler `THRESHOLD_LIMITS` içindedir. Ajan görevleri için varsayılan çıktı klasörü `~/.gitclean/agent-tasks/<proje>` (projenin **dışında**: analiz görev dosyalarını bulgu saymasın).

`SettingsViewModel` açılışta kayıtlı ayarları `ProjectService.doctor`'a uygular; `applySettings` / `resetToDefaults` / `disableRule` / `enableRule` diske yazar. `disabled_rules` tüm analizörlerin `metadata['rule']` kimlikli bulgularını eler (`ProjectDoctor._without_disabled_rules`; skor da bunlarsız hesaplanır), yalnızca SAST kurallarını değil.

## Arayüz (QML) ViewModel haritası
| ViewModel | Arayüzde karşılığı |
|---|---|
| `appVM` | Proje açma, durum çubuğu (hatalar da buraya yazılır), `openPath` (klasörü Gezgin'de aç) |
| `scanVM` | Gösterge paneli: skor, kategori puanları, dosya türü ve **dil dağılımı**, öneriler, analiz bütünlüğü (hata veren analizör, `.gitignore`, **atlanan dosya nedenleri**), HTML / denetim raporu |
| `findingsVM` | Sorunlar: şiddet ve **kategori** süzgeci, arama, **göreli yol + satır**, **tembel kaynak kodu** (sırlarda hiç gösterilmez), **"Bu Kuralı Kapat"** |
| `archiveVM`, `cleanupVM` | Arşiv / kopya / yedek, temizlik |
| `settingsVM` | 9 eşik, analizör seçimi (tümünü aç / kapat), kapatılan kurallar, `.gitignore`, ajan görevleri (klasör seçimi, parti, dışa aktarma, **sayılı doğrulama sonucu**), varsayılana sıfırlama; kalıcı |

## Yapılandırma
- `thresholds=QualityThresholds(...)`: eşikler ([[analyzers]]).
- `disabled_analyzers=("CloneAnalyzer", ...)`: analizör adıyla kapatma.
- `disabled_rules=("magic-numbers", ...)`: kural kimliğiyle kapatma (`metadata['rule']`).
- `respect_gitignore=False`: `.gitignore` uygulanmaz; izlenen dosyalar yine korunur.
- Kullanıcı SAST kuralları: `~/.gitclean/rules/*.json`. Loglar: `~/.gitclean/logs/`. Yedekler: `~/.gitclean_backups/`.

## Bilinen UI sınırları
Analiz iptal edilemiyor (iptal düğmesi yok); `read_text` 2 MB üstü dosyaları atlar; donmuş exe içinde analiz çalıştırılamadı (bkz. [[roadmap]]).
