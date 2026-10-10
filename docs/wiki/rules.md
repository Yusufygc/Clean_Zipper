# Çalışma Kuralları (Anayasa)

Bu dosya projedeki AI destekli çalışma düzenini tanımlar. Kaynak metodoloji: `C:\2UYGULAMALAR\D002-HazirPromptlar\AI-Gelistirme-Metodolojisi.md`; denetim raporu şablonu: `V2-GenelSablon.md`. Sayfa haritası için [[index]].

## Wiki akışı
- Kod yazmadan veya mimari karar vermeden önce [[index]] okunur, gerekirse `[[link]]`ler takip edilir.
- Kod değişikliği ve wiki güncellemesi aynı turda yapılır. Yeni karar, kütüphane veya yapılandırma ilgili sayfaya, [[index]]'e ve [[log]]'a işlenir.
- Her sayfa en az bir sayfaya bağlanır ve [[index]]'te listelenir. Öksüz sayfa ve kırık link bırakılmaz (`tests/unit/test_wiki.py` bunu otomatik denetler).
- Dokümantasyonda link sözdizimi örnek olarak gösterilecekse inline code kullanılır.
- Hangi bilgi nerede: karar ve gerekçe [[decisions]]; analizör, kural ve eşik [[analyzers]]; arayüzün kullanacağı yüzey [[backend-api]]; test ve doğrulama yöntemi [[testing]]; bulgu durumu [[roadmap]]; katman ve veri akışı [[architecture]].
- Yeni analizör, kural, eşik, sonuç alanı ya da karar eklenince ilgili referans sayfası (yukarıdaki liste) ve `README.md` aynı turda güncellenir.

## Operasyon komutları
- **"Bunu ingest et":** kaynağı analiz et, yeni sayfa aç, ilgili sayfaları güncelle, [[index]] ve [[log]] güncelle.
- **Detaylı proje sorusu:** önce [[index]] üzerinden ilgili sayfaları oku.
- **"Wiki'yi lint et":** çelişki, eskimiş karar, öksüz sayfa ve kırık linkleri raporla, onay sonrası düzelt. Link ve öksüz denetimi için `./venv/Scripts/python.exe -m pytest tests/unit/test_wiki.py`; sayılar (analizör, test, kural) koddan doğrulanır.

## Çalışma düzeni
- Bulgular önce raporlanır, onaydan sonra sırayla ve her biri ayrı adım olarak uygulanır.
- Büyük işlerde plan modu kullanılır. Plan onaylanmadan uygulamaya geçilmez. Çok aşamalı işte her aşama sonunda durulur, kullanıcı "commit at, devam" deyince commit atılır ve sonraki aşamaya geçilir.
- Her değişiklikten sonra `python -m py_compile` ve `pytest` çalıştırılır. Mantık değişikliğinde davranış ayrıca doğrulanır ([[testing]]).
- QML yerleşimi ekransız çizimle kodla sınanır (`test_qml_layout`); görsel his, gerçek fare / klavye etkileşimi ve gerçek pencere otomatik doğrulanamaz. Bu kısımlar "elle kontrol gerekir" diye açıkça belirtilir.
- Silinen kodun bıraktığı kalıntı referanslar (README, wiki) aynı turda temizlenir.
- Kapsam dışı bırakılan kararlar planda gerekçesiyle yazılır ([[decisions]]).

## Doğrulama kuralları
- **Bağımsız doğrulama zorunlu:** yeni analiz mantığı yalnızca birim testiyle kapanmaz; gerçek veri üzerinde başka bir araçla ya da başka bir kod yoluyla karşılaştırılır (`radon`, `pyflakes`, `grimp`, `ruff`, `grep`/`git` sayımı ...). Araçlar geçici sanal ortamda kurulur; projenin `venv`'i ve `requirements.txt` dosyası değişmez.
- **Refactor davranışı değiştirmez:** refactor öncesi ve sonrası, gerçek projelerde tam teşhis çıktısı birebir karşılaştırılır (`git worktree` oracle'ı, [[testing]]).
- **Dogfooding:** yeni kod aracın kendi taramasından bulgusuz geçmelidir; geçmiyorsa fonksiyonlar bölünür. Bilinçli istisnalar [[decisions]] içinde yazılıdır.
- **Performans bütçesi:** tüm `C:\2UYGULAMALAR` taraması < 60 sn.
- **Dürüst raporlama:** doğrulanamayan şey "doğrulanmadı" diye, başarısız test çıktısıyla birlikte söylenir; atlanan adım atlandığı belirtilir; bulunan yanlış pozitif ve hata gizlenmez.
- **Sırlar:** bulguya, rapora ya da loga sır değeri yazılmaz ([[decisions]]).

## Kod kuralları
- Yeni analizör: tek dosya, `@register_analyzer`, kural kimliği, `approximate` işareti; adım adım liste [[analyzers]] sonunda.
- Yeni kural eklenince ajan görevi eşlemesi (`agent_guidance.py`) ve `audit_catalog.py` etiketleri güncellenir ([[analyzers]]).
- Sessiz hata yutma yok: geniş `except` loglar ve yeniden fırlatır ya da sonucu `failed_*` alanına yazar (AST testiyle zorunlu).
- Kaynak dosyalar UTF-8, BOM'suz, LF satır sonlu (`.gitattributes`, `.editorconfig`; BOM testle zorunlu).
- Bağımlılık: çalışma zamanı `requirements.txt`, test `requirements-dev.txt`, derleme `requirements-build.txt`; hepsi tam sabit sürüm.
- Bash heredoc kaçış dizilerini bozar: kod yazarken `Write`/`Edit` ya da betik dosyası kullanılır ([[testing]] "Araç tuzakları").

## Commit kuralları
- Mesajlar Türkçe, Türkçe karakterler korunur (ı, ğ, ü, ş, ö, ç).
- Biçim: `tip(kapsam): kısa emir kipinde özet`, gerekirse madde madde gövde. Örnek: `fix(core): ...`. Tipler: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`.
- Commit ve PR metninde AI/asistan referansı (Co-Authored-By, "Generated with") olmaz.
- Commit öncesi `git status` gözden geçirilir. `venv/`, `build/`, `dist/` dışarıda kalır.
- Commit yalnızca kullanıcı isteyince atılır; "commit at" denmeden commit atılmaz, aşama bitince rapor verilip beklenir.
- Her commit tek bir aşamayı ya da konuyu kapsar; kod, test ve wiki aynı commit'tedir.
