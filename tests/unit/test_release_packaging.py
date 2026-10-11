"""Sürüm tutarlılığı, yayın aracı ve kurulum sihirbazı betiği."""
import importlib.util
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from src.version import RELEASE_REPO, __version__

ROOT = Path(__file__).resolve().parents[2]


def load_release_tool():
    spec = importlib.util.spec_from_file_location("release_tool", ROOT / "tools" / "release.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


# ---- sürüm kaynakları tutarlı -----------------------------------------------------------------------------------------------

def test_every_version_source_matches_src_version():
    assert f"badge/Version-{__version__}-orange" in read("README.md")
    assert not (ROOT / "version_info.txt").exists()                              # sürümle değişen exe kaynağı kalmadı (kararlı exe)


def test_the_version_is_plain_x_y_z_and_the_repo_matches_the_git_remote_url_in_the_docs():
    assert re.fullmatch(r"\d+\.\d+\.\d+", __version__)
    assert RELEASE_REPO in read("README.md")


def test_no_hardcoded_version_is_left_in_the_ui_or_the_application_id():
    assert "appVersion" not in read("src/qml_ui/qml/singletons/AppStrings.qml")
    assert not re.search(r"v\d+\.\d+\.\d+", read("src/qml_ui/qml/MainView.qml"))
    app_py = read("src/qml_ui/app.py")
    assert re.search(r'SetCurrentProcessExplicitAppUserModelID\("([^"]+)"\)', app_py).group(1) == "gitclean.archiver.qml"


# ---- yayın aracı --------------------------------------------------------------------------------------------------------

@pytest.fixture
def sandbox(tmp_path):
    for relative in ("src/version.py", "README.md"):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    return tmp_path


def test_bump_files_updates_every_source_and_changes_nothing_else(sandbox):
    tool = load_release_tool()
    before = {name: (sandbox / name).read_bytes() for name in ("src/version.py", "README.md")}
    tool.bump_files(sandbox, "12.34.56")
    assert tool.read_version(sandbox) == "12.34.56"
    assert "badge/Version-12.34.56-orange" in (sandbox / "README.md").read_text(encoding="utf-8")
    for name, old in before.items():
        new = (sandbox / name).read_bytes()
        assert b"\r\n" not in new or b"\r\n" in old                              # satır sonları korunur
        assert len(new.splitlines()) == len(old.splitlines()), name
    tool.bump_files(sandbox, __version__)                                        # geri döndürünce aynı baytlar
    assert {name: (sandbox / name).read_bytes() for name in before} == before


def test_release_tool_rejects_bad_versions_and_tag_mismatches(capsys):
    tool = load_release_tool()
    for bad in ("2.1", "v2", "abc", "2.1.0-rc1"):
        with pytest.raises(SystemExit):
            tool.as_tuple(bad)
    assert tool.check_tag("v" + __version__) == 0
    assert tool.check_tag("v99.0.0") == 1 and "uyuşmuyor" in capsys.readouterr().out
    with pytest.raises(SystemExit, match="büyük olmalı"):
        tool.release(__version__, dry_run=True)                                  # aynı sürüm yükseltme sayılmaz
    with pytest.raises(SystemExit, match="büyük olmalı"):
        tool.release("0.0.1", dry_run=True)


def test_dry_run_changes_no_file_and_creates_no_tag():
    tool = load_release_tool()
    status = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout
    branch = subprocess.run(["git", "branch", "--show-current"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout.strip()
    if status.strip() or branch != "main":
        pytest.skip("Kuru çalıştırma yalnızca temiz main dalında anlamlı (araç başka durumda zaten reddeder)")
    tool.release("99.0.0", dry_run=True)
    assert tool.read_version() == __version__
    assert subprocess.run(["git", "tag", "--list", "v99.0.0"], cwd=ROOT, capture_output=True, text=True, encoding="utf-8").stdout == ""


# ---- kurulum sihirbazı betiği ---------------------------------------------------------------------------------------------------

def test_installer_script_is_consistent_with_the_app_and_the_build():
    script = read("packaging/GitCleanArchiver.iss")
    assert "#error" in script and "AppVersion" in script                         # sürüm dışarıdan verilmezse derleme durur
    assert 'AppUserModelID: "gitclean.archiver.qml"' in script
    assert "OutputBaseFilename=GitCleanArchiver-Setup-{#AppVersion}" in script   # güncelleme denetimi bu adı arar
    assert 'GitCleanArchiver-Setup-' in read("src/services/update_service.py")
    assert "PrivilegesRequired=lowest" in script and "CloseApplications=yes" in script            # UAC sormaz, derleme sonrası sessiz deneme mümkün
    assert r'Source: "..\dist\GitCleanArchiver\*"' in script and "recursesubdirs" in script       # klasörün tamamı paketlenir
    assert re.search(r"AppId=\{\{[0-9A-F-]{36}\}", script)
    for relative in ("resources/icons/app_icon.ico", "packaging/wizard_large.bmp", "packaging/wizard_small.bmp"):
        assert (ROOT / relative).is_file(), relative
    assert read("src/qml_ui/app.py").count("gitclean.archiver.qml") == 1


def test_installer_asset_name_pattern_matches_what_the_installer_produces():
    from src.services.update_service import INSTALLER_PATTERN
    assert INSTALLER_PATTERN.match(f"GitCleanArchiver-Setup-{__version__}.exe")
    assert not INSTALLER_PATTERN.match(f"GitCleanArchiver-Setup-{__version__}.exe.sha256")


def test_wizard_images_have_the_sizes_inno_setup_expects():
    def bmp_size(name):
        data = (ROOT / "packaging" / name).read_bytes()
        assert data[:2] == b"BM"
        return int.from_bytes(data[18:22], "little"), abs(int.from_bytes(data[22:26], "little", signed=True))
    assert bmp_size("wizard_large.bmp") == (164, 314) and bmp_size("wizard_small.bmp") == (55, 55)


def test_release_workflow_triggers_on_version_tags_and_does_not_interpolate_the_tag_into_shell_code():
    workflow = read(".github/workflows/release.yml")
    assert re.search(r'tags:\s*\n\s*- "v\*"', workflow)
    assert "tools/release.py --check-tag" in workflow and "build_installer.py" in workflow
    run_lines = [line for line in workflow.splitlines() if "${{ github.ref_name }}" in line and not line.strip().startswith(("TAG:", "#"))]
    assert run_lines == []                                                       # etiket yalnızca env ile geçer
    assert "contents: write" in workflow


def test_installer_and_build_outputs_are_not_committed():
    ignore = read(".gitignore")
    assert "dist/" in ignore and "build/" in ignore


# ---- lisans, üçüncü taraf bildirimleri, kod imzalama (SignPath) ------------------------------------------------------------------

def test_the_repo_has_an_mit_license_with_the_copyright_holder():
    text = read("LICENSE")
    assert text.startswith("MIT License") and "Copyright (c) 2026 Yusuf" in text
    assert "THE SOFTWARE IS PROVIDED \"AS IS\"" in text
    assert "MIT" in read("README.md") and "LICENSE" in read("README.md")


def test_third_party_notices_cover_every_runtime_dependency_at_its_pinned_version():
    tool = load_third_party_tool()
    notices = read("THIRD_PARTY_NOTICES.md")
    for package, version in tool.requirement_versions().items():
        assert f"### {package} {version}" in notices, (package, version)         # sürüm değişince dosya yeniden üretilmeli
    assert "shiboken6" in notices and "LGPL" in notices and "yeniden bağlama" in notices
    assert notices == tool.render()                                              # elle düzenlenmemiş, güncel


def load_third_party_tool():
    spec = importlib.util.spec_from_file_location("third_party_tool", ROOT / "tools" / "third_party_notices.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_installer_ships_the_license_and_the_notices_and_shows_the_license_page():
    script = read("packaging/GitCleanArchiver.iss")
    assert r"LicenseFile=..\LICENSE" in script
    assert r'Source: "..\LICENSE"' in script and r'Source: "..\THIRD_PARTY_NOTICES.md"' in script


def test_readme_has_the_privacy_statement_and_no_code_signing_policy():
    from src.services.update_service import OPT_OUT_ENV
    readme = read("README.md")
    assert "SignPath" not in readme and "Kod İmzalama Politikası" not in readme            # imzalama bu projede yapılmıyor (karar: 2026-10-11)
    assert "## 🔒 Gizlilik" in readme and OPT_OUT_ENV in readme                    # gizlilik metni gerçek kapatma yoluyla tutarlı
    assert "api.github.com/repos/Yusufygc/Clean_Zipper/releases/latest" in readme


def test_no_signpath_leftovers_in_the_workflow_or_the_repo_root():
    workflow = read(".github/workflows/release.yml")
    assert "signpath" not in workflow.lower() and "SIGNING" not in workflow
    assert not (ROOT / ".signpath").exists()


def test_release_workflow_builds_with_build_installer_and_publishes_the_installer_and_its_checksum():
    workflow = read(".github/workflows/release.yml")
    assert "python build_installer.py" in workflow and "--skip-build" not in workflow and "checksum-only" not in workflow
    assert "gh release create" in workflow and "dist/installer/" in workflow and "--verify-tag" in workflow


def test_installer_relaunches_the_app_only_after_an_in_app_update_not_after_the_build_check():
    script = read("packaging/GitCleanArchiver.iss")
    assert "Check: RelaunchAfterUpdate" in script
    assert "WizardSilent and not HasParam('/VERYSILENT')" in script                      # /SILENT (güncelleme) açar, /VERYSILENT (deneme) açmaz
    from build_verify import installer_check  # noqa: F401
    assert "/VERYSILENT" in read("build_verify.py") and '"/SILENT"' in read("src/services/update_service.py")


# ---- kararlı exe: özet sürümler arasında sabit kalmalı (Akıllı Uygulama Denetimi onayı) ----------------------------------------------------

def test_launcher_script_and_version_resource_are_pinned_so_the_exe_hash_does_not_drift():
    """Bu dosyalar exe'nin içine gömülür; içerikleri değişirse exe özeti değişir ve Windows yeniden değerlendirir.
    Bilerek değiştiriliyorsa: yeni exe'yi Windows'ta dene, bu özetleri ve packaging/launcher.sha256'yı birlikte güncelle."""
    import hashlib
    def digest(relative):
        return hashlib.sha256((ROOT / relative).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    assert digest("packaging/launcher.py") == "fc10d323ce532006cb00b091265ba4754ad3940a93a8a95d49c3742d4a98bcc3"
    assert digest("packaging/launcher_version_info.txt") == "b1c30b9b51f9e5850fe0c78fb54decbea4e50f21a3b1b8f8c9ef52f68e2ac277"
    import build_exe
    assert build_exe.LAUNCHER_EPOCH == 1700000000 and str(build_exe.LAUNCHER_ENTRY).replace("\\", "/") == "packaging/launcher.py"


def test_the_build_is_configured_for_a_byte_stable_exe():
    import build_exe
    arguments = build_exe.pyinstaller_arguments(ROOT, ROOT / build_exe.LAUNCHER_ENTRY)
    assert "--debug=noarchive" in arguments and "--onedir" in arguments and "--noupx" in arguments
    assert any(a.startswith("--version-file=") and a.replace("\\", "/").endswith("packaging/launcher_version_info.txt") for a in arguments)
    assert f"--paths={ROOT}" in arguments
    info = read("packaging/launcher_version_info.txt")
    assert f"u'FileVersion', u'{__version__}'" not in info or __version__ == "1.0.0"      # sürümle değişmez
    source = read("build_exe.py")
    assert 'os.environ["SOURCE_DATE_EPOCH"] = str(LAUNCHER_EPOCH)' in source


def test_the_approved_launcher_hash_is_a_sha256_and_the_check_gates_the_build(tmp_path):
    import build_exe
    approved = read("packaging/launcher.sha256").split()[0]
    assert re.fullmatch(r"[0-9a-f]{64}", approved)
    exe = tmp_path / "GitCleanArchiver.exe"
    exe.write_bytes(b"MZ-onaysiz")
    (tmp_path / "packaging").mkdir()
    (tmp_path / "packaging" / "launcher.sha256").write_text(f"{approved} *GitCleanArchiver.exe\n", encoding="utf-8")
    with pytest.raises(SystemExit):                                                  # özet farklı: derleme / yayın durur
        build_exe.check_launcher_hash(tmp_path, exe)
    build_exe.check_launcher_hash(tmp_path, exe, update=True)                        # bilerek onaylama: yeni özet yazılır
    build_exe.check_launcher_hash(tmp_path, exe)                                     # artık aynı: geçer
    assert build_exe.exe_sha256(exe) in (tmp_path / "packaging" / "launcher.sha256").read_text(encoding="utf-8")
    with pytest.raises(SystemExit):
        build_exe.check_launcher_hash(tmp_path / "bos", exe)                         # onay dosyası yoksa da durur


def test_the_release_workflow_builds_through_the_hash_gate():
    workflow = read(".github/workflows/release.yml")
    assert "python build_installer.py" in workflow and "--no-verify" not in workflow
    assert "build_exe.build_executable" in read("build_installer.py")                # build_installer exe'yi kapıdan geçirerek derler
