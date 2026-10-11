"""Güncelleme denetimi: GitHub'ın son sürüm kaydını okuyup kurulu sürümle karşılaştırır.

Güvenlik ve gizlilik:
- Tek istek: `GET https://api.github.com/repos/<depo>/releases/latest`. Kimlik bilgisi, proje verisi ya da kullanıcı kimliği
  gönderilmez (yalnızca `User-Agent: GitCleanArchiver/<sürüm>`). Kapatma: ayarlardan ya da `GITCLEAN_NO_UPDATE_CHECK=1`.
- Yanıt boyutu ve süre sınırlıdır; yanıttaki adresler yalnızca `https://github.com/<depo>/...` ise kabul edilir (sahte adres
  içeren yanıt reddedilir). Sürüm notu düz metin olarak gösterilir.
- Kurulum dosyası yalnızca kullanıcı "Güncelle" derse indirilir: adres yalnızca bu deponun `releases/download/` yoludur, boyut ve SHA-256
  özeti doğrulanır (GitHub'ın verdiği `digest` ya da Release'teki `.sha256` dosyası; ikisi de yoksa güncelleme reddedilir), uyuşmazsa dosya silinir.
  Sonra kurulum dosyası sabit argümanlarla (kabuk yok) başlatılır; uygulama kapanır, kurulum üstüne yazar ve uygulama yeniden açılır.
"""
import hashlib
import json
import logging
import os
import re
import subprocess
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Tuple
from urllib.parse import urlparse

from src.version import RELEASE_REPO, __version__

logger = logging.getLogger(__name__)

API_URL = "https://api.github.com/repos/{repo}/releases/latest"
API_HOST = "api.github.com"
TIMEOUT_SECONDS = 8
MAX_RESPONSE_BYTES = 1_000_000
MAX_NOTES_CHARS = 4000
INSTALLER_PATTERN = re.compile(r"^GitCleanArchiver-Setup-[0-9.]+\.exe$")
MAX_INSTALLER_BYTES = 400 * 1024 * 1024
DOWNLOAD_CHUNK_BYTES = 64 * 1024
DOWNLOAD_TIMEOUT_SECONDS = 30
UPDATE_DIR_NAME = "GitCleanArchiverUpdate"
_VERSION = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")
OPT_OUT_ENV = "GITCLEAN_NO_UPDATE_CHECK"


class UpdateCheckError(Exception):
    """Denetim yapılamadı (ağ yok, GitHub hatası, bozuk yanıt); mesaj kullanıcıya gösterilebilir."""


@dataclass(frozen=True)
class UpdateInfo:
    version: str            # "2.1.0"
    tag: str                # "v2.1.0"
    page_url: str           # sürüm sayfası
    download_url: str       # kurulum dosyası; yoksa boş (sayfa açılır)
    asset_name: str
    size: int
    notes: str
    published: str          # "2026-10-11"
    sha256: str = ""        # GitHub'ın verdiği özet ("sha256:..." önekiz); yoksa checksum_url'deki dosyadan okunur
    checksum_url: str = ""  # Release'teki `<kurulum>.sha256` dosyası


def parse_version(text: str) -> Optional[Tuple[int, int, int]]:
    """`v2.1.0` / `2.1.0` -> (2, 1, 0). Ön sürüm (`2.1.0-rc1`) ve biçimsiz metin None döner."""
    match = _VERSION.fullmatch((text or "").strip())
    return tuple(int(part) for part in match.groups()) if match else None


def is_newer(candidate: str, current: str = __version__) -> bool:
    new, old = parse_version(candidate), parse_version(current)
    return new is not None and old is not None and new > old


def updates_disabled_by_environment() -> bool:
    return os.environ.get(OPT_OUT_ENV, "").strip().lower() in ("1", "true", "yes")


def _trusted_url(url: object, repo: str) -> str:
    """Yalnızca bu depoya ait https://github.com adresi; aksi hâlde boş."""
    if not isinstance(url, str):
        return ""
    parsed = urlparse(url)
    if parsed.scheme == "https" and parsed.hostname == "github.com" and parsed.path.startswith(f"/{repo}/"):
        return url
    return ""


_HEADING = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)
_BULLET = re.compile(r"^(\s*)[*+]\s+", re.MULTILINE)


def plain_notes(markdown: str) -> str:
    """GitHub'ın Markdown sürüm notunu düz metne indirger (`## Başlık` -> `Başlık`, `**kalın**` -> `kalın`, `* madde` -> `- madde`)."""
    text = _BULLET.sub(r"\1- ", _HEADING.sub("", markdown.replace("\r\n", "\n")))
    return text.replace("**", "").replace("__", "").strip()


