# Sürüm Yayınlama Süreci

Yeni sürüm **etiket** ile yayınlanır: `vX.Y.Z` etiketi push edilince GitHub Actions testleri koşar, uygulamayı ve Inno kurulum dosyasını derler ve GitHub Releases'e yükler.
Kurulu uygulamalar açılışta bu yayını görüp güncelleme teklif eder ([[guncelleme-sistemi]]). Aynı desen `P013-Proje_Yonetim_Platformu` projesindedir.

## Sürüm numarası

- Biçim: `MAJOR.MINOR.PATCH` (örn. `2.1.0`). Etiketin başına `v` konur (`v2.1.0`).
- Güncelleyici yalnızca bu üç sayılı biçimi tanır ve sayısal karşılaştırır (`2.10.0 > 2.9.0`). `2.2.0-rc1` gibi ön sürümler yok sayılır.
- **Tek kaynak:** `src/version.py` (`__version__`, `RELEASE_REPO`). README rozeti `tools/release.py` ile aynı değere çekilir; elle düzenlenmez (`tests/unit/test_release_packaging.py` tutarlılığı denetler). exe'nin Windows sürüm kaynağı **bilerek** yükseltilmez (kararlı exe, [[exe-dagitim-rehberi]]); ürün sürümü kurulum dosyasında, Inno kaydında ve uygulamada görünür.
  Inno betiği sürümü `build_installer.py` üzerinden `/DAppVersion` ile alır.
- Artış kuralı: hata düzeltme → PATCH; yeni özellik → MINOR; geriye dönük uyumsuz veri / ayar değişikliği → MAJOR.

## Yayın adımları

Ön koşul: yayınlanacak commit'te CI yeşil (`ruff`, `pytest`), çalışma ağacı temiz, dal `main`.

```powershell
python tools/release.py 2.1.0         # sürümü yükseltir, "chore(release): v2.1.0" commit'i atar, v2.1.0 etiketini oluşturur (itmez)
git push origin main
git push origin v2.1.0                # --follow-tags KULLANMA: hafif etiketleri göndermez
gh run watch                          # Release iş akışını izle
gh release view v2.1.0                # yayın, kurulum dosyası ve .sha256 oluştu mu
```

Release iş akışı (`.github/workflows/release.yml`) sırayla şunları yapar:

1. Etiket (`v2.1.0`) ile `src/version.py` aynı değilse **durur** (`tools/release.py --check-tag`).
2. `ruff` ve `pytest` koşar; kırmızıysa yayın yapılmaz.
3. `python build_installer.py`: PyInstaller `--onedir` ile uygulamayı derler, **exe özetini onaylanmışla (`packaging/launcher.sha256`) karşılaştırır, farklıysa yayın durur**, Inno Setup ile `GitCleanArchiver-Setup-X.Y.Z.exe` dosyasını derler ve `.sha256` yazar (CI'da Akıllı Uygulama Denetimi denemesi atlanır).
4. `gh release create`: kurulum dosyası ve `.sha256` yüklenir; sürüm notları commit mesajlarından otomatik üretilir (bu yüzden commit mesajları anlaşılır ve Türkçe yazılır).
   `-` içeren etiket (`v2.2.0-rc1`) ön sürüm olur ve güncelleme denetimince yok sayılır.

## Kontrol listesi

- [ ] CI yeşil, `python -m pytest -q` yerelde geçiyor.
- [ ] Davranış değişikliği varsa `README.md` ve ilgili wiki sayfası güncel.
- [ ] `tools/release.py` çalıştırıldı, `src/version.py` ve README rozeti aynı sürümde.
- [ ] Exe özeti onaylananla aynı (CI günlüğünde "Kararlı exe özeti onaylananla aynı"); değilse yayın durmuştur: nedeni araştır, bilerek değiştirdiysen [[exe-dagitim-rehberi]] bölüm 8.
- [ ] Etiket sürümle birebir aynı (`v` + `__version__`).
- [ ] Release iş akışı yeşil, `gh release view` kurulum dosyasını ve `.sha256` dosyasını gösteriyor.
- [ ] Yayınlanan dosya indirilip (MOTW'li) bu makinede denendi ([[exe-dagitim-rehberi]]: CI'da derlenen dosya yerelde denenmemiş dosyadır).

## Hata ve geri alma

| Durum | Ne yapılır |
|---|---|
| Etiket ile `__version__` farklı, iş akışı durdu | Yayın oluşmadı. Sürümü düzelt, commit et, etiketi yeni commit'e taşı: `git tag -f vX.Y.Z` ve `git push -f origin vX.Y.Z`. |
| Derleme adımı düştü (yayın yok) | Sebebi düzelt, etiketi aynı yolla taşı. Yayın oluşmadığı için kimse etkilenmez. |
| Yayın oluştu ama sürüm hatalı | Etiketi taşıma. Yeni PATCH sürümü çıkar. Acilse `gh release delete vX.Y.Z --cleanup-tag`: güncelleyici `latest` yayına baktığından önceki sürüm tekrar "son sürüm" olur. |
| `git push --follow-tags` etiketi göndermedi | Hafif etiketler gitmez; `git push origin vX.Y.Z` ile ayrıca gönder (`tools/release.py` ek açıklamalı etiket oluşturur). |
| Kurulu kullanıcıda güncelleme başlamadı | `%TEMP%\GitCleanArchiverUpdate\install.log` (sessiz kurulum hata göstermez, neden orada). |

## Güvenlik ve sınırlar

- Yayın, tüm kurulu kullanıcılara güncelleme penceresi çıkarır. **Yapay zeka asistanları kullanıcının açık isteği olmadan etiket oluşturmaz, etiket push etmez.**
- İndirme adresi yalnızca bu deponun `releases/download/` yolu olabilir; boyut ve SHA-256 özeti doğrulanır, özet yoksa güncelleme reddedilir. Bu kontroller kaldırılmaz.
- Kurulum dosyası **imzasızdır** (karar: imzalama yapılmıyor); Windows SmartScreen uyarısı ve Akıllı Uygulama Denetimi engeli olabilir ([[exe-dagitim-rehberi]]).
- Yalnızca Windows.
- Release iş akışı v2.1.2 – v2.1.5 için başarıyla koştu; v2.1.4 ve v2.1.5'te exe özeti CI'da yerelle aynı çıktı (kapı geçti).

İlgili: [[guncelleme-sistemi]], [[exe-dagitim-rehberi]], [[decisions]]
