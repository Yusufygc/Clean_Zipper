# Uygulama İçi Güncelleme

Paketlenmiş uygulama açılışta GitHub Releases'te yeni sürüm arar; varsa "Yeni sürüm var" penceresi çıkar. **Güncelle** denince kurulum dosyası indirilir, doğrulanır,
uygulama kapanır ve kurulum dosyası sessiz kurulumla üstüne yazar; uygulama kendiliğinden yeniden açılır. Aynı desen `P013-Proje_Yonetim_Platformu` projesindedir
(`services/update_service.py`, `UpdateViewModel`, `UpdateDialog.qml`, `installer/windows.iss`).

## Akış

1. **Yayın:** `vX.Y.Z` etiketi push edilince `.github/workflows/release.yml` testleri koşar, `GitCleanArchiver-Setup-X.Y.Z.exe` ve `.sha256` dosyalarını üretip Release olarak yükler ([[surum-yayinlama]]).
2. **Denetim:** `UpdateViewModel.startupCheck()` pencere çizildikten 3 sn sonra `run()` içinden çağrılır (`create_qml_app` içinde değil: testler ağa çıkmasın). Ağ yoksa ya da hata olursa sessiz geçer;
   Ayarlar → Güncellemeler'deki **Şimdi Denetle** her sonucu gösterir. Kapatma: aynı kartta onay kutusu ya da `GITCLEAN_NO_UPDATE_CHECK=1`.
3. **Karşılaştırma:** `update_service.release_to_update()` `releases/latest` etiketini `src/version.py` sürümüyle sayısal karşılaştırır. Ön sürüm ve taslak yok sayılır.
4. **İndirme:** **Güncelle** → arka plan iş parçacığı (`DownloadWorker`), ilerleme çubuğu. Boyut ve SHA-256 doğrulanır: özet GitHub'ın asset `digest` alanından, yoksa Release'teki `.sha256` dosyasından alınır;
   ikisi de yoksa güncelleme **reddedilir**. Uyuşmazlıkta dosya silinir. İndirme klasörü `%TEMP%\GitCleanArchiverUpdate`.
5. **Kurulum:** `/SILENT /SUPPRESSMSGBOXES /CLOSEAPPLICATIONS /LOG=<klasör>\install.log` ile bağımsız süreç başlatılır (kabuk yok), `quitRequested` ile uygulama kapanır.
   `packaging/GitCleanArchiver.iss` içindeki `Check: RelaunchAfterUpdate` kurulumdan sonra uygulamayı yeniden açar (`/VERYSILENT` olan derleme sonrası denemede açmaz).

### Windows başlatmayı engellerse

`launch_installer` önce doğrudan süreç oluşturur (`CreateProcess`), `WinError 4551` (Akıllı Uygulama Denetimi) gelirse Gezgin'in çift tıklama yolunu (`ShellExecute`) dener; ikisi de engellenirse
`InstallerBlockedError` fırlatır. `UpdateViewModel` bu durumda **otomatik yeniden dener**: 15 sn aralıkla en çok 40 kez (10 dk), pencerede "Windows bekleniyor…" yazar ve **Beklemeyi Bırak** düğmesi çıkar; engel kalkınca kurulum kendiliğinden başlar ve uygulama kapanır (tam otomatik yol). Süre dolarsa ya da kullanıcı beklemeyi bırakırsa dosya **Gezgin'de seçili gösterilir** ve pencere şunu yazar: "Windows kurulum dosyasını şimdilik engelledi... çift tıklayarak kurabilirsiniz;
olmazsa birkaç dakika sonra yeniden deneyin" (**Sürüm Sayfası** düğmesi de çıkar). Yani otomatik yol engellenirse akış P013'teki elle kuruluma (indir, çift tıkla) düşer. Neden: 2026-10-11'de CI'da derlenen v2.1.1 kurulum dosyası
uygulamadan başlatılınca engellendi (olay 3077, başlatan süreç kurulu `GitCleanArchiver.exe`); yaklaşık 10 dakika sonra **aynı dosya** (aynı SHA-256) hem Gezgin'den hem `CreateProcess` ile başladı ([[exe-dagitim-rehberi]]). Kararlı exe sonrası (v2.1.4, v2.1.5) bu yola girilmedi.

