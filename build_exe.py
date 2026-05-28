import os
import sys
import shutil
import subprocess
from pathlib import Path

def build_executable():
    print("=" * 60)
    print("      GitClean Archiver Pro - EXE Derleme Sihirbazı      ")
    print("=" * 60)

    # 1. Gerekli kütüphane kontrolü (PyInstaller)
    try:
        import PyInstaller
        print("[✓] PyInstaller kütüphanesi hazır.")
    except ImportError:
        print("[!] PyInstaller sistemde bulunamadı. Kurulum başlatılıyor...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("[✓] PyInstaller başarıyla kuruldu.")
        except Exception as e:
            print(f"[X] PyInstaller kurulamadı! Hata: {e}")
            sys.exit(1)

    # Proje kök dizini
    root_dir = Path(__file__).parent.resolve()
    entry_point = root_dir / "main.py"
    
    if not entry_point.exists():
        print(f"[X] Giriş noktası ({entry_point}) bulunamadı!")
        sys.exit(1)

    # 2. Eski derleme kalıntılarının (build/dist) temizlenmesi
    build_dir = root_dir / "build"
    dist_dir = root_dir / "dist"
    spec_file = root_dir / "GitCleanArchiverPro.spec"

    print("\n[*] Eski derleme klasörleri temizleniyor...")
    for path in [build_dir, dist_dir]:
        if path.exists():
            try:
                shutil.rmtree(path)
                print(f"  - {path.name} klasörü silindi.")
            except Exception as e:
                print(f"  - {path.name} temizlenirken uyarı: {e}")
    if spec_file.exists():
        try:
            spec_file.unlink()
            print("  - Eski .spec dosyası temizlendi.")
        except Exception as e:
            print(f"  - .spec dosyası temizlenirken uyarı: {e}")

    # 3. Veri dosyalarının ve parametrelerin yapılandırılması
    # style.qss dosyasının EXE içinde 'src/ui/themes/style.qss' konumunda kalması sağlanmalıdır.
    # Windows için ';' kullanılırken, macOS/Linux için ':' ayırıcı karakteri (pathsep) kullanılır.
    sep = os.pathsep
    style_qss_source = root_dir / "src" / "ui" / "themes" / "style.qss"
    style_qss_dest = "src/ui/themes"

    add_data_args = []
    if style_qss_source.exists():
        add_data_args = ["--add-data", f"{style_qss_source}{sep}{style_qss_dest}"]
        print(f"[✓] Veri dosyası paketlemeye eklendi: {style_qss_source.name}")
    else:
        print("[!] UYARI: src/ui/themes/style.qss dosyası bulunamadı! Arayüz stilleri eksik olabilir.")

    # 4. İkon Yapılandırması (Kullanıcı isteğine göre assets/icons/app_icon.ico)
    icon_path = root_dir / "assets" / "icons" / "app_icon.ico"
    icon_args = []
    if icon_path.exists():
        icon_args = ["--icon", str(icon_path)]
        print(f"[✓] Uygulama ikonu eklendi: {icon_path}")
    else:
        # İkon klasörünün olmaması durumuna karşı simüle etme veya uyarı verme
        print(f"[!] Bilgi: '{icon_path}' bulunamadı. Varsayılan sistem ikonuyla derleniyor.")
        print("    (assets/icons/ klasörünü oluşturup içine app_icon.ico koyarak bu ikonu kullanabilirsiniz)")

    # 5. Derleme Parametreleri (PyInstaller args)
    pyinstaller_args = [
        str(entry_point),
        "--name=GitCleanArchiverPro",
        "--onedir",            # Bağımsız tek klasör (Hata ayıklama ve performans için önerilir)
        "--windowed",          # Konsol penceresini gizle (GUI uygulamaları için zorunlu)
        "--clean",             # Önbelleği temizleyerek sıfırdan derle
        "--noconfirm"          # Onay sorularını otomatik geç
    ]

    # Ek argümanları (ikon ve veri dosyaları) ekleyelim
    pyinstaller_args.extend(add_data_args)
    pyinstaller_args.extend(icon_args)

    # 6. Derleme Sürecinin Başlatılması
    print("\n[*] Derleme işlemi başlatılıyor, bu işlem biraz zaman alabilir...")
    print(f"    Çalıştırılan komut: pyinstaller {' '.join(pyinstaller_args[1:])}\n")

    try:
        import PyInstaller.__main__
        PyInstaller.__main__.run(pyinstaller_args)
        print("\n" + "=" * 60)
        print("[✓] DERLEME BAŞARIYLA TAMAMLANDI!")
        print(f"[*] Çıktı Klasörü: {dist_dir / 'GitCleanArchiverPro'}")
        print(f"[*] Çalıştırılabilir Dosya: {dist_dir / 'GitCleanArchiverPro' / 'GitCleanArchiverPro.exe'}")
        print("=" * 60)
    except Exception as e:
        print(f"\n[X] Derleme sırasında hata oluştu: {e}")
        sys.exit(1)

if __name__ == "__main__":
    build_executable()