# Çalışma Kuralları (Anayasa)

Bu dosya projedeki AI destekli çalışma düzenini tanımlar. Kaynak metodoloji: `C:\2UYGULAMALAR\D002-HazirPromptlar\AI-Gelistirme-Metodolojisi.md`.

## Wiki akışı
- Kod yazmadan veya mimari karar vermeden önce [[index]] okunur, gerekirse `[[link]]`ler takip edilir.
- Kod değişikliği ve wiki güncellemesi aynı turda yapılır. Yeni karar, kütüphane veya yapılandırma ilgili sayfaya, [[index]]'e ve [[log]]'a işlenir.
- Her sayfa en az bir sayfaya bağlanır. Öksüz sayfa ve kırık link bırakılmaz.
- Dokümantasyonda link sözdizimi örnek olarak gösterilecekse inline code kullanılır.

## Operasyon komutları
- **"Bunu ingest et":** kaynağı analiz et, yeni sayfa aç, ilgili sayfaları güncelle, [[index]] ve [[log]] güncelle.
- **Detaylı proje sorusu:** önce [[index]] üzerinden ilgili sayfaları oku.
- **"Wiki'yi lint et":** çelişki, eskimiş karar, öksüz sayfa ve kırık linkleri raporla, onay sonrası düzelt.

## Çalışma düzeni
- Bulgular önce raporlanır, onaydan sonra sırayla ve her biri ayrı adım olarak uygulanır.
- Büyük işlerde plan modu kullanılır. Plan onaylanmadan uygulamaya geçilmez.
- Her değişiklikten sonra `python -m py_compile` ve `pytest` çalıştırılır. Mantık değişikliğinde davranış ayrıca doğrulanır.
- GUI ve görsel davranış otomatik doğrulanamaz. Bu kısımlar "elle kontrol gerekir" diye açıkça belirtilir.
- Silinen kodun bıraktığı kalıntı referanslar (README, wiki) aynı turda temizlenir.
- Kapsam dışı bırakılan kararlar planda gerekçesiyle yazılır.

## Commit kuralları
- Mesajlar Türkçe, Türkçe karakterler korunur (ı, ğ, ü, ş, ö, ç).
- Biçim: `tip(kapsam): kısa emir kipinde özet`, gerekirse madde madde gövde. Örnek: `fix(core): ...`.
- Commit ve PR metninde AI/asistan referansı (Co-Authored-By, "Generated with") olmaz.
- Commit öncesi `git status` gözden geçirilir. `venv/`, `build/`, `dist/` dışarıda kalır.
- Commit yalnızca kullanıcı isteyince atılır.
