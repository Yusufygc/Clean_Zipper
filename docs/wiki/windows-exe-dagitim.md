# Windows exe dağıtımı: Akıllı Uygulama Denetimi rehberi

Bu sayfa, imzasız bir Windows uygulamasını (PyInstaller exe + Inno Setup kurulum dosyası) dağıtırken Windows **Akıllı Uygulama Denetimi**'ne
(Smart App Control, SAC) takılmamak için bilinmesi gerekenleri toplar. Başka projelere de uygulanabilir. Dağıtım ve güncelleme deseni `P013-Proje_Yonetim_Platformu` ile aynıdır: [[surum-yayinlama]], [[guncelleme-sistemi]]. İlgili kararlar: [[decisions]]; günlük: [[log]].

## 1. Belirti ve teşhis

| Belirti | Anlamı |
|---|---|
| "Uygulama Denetimi ilkesi bu dosyayı engelledi" (Gezgin, PowerShell `Start-Process`) | SAC dosyayı çalıştırmadı |
| Python `subprocess.Popen` → `OSError: [WinError 4551]` | aynı engel (kod: `build_verify.is_blocked`) |
| Bash: `Permission denied` (çıkış 126) | aynı engel, kabuk farklı mesaj veriyor |

Olay günlüğünde kesin kanıt (kimin neyi neden engellediği):

```powershell
Get-WinEvent -LogName "Microsoft-Windows-CodeIntegrity/Operational" -MaxEvents 400 |
  Where-Object { $_.Id -in 3077,3033 } | Select-Object -First 5 TimeCreated, Id, Message | Format-List
# 3077: "...did not meet the Enterprise signing level requirements or violated code integrity policy (Policy ID:{0283ac0f-fff1-49ae-ada1-8a933130cad6})"
```

