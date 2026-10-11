"""Güncelleme denetimi: GitHub'ın son sürüm kaydını okuyup kurulu sürümle karşılaştırır.

Güvenlik ve gizlilik:
- Tek istek: `GET https://api.github.com/repos/<depo>/releases/latest`. Kimlik bilgisi, proje verisi ya da kullanıcı kimliği
  gönderilmez (yalnızca `User-Agent: GitCleanArchiver/<sürüm>`). Kapatma: ayarlardan ya da `GITCLEAN_NO_UPDATE_CHECK=1`.
- Yanıt boyutu ve süre sınırlıdır; yanıttaki adresler yalnızca `https://github.com/<depo>/...` ise kabul edilir (sahte adres
  içeren yanıt reddedilir). Sürüm notu düz metin olarak gösterilir.
- Hiçbir şey indirilmez ya da çalıştırılmaz: kullanıcı onaylarsa sürüm sayfası / kurulum dosyası tarayıcıda açılır.
"""
import json
import logging
import os
import re
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


def _installer_asset(data: dict, repo: str) -> Tuple[str, str, int]:
    for asset in data.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        name = asset.get("name")
        url = _trusted_url(asset.get("browser_download_url"), repo)
        if isinstance(name, str) and INSTALLER_PATTERN.match(name) and url:
            size = asset.get("size")
            return name, url, size if isinstance(size, int) and size > 0 else 0
    return "", "", 0


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
    name, download_url, size = _installer_asset(data, repo)
    notes = data.get("body") if isinstance(data.get("body"), str) else ""
    published = data.get("published_at") if isinstance(data.get("published_at"), str) else ""
    return UpdateInfo(version=tag.lstrip("v"), tag=tag, page_url=page_url, download_url=download_url, asset_name=name,
                      size=size, notes=plain_notes(notes)[:MAX_NOTES_CHARS], published=published[:10])


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
