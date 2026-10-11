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
    major, minor, patch = (int(part) for part in __version__.split("."))
    info = read("version_info.txt")
    assert f"filevers=({major}, {minor}, {patch}, 0)" in info and f"prodvers=({major}, {minor}, {patch}, 0)" in info
    assert f"u'FileVersion', u'{__version__}'" in info and f"u'ProductVersion', u'{__version__}'" in info
    assert f"badge/Version-{__version__}-orange" in read("README.md")


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
    for relative in ("src/version.py", "version_info.txt", "README.md"):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    return tmp_path


def test_bump_files_updates_every_source_and_changes_nothing_else(sandbox):
    tool = load_release_tool()
    before = {name: (sandbox / name).read_bytes() for name in ("src/version.py", "version_info.txt", "README.md")}
    tool.bump_files(sandbox, "12.34.56")
    assert tool.read_version(sandbox) == "12.34.56"
    info = (sandbox / "version_info.txt").read_text(encoding="utf-8")
    assert "filevers=(12, 34, 56, 0)" in info and "prodvers=(12, 34, 56, 0)" in info and "u'FileVersion', u'12.34.56'" in info
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
    assert "OutputBaseFilename=GitCleanArchiver-InnoSetup-{#AppVersion}" in script   # güncelleme denetimi bu çıktıyı önermez
    assert 'GitCleanArchiver-' in read("src/services/update_service.py")
    assert "PrivilegesRequired=lowest" in script and "CloseApplications=yes" in script
    assert re.search(r"AppId=\{\{[0-9A-F-]{36}\}", script)
    for relative in ("resources/icons/app_icon.ico", "packaging/wizard_large.bmp", "packaging/wizard_small.bmp"):
        assert (ROOT / relative).is_file(), relative
    assert read("src/qml_ui/app.py").count("gitclean.archiver.qml") == 1


def test_installer_asset_name_pattern_matches_what_the_installer_produces():
    from src.services.update_service import INSTALLER_PATTERN
    assert INSTALLER_PATTERN.match(f"GitCleanArchiver-{__version__}.exe")
    assert not INSTALLER_PATTERN.match(f"GitCleanArchiver-InnoSetup-{__version__}.exe")    # imzasız Inno çıktısı önerilmez
    assert not INSTALLER_PATTERN.match(f"GitCleanArchiver-{__version__}.exe.sha256")


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