def _installer_asset(data: dict, repo: str) -> Tuple[str, str, int, str, str]:
    """(ad, indirme adresi, boyut, SHA-256, `.sha256` dosyası adresi); kurulum dosyası yoksa boş değerler."""
    assets = [a for a in data.get("assets") or [] if isinstance(a, dict)]
    for asset in assets:
        name = asset.get("name")
        url = _trusted_url(asset.get("browser_download_url"), repo)
        if isinstance(name, str) and INSTALLER_PATTERN.match(name) and url:
            size = asset.get("size")
            digest = asset.get("digest") if isinstance(asset.get("digest"), str) else ""
            sha256 = digest.removeprefix("sha256:").lower() if digest.startswith("sha256:") else ""
            checksum = next((_trusted_url(a.get("browser_download_url"), repo) for a in assets if a.get("name") == name + ".sha256"), "")
            return name, url, size if isinstance(size, int) and size > 0 else 0, sha256, checksum
    return "", "", 0, "", ""


def release_to_update(data: object, current: str = __version__, repo: str = RELEASE_REPO) -> Optional[UpdateInfo]:
    """GitHub sürüm kaydından `UpdateInfo`; taslak, ön sürüm, daha eski / aynı sürüm ya da güvenilmez adres için None."""
    if not isinstance(data, dict) or data.get("draft") or data.get("prerelease"):
        return None
    tag = data.get("tag_name")
    if not isinstance(tag, str) or not is_newer(tag, current):
        return None
    page_url = _trusted_url(data.get("html_url"), repo)
    if not page_url:
        raise UpdateCheckError("Sürüm kaydındaki adres güvenilir değil, yok sayıldı.")
    name, download_url, size, sha256, checksum_url = _installer_asset(data, repo)
    notes = data.get("body") if isinstance(data.get("body"), str) else ""
    published = data.get("published_at") if isinstance(data.get("published_at"), str) else ""
    return UpdateInfo(version=tag.lstrip("v"), tag=tag, page_url=page_url, download_url=download_url, asset_name=name,
                      size=size, notes=plain_notes(notes)[:MAX_NOTES_CHARS], published=published[:10], sha256=sha256, checksum_url=checksum_url)


