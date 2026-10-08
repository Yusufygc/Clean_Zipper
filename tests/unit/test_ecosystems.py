import json
from pathlib import Path

from src.analyzers.dead_weight_analyzer import DeadWeightAnalyzer
from src.core.project_index import ProjectIndex
from src.languages.ecosystems import GoEcosystem, NpmEcosystem, PythonEcosystem, RustEcosystem
from src.models.analysis_models import Severity


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def unused(tmp_path):
    results = DeadWeightAnalyzer().analyze(ProjectIndex.build(tmp_path))
    return sorted((r.metadata["ecosystem"], r.title.split(": ", 1)[1]) for r in results if r.severity == Severity.MEDIUM)


# ---- ayrıştırıcılar -------------------------------------------------------------------

def test_python_requirements_parsing():
    text = "# yorum\nrequests==2.0  # satır sonu\nflask[async]>=2 ; python_version>'3.8'\n-r other.txt\n--index-url https://x\ngit+https://github.com/a/b.git\n\nPyYAML\npytest>=7\n"
    parsed = PythonEcosystem().parse(text)
    assert [(d.name, d.dev) for d in parsed.dependencies] == [
        ("requests", False), ("flask", False), ("PyYAML", False), ("pytest", True)]


def test_npm_parsing_ignores_dev_dependencies_and_types():
    pkg = {"dependencies": {"react": "^18", "@types/node": "^20", "@scope/pkg": "1"},
           "devDependencies": {"typescript": "5"}, "scripts": {"clean": "rimraf dist"}}
    parsed = NpmEcosystem().parse(json.dumps(pkg))
    assert [(d.name, d.dev) for d in parsed.dependencies] == [("react", False), ("@types/node", True), ("@scope/pkg", False)]
    assert "rimraf" in parsed.usage_text


def test_go_mod_parsing_block_single_and_indirect():
    text = ("module example.com/app\n\ngo 1.21\n\nrequire (\n\tgithub.com/a/b v1.0.0\n"
            "\tgithub.com/c/d v2.0.0 // indirect\n)\nrequire github.com/e/f v0.1.0\n")
    assert [d.name for d in GoEcosystem().parse(text).dependencies] == ["github.com/a/b", "github.com/e/f"]


def test_cargo_parsing_sections_tables_and_dev():
    text = ('[package]\nname = "app"\n\n[dependencies]\nserde = { version = "1", features = ["derive"] }\n'
            'serde_json = "1"  # yorum\nlog.workspace = true\n\n[dependencies.rand]\nversion = "0.8"\n\n'
            '[dev-dependencies]\ncriterion = "0.5"\n\n[build-dependencies]\ncc = "1"\n\n'
            "[target.'cfg(windows)'.dependencies]\nwinapi = \"0.3\"\n")
    assert [d.name for d in RustEcosystem().parse(text).dependencies] == ["serde", "serde_json", "log", "rand", "winapi"]


# ---- analizör -----------------------------------------------------------------------------

def test_python_behaviour_is_preserved(tmp_path):
    write(tmp_path / "requirements.txt", "pathspec>=0.11\nnumpy==1.0\nPillow\npytest\npyinstaller\n")
    write(tmp_path / "app.py", "import pathspec\nfrom PIL import Image\n")
    assert unused(tmp_path) == [("python", "numpy")]            # araçlar (pytest, pyinstaller) raporlanmaz


def test_python_hyphen_and_underscore_names(tmp_path):
    write(tmp_path / "requirements.txt", "my-lib\nother-lib\n")
    write(tmp_path / "app.py", "import my_lib.sub\n")
    assert unused(tmp_path) == [("python", "other-lib")]


def test_npm_unused_scoped_subpath_and_scripts(tmp_path):
    pkg = {"dependencies": {"react": "1", "lodash": "1", "@scope/ui": "1", "rimraf": "1", "left-pad": "1", "@types/react": "1"},
           "devDependencies": {"eslint": "1"}, "scripts": {"clean": "rimraf dist"}}
    write(tmp_path / "package.json", json.dumps(pkg))
    write(tmp_path / "src" / "a.tsx", "import React from 'react';\nimport {x} from '@scope/ui/button';\nimport 'lodash/fp';\n")
    assert unused(tmp_path) == [("npm", "left-pad")]


def test_npm_require_and_dynamic_import_count_as_usage(tmp_path):
    write(tmp_path / "package.json", json.dumps({"dependencies": {"a": "1", "b": "1", "c": "1"}}))
    write(tmp_path / "x.js", "const a = require('a');\nconst b = await import('b');\n")
    assert unused(tmp_path) == [("npm", "c")]


def test_npm_monorepo_scope_is_manifest_directory(tmp_path):
    write(tmp_path / "packages" / "web" / "package.json", json.dumps({"dependencies": {"react": "1", "vue": "1"}}))
    write(tmp_path / "packages" / "web" / "src" / "a.js", "import 'react';\n")
    write(tmp_path / "packages" / "api" / "src" / "b.js", "import 'vue';\n")      # başka paketin kaynağı sayılmaz
    assert unused(tmp_path) == [("npm", "vue")]


def test_go_module_prefix_usage(tmp_path):
    write(tmp_path / "go.mod", "module x\n\nrequire (\n\tgithub.com/a/b v1.0.0\n\tgithub.com/c/d v1.0.0\n\tgithub.com/z/ind v1.0.0 // indirect\n)\n")
    write(tmp_path / "main.go", 'package main\n\nimport (\n\t"fmt"\n\t"github.com/a/b/sub"\n)\n')
    assert unused(tmp_path) == [("go", "github.com/c/d")]


def test_rust_use_and_fully_qualified_usage(tmp_path):
    write(tmp_path / "Cargo.toml", '[dependencies]\nserde = "1"\nserde_json = "1"\nrand = "0.8"\nunused-crate = "1"\n[dev-dependencies]\ncriterion = "1"\n')
    write(tmp_path / "src" / "main.rs",
          "use serde::Serialize;\nfn main() {\n    let v = serde_json::json!({});\n    extern crate rand;\n}\n")
    assert unused(tmp_path) == [("cargo", "unused-crate")]


def test_missing_requirements_notice_only_for_python_projects_without_any_manifest(tmp_path):
    def notices(root):
        return [r for r in DeadWeightAnalyzer().analyze(ProjectIndex.build(root)) if r.severity == Severity.INFO]

    java = tmp_path / "java"
    write(java / "A.java", "class A {}\n")
    assert notices(java) == []                                      # Java projesinde anlamsız

    py = tmp_path / "py"
    write(py / "app.py", "import os\n")
    assert len(notices(py)) == 1

    modern = tmp_path / "modern"
    write(modern / "app.py", "import os\n")
    write(modern / "pyproject.toml", "[project]\nname='x'\n")
    assert notices(modern) == []                                    # başka bir Python manifesti yeterli


def test_broken_manifest_is_skipped_not_fatal(tmp_path):
    write(tmp_path / "package.json", "{ bozuk json")
    write(tmp_path / "go.mod", "")
    assert unused(tmp_path) == []


def test_finding_points_to_manifest_and_names_it(tmp_path):
    write(tmp_path / "web" / "package.json", json.dumps({"dependencies": {"left-pad": "1"}}))
    write(tmp_path / "web" / "a.js", "x = 1;\n")
    result = [r for r in DeadWeightAnalyzer().analyze(ProjectIndex.build(tmp_path)) if r.severity == Severity.MEDIUM][0]
    assert result.file_path.name == "package.json" and "package.json" in result.description
