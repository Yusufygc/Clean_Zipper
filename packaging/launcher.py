"""GitClean Archiver başlatıcısı (PyInstaller giriş betiği). BU DOSYAYI DEĞİŞTİRME.

Bu betik exe'nin içine gömülür; içeriği değişirse exe'nin SHA-256 özeti değişir ve Windows Akıllı Uygulama Denetimi yeni exe'yi yeniden
değerlendirir (engelleyebilir). Uygulama kodu exe'nin dışında (`_internal` altında `.pyc` dosyaları) durur; sürümler arasında yalnızca onlar değişir.
Gerçek giriş mantığı `src/qml_ui/app.py` içindedir. Ayrıntı: docs/wiki/windows-exe-dagitim.md
"""
from src.qml_ui.app import run

run()
