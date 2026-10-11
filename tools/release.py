"""Sürüm yayınlama yardımcısı: sürüm numarasını tüm kaynaklarda yükseltir, commit atar ve etiket (tag) oluşturur.

Kullanım:
    python tools/release.py 2.1.0              # sürümü yükselt, "chore(release): v2.1.0" commit'i at, v2.1.0 etiketini oluştur
    python tools/release.py 2.1.0 --dry-run    # yalnızca ne yapılacağını göster
    python tools/release.py --check-tag v2.1.0 # etiket, src/version.py ile aynı mı (CI'da kullanılır)

Hiçbir şey GitHub'a gönderilmez. Sonra elle: `git push origin main` ve `git push origin v2.1.0`; etiket itilince
`.github/workflows/release.yml` testleri koşar, kurulum dosyasını derler ve GitHub Release olarak yayınlar.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"(\d+)\.(\d+)\.(\d+)")


def read_version(root: Path = ROOT) -> str:
    match = re.search(r'__version__ = "([^"]+)"', (root / "src" / "version.py").read_text(encoding="utf-8"))
    if not match:
        raise SystemExit("src/version.py içinde __version__ bulunamadı.")
    return match.group(1)


def as_tuple(version: str):
    match = SEMVER.fullmatch(version)
    if not match:
        raise SystemExit(f"Geçersiz sürüm: {version!r} (beklenen biçim: X.Y.Z)")
    return tuple(int(part) for part in match.groups())


def _sub(path: Path, pattern: str, replacement: str, count_expected: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    new_text, count = re.subn(pattern, replacement, text)
    if count != count_expected:
        raise SystemExit(f"{path.name}: {pattern!r} için {count_expected} eşleşme beklendi, {count} bulundu.")
    path.write_bytes(new_text.encode("utf-8"))                      # satır sonlarını (LF) olduğu gibi korur


def bump_files(root: Path, version: str) -> None:
    """Sürümü tek kaynakta (`src/version.py`) ve ondan türeyen dosyalarda (Windows sürüm bilgisi, README rozeti) yazar."""
    major, minor, patch = as_tuple(version)
    _sub(root / "src" / "version.py", r'__version__ = "[^"]+"', f'__version__ = "{version}"')
    info = root / "version_info.txt"
    _sub(info, r"filevers=\(\d+, \d+, \d+, \d+\)", f"filevers=({major}, {minor}, {patch}, 0)")
    _sub(info, r"prodvers=\(\d+, \d+, \d+, \d+\)", f"prodvers=({major}, {minor}, {patch}, 0)")
    _sub(info, r"u'FileVersion', u'[^']+'", f"u'FileVersion', u'{version}'")
    _sub(info, r"u'ProductVersion', u'[^']+'", f"u'ProductVersion', u'{version}'")
    _sub(root / "README.md", r"badge/Version-[0-9.]+-orange", f"badge/Version-{version}-orange")


def git(*args: str) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} başarısız:\n{result.stderr.strip()}")
    return result.stdout.strip()


def check_tag(tag: str) -> int:
    expected = "v" + read_version()
    if tag != expected:
        print(f"Etiket {tag!r}, src/version.py sürümüyle ({expected!r}) uyuşmuyor.")
        return 1
    print(f"Etiket {tag} sürümle uyumlu.")
    return 0


def release(version: str, dry_run: bool) -> int:
    current = read_version()
    if as_tuple(version) <= as_tuple(current):
        raise SystemExit(f"Yeni sürüm ({version}) mevcut sürümden ({current}) büyük olmalı.")
    tag = f"v{version}"
    if git("tag", "--list", tag):
        raise SystemExit(f"{tag} etiketi zaten var.")
    if git("status", "--porcelain"):
        raise SystemExit("Çalışma ağacı temiz değil; önce değişiklikleri commit'leyin.")
    branch = git("branch", "--show-current")
    if branch != "main":
        raise SystemExit(f"Yayın yalnızca main dalından yapılır (şu an: {branch}).")
    print(f"{current} -> {version}  (etiket: {tag})")
    if dry_run:
        print("Deneme çalıştırması: hiçbir dosya değişmedi.")
        return 0
    bump_files(ROOT, version)
    git("add", "src/version.py", "version_info.txt", "README.md")
    git("commit", "-m", f"chore(release): v{version}")
    git("tag", "-a", tag, "-m", f"GitClean Archiver {version}")
    print(f"Hazır. GitHub'a göndermek için:\n  git push origin main\n  git push origin {tag}")
    return 0


def main(argv) -> int:
    if len(argv) == 2 and argv[0] == "--check-tag":
        return check_tag(argv[1])
    versions = [a for a in argv if not a.startswith("--")]
    if len(versions) != 1:
        print(__doc__)
        return 2
    return release(versions[0].lstrip("v"), dry_run="--dry-run" in argv)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