def fetch_latest_release(repo: str = RELEASE_REPO, current: str = __version__) -> Optional[dict]:
    """En son yayınlanmış sürümün kaydı; hiç sürüm yoksa (404) None."""
    request = urllib.request.Request(API_URL.format(repo=repo), headers={
        "Accept": "application/vnd.github+json", "User-Agent": f"GitCleanArchiver/{current}"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            if urlparse(response.geturl()).hostname != API_HOST:
                raise UpdateCheckError("Beklenmeyen bir adrese yönlendirildi.")
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        if e.code in (403, 429):
            raise UpdateCheckError("GitHub istek sınırına ulaşıldı; biraz sonra yeniden deneyin.") from e
        raise UpdateCheckError(f"GitHub yanıt hatası ({e.code}).") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise UpdateCheckError("GitHub'a ulaşılamadı. İnternet bağlantınızı denetleyin.") from e
    if len(body) > MAX_RESPONSE_BYTES:
        raise UpdateCheckError("Yanıt beklenenden büyük, yok sayıldı.")
    try:
        return json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as e:
        raise UpdateCheckError("GitHub yanıtı okunamadı.") from e


def check_for_update(current: str = __version__, repo: str = RELEASE_REPO,
                     fetch: Callable[..., Optional[dict]] = fetch_latest_release) -> Optional[UpdateInfo]:
    """Daha yeni bir sürüm varsa `UpdateInfo`, yoksa None; denetlenemezse `UpdateCheckError` fırlatır."""
    return release_to_update(fetch(repo, current), current, repo)


# ── İndirme ve kurulum ──

ProgressCallback = Callable[[int], None]
_SHA256 = re.compile(r"^\s*([0-9a-fA-F]{64})(?:\s|$)")
_DOWNLOAD_HOSTS = ("github.com", "githubusercontent.com")


def parse_checksum_file(text: str) -> str:
    """`<64 hane> *dosya` biçimindeki özet dosyasından SHA-256; biçim bozuksa boş."""
    match = _SHA256.match(text or "")
    return match.group(1).lower() if match else ""


def update_directory() -> Path:
    return Path(tempfile.gettempdir()) / UPDATE_DIR_NAME


def _host_allowed(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return urlparse(url).scheme == "https" and any(host == allowed or host.endswith("." + allowed) for allowed in _DOWNLOAD_HOSTS)


def _open_download(url: str, opener: Callable = urllib.request.urlopen):
    request = urllib.request.Request(url, headers={"User-Agent": f"GitCleanArchiver/{__version__}"})
    try:
        response = opener(request, timeout=DOWNLOAD_TIMEOUT_SECONDS)
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise UpdateCheckError("Güncelleme sunucusuna ulaşılamadı.") from e
    if not _host_allowed(response.geturl()):
        response.close()
        raise UpdateCheckError("Beklenmeyen bir adrese yönlendirildi.")
    return response


def _expected_sha256(info: UpdateInfo, opener: Callable) -> str:
    if info.sha256:
        return info.sha256.lower()
    if info.checksum_url:
        with _open_download(info.checksum_url, opener) as response:
            return parse_checksum_file(response.read(1024).decode("utf-8", errors="replace"))
    return ""


def download_installer(info: UpdateInfo, progress: Optional[ProgressCallback] = None, opener: Callable = urllib.request.urlopen,
                       directory: Optional[Path] = None) -> Path:
    """Kurulum dosyasını geçici klasöre indirir; boyut ya da SHA-256 uyuşmazsa dosyayı silip `UpdateCheckError` verir."""
    if not info.download_url or not INSTALLER_PATTERN.match(info.asset_name):
        raise UpdateCheckError("Bu sürümde kurulum dosyası yok; sürüm sayfasından indirin.")
    expected = _expected_sha256(info, opener)
    if not expected:
        raise UpdateCheckError("Kurulum dosyasının SHA-256 özeti bulunamadı; güvenlik için güncelleme iptal edildi.")
    target_dir = directory or update_directory()
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / info.asset_name
    limit = min(info.size, MAX_INSTALLER_BYTES) if info.size else MAX_INSTALLER_BYTES
    digest, received = hashlib.sha256(), 0
    try:
        with _open_download(info.download_url, opener) as response, target.open("wb") as out:
            while chunk := response.read(DOWNLOAD_CHUNK_BYTES):
                received += len(chunk)
                if received > limit:
                    raise UpdateCheckError("İndirilen dosya beklenenden büyük; iptal edildi.")
                out.write(chunk)
                digest.update(chunk)
                if progress is not None and info.size > 0:
                    progress(min(100, received * 100 // info.size))
        if info.size and received != info.size:
            raise UpdateCheckError("İndirilen dosya eksik; boyut uyuşmuyor.")
        if digest.hexdigest() != expected:
            raise UpdateCheckError("İndirilen dosya doğrulanamadı; özet uyuşmuyor.")
    except UpdateCheckError:
        target.unlink(missing_ok=True)
        raise
    except OSError as e:
        target.unlink(missing_ok=True)
        raise UpdateCheckError(f"Güncelleme indirilemedi: {e.strerror or e}") from e
    return target


def launch_installer(installer: Path, popen: Callable = subprocess.Popen) -> None:
    """Kurulumu uygulamadan bağımsız başlatır (kabuk yok, sabit argümanlar); çağıran uygulamayı kapatmalıdır.

    `/SILENT`: ilerleme penceresiyle sormadan kurar, çalışan uygulamayı kapatır, kurulumdan sonra uygulama yeniden açılır
    (Inno betiğindeki `Check: WizardSilent`). Sessiz kurulum hata göstermez: neden `install.log` içindedir.
    """
    if os.name != "nt":
        raise UpdateCheckError("Otomatik kurulum yalnızca Windows'ta desteklenir.")
    if not INSTALLER_PATTERN.match(installer.name) or not installer.is_file():
        raise UpdateCheckError("Kurulum dosyası bulunamadı.")
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    popen([str(installer), "/SILENT", "/SUPPRESSMSGBOXES", "/CLOSEAPPLICATIONS", f"/LOG={installer.with_name('install.log')}"],
          close_fds=True, creationflags=flags)


# ── Kullanıcı tercihleri: ayrı dosya (ana ayar dosyasını yazan ViewModel ile çakışmaz) ──

@dataclass
class UpdatePreferences:
    check_enabled: bool = True
    skipped_version: str = ""        # "Bu sürümü atla": o sürüm için açılış penceresi çıkmaz


def preferences_path() -> Path:
    return Path.home() / ".gitclean" / "updates.json"


def load_preferences(path: Optional[Path] = None) -> UpdatePreferences:
    target = Path(path) if path else preferences_path()
    try:
        data = json.loads(target.read_text(encoding="utf-8")) if target.is_file() else {}
    except (OSError, ValueError) as e:
        logger.warning("Güncelleme tercihleri okunamadı, varsayılanlar kullanılıyor: %s (%s)", target, e)
        data = {}
    if not isinstance(data, dict):
        data = {}
    skipped = data.get("skipped_version")
    return UpdatePreferences(check_enabled=data.get("check_enabled") is not False,
                             skipped_version=skipped if isinstance(skipped, str) and parse_version(skipped) else "")


def save_preferences(preferences: UpdatePreferences, path: Optional[Path] = None) -> bool:
    target = Path(path) if path else preferences_path()
    temporary = target.with_name(target.name + ".tmp")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary.write_text(json.dumps({"check_enabled": preferences.check_enabled,
                                         "skipped_version": preferences.skipped_version}, indent=1), encoding="utf-8")
        os.replace(temporary, target)
        return True
    except OSError as e:
        logger.warning("Güncelleme tercihleri kaydedilemedi: %s (%s)", target, e)
        try:
            temporary.unlink()
        except OSError:
            pass
        return False
