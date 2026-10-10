"""Katman yönü: alt katmanlar (çekirdek, analizörler, diller, doktorlar, modeller, araçlar) servisleri ve arayüzü
import etmez; arayüz ise yalnızca `ProjectService` yüzeyini kullanır (alt servislerin yöntemlerini doğrudan çağırmaz)."""
import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src"
LOWER = ("core", "analyzers", "languages", "doctors", "models", "utils")
UPPER = ("src.services", "src.qml_ui")


def imported_modules(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            yield node.module
        elif isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)


def test_lower_layers_do_not_import_services_or_ui():
    offenders = [f"{path.relative_to(SRC).as_posix()}: {module}"
                 for package in LOWER for path in (SRC / package).rglob("*.py")
                 for module in imported_modules(path) if module.startswith(UPPER)]
    assert offenders == []


def test_view_models_call_project_service_not_its_sub_services():
    """Eski arayüz alt servisleri doğrudan çağırıp teşhis kilidini / önbelleğini atlıyordu."""
    offenders = []
    for path in (SRC / "qml_ui").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for call in ("service.doctor.diagnose", "service.archive_service.create_zip", "service.archive_service.copy_project",
                     "service.cleanup_service.cleanup", "service.backup_service.create_backup"):
            if call in text:
                offenders.append(f"{path.name}: {call}")
    assert offenders == []
