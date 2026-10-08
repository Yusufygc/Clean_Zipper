from pathlib import Path

from src.analyzers.architecture_analyzer import ArchitectureAnalyzer
from src.core.project_index import ProjectIndex
from src.models.analysis_models import Severity
from src.services.project_service import ProjectService


def write(path: Path, content: str = ""):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run(root: Path):
    return ArchitectureAnalyzer().analyze(ProjectIndex.build(root))


def cycles(results):
    return [r for r in results if r.metadata["rule"] == "import-cycle"]


def summary(results, language="python"):
    return next(r for r in results if r.metadata["rule"] == "dependency-graph" and r.metadata["language"] == language)


def test_python_two_file_cycle_is_medium_with_path(tmp_path):
    write(tmp_path / "pkg" / "__init__.py")
    write(tmp_path / "pkg" / "a.py", "from pkg import b\n")
    write(tmp_path / "pkg" / "b.py", "from . import a\n")
    write(tmp_path / "main.py", "import pkg.a\n")
    results = run(tmp_path)
    (cycle,) = cycles(results)
    assert cycle.severity == Severity.MEDIUM and cycle.category == "architecture"
    assert cycle.metadata["files"] == ["pkg/a.py", "pkg/b.py"]
    assert cycle.metadata["cycle"] == ["pkg/a.py", "pkg/b.py", "pkg/a.py"]
    assert cycle.metadata["approximate"] is False and cycle.file_path == tmp_path / "pkg" / "a.py"
    assert "pkg/a.py -> pkg/b.py -> pkg/a.py" in cycle.description
    assert summary(results).metadata["cycles"] == 1 and summary(results).metadata["files_in_cycles"] == 2


def test_four_file_cycle_is_high(tmp_path):
    names = ["a", "b", "c", "d"]
    for i, name in enumerate(names):
        write(tmp_path / f"{name}.py", f"import {names[(i + 1) % 4]}\n")
    (cycle,) = cycles(run(tmp_path))
    assert cycle.severity == Severity.HIGH and cycle.metadata["size"] == 4


def test_lazy_and_type_checking_imports_do_not_form_cycles(tmp_path):
    write(tmp_path / "a.py", "import b\n")
    write(tmp_path / "b.py",
          "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    import a\n\n\ndef f():\n    import a\n    return a\n")
    results = run(tmp_path)
    assert cycles(results) == []
    assert summary(results).metadata["edges"] == 1


def test_no_edges_means_no_findings(tmp_path):
    write(tmp_path / "a.py", "import os\n")
    write(tmp_path / "notes.txt", "x")
    assert run(tmp_path) == []


def test_summary_lists_most_depended_on_file(tmp_path):
    write(tmp_path / "core.py", "X = 1\n")
    for name in ("a", "b", "c"):
        write(tmp_path / f"{name}.py", "import core\n")
    top = summary(run(tmp_path)).metadata["top_fan_in"][0]
    assert top == ("core.py", 3)


def test_typescript_cycle_is_approximate_and_type_only_import_is_ignored(tmp_path):
    write(tmp_path / "src" / "a.ts", "import { b } from './b';\nexport const a = 1;\n")
    write(tmp_path / "src" / "b.ts", "import { a } from './a';\nexport const b = 2;\n")
    write(tmp_path / "src" / "c.ts", "import { d } from './d';\nexport const c = 1;\n")
    write(tmp_path / "src" / "d.ts", "import type { c } from './c';\nexport const d = 2;\n")
    results = run(tmp_path)
    (cycle,) = cycles(results)
    assert cycle.metadata["files"] == ["src/a.ts", "src/b.ts"] and cycle.metadata["approximate"] is True
    assert cycle.metadata["language"] == "javascript"


def test_alias_imports_are_resolved(tmp_path):
    write(tmp_path / "lib" / "x.ts", "import { y } from '@/lib/y';\nexport const x = 1;\n")
    write(tmp_path / "lib" / "y.ts", "import { x } from '@/lib/x';\nexport const y = 1;\n")
    assert len(cycles(run(tmp_path))) == 1


def test_service_scores_architecture_category(tmp_path):
    write(tmp_path / "a.py", "import b\n")
    write(tmp_path / "b.py", "import a\n")
    analysis = ProjectService().doctor.diagnose(tmp_path)
    assert analysis.category_scores["architecture"] < 100
    assert not analysis.failed_analyzers
