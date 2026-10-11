"""Güncelleme denetimi: sürüm karşılaştırma, GitHub kaydının doğrulanması, ağ hatalarının karşılanması, tercihler."""
import io
import json
import urllib.error

import pytest

from src.services import update_service as svc
from src.services.update_service import UpdateCheckError

REPO = "Yusufygc/Clean_Zipper"
BASE = f"https://github.com/{REPO}"


def release(tag="v2.1.0", **overrides):
    data = {
        "tag_name": tag, "draft": False, "prerelease": False, "html_url": f"{BASE}/releases/tag/{tag}",
        "published_at": "2026-10-11T12:00:00Z", "body": "Yenilikler\n- gruplu liste",
        "assets": [
            {"name": "GitCleanArchiver-Setup-2.1.0.exe.sha256", "size": 90,
             "browser_download_url": f"{BASE}/releases/download/{tag}/GitCleanArchiver-Setup-2.1.0.exe.sha256"},
            {"name": "GitCleanArchiver-Setup-2.1.0.exe", "size": 52_428_800,
             "browser_download_url": f"{BASE}/releases/download/{tag}/GitCleanArchiver-Setup-2.1.0.exe"},
        ],
    }
    data.update(overrides)
    return data


# ---- sürüm karşılaştırma ------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [("v2.1.0", (2, 1, 0)), ("2.1.0", (2, 1, 0)), (" v10.0.12 ", (10, 0, 12)),
                                           ("v2.1", None), ("v2.1.0-rc1", None), ("latest", None), ("", None), (None, None)])
def test_parse_version(text, expected):
    assert svc.parse_version(text) == expected


def test_versions_compare_numerically_not_alphabetically():
    assert svc.is_newer("v2.10.0", "2.9.0") and svc.is_newer("3.0.0", "2.99.99")
    assert not svc.is_newer("v2.1.0", "2.1.0") and not svc.is_newer("2.0.9", "2.1.0")
    assert not svc.is_newer("v2.2.0-beta", "2.1.0")                    # ön sürüm sayılmaz
    assert not svc.is_newer("garbage", "2.1.0") and not svc.is_newer("2.2.0", "garbage")


# ---- GitHub kaydını güncelleme bilgisine çevirme ------------------------------------------------------------------------------

def test_a_newer_release_becomes_update_info_with_the_installer_asset():
    info = svc.release_to_update(release(), "2.0.0", REPO)
    assert info.version == "2.1.0" and info.tag == "v2.1.0" and info.published == "2026-10-11"
    assert info.asset_name == "GitCleanArchiver-Setup-2.1.0.exe" and info.size == 52_428_800
    assert info.download_url == f"{BASE}/releases/download/v2.1.0/GitCleanArchiver-Setup-2.1.0.exe"
    assert info.page_url == f"{BASE}/releases/tag/v2.1.0" and "gruplu liste" in info.notes


@pytest.mark.parametrize("data", [release(draft=True), release(prerelease=True), release("v2.0.0"), release("v1.9.0"),
                                  release("v2.1.0-rc1"), release("nightly"), {}, [], None, "x"])
def test_drafts_prereleases_old_or_malformed_records_offer_no_update(data):
    assert svc.release_to_update(data, "2.0.0", REPO) is None


def test_a_record_without_the_installer_falls_back_to_the_release_page():
    info = svc.release_to_update(release(assets=[]), "2.0.0", REPO)
    assert info.download_url == "" and info.page_url.endswith("/releases/tag/v2.1.0")


@pytest.mark.parametrize("url", ["http://github.com/Yusufygc/Clean_Zipper/releases/tag/v2.1.0",         # https değil
                                 "https://evil.example/Yusufygc/Clean_Zipper/releases/tag/v2.1.0",       # başka alan adı
                                 "https://github.com.evil.example/Yusufygc/Clean_Zipper/x",              # alt alan adı hilesi
                                 "https://github.com/someone-else/repo/releases/tag/v2.1.0",             # başka depo
                                 "https://github.com/Yusufygc/Clean_Zipper-evil/releases", "javascript:alert(1)", "", None])
def test_untrusted_release_page_addresses_are_rejected(url):
    with pytest.raises(UpdateCheckError):
        svc.release_to_update(release(html_url=url), "2.0.0", REPO)


def test_an_installer_asset_with_an_untrusted_address_or_name_is_ignored():
    tag = "v2.1.0"
    assets = [{"name": "GitCleanArchiver-Setup-2.1.0.exe", "size": 1, "browser_download_url": "https://evil.example/a.exe"},
              {"name": "malware.exe", "size": 1, "browser_download_url": f"{BASE}/releases/download/{tag}/malware.exe"},
              {"name": "GitCleanArchiver-Setup-2.1.0.exe", "size": 1, "browser_download_url": "http://github.com/Yusufygc/Clean_Zipper/x.exe"}]
    assert svc.release_to_update(release(assets=assets), "2.0.0", REPO).download_url == ""