## Katmanlar

`UpdateDialog.qml` → `UpdateViewModel` (`src/qml_ui/viewmodels/update_viewmodel.py`) → `update_service` (`src/services/update_service.py`; projeden bağımsız, `ProjectService` kullanmaz).
Tercihler ayrı dosyada (`~/.gitclean/updates.json`: açılış denetimi, atlanan sürüm).

## Güvenlik

- İndirme adresi yalnızca `https://github.com/<depo>/releases/download/...` olabilir; yönlendirme yalnızca `github.com` / `*.githubusercontent.com` adreslerine kabul edilir.
- Kurulum dosyası adı sıkı desene uymalı (`GitCleanArchiver-Setup-X.Y.Z.exe`); başka ad indirilmez ve başlatılmaz.
- Boyut sınırı 400 MB; sürüm notu düz metin gösterilir; yanıt boyutu ve süre sınırlıdır; kimlik bilgisi gönderilmez.
- **Sınır:** özet GitHub'dan gelir; GitHub hesabı ele geçirilirse sahte dosya + sahte özet yayınlanabilir (imza olmadığından fark yakalanamaz). Bu risk imzasız dağıtımın doğasıdır.
- Windows Akıllı Uygulama Denetimi imzasız kurulum dosyasını engelleyebilir; bu durumda indirme tamamlanır ama kurulum başlamaz ([[exe-dagitim-rehberi]]).

## P013 ile farklar

| | P013 | GitClean Archiver |
|---|---|---|
| Kurulum dosyası adı | sabit (`...Setup.exe`) | sürümlü (`...Setup-X.Y.Z.exe`) + `.sha256` |
| Özet | yalnızca GitHub `digest` (yoksa doğrulamasız) | `digest` ya da `.sha256` dosyası; ikisi de yoksa reddeder |
| "Bu sürümü atla", açılış denetimini kapatma | yok | var |
| Yeniden açma | `Check: WizardSilent` | `Check: RelaunchAfterUpdate` (`/VERYSILENT` hariç) |
| Yetki | yönetici kurulumu (`{autopf}`) | kullanıcıya özel (`PrivilegesRequired=lowest`): güncelleme UAC sormaz |

## Sınırlar

- Yalnızca Windows.
- **Doğrulandı (gerçek Release, 2026-10-12):** v2.1.4 → v2.1.5 uygulama içi güncellemede güncelleme penceresi çıktı, bekleme olmadı, kurulum ilerleme penceresi göründü, uygulama kendiliğinden yeniden açıldı, yeni sürümün exe'si engellenmedi. Önceki denemelerde (v2.1.1 → v2.1.2, v2.1.2 → v2.1.3) kurulum dosyası engele takılmıştı; yeniden deneme kodu o zaman yazıldı.
- İndirme sürerken pencere kapatılamaz; iptal düğmesi yok.
- Engelin kalkması zamana ya da başlatan sürece bağlı olabilir; hangisi olduğu ayrıştırılamadı (gözlemler: v2.1.1 ~10 dk, v2.1.2 birkaç dk, v2.1.3 ~1 dk; son güncellemede hiç engel olmadı). Otomatik yeniden deneme bu gözlemlere dayanır; engel sürerse kullanıcı dosyayı elle çalıştırır.
- Her sürümde yeni olan tek çalıştırılabilir dosya Inno kurulum dosyasıdır (exe kararlıdır); bu yüzden engel ihtimali tümüyle yok değildir. Ayrıntı, kökler ve alternatifler: [[exe-dagitim-rehberi]].
