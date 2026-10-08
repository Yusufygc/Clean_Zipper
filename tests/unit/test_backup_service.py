import zipfile
from pathlib import Path

from src.services.backup_service import MAX_REPORTED_EXCLUDED, BackupService
from src.services.project_service import ProjectService


def write(path: Path, content: str = "x"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def zip_names(result, backups: Path):
    name = result["backup_name"]
    with zipfile.ZipFile(backups / name / f"{name}.zip") as archive:
        return set(archive.namelist())


def backup(project: Path, tmp_path: Path, name: str = "b"):
    backups = tmp_path / "backups"
    return BackupService(backups).create_backup(project, name), backups


def test_gitignored_files_are_kept_because_git_cannot_restore_them(tmp_path):
    project = tmp_path / "app"
    write(project / ".gitignore", ".env\n*.db\nmodels/\nsecrets.json\n")
    write(project / ".env", "TOKEN=1")
    write(project / "data" / "local.db", "sqlite")
    write(project / "models" / "net.tflite", "weights")
    write(project / "secrets.json", "{}")
    write(project / "main.py", "x = 1\n")
    result, backups = backup(project, tmp_path)
    assert {".env", "data/local.db", "models/net.tflite", "secrets.json", "main.py", ".gitignore"} <= {
        n.replace("\\", "/") for n in zip_names(result, backups)}


def test_regenerable_folders_are_left_out_at_any_depth(tmp_path):
    project = tmp_path / "app"
    write(project / "main.py")
    for folder in (".git", "venv", "node_modules", "__pycache__", "dist", "build", ".pytest_cache",
                   "web/node_modules", "src/__pycache__", "tools/.next"):
        write(project / folder / "junk.bin")
    write(project / "myenv" / "pyvenv.cfg", "home = x")                      # adı ne olursa olsun sanal ortam
    write(project / "myenv" / "lib.py")
    result, backups = backup(project, tmp_path)
    assert {n.replace("\\", "/") for n in zip_names(result, backups)} == {"main.py"}


def test_conditional_folders_are_excluded_only_next_to_a_build_file(tmp_path):
    rust = tmp_path / "rust"
    write(rust / "Cargo.toml")
    write(rust / "target" / "debug.o")
    plain = tmp_path / "plain"
    write(plain / "target" / "report.txt")                                    # yanında derleme dosyası yok: kaynak
    names_rust = {n.replace("\\", "/") for n in zip_names(*backup(rust, tmp_path, "r"))}
    names_plain = {n.replace("\\", "/") for n in zip_names(*backup(plain, tmp_path, "p"))}
    assert names_rust == {"Cargo.toml"} and names_plain == {"target/report.txt"}


def test_result_reports_what_was_left_out(tmp_path):
    project = tmp_path / "app"
    write(project / "main.py")
    write(project / "node_modules" / "a.js")
    write(project / "web" / "node_modules" / "b.js")
    write(project / ".git" / "HEAD")
    result, _ = backup(project, tmp_path)
    assert result["success"] and result["complete"]
    assert sorted(result["excluded_dirs"]) == [".git", "node_modules", "web/node_modules"]
    assert result["excluded_dir_count"] == 3


def test_excluded_list_is_capped_but_count_is_exact(tmp_path):
    project = tmp_path / "app"
    write(project / "main.py")
    for i in range(MAX_REPORTED_EXCLUDED + 20):
        write(project / f"pkg{i}" / "node_modules" / "a.js")
    result, _ = backup(project, tmp_path)
    assert len(result["excluded_dirs"]) == MAX_REPORTED_EXCLUDED and result["excluded_dir_count"] == MAX_REPORTED_EXCLUDED + 20


def test_nothing_excluded_gives_empty_report(tmp_path):
    project = tmp_path / "app"
    write(project / "main.py")
    result, _ = backup(project, tmp_path)
    assert result["excluded_dirs"] == [] and result["excluded_dir_count"] == 0


def test_backup_never_contains_itself_when_stored_inside_the_project(tmp_path):
    project = tmp_path / "app"
    write(project / "main.py")
    service = BackupService(project / "_backups")
    result = service.create_backup(project, "self")
    with zipfile.ZipFile(project / "_backups" / "self" / "self.zip") as archive:
        assert [n for n in archive.namelist() if n.endswith(".zip")] == []
        assert "main.py" in archive.namelist()
    assert result["success"] and result["complete"]


def test_contents_equal_an_independent_walk(tmp_path):
    """Bağımsız `Path.rglob` + elle yazılmış dışlama listesi ile birebir aynı dosya kümesi."""
    project = tmp_path / "app"
    for rel in ("a.py", "src/b.py", "src/deep/c.txt", ".env", ".hidden/x", "venv/z.py", "src/node_modules/q.js",
                "docs/readme.md", "dist/o.js", "build/x.o"):
        write(project / rel)
    skip = {"venv", "node_modules", "dist", "build", ".git", "__pycache__"}
    expected = {p.relative_to(project).as_posix() for p in project.rglob("*")
                if p.is_file() and not skip.intersection(p.relative_to(project).parts)}
    result, backups = backup(project, tmp_path)
    assert {n.replace("\\", "/") for n in zip_names(result, backups)} == expected


def test_project_service_backup_reports_exclusions(tmp_path):
    project = tmp_path / "app"
    write(project / "main.py")
    write(project / "venv" / "lib.py")
    service = ProjectService()
    service.backup_service = BackupService(tmp_path / "backups")
    service.set_project(project)
    result = service.create_backup("svc")
    assert result["success"] and result["excluded_dirs"] == ["venv"]