def test_release_notes_are_capped_and_stay_plain_text():
    info = svc.release_to_update(release(body="x" * 20_000), "2.0.0", REPO)
    assert len(info.notes) == svc.MAX_NOTES_CHARS
    assert svc.release_to_update(release(body=None), "2.0.0", REPO).notes == ""


def test_markdown_release_notes_are_shown_as_plain_text():
    markdown = ("## Yenilikler\r\n* **Gruplu** liste\r\n+ Hızlı\r\n### Düzeltmeler\r\n- Arama\r\n\r\n"
                "**Full Changelog**: https://github.com/x/y/compare/a...b")
    expected = ("Yenilikler\n- Gruplu liste\n- Hızlı\nDüzeltmeler\n- Arama\n\n"
                "Full Changelog: https://github.com/x/y/compare/a...b")
    assert svc.plain_notes(markdown) == expected


# ---- ağ ----------------------------------------------------------------------------------------------------------------

class FakeResponse(io.BytesIO):
    def __init__(self, payload: bytes, url="https://api.github.com/repos/Yusufygc/Clean_Zipper/releases/latest"):
        super().__init__(payload)
        self._url = url

    def geturl(self):
        return self._url

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def serve(monkeypatch, result):
    seen = {}

    def fake_urlopen(request, timeout=None):
        seen["request"], seen["timeout"] = request, timeout
        if isinstance(result, Exception):
            raise result
        return result
    monkeypatch.setattr(svc.urllib.request, "urlopen", fake_urlopen)
    return seen


def test_fetch_sends_one_anonymous_https_request_with_a_timeout(monkeypatch):
    seen = serve(monkeypatch, FakeResponse(json.dumps(release()).encode()))
    assert svc.fetch_latest_release(REPO, "2.0.0")["tag_name"] == "v2.1.0"
    request = seen["request"]
    assert request.full_url == f"https://api.github.com/repos/{REPO}/releases/latest" and seen["timeout"] == svc.TIMEOUT_SECONDS
    assert request.get_header("User-agent") == "GitCleanArchiver/2.0.0"
    assert not any(key.lower() in ("authorization", "cookie") for key in request.headers)       # kimlik bilgisi gönderilmez


def http_error(code):
    return urllib.error.HTTPError("https://api.github.com/x", code, "msg", {}, io.BytesIO(b""))


def test_no_published_release_is_not_an_error(monkeypatch):
    serve(monkeypatch, http_error(404))
    assert svc.fetch_latest_release(REPO) is None
    assert svc.check_for_update("2.0.0", REPO, fetch=lambda repo, current: None) is None


@pytest.mark.parametrize("failure,expected", [(http_error(403), "istek sınırı"), (http_error(429), "istek sınırı"),
                                              (http_error(500), "500"), (urllib.error.URLError("dns"), "ulaşılamadı"),
                                              (TimeoutError(), "ulaşılamadı")])
def test_network_failures_become_readable_errors(monkeypatch, failure, expected):
    serve(monkeypatch, failure)
    with pytest.raises(UpdateCheckError, match=expected):
        svc.fetch_latest_release(REPO)


def test_oversized_corrupt_or_redirected_responses_are_rejected(monkeypatch):
    serve(monkeypatch, FakeResponse(b"{" + b" " * (svc.MAX_RESPONSE_BYTES + 10)))
    with pytest.raises(UpdateCheckError, match="büyük"):
        svc.fetch_latest_release(REPO)
    serve(monkeypatch, FakeResponse(b"not json"))
    with pytest.raises(UpdateCheckError, match="okunamadı"):
        svc.fetch_latest_release(REPO)
    serve(monkeypatch, FakeResponse(b"{}", url="https://evil.example/releases/latest"))
    with pytest.raises(UpdateCheckError, match="yönlendirildi"):
        svc.fetch_latest_release(REPO)


def test_opt_out_environment_variable(monkeypatch):
    monkeypatch.delenv(svc.OPT_OUT_ENV, raising=False)
    assert svc.updates_disabled_by_environment() is False
    for value in ("1", "true", "YES"):
        monkeypatch.setenv(svc.OPT_OUT_ENV, value)
        assert svc.updates_disabled_by_environment() is True
    monkeypatch.setenv(svc.OPT_OUT_ENV, "0")
    assert svc.updates_disabled_by_environment() is False


