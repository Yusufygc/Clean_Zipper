# Üçüncü taraf bileşenler ve lisansları

GitClean Archiver, [MIT lisansı](LICENSE) altındadır. Dağıtılan uygulama (PyInstaller paketi) aşağıdaki bileşenleri içerir.
Bu dosya `python tools/third_party_notices.py` ile üretilir.

## Qt (PySide6 / shiboken6): LGPL-3.0

Arayüz Qt 6 ile (Qt for Python, PySide6-Essentials) çizilir; Qt, **GNU LGPL sürüm 3** koşulları altında kullanılır
([metin](https://www.gnu.org/licenses/lgpl-3.0.html)). Uygulama klasör olarak dağıtılır (`--onedir`): Qt kütüphaneleri `_internal` klasöründe
ayrı dosyalardır ve değiştirilmiş bir Qt sürümüyle değiştirilebilir (yeniden bağlama hakkı). Qt ve PySide6 kaynak kodu:
<https://code.qt.io> ve <https://pyside.org>. Qt'nin ticari lisansı kullanılmaz.

## Python ve PyInstaller

- **Python** ([PSF License](https://docs.python.org/3/license.html)): paketlenmiş yorumlayıcı ve standart kitaplık.
- **PyInstaller** ([GPL-2.0-or-later, derlenen uygulamanın dağıtımına izin veren özel istisnayla](https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt)):
  yalnızca paketleme aracı ve açılış yükleyicisi.

## Python paketleri

### PySide6-Essentials 6.12.0

- Lisans: LGPL-3.0-only (Qt for Python)
- Kaynak: <https://pyside.org>

### shiboken6 6.12.0

- Lisans: LGPL-3.0-only (Qt for Python)
- Kaynak: <https://pyside.org>

### pathspec 1.1.1

- Lisans: MPL-2.0
- Kaynak: <https://github.com/cpburnz/python-pathspec>

Bu bileşen değiştirilmeden kullanılır; kaynak kodu yukarıdaki adresten ve PyPI'dan alınabilir ([MPL-2.0 metni](https://www.mozilla.org/en-US/MPL/2.0/)).

### Send2Trash 2.1.0

- Lisans: BSD-3-Clause
- Kaynak: <https://github.com/arsenetar/send2trash>

```text
Copyright (c) 2017, Virgil Dupras
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    * Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
    * Neither the name of Hardcoded Software Inc. nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
```

### tomli 2.5.0

- Lisans: MIT
- Kaynak: <https://github.com/hukkin/tomli>

```text
MIT License

Copyright (c) 2021 Taneli Hukkinen

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
