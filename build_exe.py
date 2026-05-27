import sys, os
from pathlib import Path

APP_NAME = "GitCleanArchiverPro"

def main():
    print(f"🔨 {APP_NAME} build ediliyor...")
    try:
        import PyInstaller.__main__
        args = [
            'main.py', f'--name={APP_NAME}', '--onefile', '--windowed',
            '--clean', '--noconfirm', '--add-data=src;src',
            '--hidden-import=customtkinter', '--hidden-import=pathspec',
            '--collect-all=customtkinter', '--collect-all=pathspec'
        ]
        PyInstaller.__main__.run(args)
        print(f"✅ Build tamamlandi: dist/{APP_NAME}.exe")
    except Exception as e:
        print(f"❌ Hata: {e}")

if __name__ == "__main__":
    main()