# ---- tercihler ---------------------------------------------------------------------------------------------------------

def test_preferences_round_trip_and_defaults(tmp_path):
    path = tmp_path / "updates.json"
    assert svc.load_preferences(path) == svc.UpdatePreferences(True, "")              # dosya yok: açık, atlanan yok
    assert svc.save_preferences(svc.UpdatePreferences(False, "2.1.0"), path) is True
    assert svc.load_preferences(path) == svc.UpdatePreferences(False, "2.1.0")
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.parametrize("content", ["{bozuk", "[]", '"x"', '{"check_enabled": "hayır", "skipped_version": 5}',
                                     '{"skipped_version": "../../etc"}'])
def test_corrupt_preferences_fall_back_to_safe_defaults(tmp_path, content):
    path = tmp_path / "updates.json"
    path.write_text(content, encoding="utf-8")
    assert svc.load_preferences(path) == svc.UpdatePreferences(True, "")


# ---- indirme, doğrulama ve kurulum (uygulama içi güncelleme) ----------------------------------------------------------------

INSTALLER_NAME = "GitCleanArchiver-Setup-2.1.0.exe"
INSTALLER_BYTES = b"MZ" + b"installer-bytes" * 200


def sha(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()


def info_for(data: bytes = INSTALLER_BYTES, **overrides):
    values = dict(version="2.1.0", tag="v2.1.0", page_url=f"{BASE}/releases/tag/v2.1.0",
                  download_url=f"{BASE}/releases/download/v2.1.0/{INSTALLER_NAME}", asset_name=INSTALLER_NAME, size=len(data),
                  notes="", published="2026-10-11", sha256=sha(data), checksum_url="")
    values.update(overrides)
    return svc.UpdateInfo(**values)


def serving(files: dict):
    """URL -> bayt sözlüğünden yanıt veren sahte `urlopen` (adres sonradan yönlendirilmiş gibi `geturl` döner)."""
    requested = []

    def opener(request, timeout=None):
        requested.append(request.full_url)
        data, final = files[request.full_url]
        return FakeResponse(data, url=final)
    opener.requested = requested
    return opener


def plain(data: bytes, url: str):
    return {url: (data, url)}


def test_release_record_carries_the_digest_and_the_checksum_asset():
    data = release()
    data["assets"][1]["digest"] = "sha256:" + "AB" * 32
    info = svc.release_to_update(data, "2.0.0", REPO)
    assert info.sha256 == "ab" * 32 and info.checksum_url.endswith("GitCleanArchiver-Setup-2.1.0.exe.sha256")
    assert svc.release_to_update(release(), "2.0.0", REPO).sha256 == ""                 # digest yok: .sha256 dosyası kullanılır


@pytest.mark.parametrize("text,expected", [(("ab" * 32) + " *GitCleanArchiver-Setup-2.1.0.exe\n", "ab" * 32), (("AB" * 32), "ab" * 32),
                                           ("kısa", ""), ("", ""), (("zz" * 32) + " x", "")])
def test_parse_checksum_file(text, expected):
    assert svc.parse_checksum_file(text) == expected


def test_download_verifies_size_and_sha256_and_reports_progress(tmp_path):
    info = info_for()
    opener = serving(plain(INSTALLER_BYTES, info.download_url))
    steps = []
    path = svc.download_installer(info, steps.append, opener=opener, directory=tmp_path)
    assert path == tmp_path / INSTALLER_NAME and path.read_bytes() == INSTALLER_BYTES
    assert steps[-1] == 100 and steps == sorted(steps)


def test_download_uses_the_checksum_asset_when_github_gave_no_digest(tmp_path):
    checksum_url = f"{BASE}/releases/download/v2.1.0/{INSTALLER_NAME}.sha256"
    info = info_for(sha256="", checksum_url=checksum_url)
    files = {**plain(INSTALLER_BYTES, info.download_url), **plain(f"{sha(INSTALLER_BYTES)} *{INSTALLER_NAME}\n".encode(), checksum_url)}
    assert svc.download_installer(info, opener=serving(files), directory=tmp_path).is_file()


def test_download_is_refused_without_any_checksum(tmp_path):
    info = info_for(sha256="", checksum_url="")
    opener = serving(plain(INSTALLER_BYTES, info.download_url))
    with pytest.raises(UpdateCheckError, match="SHA-256 özeti bulunamadı"):
        svc.download_installer(info, opener=opener, directory=tmp_path)
    assert opener.requested == [] and list(tmp_path.iterdir()) == []                   # hiçbir şey indirilmedi


@pytest.mark.parametrize("data,overrides,message", [
    (INSTALLER_BYTES[:-1] + b"X", {}, "özet uyuşmuyor"),                              # içerik bozuk (boyut aynı)
    (INSTALLER_BYTES[:100], {"sha256": sha(INSTALLER_BYTES[:100])}, "boyut uyuşmuyor"),   # eksik indirme
    (INSTALLER_BYTES + b"fazla", {"size": len(INSTALLER_BYTES), "sha256": sha(INSTALLER_BYTES + b"fazla")}, "büyük"),   # beklenenden fazla
])
def test_a_bad_download_is_deleted_and_reported(tmp_path, data, overrides, message):
    info = info_for(**overrides)
    with pytest.raises(UpdateCheckError, match=message):
        svc.download_installer(info, opener=serving(plain(data, info.download_url)), directory=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_download_rejects_a_redirect_to_an_untrusted_host_and_unknown_assets(tmp_path):
    info = info_for()
    evil = {info.download_url: (INSTALLER_BYTES, "https://evil.example/x.exe")}
    with pytest.raises(UpdateCheckError, match="yönlendirildi"):
        svc.download_installer(info, opener=serving(evil), directory=tmp_path)
    cdn = {info.download_url: (INSTALLER_BYTES, "https://release-assets.githubusercontent.com/abc/installer.exe")}
    assert svc.download_installer(info, opener=serving(cdn), directory=tmp_path).is_file()       # GitHub'ın kendi CDN'i kabul edilir
    for bad in (info_for(download_url=""), info_for(asset_name="../../evil.exe"), info_for(asset_name="malware.exe")):
        with pytest.raises(UpdateCheckError, match="kurulum dosyası yok"):
            svc.download_installer(bad, opener=serving({}), directory=tmp_path)


def test_launch_installer_uses_fixed_arguments_without_a_shell(tmp_path, monkeypatch):
    installer = tmp_path / INSTALLER_NAME
    installer.write_bytes(b"MZ")
    calls = []
    svc.launch_installer(installer, popen=lambda cmd, **kw: calls.append((cmd, kw)))
    command, options = calls[0]
    assert command == [str(installer), "/SILENT", "/SUPPRESSMSGBOXES", "/CLOSEAPPLICATIONS", f"/LOG={tmp_path / 'install.log'}"]
    assert options["close_fds"] is True and "shell" not in options                      # kabuk yok: argümanlar komut olarak yorumlanmaz
    for bad in (tmp_path / "evil.exe", tmp_path / "yok" / INSTALLER_NAME):
        bad.parent.mkdir(exist_ok=True)
        with pytest.raises(UpdateCheckError, match="bulunamadı"):
            svc.launch_installer(bad, popen=lambda *a, **kw: pytest.fail("başlatılmamalı"))


def blocked_oserror():
    error = OSError(22, "Uygulama Denetimi ilkesi bu dosyayı engelledi")
    error.winerror = 4551
    return error


def installer_file(tmp_path):
    installer = tmp_path / INSTALLER_NAME
    installer.write_bytes(b"MZ")
    return installer


def test_a_blocked_direct_launch_falls_back_to_the_explorer_route(tmp_path):
    installer, shell_calls = installer_file(tmp_path), []

    def popen(*a, **kw):
        raise blocked_oserror()
    svc.launch_installer(installer, popen=popen, shell_execute=lambda path, parameters: shell_calls.append((path, parameters)))
    assert shell_calls == [(installer, f'/SILENT /SUPPRESSMSGBOXES /CLOSEAPPLICATIONS "/LOG={tmp_path / "install.log"}"')]


def test_when_both_routes_are_blocked_the_error_carries_the_downloaded_file(tmp_path):
    installer = installer_file(tmp_path)

    def popen(*a, **kw):
        raise blocked_oserror()

    def shell(path, parameters):
        raise OSError(5, "erişim engellendi")
    with pytest.raises(svc.InstallerBlockedError) as caught:
        svc.launch_installer(installer, popen=popen, shell_execute=shell)
    assert caught.value.path == installer and "Akıllı Uygulama Denetimi" in str(caught.value) and "çift tıklayarak" in str(caught.value)
    assert isinstance(caught.value, UpdateCheckError)


def test_other_launch_errors_are_readable_and_do_not_try_the_explorer_route(tmp_path):
    installer = installer_file(tmp_path)

    def popen(*a, **kw):
        raise OSError(5, "Erişim engellendi")
    with pytest.raises(UpdateCheckError, match="Kurulum başlatılamadı: Erişim engellendi") as caught:
        svc.launch_installer(installer, popen=popen, shell_execute=lambda *a: pytest.fail("Gezgin yolu denenmemeli"))
    assert not isinstance(caught.value, svc.InstallerBlockedError)
