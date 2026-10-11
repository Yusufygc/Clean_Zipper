# Windows exe, sürüm ve uygulama içi güncelleme rehberi

## Bu dosyanın amacı ve nasıl güncellenir

**Amaç:** imzasız bir Windows masaüstü uygulamasını sorunsuz kurulan (Akıllı Uygulama Denetimi'ne takılmayan), etiketle yayınlanan ve kendini güncelleyen hâle getirmek için tek başına verilebilen rehber ve gerekçe kaynağıdır. Genel proje altyapısı (lint, test, CI, güvenlik) ayrı dosyadadır: [[proje-altyapi-rehberi]].

**Kullanım (yeni proje):** bir yapay zekâ ajanına bu dosyayı ver; bölüm 10'daki "Kurulum (bir kez)" listesini sırayla uygulamasını iste. Önce bölüm 3.ü (kararlı exe ve 3.1 özet onay kapısı) okutmak, en çok zaman kazandıran adımdır.

**Güncelleme (başka projelerinden öğrendiklerinle):** başka bir projedeki yeni bir dağıtım / güncelleme özelliğini ya da dersi bu dosyaya işlemek için ajana şu talimatı ver:

> `docs/wiki/exe-dagitim-rehberi.md` dosyasını oku. Şu projeyi (`<yol>`) incele: exe derleme, kurulum sihirbazı, sürüm / yayın süreci ve uygulama içi güncelleme tarafında bu dosyada **olmayan** ya da **daha iyi çalışan** bir yaklaşım bul (örn. imzalama, delta / yama güncellemesi, farklı kurulum aracı, farklı SAC önlemi). Her bulguyu ilgili bölüme ekle; **ölçüm ya da gerçek deneme** ile desteklenmeyen iddiayı "doğrulanmadı" diye işaretle. Bu dosyadakiyle çelişen sonuç bulursan sessizce ezme: çelişkiyi, iki tarafın ölçümünü ve hangisinin geçerli olduğunu raporla. Bölüm 2'deki ölçüm tablosuna yeni gözlemi tarih ve makineyle ekle, eskiyen maddeyi düzelt, `docs/wiki/log.md`'ye kayıt düşüp `tests/unit/test_wiki.py` ile bağlantıları doğrula.

**Güncelleme kuralları:**
- Windows Akıllı Uygulama Denetimi davranışı Microsoft tarafında değişebilir: bölüm 2'deki ölçümler tarihlidir; yeni bir Windows sürümünde yeniden doğrula.
- "Çalıştı" iddiası **hangi makinede, hangi dosya özetiyle, kaç denemede** sorusuna cevap vermeden yazılmaz.
- Başarısız ya da geri alınan yaklaşımlar silinmez; bölüm 9'a (yapılmaması gerekenler) nedeniyle eklenir.
- Kod parçaları bu depodaki referans dosyalarla (bölüm 12) uyumlu tutulur; referans dosya değişirse rehber de değişir.

Bu sayfa kendi başına yeterlidir: başka bir projede bir yapay zekâ ajanına **doğrudan bu dosya verilerek** imzasız, sorunsuz kurulan, sürüm etiketiyle yayınlanan ve kendini güncelleyen bir Windows masaüstü uygulaması kurulabilir.
Her madde bu depoda (GitClean Archiver) yaşanmış, ölçülmüş ve çalıştığı doğrulanmış bir şeye dayanır. Örnek gerçekleştirme bu depodadır; dosya adları "referans" olarak verilir.
Bu depoya özgü ayrıntılar: [[surum-yayinlama]] (yayın adımları), [[guncelleme-sistemi]] (uygulama içi güncelleme tasarımı), [[decisions]] (kararlar), [[log]] (tarihçe).

Yığın: Python 3.10, PySide6/QML, PyInstaller 6.22.3, Inno Setup 6, GitHub Actions + GitHub Releases. İlke aynı kalarak başka yığınlara uyarlanabilir (bkz. bölüm 11).

---

## 1. Hedef ve doğrulanmış sonuç

Hedef: son kullanıcı **kurulum dosyasını indirir, çalıştırır, kullanır**; sonraki sürümlerde uygulama kendi içinden güncellenir ve **beklemeden** yeniden açılır. Kod imzalama, üçüncü taraf hesap ya da servis **yok** (kullanıcı kararı: imza sertifikası, SignPath, benzeri başvurular istenmiyor).

Doğrulanan son durum (2026-10-12):

| Ne | Sonuç |
|---|---|
| CI'da (GitHub `windows-latest`) derlenen exe | Yerelde derlenenle **bayt bayt aynı** (SHA-256 `fec37f4e25de832d…`); yayın kapısı bunu her sürümde denetler |
| 2.1.4 kurulum dosyası GitHub'dan indirilip elle çalıştırıldı | Kuruldu, uygulama açıldı, Windows engellemedi |
| 2.1.4 → 2.1.5 uygulama içi güncelleme | Güncelleme penceresi çıktı; **bekleme olmadı**; kurulum ilerleme penceresi göründü; uygulama kendiliğinden yeniden açıldı; yeni sürümün exe'si engellenmedi |

Hâlâ doğrulanmayanlar: bu exe özetinin **başka kullanıcı makinelerinde** de açılacağı (beklenir, kanıtlanmadı); her sürümde yeni olan Inno kurulum dosyasının her makinede engellenmeyeceği (uygulama içi güncelleme engel çıkarsa bekleyip yeniden dener, bölüm 7).

---

## 2. Kök sorun: Akıllı Uygulama Denetimi (Smart App Control, SAC)

Windows 11'de SAC açıksa **imzasız** her çalıştırılabilir dosya (exe, DLL, kurulum dosyası, kaldırıcı) dosya **özetine (SHA-256)** göre Microsoft'un bulut itibar kararına bırakılır.

- Karar **dosya başına ve öngörülemezdir**. Aynı kaynaktan, aynı bayraklarla yapılan iki derlemenin özeti farklıdır; biri çalışır, diğeri engellenir.
- Karar konuma, yetki düzeyine, `onefile` / `onedir` ayrımına, indirme işaretine (MOTW) bağlı değildi (hepsi denendi, fark görülmedi). Engellenen dosyanın aynı özetli kopyası başka klasörde de engellendi: **içeriğe bağlıdır**.
- Karar zamanla değişebilir: engellenen aynı dosya bazen dakikalar sonra açıldı (SAC penceresi "Microsoft inceleyecek" der).
- Kullanıcı başına izin listesi **yoktur**. SAC'ı kapatmak çözüm değildir (Windows'ta kapatılınca yeniden açmak için sıfırlama gerekir) ve **önerilmez**; güvenlik ayarlarına dokunmak yasak sayılmalıdır.

