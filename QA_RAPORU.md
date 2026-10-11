# GitClean Archiver: QA Denetim Raporu

| | |
|---|---|
| **Tarih** | 11 Ekim 2026 |
| **Sürüm** | 2.0.0, dal `ui/xp-retro-tema` (3 commit `main`'in önünde: `a50f6b3`, `a8a8d34`, `2bad333`) |
| **Ortam** | Windows 11, Python 3.10.11, PySide6 6.12.0 |
| **Yöntem** | Uygulama kendi kendini denetledi (dogfooding) ve gerçek pencere üzerinden uçtan uca sınandı |
| **Karar** | **İlk tur: koşullu geçer; düzeltme turundan sonra: geçer.** Çekirdek işlevler (analiz, arşiv, yedek, temizlik, dışa aktarma) baştan doğru çalışıyordu, veri kaybı ya da sır sızıntısı bulunmadı. Raporlanan 12 bulgunun hepsi düzeltildi ve yeniden sınandı (Bölüm 9). |

---

## 1. Özet

| Gösterge | Değer |
|---|---|
| Otomatik test | **792 geçti, 2 atlandı** (794 toplandı) |
| Lint (ruff) | Temiz |
| Bağımlılık taraması (pip-audit) | Bilinen açık yok |
| CI (`main`, GitHub Actions) | Yeşil |
| Uçtan uca QA kontrolü | 135 kontrol: 109 geçti, 15 kaldı, 11 gözlem; kalanların dökümü Bölüm 4'te |
| Hedefli ikinci tur | 7 senaryo (şüpheli sonuçların ayrıştırılması), klavye / erişilebilirlik denemesi ve gerçek platformda çizim |
| EXE (`GitCleanArchiver.exe`, 59 MB) | Açılıyor, yanıt veriyor, başlık / sürüm / ikon doğru, kapanınca işlem kalmıyor |
| Uygulamanın kendi denetimi (kendi deposu) | 216 dosya, **skor 86/100 (A)**, 0 çöken analizör, 2,3 sn |

**Bulgu özeti (ilk tur):** 4 orta, 5 düşük, 3 bilgi; hepsi Bölüm 9'daki düzeltme turunda kapatıldı. Bölüm 3 ve 6, ilk turdaki hâli korur (kayıt amacıyla).

---

## 2. Kapsam ve yöntem

**Kullanılan düzenek.** Bir uçtan uca betik, gerçek QML penceresini açıyor ve **gerçek fare tıklamalarıyla** (`QTest.mouseClick`) sürüyor; servisler gerçek, kullanıcı klasörleri yalıtılmış (ayarlar, yedekler, ajan görevleri geçici klasöre yönlendirildi, gerçek `~/.gitclean` değişmedi). Doğrulamalar uygulamanın verdiği cevabı **bağımsız bir kaynakla** karşılaştırır: ayrı bir `ProjectIndex`, `zipfile.testzip`, dosya sistemi durumu.

**Örnek proje.** Bilinçli yerleştirilmiş sorunlarla kurulan, Türkçe karakterli ve boşluklu yola sahip, `git` deposu hâlinde bir proje: sır içeren `.env` (commit edilmiş), koda gömülü parola, çıplak `except`, kullanılmayan import, kopya dosyalar, 12 MB'lık dosya, boş ve iç içe boş klasörler, `venv` ve `node_modules`, `.gitignore`'lu veri, `__pycache__`, `.tmp`, `.log`, `.bak`, kullanılmayan bağımlılık ve **proje dışına işaret eden bir junction**.

**Senaryolar:** açılış, proje açma, dashboard, bulgu gezgini ve süzgeçler, kural kapatma, ayarlar, 3 arşiv profili, temiz kopya, yedek ve rotasyon, temizlik, eşzamanlı işlemler, dışa aktarmalar, tema ve sekmeler, pencere boyutları (900×600, 1100×700, 1920×1080), uç durumlar, erişilebilirlik (kontrast, klavye), EXE.

**Ek:** ekran görüntüleri `docs/qa/` klasöründe.

---

## 3. Bulgular

Önem: 🔴 Yüksek · 🟠 Orta · 🟡 Düşük · ℹ️ Bilgi

### QA-01 🟠 Üç sayfada kaydırma çubuğu görünmüyordu (QA'da bulundu, **düzeltildi**)

- **Belirti:** Gösterge Paneli, Arşivleme ve Ayarlar sayfalarında görünür kaydırma çubuğu yok; ilk kartın sol üst köşesinde 20×4 px'lik küçük bir çerçeve artefaktı var.
- **Neden:** Bu dalda eklenen `ThemedScrollBar` bir `ScrollView`'a atanınca Qt varsayılan konumlandırmayı uygulamıyor; çubuk sağ kenara oturmak yerine sol üstte 10×4 px kalıyordu. **Benim önceki değişikliğimden doğan bir gerilemeydi.** Fark, gerçek platformda çizilen ekran görüntüsünde büyütülen artefakttan, ardından öğe konumlarını listeleyerek bulundu.
- **Düzeltme:** çubuk `ScrollView` içindeyken sağ kenara ve içerik yüksekliğine oturtuluyor. Yeni test `test_scroll_views_place_their_themed_scrollbar_on_the_right_edge` eski kodda kırmızı, yeni kodda yeşil.
- **Durum:** düzeltildi.

### QA-02 🟠 Temizlikten sonra dashboard ve bulgu listesi bayat kalıyor

- **Tekrar:** proje aç → "Temizliği Başlat" (`.tmp` dosyası siliniyor) → dashboard'a bak.
- **Beklenen:** sayılar güncel.
- **Gözlenen:** dashboard **3 dosya** diyor, gerçekte **2**; bulgu sayısı 8 olarak kalıyor (silinen dosyayla ilgili bulgular listede duruyor). Servis tarafı doğru (önbellek geçersiz kılınıyor ve taze teşhis 2 veriyor); eksik olan, arayüzün yeniden analiz başlatması.
- **Etki:** kullanıcı eski sayılara güvenip karar verebilir; "Yeniden Analiz Et" demedikçe düzelmez.
- **Öneri:** başarılı temizlikten sonra otomatik yeniden analiz (ya da en azından "Sonuçlar eski, yeniden analiz edin" uyarısı).

### QA-03 🟠 Türkçe büyük harfle arama çalışmıyor

- **Tekrar:** Sorunlar sayfasında arama kutusuna `ŞİFRE` ya da `AÇIK` yaz.
- **Gözlenen:** `şifre` ve `Şifre` 1 sonuç verir; **`ŞİFRE` ve `AÇIK` 0 sonuç**. Ayrıca yanlış bir eşleşme var: `ŞIFRE` (noktasız I) 1 sonuç verir.
- **Neden:** `str.lower()` `İ` → `i̇` (nokta birleştiren karakterle) ve `I` → `i` dönüştürür; Türkçede `I` → `ı`.
- **Öneri:** aramada hem sorguyu hem hedefi Türkçe duyarlı katlama ile normalize etmek (`İ→i`, `I→ı`, ardından `lower()`), tercihen `i/ı` farkını da gevşeterek.

### QA-04 🟠 Uygulama klavyeyle kullanılamıyor (erişilebilirlik)

- **Gözlenen:** Tab ile odaklanabilen **0 öğe**; 12 Tab sonrası odak kök öğede kalıyor; Enter / Boşluk hiçbir şey yapmıyor. Kaynakta `Accessible` kullanımı yok. (İlk turda adları `property("Accessible.name")` ile saymaya çalıştım; QML ekli özellikleri bu yolla okunamaz, o sayı geçersizdi. Düzeltme turunda gerçek erişilebilirlik arayüzüyle `QAccessible` üzerinden ölçüldü.)
- **Neden:** düğmeler ve sekmeler yalnızca `MouseArea`; odak, klavye işleyicisi ve erişilebilirlik rolü yok.
- **Etki:** yalnızca fare kullanılabilir; ekran okuyucu ve klavye kullanıcıları için uygulama işlevsiz.
- **Öneri:** `CustomButton`, `IconButton` ve sekmelere `activeFocusOnTab`, `Keys.onReturnPressed/onSpacePressed`, odak göstergesi ve `Accessible.role/name` eklemek.

### QA-05 🟡 XP temasında bazı metinlerin kontrastı düşük

WCAG AA için normal metinde en az 4,5:1 beklenir. Ölçülen (hesaplanan) değerler:

| Çift | Kontrast |
|---|---|
| Yeşil düğme yazısı / gradyan üstü `#74D874` | **1,78:1** |
| Mavi (vurgu) düğme yazısı / `#5EA3FF` | **2,57:1** |
| Başlık yazısı / başlık ortası `#2F8BFF` | 3,36:1 |
| Yeşil düğme yazısı / gradyan altı `#2E9A2E` | 3,63:1 |
| Koyu tema: `danger` / yüzey | 3,89:1 |
| Koyu tema: `primary` / yüzey | 3,98:1 |
| Pasif düğme yazısı (açık / koyu) | 3,05 / 3,34:1 (pasif öğeler WCAG'de muaf) |

Geçenler: ana metin 15,6:1, ikincil 11,6:1, soluk metin 6,2:1, başarı / uyarı / vurgu renkleri 5,0 – 6,4:1, pasif sekme yazısı 4,7:1.

- **Öneri:** yeşil ve mavi düğme gradyanlarının üst uçlarını koyulaştırmak (yazı ortada olduğundan etkin kontrast iki ucun karışımıdır), koyu temada `danger` / `primary` tonlarını biraz açmak.

### QA-06 🟡 Bazı bulgu başlıkları Türkçe karaktersiz

5 eski analizörde kullanıcıya görünen metinler ASCII: **"Cift dosyalar"**, **"Buyuk dosya"**, **"Derin klasor yapisi"**, "Klasor yapisini basitlestirmeyi dusunun" (`duplicate_finder.py`, `size_analyzer.py`, `structure_analyzer.py`; analizör adları da: "Bos Klasor Bulucu", "Boyut Analizoru", "Yapi Analizoru", "Dosya Turu Analizoru").

- **Not:** `test_analyzers.py` bazı bu başlıkları sabitlediği için düzeltme testleri de günceller.

### QA-07 🟡 README'deki klonlama adresi gerçek depo değil

`git clone https://github.com/gitclean/archiver-pro.git`; gerçek depo `github.com/Yusufygc/Clean_Zipper`. Ayrıca README rozeti **Linux ve macOS** desteği belirtiyor; CI yalnızca Windows'ta koşuyor ve bağ (junction) denetimi Windows'a özgü, Linux / macOS **doğrulanmadı**.

### QA-08 🟡 Geliştirici profili `.env` dosyasını zip'e koyuyor ve uyarmıyor

Geliştirici (Standart) profili yalnızca `.gitignore`'a uyar; git'te izlenen `.env` zip'e giriyor. Bu bir tasarım kararı, ama paylaşılan bir arşivde sırrın uyarısız çıkması riskli. Müşteri Teslimi profili `.env` ve testleri doğru eliyor. **Öneri:** zip'e giren hassas dosya varsa (uygulamada zaten `secret_kind` var) sonuç ekranında uyarı göstermek.

### QA-09 🟡 Dashboard puanı kırpılıyor, yuvarlanmıyor

Servis 80,7 verirken dashboard `int()` ile **80** gösteriyor (arayüz ve denetim raporu arasında ±1 fark çıkabilir). Öneri: `round()`.

### QA-10 ℹ️ Ayarları uygulayınca sonuçlar kendiliğinden yenilenmiyor

Mesaj bunu açıkça söylüyor ("Sonuçları görmek için analizi yenileyin"). Kural kapatma ise otomatik yeniliyor; iki akış tutarsız. Düşük etkili bir sürtünme.

### QA-11 ℹ️ Temizlik önizlemesi "dosya" diyor ama klasör de sayıyor

"3 dosya tespit edildi" etiketi iki `__pycache__` klasörünü de sayıyor; küçük öğeler "0 KB" görünüyor.

### QA-12 ℹ️ Diğer gözlemler

- **EXE boyutu:** yaklaşık 49 MB (QA öncesi ilk derleme) → yaklaşık **59 MB** (PySide6 6.12 ve QML dosyalarıyla); büyüme nedeni ayrıştırılmadı.
- **Günlük gürültüsü:** görev klasörü yokken "Doğrula" gibi beklenen kullanıcı hataları `ERROR` + traceback olarak günlüğe yazılıyor (kullanıcıya gösterilen metin doğru ve anlaşılır).
- **Qt uyarıları:** ekransız modda 48 uyarı (`AppCheckBox` stil özelleştirmesi, `OpenThemeData`) görüldü; **gerçek Windows platformunda 0 uyarı**, simgeler ve onay kutuları doğru çiziliyor, yani ekransız ortamın yan etkisi. `CustomButton` / `IconButton` içindeki `enabled` özelliğinin temel sınıfı ezmesi uyarısı yalnızca ekransız modda görüldü, gerçekte **doğrulanmadı**.

---

## 4. Başarısız kontrollerin ayrıştırılması

Uçtan uca turda 15 kontrol "kaldı" çıktı. Ayrıştırma sonucu:

| Kontrol | Sonuç |
|---|---|
| `missing-license` yakalanmadı | **Beklenen davranış.** Politika: LICENSE yalnızca ≥ 100 kaynak satırı olan projelerde beklenir; örnek proje küçük. Harness varsayımı yanlıştı. |
| "password" araması 0 sonuç | **Harness hatası.** Arayüz Türkçe ("Şifre"); gerçek hata QA-03. |
| "+" düğmesi tıklaması | **Harness hatası.** İlk eşleşen düğme pencere dışındaydı (y=1417). Pencere içindeki "+" tıklandı, eşik değişti. |
| "Ayarları Kaydet ve Uygula" yazmadı | Yukarıdakinin devamı. |
| `.gitignore` kapatılınca sayı değişmedi | **Harness hatası.** Uygulama, mesajda söylediği gibi kendiliğinden yenilemiyor (QA-10); elle yenilemede 3 → 5 dosya, davranış doğru. |
| Temizlik sonrası panel güncel değil | **Gerçek hata, QA-02.** |
| 8 kontrast ölçümü | **Gerçek, QA-05.** |
| Qt uyarı sayısı | Ekransız ortam artefaktı; gerçek platformda 0 (QA-12). |

Yani 15 "kaldı"nın **9'u gerçek bulgu** (QA-02, QA-05), **6'sı harness hatası veya beklenen davranış**.

---

## 5. Geçen kontroller (kısa döküm)

| Alan | Geçti / kaldı / gözlem | Öne çıkanlar |
|---|---|---|
| Açılış | 5 / 0 / 0 | Başlık, 5 sekme; proje yokken yedek, temizlik, tarama **çökmüyor** |
| Proje açma | 8 / 1 / 2 | Türkçe + boşluklu yol `file:///` ile açılır; olmayan yol ve dosya yolu reddedilir; dosya sayısı bağımsız indeksle **birebir eşleşir**; **junction hedefi (proje dışı) taranmadı**; commit edilmiş `.env` KRİTİK olarak bulundu |
| Gösterge paneli | 6 / 0 / 0 | 11 kategori, en çok 5 öneri, yeniden analiz kararlı |
| Sorunlar | 10 / 1 / 2 | Şiddet süzgeçleri toplamla uyumlu; **sır değeri arayüze sızmıyor**; "Bu Kuralı Kapat" kapatır, diske yazar, skoru günceller, yeniden açınca bulgular geri gelir |
| Ayarlar | 4 / 3 / 0 | Eşik alt sınırı korunur, sıfırlama çalışır, ayarlar yeniden açılışta korunur (3 "kaldı" harness kaynaklı) |
| Arşiv | 20 / 0 / 2 | 3 profil: zip sağlam; `venv`, `node_modules`, ignore'lu, **junction hedefi** ve önbellek **hiçbirinde yok**; zip kendini içermez; Türkçe adlı dosya korunur; sayılar zip içeriğiyle uyumlu; hedef = kaynak reddedilir |
| Yedek | 5 / 0 / 0 | **7 yedekten sonra 5 kalır (rotasyon)**; elle adlandırılan silinmez; yedek `.env` ve ignore'lu dosyaları içerir, `venv` / junction içermez |
| Temizlik | 9 / 1 / 1 | `.tmp` ve `__pycache__` kaldırılır; log, bak, venv, ignore'lu veri **yerinde**; **junction hedefindeki proje dışı dosyalara dokunulmaz** |
| Eşzamanlılık | 2 / 0 / 1 | Arşiv sürerken temizlik reddedilir, kullanıcıya anlaşılır metin gösterilir, kilit sonra serbest kalır |
| Dışa aktarma | 7 / 0 / 1 | HTML ve denetim raporu yazılır; **raporlarda ve ajan görev dosyalarında sır değeri yok**; üretilen `verify.py` bağımsız çalışır |
| Arayüz | 10 / 0 / 0 | 5 sekme gerçek tıklamayla; açık ↔ koyu tema; 900×600, 1100×700, 1920×1080'de metin taşması yok |
| Uç durumlar | 4 / 0 / 2 | Boş proje, yalnızca ikili dosyalı proje, kökü junction olan proje açılır; **3000 dosya 5,7 sn** |

**Hedefli ikinci tur ek doğrulamaları:** arşiv hedefi yazılamaz bir sürücüyse (`Z:\`) işlem hata verip meşgul durumunu serbest bırakıyor; ajan doğrulaması görev klasörü yokken anlaşılır bir hata gösteriyor; gerçek kullanıcı günlüğünde sır yok.

**EXE:** başka bir çalışma dizininden (`C:\`) başlatıldı; 14 sn sonra açık, yanıt veriyor, 202 MB bellek, başlık `GitClean Archiver  v2.0.0`, sürüm bilgisi `GitClean Archiver / 2.0.0 / GitCleanArchiver.exe`, gömülü ikon yeni kalkan, işlem kapatılınca kalan yok. Pakette 25 QML dosyası, 19 arayüz simgesi, kurallar ve profiller var; eski arayüzden kalıntı yok.

---

## 6. Öneriler (öncelik sırasıyla)

1. **QA-02:** temizlik sonrası otomatik yeniden analiz (en görünür kullanıcı etkisi).
2. **QA-03:** Türkçe duyarlı arama (kolay ve Türkçe arayüz için önemli).
3. **QA-04:** klavye ve erişilebilirlik adı (daha büyük iş; önce düğmeler ve sekmeler).
4. **QA-05:** XP temasında yeşil ve mavi düğme gradyanlarını koyulaştırmak.
5. **QA-01'in düzeltmesini** commit'lemek.
6. QA-06 ve QA-07 (metin düzeltmeleri), QA-08 (arşivde hassas dosya uyarısı), QA-09 (`round`).

---

## 7. Kapsam dışı ve sınırlar

Bu denetimde **sınanamayanlar**; bunları kendi gözünle kontrol etmen gerekiyor:

- **Yerel klasör ve dosya seçme pencereleri** (`FolderDialog`, `FileDialog`) otomasyonla sürülemez; proje, zip ve kopya yolları, pencerenin döndürdüğü `file:///` URL'siyle ve ilgili slotla simüle edildi. "Gezgin'de aç" (`openPath`) denenmedi.
- **Ekran okuyucu** ile gerçek deneme ve **yüksek DPI ölçekleme** (%125 / %150) yapılmadı.
- **Linux / macOS** doğrulanmadı (README bu platformları belirtiyor).
- **Çok büyük depolar:** en büyük sınanan 5974 dosya (tüm `C:\2UYGULAMALAR`, 35 sn); 20 bin+ dosyada davranış ve analiz iptali (yok) sınanmadı.
- **Gerçek Geri Dönüşüm Kutusu:** temizlik testi gerçek `send2trash` ile yapıldı; kutudan geri yükleme denenmedi.
- Ekransız çizimde ve QA kurulumunda SVG simgeleri boş çıkar; simgeler **gerçek Windows platformunda** doğrulandı.
- Dal henüz `main`'e alınmadı ve GitHub'a gönderilmedi; XP temasının CI sonucu görülmedi.

---

## 8. Ekler

| Dosya | İçerik |
|---|---|
| `docs/qa/ekran_dashboard.png` | Gösterge paneli (gerçek platform, açık tema, düzeltilmiş çubuk) |
| `docs/qa/ekran_findings.png` | Sorunlar ve bulgular |
| `docs/qa/ekran_archive.png` | Arşivleme ve dağıtım |
| `docs/qa/ekran_cleanup.png` | Proje temizliği |
| `docs/qa/ekran_settings.png` | Ayarlar ve eşikler |
| `docs/qa/ekran_koyu_sorunlar.png` | Koyu tema, sorunlar (ekransız çizim, simgeler boş) |

QA betikleri depoya eklenmedi (oturum geçici klasöründe); istenirse `tools/qa/` altına alınıp tekrar koşulabilir hâle getirilebilir.

---

## 9. Düzeltme turu (aynı gün)

Tüm bulgular düzeltildi. Her düzeltme için yeni bir gerileme testi yazıldı (`tests/unit/test_qa_fixes.py`, 25 test); yeni testler düzeltmeler olmadan kırmızı, düzeltmelerle yeşil. Uçtan uca QA betiği yeniden koşuldu.

| # | Bulgu | Düzeltme | Doğrulama |
|---|---|---|---|
| QA-01 | Kaydırma çubuğu görünmüyordu | Çubuk `ScrollView` içinde sağ kenara oturur | `test_scroll_views_place_their_themed_scrollbar_on_the_right_edge`; gerçek platformda çizim |
| QA-02 | Temizlikten sonra panel bayat | Temizlik ve proje içine yazılan zip / kopya sonrası otomatik yeniden analiz (`projectModified` sinyali) | 3 test; uçtan uca: panel temizlik sonrası kendiliğinden güncel |
| QA-03 | Türkçe büyük harfle arama | `fold_turkish`: `İ→i`, `I→ı`, aksan duyarsız (`ŞİFRE`, `AÇIK`, `sifre` hepsi bulur) | 11 test |
| QA-04 | Klavye ve erişilebilirlik yok | Düğmeler, sekmeler, süzgeç segmentleri, mod düğmeleri, profil kartları ve onay kutuları: Tab odağı, Enter / Boşluk, odak halkası, `Accessible` rol ve ad | Test: odaklanabilen her öğenin erişilebilirlik adı dolu; Tab + Enter / Boşluk sekme açar. Gerçek ağaçta ayrıca **onay kutularının adı boştu**, onlar da adlandırıldı |
| QA-05 | Düşük kontrast | Yeşil, mavi, kırmızı düğme gradyanları ve pasif sekme koyulaştırıldı; başlık ortası, koyu tema `primary` / `danger` ayarlandı; üzerine gelince dolgu açılmaz (turuncu çerçeve) | 2 test: beyaz yazı her gradyan ucunda, durum renkleri iki temada ≥ 4,5:1; uçtan uca: 8 kontrast kaydının hepsi geçti |
| QA-06 | Türkçe karaktersiz metinler | 5 analizör adı ve başlığı düzeltildi | Test + 2 mevcut test güncellendi |
| QA-07 | README adresi, platform iddiası | Klonlama adresi `Yusufygc/Clean_Zipper`, rozet ve kurulum bölümü Windows (Linux / macOS "doğrulanmadı"), Python 3.10+ | Belge denetimi |
| QA-08 | `.env` uyarısız zip'e giriyor | Zip ve kopya sonucu `sensitive_files` döner; sonuç kartında uyarı ve dosya listesi | 2 test |
| QA-09 | Puan kırpılıyor | `round()` | Test (80,7 → 81) |
| QA-10 | Ayar uygulayınca yenileme yok | Ayarları uygula ve varsayılana dön analizi yeniler | Test |
| QA-11 | Önizleme etiketi | "öğe tespit edildi"; küçük boyutlar "< 1 KB" | Çizim |
| QA-12 | Günlük gürültüsü, Qt uyarıları, EXE boyutu | Beklenen "görev dosyası yok" hatası uyarı olarak, traceback'siz yazılır; `enabled` özelliği yeniden tanımlanmaz; **Basic stili açıkça seçilir** (ekransız moddaki onay kutusu uyarıları biter); EXE boyutu ayrıştırıldı | 2 test; gerçek platformda 0 uyarı |

**EXE boyutu (QA-12) ayrıştırması:** sıkıştırılmış 61,4 MB; en büyük kalemler `opengl32sw.dll` 7,7 MB (GPU'suz makineler için yazılım çizici, gerekli), kullanılmayan Qt Controls stilleri ~6 MB, Qt çevirileri 2,5 MB, `Qt6Gui` 4,3 MB, `Qt6Core` 3,7 MB. Büyümenin nedeni PySide6 6.12'nin DLL'leri. **Bu turda boyut küçültülmedi;** stil ve çeviri dosyalarını dışlamak ayrı bir derleme ayarı işi ve riskli (açılış doğrulaması gerekir). Basic stilini açıkça seçmek bunun önkoşulu.

**Yeniden koşulan uçtan uca QA:** 137 kontrol, **122 geçti, 4 kaldı** (ilk turda 135 / 109 / 15). Kalan 4 kayıt uygulama hatası değil (Bölüm 4): LICENSE politikası (küçük örnek proje), Türkçe arayüze İngilizce "password" araması, `.gitignore` kontrolünün asenkron yenilemeyi beklemeyen betik yarışı (davranış birim testiyle doğrulandı) ve ekransız ortamın Qt uyarısı (gerçek platformda 0).

**Hâlâ sınanmayanlar (Bölüm 7) değişmedi.** Düzeltmeler gerçek EXE'de ayrıca denenmedi; EXE yeniden derlenmedi.
