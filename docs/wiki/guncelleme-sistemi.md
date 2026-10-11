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

## Katmanlar

`UpdateDialog.qml` → `UpdateViewModel` (`src/qml_ui/viewmodels/update_viewmodel.py`) → `update_service` (`src/services/update_service.py`; projeden bağımsız, `ProjectService` kullanmaz).
Tercihler ayrı dosyada (`~/.gitclean/updates.json`: açılış denetimi, atlanan sürüm).

## Güvenlik

- İndirme adresi yalnızca `https://github.com/<depo>/releases/download/...` olabilir; yönlendirme yalnızca `github.com` / `*.githubusercontent.com` adreslerine kabul edilir.
- Kurulum dosyası adı sıkı desene uymalı (`GitCleanArchiver-Setup-X.Y.Z.exe`); başka ad indirilmez ve başlatılmaz.
- Boyut sınırı 400 MB; sürüm notu düz metin gösterilir; yanıt boyutu ve süre sınırlıdır; kimlik bilgisi gönderilmez.
- **Sınır:** özet GitHub'dan gelir; GitHub hesabı ele geçirilirse sahte dosya + sahte özet yayınlanabilir (imza olmadığından fark yakalanamaz). Bu risk imzasız dağıtımın doğasıdır.
- Windows Akıllı Uygulama Denetimi imzasız kurulum dosyasını engelleyebilir; bu durumda indirme tamamlanır ama kurulum başlamaz ([[windows-exe-dagitim]]).

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
- Release iş akışı ve uygulama içi indirme / kurulum zinciri gerçek bir Release ile hiç koşmadı (doğrulanan: birim testleri, sahte sunucu ile indirme / doğrulama, kurulum dosyasının sessiz kurulumu, `RelaunchAfterUpdate`'in derlenmesi).
- İndirme sürerken pencere kapatılamaz; iptal düğmesi yok.