### Belirtiler

| Belirti | Anlam |
|---|---|
| "Uygulama Denetimi ilkesi bu dosyayı engelledi" (Gezgin, `Start-Process`) | SAC dosyayı çalıştırmadı |
| Python `subprocess.Popen` → `OSError: [WinError 4551]` | aynı engel |
| Bash `Permission denied` (çıkış 126) | aynı engel, kabuk farklı mesaj verir |
| Windows bildirimi "Bu uygulamanın bir kısmı engellendi" | aynı |

Kesin kanıt (kimin neyi neden engellediği):

```powershell
Get-WinEvent -LogName "Microsoft-Windows-CodeIntegrity/Operational" -MaxEvents 400 |
  Where-Object { $_.Id -in 3077,3033 } | Select-Object -First 5 TimeCreated, Id, Message | Format-List
# 3077: "...did not meet the Enterprise signing level requirements or violated code integrity policy (Policy ID:{0283ac0f-...})"
```

SAC durumu: `HKLM\SYSTEM\CurrentControlSet\Control\CI\Policy` altında `VerifiedAndReputablePolicyState` (`1` iken engelliyor). İmza: `Get-AuthenticodeSignature <dosya>` (`NotSigned` ise SAC'ın "güvenilir imza" yolu yok).

### Ölçümler (bu depoda, 2026-10-11/12)

| Deney | Sonuç |
|---|---|
| `--onefile` exe, 4 ardışık derleme | 3 çalıştı, 1 engellendi |
| `--onedir` exe, 5 derleme | 3 çalıştı, 2 engellendi |
| Inno kurulum dosyası, 4 derleme | 3 çalıştı, 1 engellendi |
| Doğrulamalı derleme turu, 6 deneme | 5 exe + 1 kaldırıcı (`unins000.exe`) engellendi, hiçbiri geçmedi |
| CI'da derlenen v2.1.1 kurulum dosyası, kurulu uygulamanın başlattığı süreçten | engellendi; aynı dosya ~10 dk sonra Gezgin'den ve `CreateProcess` ile **açıldı** |
| v2.1.2: uygulama başlatınca engel; kullanıcı dakikalar sonra `%TEMP%`'ten çift tıkladı | **bekletmeden açıldı** |
| v2.1.3 güncellemesi | kurulum dosyası ~1 dk beklemeyle başladı, ama kurulan **yeni exe engellendi**, uygulama açılmadı |
| **Sabit exe (aşağıda) ile v2.1.4 ve v2.1.5** | engel yok |

### Güncelleme zincirinde SAC'ın asıl zararı

Her sürümün exe'si yeni bir özet demekti. Kurulum ne kadar sorunsuz olsa da **kurulan yeni exe** engellenirse kullanıcı uygulamayı açamıyordu. Bu yüzden asıl çözüm: **exe'yi sürümler arasında değiştirmemek** (bölüm 3).

---

## 3. Çözüm: her sürümde BAYT BAYT AYNI exe ("kararlı exe")

Fikir: SAC yalnızca **yeni çalıştırılabilir dosyayı** değerlendirir. Uygulama kodunu exe'nin dışına çıkarırsak, bir kez onaylanan exe sonraki tüm sürümlerde aynı kalır; güncellemeyle yalnızca `.pyc` ve veri dosyaları (çalıştırılabilir olmayan dosyalar) değişir.

Gerekli dört parça (hepsi gerekli, biri eksikse özet değişir):

| Parça | Ne yapılır | Neden |
|---|---|---|
| Sabit giriş betiği | `packaging/launcher.py` yalnızca uygulamanın `run()` işlevini çağırır (3 satır). **Asla değiştirilmez.** Gerçek mantık uygulama paketindedir | Giriş betiği exe'nin içine gömülür; içeriği değişirse özet değişir |
| Modüller exe dışında | PyInstaller `--debug=noarchive`: Python modülleri exe'ye gömülmez, `_internal` altında `.pyc` olarak durur | Sürümle değişen kod exe'yi değiştirmesin |
| Sabit zaman damgası | Derlemeden önce `os.environ["SOURCE_DATE_EPOCH"] = "1700000000"` | `--debug=noarchive` tek başına YETMEDİ: PE zaman damgası yüzünden iki derlemede özet farklıydı |
| Sabit sürüm kaynağı | `--version-file=packaging/launcher_version_info.txt`, içinde sabit `1.0.0.0` | Sürümle değişen sürüm kaynağı exe'yi değiştirir |

Ürün sürümü başka yerde görünür: Inno kurulum dosyası, "Uygulamalar ve özellikler" kaydı ve uygulamanın kendi başlığı. **Bedel (kullanıcı kabul etti):** Gezgin'de exe → Özellikler sekmesi hep `1.0.0.0` gösterir.

Referans giriş betiği (`packaging/launcher.py`):

```python
"""Başlatıcı. BU DOSYAYI DEĞİŞTİRME (içeriği exe özetine girer)."""
from src.qml_ui.app import run

run()
```

Referans PyInstaller bağımsız değişkenleri (`build_exe.py`):

```python
LAUNCHER_EPOCH = 1700000000                                  # DEĞİŞTİRME (bilerek yeni özet denemek için tek yol)
arguments = [
    str(root / "packaging" / "launcher.py"),
    f"--paths={root}",              # giriş betiği packaging/ altında: uygulama paketi kökten bulunur
    "--name=GitCleanArchiver",
    "--onedir", "--windowed", "--clean", "--noconfirm",
    "--noupx",                      # UPX DLL imzalarını bozar, antivirüs yanlış pozitifini artırır
    "--debug=noarchive",            # modüller .pyc olarak _internal altında
    "--collect-submodules=src.analyzers",   # dinamik yüklenen paketleri açıkça ekle
    f"--version-file={root / 'packaging' / 'launcher_version_info.txt'}",
    # --add-data ... ve --icon ...
]
os.environ["SOURCE_DATE_EPOCH"] = str(LAUNCHER_EPOCH)      # PyInstaller'ı çalıştırmadan hemen önce
```

Özet; PyInstaller sürümü, Python sürümü, simge, ad, sürüm kaynağı, giriş betiği ve epoch'tan oluşur. Bu yüzden `requirements-build.txt` içinde `pyinstaller==X.Y.Z` **sabitlenir**, CI'daki Python sürümü yerelle aynı olur (burada 3.10). Satır sonları: `.gitattributes` içinde `* text=auto eol=lf` (giriş betiği her makinede aynı derlenmeli).

Not: bu depodaki `launcher.py` docstring'inde eski bir sayfa adı geçer (`windows-exe-dagitim.md`). Docstring exe özetine girdiği için **bilerek düzeltilmedi**; yeni projede docstring'i en baştan doğru yaz ve bir daha dokunma.

Kanıt: yeniden derleme, kaynak kod değişikliği ve **farklı kök klasörde derleme** (CI'a benzetmek için `C:\gcx_w\proje_kopyasi`) aynı özeti verdi; GitHub Actions'taki derleme de yerel özetle aynı çıktı.

### 3.1 Onay kapısı: `packaging/launcher.sha256`

Windows'ta gerçekten **denenmiş** exe özeti depoya yazılır (`<64 hane> *GitCleanArchiver.exe`). Derleme bittikten sonra `check_launcher_hash` çalışır:

- özet aynı → devam;
- farklı ya da dosya yok → **derleme ve yayın durur** (`sys.exit(1)`), kullanıcıya nedenler ve çıkış yolu yazılır;
- bilerek değiştirildiyse `python build_installer.py --update-launcher-hash` yeni özeti yazar.

Neden gerekli: PyInstaller / Python / ortam farkı yüzünden özet sessizce değişirse kullanıcıya onaysız, engellenebilecek yeni bir exe gider. Kapı bunu yayından önce yakalar. CI aynı kapıdan geçer.

### 3.2 Testlerle sabitleme (`tests/unit/test_release_packaging.py`)

- `packaging/launcher.py` ve `packaging/launcher_version_info.txt` dosyalarının SHA-256 değerleri (satır sonları LF'ye çevrilerek) testte sabittir; biri değişirse test kırılır ve nedenini söyler.
- `LAUNCHER_EPOCH`, giriş betiği yolu, `--debug=noarchive`, `--onedir`, `--noupx`, `--version-file`, `SOURCE_DATE_EPOCH` atamasının varlığı denetlenir.
- Kapı testi: farklı özet → `SystemExit`; `update=True` → yazar; sonra geçer; onay dosyası yoksa durur.
- Yayın iş akışı `python build_installer.py` çağırır ve `--no-verify` içermez (kapıyı atlayamaz).

---

## 4. Kurulum sihirbazı (Inno Setup 6)

Referans: `packaging/GitCleanArchiver.iss`. Önemli satırlar ve nedenleri:

```ini
[Setup]
AppId={{B4C7E1A2-5D3F-4E8A-9C21-6F0A7D9E3B58}   ; SABİT. Değişirse sonraki sürüm üstüne yazmaz, ikinci kurulum olur
PrivilegesRequired=lowest                      ; UAC sormaz; güncelleme sessiz çalışır; derleme sonrası deneme mümkün
PrivilegesRequiredOverridesAllowed=dialog      ; kullanıcı isterse "tüm kullanıcılar" seçebilir
DefaultDirName={autopf}\Uygulama               ; lowest iken %LOCALAPPDATA%\Programs
CloseApplications=yes                          ; güncellemede çalışan uygulama kapatılır (dosya kilidi olmasın)
RestartApplications=no                         ; yeniden açmayı biz [Run] ile yapıyoruz
OutputBaseFilename=Uygulama-Setup-{#AppVersion}  ; sürümlü ad: güncelleyici bu desene bakar
LicenseFile=..\LICENSE
[Files]
Source: "..\dist\Uygulama\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
[Run]
Filename: "{app}\Uygulama.exe"; Description: "..."; Flags: nowait postinstall skipifsilent
Filename: "{app}\Uygulama.exe"; Flags: nowait; Check: RelaunchAfterUpdate
[Code]
function HasParam(const Name: String): Boolean; ...        ; ParamStr döngüsü
function RelaunchAfterUpdate: Boolean;
begin
  Result := WizardSilent and not HasParam('/VERYSILENT');
end;
```

- **Yeniden açma:** uygulama içi güncelleme `/SILENT` ile (ilerleme penceresi görünür), derleme sonrası deneme `/VERYSILENT` ile kurar. `WizardSilent` ikisinde de doğrudur; `/VERYSILENT` olanı `HasParam` ile ayırırız. (Denemede uygulama açılıp kalmasın.) `WizardVerySilent` diye bir Inno işlevi **yoktur**.
- `ISCC` bağımsız değişkeni git-bash'te `//D` olarak yazılmalı (`/D` yola çevrilir); `build_installer.py` bunu `subprocess` ile doğrudan verdiği için sorun çıkmaz: `[iscc, f"/DAppVersion={sürüm}", betik]`.
- Kullanıcı verisi (`~/.uygulama`) kaldırıcı tarafından **silinmez**.
- Qt/LGPL gibi lisanslar için `LICENSE` ve `THIRD_PARTY_NOTICES.md` kurulumla birlikte dağıtılır; `--onedir` Qt'nin yeniden bağlanabilirliğini korur.
- `--onedir` + Inno: kurulum dosyası tek dosya `--onefile` sürümüne göre küçük (62 → 40 MB), açılışta `%TEMP%`'e açma yok. SAC açısından kanıtlı üstünlüğü yoktur.

---

## 5. Derleme betikleri

### `build_installer.py` (tek komut)

Akış: ISCC bul → `build_exe.build_executable()` (kapı dahil) → exe'yi bu makinede dene → Inno derle → kurulum dosyasını dene → `.sha256` yaz.

- Exe deneme **başarısızsa durur** ve `LAUNCHER_EPOCH` yoluna yönlendirir. Yeniden derlemek aynı exe'yi verir, **döngü yok**.
- Kurulum dosyası denemesi başarısızsa yalnızca **uyarı** verir (her sürümde yeni olan tek çalıştırılabilir dosya budur; uygulama içi güncelleme bekler).
- `CI` ortam değişkeni varsa (GitHub Actions) ve `--no-verify` ile deneme atlanır (CI'da SAC yoktur).
- Seçenekler: `--skip-build`, `--no-verify`, `--update-launcher-hash`.

### `build_verify.py` (bağımsız, yalnızca standart kitaplık; başka projeye kopyalanabilir)

- `launch_check(exe, seconds=8)`: exe'yi başlatır, süre sonunda hâlâ çalışıyorsa `taskkill /T /F` ile kapatır. `OSError.winerror in (4551, 1260)` engel sayılır. Denemede ağ isteği olmasın diye ortam değişkeniyle güncelleme denetimi kapatılır.
- `installer_check(installer)`: **geçici klasöre sessizce** kurar (`/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CURRENTUSER /DIR=<geçici> /LOG=...`), kurulan exe'yi açar, **kaldırıcıyı da çalıştırır** (kaldırıcı da imzasız exe'dir, engellenirse kullanıcı uygulamayı kaldıramaz), geçici klasörü siler.
- **Gerçek kurulumu koruma (yaşanmış kaza):** deneme kurulumu gerçek kurulumla aynı `AppId`'yi kullanır; Inno aynı `HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\{AppId}_is1` kaydını ve Başlat menüsü kısayolunu yazar / siler. Deneme çökünce kullanıcının kaydı geçici klasörü gösterdi. Çözüm: deneme öncesi kayıt değerleri ve kısayol baytları yedeklenir, `try/finally` ile **her durumda** geri yazılır (`save_registration` / `restore_registration`, testli).

---

## 6. Sürüm ve yayın

### Sürüm numarası

- Biçim `MAJOR.MINOR.PATCH` (`2.1.5`); etiket `v` önekli (`v2.1.5`). Ön sürüm (`-rc1`) güncelleyici tarafından yok sayılır.
- **Tek kaynak:** `src/version.py` içinde `__version__` (ve `RELEASE_REPO`). Kurulum dosyası sürümü bundan alır (`/DAppVersion`); README rozeti `tools/release.py` ile aynı değere çekilir.
- exe sürüm kaynağı **bilerek yükseltilmez** (bölüm 3). Testle: `version_info.txt` gibi sürümle değişen bir exe kaynağı kökte yoktur.
- Artış: hata düzeltmesi → PATCH, özellik → MINOR, uyumsuz değişiklik → MAJOR.

### `tools/release.py X.Y.Z`

Çalışma ağacı temiz ve dal `main` olmalı, sürüm mevcuttan büyük olmalı, etiket yok olmalı. Yaptığı: `src/version.py` + README rozetini günceller, `chore(release): vX.Y.Z` commit'i atar, ek açıklamalı `vX.Y.Z` etiketi oluşturur. **Hiçbir şey göndermez.** `--check-tag vX.Y.Z` (CI'da) etiket ile `src/version.py` uyumunu denetler.

```powershell
python tools/release.py 2.1.5
git push origin main
git push origin v2.1.5        # --follow-tags KULLANMA: hafif etiketleri göndermez
gh run watch
gh release view v2.1.5        # kurulum dosyası ve .sha256 var mı
```

### `.github/workflows/release.yml` (etiket `v*` itilince)

`windows-latest`, Python 3.10 (pip önbellekli), `permissions: contents: write`. Adımlar:

1. Etiket ↔ `src/version.py` denetimi. Etiket adı `env: TAG: ${{ github.ref_name }}` ile **ortam değişkeninden** verilir (betiğe doğrudan gömülmez: komut enjeksiyonu olmasın).
2. Bağımlılıklar (`requirements-dev.txt`, `requirements-build.txt`), `ruff`, `pytest` (kırmızıysa yayın yok).
3. Inno Setup yoksa `choco install innosetup -y`.
4. `python build_installer.py` → exe kapıdan geçer, kurulum dosyası + `.sha256` üretilir.
5. `gh release create $tag dist/installer/* --title ... --generate-notes --verify-tag` (`-` içeren etiket → `--prerelease`).

Normal CI (`ci.yml`) da `main` ve etiket itmesinde koşar (lint, test, `pip-audit`).

### Yayından sonra

- CI günlüğünde "Kararlı exe özeti onaylananla aynı" satırını gör.
- **İndirilmiş (MOTW'li) kurulum dosyasını SAC'lı gerçek bir makinede aç.** CI'daki Windows'ta SAC yoktur; CI'da derlenen dosya hiç denenmemiş dosyadır.
- Release'e yüklediğin dosya denediğin dosya olmalı: yeniden derleme / paketleme / yeniden adlandırma özeti (ve itibarı) değiştirir.

### Hata ve geri alma

| Durum | Yapılacak |
|---|---|
| Etiket ↔ sürüm farklı, iş akışı durdu (yayın yok) | Düzelt, commit'le, etiketi taşı (`git tag -f`, `git push -f origin vX.Y.Z`) |
| Yayın oluştu ama sürüm hatalı | **Yayınlanmış etiketi taşıma.** Yeni PATCH çıkar. Acilse `gh release delete vX.Y.Z --cleanup-tag` (güncelleyici `latest`e baktığından önceki sürüm yeniden son sürüm olur) |
| `git push` etiketi göndermedi | `git push origin vX.Y.Z` ayrıca |
| Kapı "özet DEĞİŞTİ" dedi | Bölüm 8 |
| Kurulu kullanıcıda güncelleme başlamadı | `%TEMP%\<UygulamaAdı>Update\install.log` |

Yaşanmış: yerelde taşıdığım `v2.1.0` etiketi uzakta zaten vardı ve `git push` "already exists" ile reddedildi. Yayınlanmış etiketi asla taşıma; yeni sürüm çıkar.

---

## 7. Uygulama içi güncelleme

Akış (referans: `src/services/update_service.py`, `UpdateViewModel`, `UpdateDialog.qml`):

1. **Denetim:** pencere çizildikten ~3 sn sonra (`run()` içinden, UI fabrikasında değil: testler ağa çıkmasın) tek istek: `GET https://api.github.com/repos/<depo>/releases/latest`. Kimlik bilgisi göndermez. Ağ yoksa sessiz geçer; "Şimdi Denetle" her sonucu gösterir. Kapatma: ayar onay kutusu ya da `<UYGULAMA>_NO_UPDATE_CHECK=1`.
2. **Karşılaştırma:** `releases/latest` etiketi sayısal olarak (`2.10.0 > 2.9.0`) yüklü sürümle kıyaslanır; taslak ve ön sürüm yok sayılır.
3. **İndirme (kullanıcı "Güncelle" deyince):** arka plan iş parçacığı + ilerleme çubuğu. Doğrulama **zorunlu**:
   - adres yalnızca `https://github.com/<depo>/...` (yönlendirme sonrası host `github.com` ya da `*.githubusercontent.com`), aksi hâlde reddedilir;
   - dosya adı sıkı desene uymalı: `^Uygulama-Setup-[0-9.]+\.exe$`;
   - boyut sınırı (400 MB) ve Release'teki boyutla birebir eşleşme;
   - SHA-256: GitHub asset `digest` alanından, yoksa Release'teki `<dosya>.sha256` dosyasından; **ikisi de yoksa güncelleme reddedilir**; uyuşmazlıkta dosya silinir.
4. **Kurulum:** bağımsız süreç, kabuk yok, sabit argümanlar:
   `Setup.exe /SILENT /SUPPRESSMSGBOXES /CLOSEAPPLICATIONS /LOG=<klasör>\install.log` (`DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP`). Sonra `quitRequested` sinyaliyle uygulama kapanır; Inno kurar; `[Run]` ile uygulama **kendiliğinden yeniden açılır**.
5. **Windows başlatmayı engellerse (emniyet ağı):** önce `CreateProcess`; `WinError 4551/1260` gelirse Gezgin'in çift tıklama yolu (`ShellExecuteW`); ikisi de engelliyse `InstallerBlockedError`. ViewModel bu durumda **15 sn aralıkla en çok 40 kez** yeniden dener (pencerede "Windows bekleniyor…", **Beklemeyi Bırak** düğmesi); süre dolarsa / kullanıcı vazgeçerse dosya Gezgin'de seçili gösterilir ve "Sürüm Sayfası" düğmesi çıkar. Son sürümlerde bu yola **hiç girilmedi** (kurulum dosyası beklemeden başladı); yine de kurulum dosyası her sürümde yeni olduğu için tutulur.

Katmanlar: `UpdateDialog.qml` → `UpdateViewModel` → `update_service` (UI'dan bağımsız, birim testli, ağ sahte `opener` ile). Tercihler ayrı dosyada (`~/.<ad>/updates.json`: açılış denetimi, atlanan sürüm).

### Güvenlik sınırı (bilerek kabul edildi)

Özet GitHub'dan gelir. GitHub hesabı ele geçirilirse sahte dosya + sahte özet yayınlanabilir; imza olmadığı için fark yakalanamaz. İmzasız dağıtımın doğasıdır.

---

## 8. Exe'yi BİLEREK değiştirmek (nadir, dikkatli)

Gerekçeler: PyInstaller / Python sürümü yükseltme, simge, giriş betiği ya da sürüm kaynağı değişikliği. Derleme "özet DEĞİŞTİ" der ve durur. Sıra:

1. Yeni exe'yi yerelde derle (`python build_exe.py` hata verir ama exe `dist/` altında oluşmuştur) ve `build_verify.launch_check` ile **bu makinede aç**.
2. Engellendiyse **yalnızca** `LAUNCHER_EPOCH` değerini değiştir (tek yol: özet değişir), yeniden derle, tekrar dene. Yeniden derlemek epoch aynıysa aynı exe'yi verir.
3. Açılan özeti onayla: `python build_installer.py --update-launcher-hash`.
4. Testlerdeki sabit özetleri (giriş betiği / sürüm kaynağı değiştiyse) ve `LAUNCHER_EPOCH` değerini güncelle.
5. CI aynı özeti üretiyor mu? Üretmiyorsa kapı yayını durdurur. Nedenleri: Python / PyInstaller sürümü farkı, satır sonları, ortama bağlı yol, simge. Gerekçeyi bul; bulunamıyorsa CI'ın ürettiği exe'yi **SAC'lı makinede indirip dene** ve onayla.
6. Bu, tüm kullanıcılar için **yeni** bir exe demektir (ilk açılışta yeniden değerlendirilir). Sık yapma.

---

## 9. YAPILMAMASI gerekenler (bu depoda yaşandı)

1. **Her sürümde yeni bir exe özeti üretmek.** SAC her seferinde yeni karar verir; güncelleme başarılı görünür ama uygulama açılmaz (v2.1.3). → Kararlı exe.
2. **Engellendi diye yeniden derleyip şansa güvenmek** (derleme–dene–yeniden derle döngüsü). Oran düşüktü, hiçbir şey garanti etmez; kaynak değişmezse kararlı exe aynı özeti verir. → Döngü kaldırıldı.
3. **"Şu bayrakla derlersen geçer" aramak.** `--onefile`/`--onedir`, MOTW, yetki düzeyi, konum: hiçbirinin etkisi görülmedi. Kod imzalamak dışında deterministik tarif yok.
4. **Kendi kendini kuran tek exe** ("exe kendini kursun"): denendi, geri alındı. Engel kurulum programında değil, her yeni exe'nin kendisindedir; tek exe'nin riski ayrı kurulum dosyasınınkiyle aynıdır.
5. **Yeniden açma yardımcısı (PowerShell / ek exe) eklemek.** Kullanıcı reddetti ("son kullanıcı 10 dk beklemez"): yeni bir çalıştırılabilir dosya yeni engel riski demektir. Yeniden açma Inno `[Run]` ile yapılır, ek dosya yok.
6. **SAC'ı kapatmayı önermek / güvenlik ayarlarına dokunmak.** Geri alınması zor, kullanıcıya zarar verir.
7. **Inno kurulum dosyasını "açılıyor mu" diye elle başlatıp öldürmek.** Sihirbaz yükseltilmiş çalışırsa süreç öldürülemez (`Erişim engellendi`), kurulum tamamlanabilir ve makinede gerçek kayıt / kısayol kalır. Deneme yalnızca sessiz modda, geçici dizine yapılır, ardından kaldırıcı çalıştırılır.
8. **Deneme kurulumunu gerçek `AppId` ile yapıp kaydı yedeklememek.** Kullanıcının "Uygulamalar ve özellikler" kaydı ve kısayolu bozuldu. → `save_registration` / `restore_registration` (try/finally).
9. **Kaldırıcıyı (`unins000.exe`) denemeden bırakmak.** Kaldırıcı da imzasız exe'dir.
10. **`PrivilegesRequired=admin` ile kurulum dosyasını Python'dan başlatmak.** `CreateProcess` 740 verir; denetim otomasyonu için `lowest` kullanıldı.
11. **Yayınlanmış etiketi taşımak / silip yeniden itmek** (kullanıcıların güncelleyicisi etiketi önbelleğe almış olabilir). Yeni PATCH çıkar.
12. **`git push --follow-tags`**: hafif etiketi göndermez. Etiketi ayrıca it.
13. **Yapay zekâ ajanının kullanıcı istemeden etiket oluşturması / itmesi.** Etiket itmek herkese güncelleme penceresi çıkarır; yalnızca açık istekle.
14. **UPX kullanmak** (`--noupx`): DLL imzalarını bozar, antivirüs yanlış pozitifini artırır.
15. **Kapıyı atlamak** (`--no-verify` ile yayın, özet dosyasını CI'da yeniden üretmek). Kapı yayını onaysız exe'den korur.
16. **Özet doğrulamasını isteğe bağlı bırakmak.** Özet yoksa güncelleme reddedilir; "özet yoksa yine de kur" yok.
17. **Güncelleme denetimini `create_qml_app`/testte tetiklemek.** Testler ağa çıkmasın; denetim `run()` içinde.
18. **Kullanıcı verisini kaldırıcıyla silmek.**
19. **Kabuk heredoc'u ile kod yazmak** (ajan aracı için): `\u`, `\x` gibi kaçışlar bozulur; dosyayı yazma aracıyla oluştur.

---

## 10. YAPILMASI gerekenler (kontrol listesi)

Kurulum (bir kez):

- [ ] `packaging/launcher.py`, `packaging/launcher_version_info.txt` (sabit `1.0.0.0`), `LAUNCHER_EPOCH`, `--debug=noarchive`, `--noupx`, `--onedir`, `--paths`, sürümü sabit `pyinstaller==X.Y.Z`.
- [ ] İlk exe'yi yerelde derle, **bu makinede aç**; engellenirse epoch'u değiştirip tekrar; açılınca `--update-launcher-hash` ile `packaging/launcher.sha256` yaz, commit'le.
- [ ] Testlerde giriş betiği ve sürüm kaynağı özetlerini sabitle, kapı testini ekle.
- [ ] `.gitattributes`: `* text=auto eol=lf`.
- [ ] Inno betiği: sabit `AppId`, `PrivilegesRequired=lowest`, `CloseApplications=yes`, `Check: RelaunchAfterUpdate`, sürümlü çıktı adı.
- [ ] `src/version.py` tek sürüm kaynağı, `tools/release.py`, `release.yml` (etiket denetimi, lint, test, `build_installer.py`, `gh release create --verify-tag`).
- [ ] `update_service` güvenlik kuralları (host listesi, sıkı ad, boyut, zorunlu SHA-256) ve testleri.
- [ ] İlk Release sonrası CI özeti = yerel özet mi bak; kurulum dosyasını GitHub'dan indirip SAC'lı makinede aç.

Her sürümde:

- [ ] Testler ve lint yeşil, çalışma ağacı temiz, dal `main`.
- [ ] `python tools/release.py X.Y.Z` → `git push origin main` → `git push origin vX.Y.Z`.
- [ ] Release iş akışı yeşil; günlükte "Kararlı exe özeti onaylananla aynı".
- [ ] Release'te `Setup-X.Y.Z.exe` ve `.sha256` var.
- [ ] Önceki sürümden uygulama içi güncelleme dene: pencere çıktı mı, kurulum başladı mı, uygulama yeniden açıldı mı, yeni sürüm numarası görünüyor mu.

Dağıtım ilkeleri:

- Denediğin dosyanın aynısını dağıt; yeniden paketleme özeti değiştirir.
- Kullanıcıya not (README): SmartScreen uyarısında "Ek bilgi → Yine de çalıştır"; SAC engelinde bu seçenek yoktur, "birkaç dakika sonra aynı dosyayı yeniden çalıştır / yeni sürümü indir".

---

## 11. Başka projeye uyarlama notları

- **Python/PyInstaller dışı yığınlar** (Electron, .NET, Go, C++): ilke aynıdır — çalıştırılabilir "kabuk" sabit kalsın, sürümle değişen kod veri dosyası olarak dışarıda dursun, kabuğun özeti derleme sonrası bir kapıyla sabitlensin. Yığın zaman damgası / derleme yolu gömüyorsa tekrarlanabilir derleme ayarlarını bul (örn. `SOURCE_DATE_EPOCH`, `-trimpath`, deterministik bağlayıcı).
- **Kurulum dosyası** her sürümde yenidir (Inno içinde sürüm var). Çok daha kesin sıfır-bekleme için ileride: dosya düzeyinde yama güncellemesi (yalnızca değişen `.pyc`/veri dosyalarını indir, SHA-256 doğrula, yerinde değiştir; PE dosyaları değişince kurulum dosyasına dön). Bu depoda **henüz yapılmadı**; son testte ihtiyaç doğmadı.
- Kullanıcı kimlik bilgisi, ağ ve veri minimizasyonu: yalnızca güncelleme denetimi için tek istek, kapatma yolları belgelenmiş olsun.
- Ajan çalışma kuralları (bu depoda geçerli): commit yalnızca kullanıcı "commit at" deyince; AI imzası / `Co-Authored-By` yok; etiket yalnızca açık istekle; yapılanı ve **doğrulanmayanı** dürüstçe raporla.

---

## 12. Bu depodaki referans dosyalar

| Dosya | Görev |
|---|---|
| `packaging/launcher.py`, `packaging/launcher_version_info.txt`, `packaging/launcher.sha256` | sabit giriş, sabit sürüm kaynağı, onaylı özet |
| `build_exe.py` | PyInstaller bağımsız değişkenleri, `LAUNCHER_EPOCH`, `check_launcher_hash` |
| `build_installer.py` | tek komutla exe + kurulum dosyası + `.sha256`, deneme |
| `build_verify.py` | `launch_check`, `installer_check`, kayıt / kısayol yedeği |
| `packaging/GitCleanArchiver.iss` | Inno betiği |
| `tools/release.py` | sürüm yükselt, commit, etiket; `--check-tag` |
| `.github/workflows/release.yml`, `ci.yml` | yayın ve sürekli tümleştirme |
| `src/version.py` | tek sürüm kaynağı |
| `src/services/update_service.py` | denetim, indirme, doğrulama, kurulumu başlatma |
| `src/qml_ui/viewmodels/update_viewmodel.py`, `src/qml_ui/qml/components/UpdateDialog.qml` | güncelleme arayüzü, bekleme / yeniden deneme |
| `tests/unit/test_release_packaging.py`, `tests/unit/test_build_verify.py`, güncelleme testleri | sabitleme, kapı, deneme izolasyonu, güvenlik kuralları |
