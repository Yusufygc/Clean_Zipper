# GitClean Archiver

PySide6 tabanlı proje analiz, temizlik ve arşivleme aracı. Python 3.10, `venv/` kökte.

## Her oturumda
1. `docs/wiki/index.md` oku. Projeyi sıfırdan keşfetme, `[[link]]`leri takip et.
2. Çalışma düzeni, doğrulama ve commit kuralları: `docs/wiki/rules.md`.
   Kararlar: `docs/wiki/decisions.md`; analizör kataloğu: `analyzers.md`; UI'nin kullanacağı backend yüzeyi: `backend-api.md`; test ve doğrulama yöntemi: `testing.md`.
3. Kod değişikliğiyle wiki güncellemesi aynı turda yapılır; `docs/wiki/log.md`'ye kayıt düşülür.

## Komutlar
```bash
./venv/Scripts/python.exe -m pytest          # testler (790+; requirements-dev.txt gerekir)
./venv/Scripts/python.exe -m ruff check .    # lint (CI'da da koşar)
./venv/Scripts/python.exe -m py_compile <dosya>
./venv/Scripts/python.exe main.py            # uygulama (QML arayüzü, src/qml_ui)
./venv/Scripts/python.exe build_installer.py # EXE (onedir, kararlı: özet packaging/launcher.sha256 ile aynı olmalı) + Inno sihirbazı, bu makinede dener; sürüm: src/version.py. Akıllı Uygulama Denetimi: docs/wiki/windows-exe-dagitim.md
./venv/Scripts/python.exe tools/release.py X.Y.Z  # sürüm yükselt + commit + etiket (push elle)
pip install -r requirements.txt              # yalnızca çalıştırmak için (dev: requirements-dev.txt, derleme: requirements-build.txt)
```

## Operasyonlar
"Bunu ingest et", "Wiki'yi lint et" ve detaylı proje soruları için `docs/wiki/rules.md`'ye bak. Wiki bütünlüğü `tests/unit/test_wiki.py` ile denetlenir.

## Önemli kurallar (özet)
- Commit yalnızca kullanıcı "commit at" deyince; Türkçe, `tip(kapsam): özet`, AI/Co-Authored-By referansı yok.
- Aşama sonunda rapor verip dur; bağımsız doğrulama yap ve doğrulanamayanı dürüstçe söyle.
- Kod yazarken bash heredoc kullanma (kaçış dizileri bozulur); `Write`/`Edit` ya da betik dosyası kullan.
- Arayüz yalnızca `src/qml_ui` (QML + ViewModel'ler); eski `src/ui` (QWidget) 2026-10-10'da kaldırıldı. ViewModel'ler alt servisleri değil `ProjectService` yöntemlerini çağırır.
