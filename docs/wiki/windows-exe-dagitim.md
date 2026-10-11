# Windows exe dağıtımı: Akıllı Uygulama Denetimi rehberi

Bu sayfa, imzasız bir Windows uygulamasını (PyInstaller exe + Inno Setup kurulum dosyası) dağıtırken Windows **Akıllı Uygulama Denetimi**'ne
(Smart App Control, SAC) takılmamak için bilinmesi gerekenleri toplar. Başka projelere de uygulanabilir. İlgili kararlar: [[decisions]]; günlük: [[log]].

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
| Engellenen exe'nin **aynı hash'li kopyası başka klasörde** | yine engellendi: konuma bağlı değil, içeriğe bağlı |
| İndirilmiş dosya işareti (MOTW, `Zone.Identifier` ZoneId=3) ekli kopya | çalışanlarda sonucu değiştirmedi |
| Yetki düzeyi (yönetici / kullanıcıya özel kurulum) | belirgin etkisi görülmedi |
| `onefile` ile `onedir` ayrımı | istatistiksel fark görülmedi (onedir yalnızca daha küçük kurulum dosyası ve hızlı açılış verir) |

Sonuç: "şu bayrakla derlersen geçer" diye bir tarif **yok**. Güvenilir tek yol imzalamaktır; imzasız dağıtımda risk azaltılabilir, sıfırlanamaz.

## 3. Kalıcı çözüm: kod imzalama

SAC, Microsoft'un güvenilir kök programındaki bir sertifikayla imzalı dosyaları itibar sorgusuna gerek kalmadan çalıştırır.
Kendinden imzalı sertifika SAC'ı **geçmez** (yalnızca o makinede güven deposuna eklenirse ve bu bir güvenlik ayarıdır; önerilmez).

- **SignPath Foundation:** açık kaynak projelere ücretsiz, GitHub Actions ile çalışır. Başvuru için depoda OSI uyumlu **lisans** gerekir (bu repoda `LICENSE` yok).
- **Azure Trusted Signing:** ücretli, kolay; bireysel / kurumsal hesabın ülke uygunluğu kontrol edilmeli (Türkiye için doğrulanmadı).
- **Ticari OV / EV sertifika:** yıllık ücretli; OV sertifikalar donanım anahtarı / HSM ister.
- İmzalanacaklar: uygulama exe'si, Inno kurulum dosyası **ve** kaldırıcı (`SignedUninstaller=yes`); `signtool sign /fd SHA256 /tr <zaman damgası> /td SHA256`. Zaman damgası olmadan sertifika bitince imza geçersiz olur.

## 4. İmzasız dağıtımda yapılacaklar (kontrol listesi)

1. **Dağıtmadan önce bu makinede dene, engellenirse yeniden derle.** `python build_installer.py` bunu yapar (`build_verify.py`): exe'yi başlatır, kurulum dosyasını geçici klasöre sessizce kurup açar ve kaldırır; engellenirse özet değişsin diye en çok 6 kez yeniden derler. CI'da (`CI` ortam değişkeni) ve `--no-verify` ile atlanır.
2. **Denediğin dosyanın aynısını dağıt.** Dosyayı yeniden derleme, yeniden paketleme ya da yeniden adlandırma hash'i (ve itibarı) değiştirir; GitHub Release'e yüklediğin dosya denediğin dosya olmalı.
3. **CI'da derlenen dosya yerelde denenmemiş dosyadır.** GitHub runner'da SAC yoktur; Release yayınlandıktan sonra **indirilmiş (MOTW'li) kopyayı** SAC'lı bir makinede aç. Engellenirse yerelde derleyip denenmiş dosyayı Release'e elle yükle.
4. **`--noupx`:** UPX, Python / Qt DLL'lerinin imzasını bozar ve antivirüs yanlış pozitifi artırır.
5. **PyInstaller `--onedir` + Inno Setup** tercih edilir (SAC için kanıtlı bir üstünlüğü yok; kurulum dosyası 62 → 40 MB, her açılışta `%TEMP%`'e 60 MB açma yok).
6. **Sürüm bilgisi (`--version-file`) ve simge** gömülü olsun (kurumsal görünüm, SmartScreen / antivirüs güveni); tek başına SAC'ı geçirmez.
7. **Kullanıcıya not:** SmartScreen uyarısında "Ek bilgi → Yine de çalıştır". SAC engelinde bu seçenek yoktur; kullanıcıya "dosyayı kaldırıp yeni sürümü indir" ya da imzalı sürümü bekle de. **SAC'ı kapatmayı önerme:** Windows'ta kapatılınca yeniden açmak için sıfırlama gerekir.
8. **Kendini kuran tek exe fikri çözüm değildir** (denendi ve geri alındı: engel kurulum programında değil, her yeni exe'nin kendisinde; tek exe'nin engellenme riski ayrı kurulum programınınkiyle aynıdır).

## 5. Yapılmaması gerekenler (bu depoda yaşandı)

- **Inno kurulum dosyasını "açılıyor mu" diye elle başlatıp öldürmek:** sihirbaz yükseltilmiş çalıştıysa süreç öldürülemez (`Erişim engellendi`) ve kurulum tamamlanabilir; makinede gerçek kurulum, kayıt ve Başlat menüsü grubu kalır. Denemeyi yalnızca `/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR=<geçici klasör>` ile yap, ardından `unins000.exe /VERYSILENT` çalıştır (`build_verify.installer_check`).
- **Aynı `AppId` ile deneme kurulumu bırakmak:** gerçek kurulumun kaydıyla çakışır; deneme sonrası kaydın (`HKLM`/`HKCU ...\Uninstall\{AppId}_is1`) ve Başlat menüsü grubunun kalktığını doğrula.
- **Yetki gerektiren kurulum dosyasını Python `subprocess` ile başlatmak:** `PrivilegesRequired=admin` iken CreateProcess 740 hatası verir; denetimi otomatikleştirmek için kullanıcıya özel (`PrivilegesRequired=lowest`) kurulum kullanıldı.
- **Engeli "kodla aşmaya" çalışmak** (hash değiştirme dışında): SAC bir güvenlik özelliğidir; hash değiştirerek yeniden derlemek yalnızca yanlış pozitif ya da bilinmeyen dosyaya yeni karar aldırır, korumayı aşmaz.
- **MOTW'yi kaldırmanın SAC'ı geçireceğini sanmak:** SAC için etkisizdir (SmartScreen için işe yarar).

## 6. Bu repoda akış

```text
python build_installer.py              # build_exe.py (onedir, noupx) → exe dene → Inno derle → kurulum dosyasını dene → .sha256
python build_installer.py --no-verify  # denemeden
python tools/release.py X.Y.Z          # sürüm + commit + etiket (push elle)
```

Çıktılar `dist/GitCleanArchiver/` (onedir) ve `dist/installer/GitCleanArchiver-Setup-X.Y.Z.exe` (+ `.sha256`). Güncelleme denetimi bu dosya adını arar (`update_service.INSTALLER_PATTERN`).
`build_verify.py` bağımsızdır: başka bir projeye kopyalanabilir (`launch_check`, `installer_check`; yalnızca standart kitaplık).
