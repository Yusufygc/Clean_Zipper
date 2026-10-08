from pathlib import Path

from src.core.exclusions import is_excluded_dir


def make(tmp_path, *relative_files):
    for rel in relative_files:
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x")
    return tmp_path


def test_named_directories(tmp_path):
    for name in ("venv", ".venv", "node_modules", ".next", "coverage", "dist", "build", ".git"):
        assert is_excluded_dir(str(tmp_path / name), name, [name]) is True
    assert is_excluded_dir(str(tmp_path / "src"), "src", ["src"]) is False


def test_conditional_directories_need_a_sibling_build_file(tmp_path):
    assert is_excluded_dir(str(tmp_path / "target"), "target", ["target", "Cargo.toml"]) is True
    assert is_excluded_dir(str(tmp_path / "target"), "target", ["target", "notes.txt"]) is False
    assert is_excluded_dir(str(tmp_path / "bin"), "bin", ["bin", "App.csproj"]) is True
    assert is_excluded_dir(str(tmp_path / "bin"), "bin", ["bin", "run.sh"]) is False


def test_virtualenv_detected_by_marker_file(tmp_path):
    make(tmp_path, "myenv/pyvenv.cfg", "plain/readme.txt")
    assert is_excluded_dir(str(tmp_path / "myenv"), "myenv", ["myenv", "plain"]) is True
    assert is_excluded_dir(str(tmp_path / "plain"), "plain", ["myenv", "plain"]) is False


def test_custom_excluded_set(tmp_path):
    assert is_excluded_dir(str(tmp_path / "x"), "x", ["x"], excluded=frozenset({"x"})) is True
    assert is_excluded_dir(str(tmp_path / "venv"), "venv", ["venv"], excluded=frozenset({"x"})) is False