SAC durumu: `HKLM\SYSTEM\CurrentControlSet\Control\CI\Policy` altında `VerifiedAndReputablePolicyState` (bu makinede `1` iken engelliyor).
Dosyanın imzası: `Get-AuthenticodeSignature <dosya>` (`NotSigned` ise SAC'ın "güvenilir imza" yolu yok).

## 2. Kök neden (bu repoda ölçüldü, 2026-10-11)

SAC, imzasız bir exe'yi dosya **özetine (hash)** göre Microsoft'un bulut itibar / yapay zekâ kararına bırakır. Bilinmeyen bir dosya engellenebilir.
Karar **dosya başına ve öngörülemez**: aynı kaynak koddan, aynı bayraklarla yapılan iki derleme farklı sonuç verebilir (özet her derlemede değişir).

| Deney | Sonuç |
|---|---|
| `--onefile` exe, 4 ardışık derleme | ilk 3 çalıştı, 4. engellendi |
| `--onedir` exe, 5 derleme | 3 çalıştı, 2 engellendi |
| Inno Setup kurulum dosyası, 4 derleme | 3 çalıştı, 1 engellendi (çalışanlar sessiz kurulup kaldırıldı) |
| Kullanıcının diğer projeleri (imzasız PyInstaller exe + Inno kurulum, 16-98 günlük) | 8 çalıştı, 2 engellendi (en eski ikisi) |
| **P013 (Proje Takip Platformu), desenin kaynağı:** onedir exe (8 Ekim, `upx=False`, sürüm bilgisi gömülü) | **engellendi**; aynı projenin eski `--onefile` exe'si (Temmuz) çalıştı |
| Engellenen exe'nin **aynı hash'li kopyası başka klasörde** | yine engellendi: konuma bağlı değil, içeriğe bağlı |
| **CI'da derlenen v2.1.1 kurulum dosyası**, kurulu uygulamanın başlattığı süreçten (`CreateProcess`) | engellendi (olay 3077, başlatan: kurulu `GitCleanArchiver.exe`); SHA-256 doğrulaması geçmişti |
| **Aynı dosya (aynı SHA-256), ~10 dk sonra**, Gezgin (`ShellExecute`) ve `CreateProcess` ile | **başladı** (sihirbaz açıldı): verdict zamanla ya da başlatan sürece göre değişmiş; hangisi olduğu ayrıştırılamadı |
| **v2.1.2 (CI derlemesi), 2026-10-11 23:35-23:4x:** v2.1.1 uygulaması indirip başlatınca "Kurulum başlatılamadı." (eski kod) ve Windows bildirimi "Bu uygulamanın bir kısmı engellendi"; benim Gezgin denemem SAC penceresi çıkardı ("Yayımcısı doğrulanamadığı için... Microsoft, uygulamanın güvenli olup olmadığını doğrulamak için **inceleyecek**", olay 3077); kullanıcı dakikalar içinde aynı dosyaya `%TEMP%`'ten çift tıkladı ve **bekletmeden açıldı**, kurulum tamamlandı | engel kısa sürdü; bulut incelemesi (zaman) ya da çift tıklama yolu etkili, ayrıştırılamadı |
| Doğrulamalı derleme turu (6 deneme, 2026-10-11 akşam) | 5 exe + 1 kaldırıcı (`unins000.exe`) engellendi, geçen derleme çıkmadı: oran zamanla kötüleşiyor gibi, ama örnek küçük |
| İndirilmiş dosya işareti (MOTW, `Zone.Identifier` ZoneId=3) ekli kopya | çalışanlarda sonucu değiştirmedi |
| Yetki düzeyi (yönetici / kullanıcıya özel kurulum) | belirgin etkisi görülmedi |
| `onefile` ile `onedir` ayrımı | istatistiksel fark görülmedi (onedir yalnızca daha küçük kurulum dosyası ve hızlı açılış verir) |

Sonuç: "şu bayrakla derlersen geçer" diye bir tarif **yok**. Güvenilir tek yol imzalamaktır; imzasız dağıtımda risk azaltılabilir, sıfırlanamaz.

### Pratik çıkarım (v2.1.1 ve v2.1.2 gözlemleri)

- SAC penceresi engeli "Microsoft inceleyecek" diye açıklıyor: karar bulutta verilir, aynı dosya birkaç dakika içinde açılabilir. İki vakada da (v2.1.1 ~10 dk, v2.1.2 birkaç dk) engel kısa sürdü.
- Engellenen dosya bozuk değildir: indirme SHA-256'sı Release `digest` ile aynıydı. Kullanıcıya doğru talimat: dosyayı silme, birkaç dakika bekleyip `%TEMP%\GitCleanArchiverUpdate\GitCleanArchiver-Setup-X.Y.Z.exe` dosyasına çift tıkla.
- Eski sürüm uygulama (yeni yeniden deneme koduna sahip olmayan) engelde yalnızca genel hata gösterir; yeniden deneme / Gezgin'de gösterme **kurulu sürümde** çalışır. Bu yüzden bu kod bir sürüm sonra (kurulu sürüm ≥ 2.1.2 olduktan sonra) devreye girer; v2.1.1 → v2.1.2 geçişi elle kaldı.

## 3. İmza: bu projede yapılmıyor

Tek deterministik çözüm kod imzalamadır (Microsoft'un güvenilir kök programındaki bir sertifikayla imzalı dosyaları SAC itibar sorgusu olmadan çalıştırır); ücretsiz yol (SignPath Foundation) ve ücretli yollar vardır.
**Karar (2026-10-11): imzalama yapılmayacak** (üçüncü taraf hesabı / başvuru / sertifika yönetimi istenmiyor). Sonuç: engel riski kalır; aşağıdaki liste yalnızca riski azaltır.
Kullanıcıya düşen: engellenen dosyada "dosyayı yeniden indir / yeni sürümü bekle"; SAC'ı kapatmak önerilmez (Windows'ta kapatılınca yeniden açmak için sıfırlama gerekir).

## 4. İmzasız dağıtımda yapılacaklar (kontrol listesi)

1. **Dağıtmadan önce bu makinede dene, engellenirse yeniden derle.** `python build_installer.py` bunu yapar (`build_verify.py`): exe'yi başlatır, kurulum dosyasını geçici klasöre sessizce kurup açar ve kaldırır; engellenirse özet değişsin diye en çok 6 kez yeniden derler. CI'da (`CI` ortam değişkeni) ve `--no-verify` ile atlanır.
2. **Denediğin dosyanın aynısını dağıt.** Dosyayı yeniden derleme, yeniden paketleme ya da yeniden adlandırma hash'i (ve itibarı) değiştirir; GitHub Release'e yüklediğin dosya denediğin dosya olmalı.
3. **CI'da derlenen dosya yerelde denenmemiş dosyadır.** GitHub runner'da SAC yoktur; Release yayınlandıktan sonra **indirilmiş (MOTW'li) kopyayı** SAC'lı bir makinede aç. Engellenirse yerelde derleyip denenmiş dosyayı Release'e elle yükle.
4. **`--noupx` (P013 de `upx=False`):** UPX, Python / Qt DLL'lerinin imzasını bozar ve antivirüs yanlış pozitifi artırır.
5. **PyInstaller `--onedir` + Inno Setup** tercih edilir (SAC için kanıtlı bir üstünlüğü yok; kurulum dosyası 62 → 40 MB, her açılışta `%TEMP%`'e 60 MB açma yok).
6. **Sürüm bilgisi (`--version-file`) ve simge** gömülü olsun (kurumsal görünüm, SmartScreen / antivirüs güveni); tek başına SAC'ı geçirmez.
7. **Kullanıcıya not:** SmartScreen uyarısında "Ek bilgi → Yine de çalıştır". SAC engelinde bu seçenek yoktur; kullanıcıya "dosyayı kaldırıp yeni sürümü indir" ya da imzalı sürümü bekle de. **SAC'ı kapatmayı önerme:** Windows'ta kapatılınca yeniden açmak için sıfırlama gerekir.
8. **Kendini kuran tek exe fikri çözüm değildir** (denendi ve geri alındı: engel kurulum programında değil, her yeni exe'nin kendisinde; tek exe'nin engellenme riski ayrı kurulum programınınkiyle aynıdır).

## 5. Yapılmaması gerekenler (bu depoda yaşandı)

- **Inno kurulum dosyasını "açılıyor mu" diye elle başlatıp öldürmek:** sihirbaz yükseltilmiş çalıştıysa süreç öldürülemez (`Erişim engellendi`) ve kurulum tamamlanabilir; makinede gerçek kurulum, kayıt ve Başlat menüsü grubu kalır. Denemeyi yalnızca `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR=<geçici klasör>` ile yap, ardından `unins000.exe /VERYSILENT` çalıştır (`build_verify.installer_check`).
- **Derleme sonrası denemenin gerçek kurulumu ezmesi (yaşandı, düzeltildi):** deneme kurulumu gerçek kurulumla aynı `AppId`'yi kullanır; Inno aynı "Uygulamalar ve özellikler" kaydını ve Başlat menüsü kısayolunu yazar / siler. Deneme çökünce kullanıcının kaydı ve kısayolu geçici klasörü gösteriyordu. `build_verify.py` artık denemeden önce kaydı ve kısayolu yedekler, ne olursa olsun geri yükler (`save_registration` / `restore_registration`, testli).
- **Kaldırıcıyı (`unins000.exe`) unutmak:** kurulum sırasında üretilen kaldırıcı da imzasız bir exe'dir ve engellenebilir (kullanıcı "Uygulamalar ve özellikler"den kaldıramaz); `installer_check` kaldırıcıyı da çalıştırır ve engellenirse denemeyi başarısız sayar.
- **Aynı `AppId` ile deneme kurulumu bırakmak:** gerçek kurulumun kaydıyla çakışır; deneme sonrası kaydın (`HKLM`/`HKCU ...\Uninstall\{AppId}_is1`) ve Başlat menüsü grubunun kalktığını doğrula.
- **Yetki gerektiren kurulum dosyasını Python `subprocess` ile başlatmak:** `PrivilegesRequired=admin` iken CreateProcess 740 hatası verir; denetimi otomatikleştirmek için kullanıcıya özel (`PrivilegesRequired=lowest`) kurulum kullanıldı.
- **Engeli "kodla aşmaya" çalışmak** (hash değiştirme dışında): SAC bir güvenlik özelliğidir; hash değiştirerek yeniden derlemek yalnızca yanlış pozitif ya da bilinmeyen dosyaya yeni karar aldırır, korumayı aşmaz.
- **MOTW'yi kaldırmanın SAC'ı geçireceğini sanmak:** SAC için etkisizdir (SmartScreen için işe yarar).

## 6. Bu repoda akış

```text
python build_installer.py              # build_exe.py (onedir, noupx) → exe dene → Inno derle → kurulum dosyasını dene → .sha256
python build_installer.py --no-verify  # denemeden
python tools/release.py X.Y.Z          # sürüm + commit + etiket (push elle) -> Release iş akışı: [[surum-yayinlama]]
```

Çıktılar `dist/GitCleanArchiver/` (onedir) ve `dist/installer/GitCleanArchiver-Setup-X.Y.Z.exe` (+ `.sha256`). Güncelleme denetimi bu dosya adını arar (`update_service.INSTALLER_PATTERN`).
`build_verify.py` bağımsızdır: başka bir projeye kopyalanabilir (`launch_check`, `installer_check`; yalnızca standart kitaplık).
