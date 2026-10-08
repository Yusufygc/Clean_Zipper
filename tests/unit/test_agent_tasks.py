import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.core.errors import GitCleanError, ProjectNotSelectedError
from src.services import agent_guidance as guide
from src.services.agent_tasks import build_items, plan_tasks
from src.services.project_service import ProjectService

SECRET = "hunter2hunter2xyz"
APP = """import os
import json
from datetime import datetime


def run(value):
    try:
        result = eval(value)
    except:
        result = None
    unused = 1
    return datetime.now(), result
"""


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "proj"
    write(root / "app.py", APP)
    write(root / "config.py", f"PASSWORD = '{SECRET}'\n")
    write(root / "requirements.txt", "requests\npytest==7.0\n")
    return root


def service_for(root: Path) -> ProjectService:
    service = ProjectService()
    service.set_project(root)
    return service


def items_of(root: Path):
    return build_items(service_for(root).doctor.diagnose(root.resolve()))


def by_rule(items):
    result = {}
    for item in items:
        result.setdefault(item.rule, []).append(item)
    return result


# ---- öğeler ve dalgalar --------------------------------------------------------------------------------------------

def test_findings_become_items_in_the_planned_waves(project):
    found = by_rule(items_of(project))
    assert {i.wave for i in found["hardcoded-secret"]} == {0}
    assert {i.wave for i in found["py-eval"]} == {1}
    assert {i.wave for i in found["bare-except"]} == {2}
    assert {found[r][0].wave for r in ("unused-import", "unused-variable", "naive-datetime")} == {3}
    assert found["unpinned-dependencies"][0].wave == 4


def test_multi_entry_findings_expand_to_one_item_per_entry(project):
    found = by_rule(items_of(project))
    assert sorted(i.message.split("'")[1] for i in found["unused-import"]) == ["json", "os"]
    assert [i.line for i in sorted(found["unused-import"], key=lambda i: i.line)] == [1, 2]
    assert len(found["unused-variable"]) == 1 and "unused" in found["unused-variable"][0].message


def test_info_findings_and_notes_are_not_tasks(project):
    rules = {i.rule for i in items_of(project)}
    assert not rules & guide.SKIPPED_RULES
    assert "test-summary" not in rules and "hygiene-summary" not in rules


def test_every_rule_with_a_wave_has_guidance_and_known_wave():
    assert set(guide.RULE_WAVE) <= set(guide.GUIDANCE)
    assert set(guide.RULE_WAVE.values()) | set(guide.CATEGORY_WAVE.values()) <= set(guide.WAVES)
    assert guide.WAVES[guide.HUMAN_WAVE][1] == "insan"


def test_sast_rules_use_their_own_advice_in_the_security_wave():
    from src.core.security_rules import load_security_rules
    rules = load_security_rules()
    assert rules
    for rule in rules:
        assert guide.wave_of(rule.id, "security") == 1
        assert guide.guidance_for(rule.id, rule.advice).how == rule.advice


def test_unknown_rule_falls_back_to_category_wave_and_default_guidance():
    assert guide.wave_of("yeni-kural", "testing") == 5 and guide.wave_of("yeni-kural", "bilinmeyen") == guide.DEFAULT_WAVE
    assert guide.guidance_for("yeni-kural") is guide.DEFAULT


# ---- parmak izi ------------------------------------------------------------------------------------------------------

def test_fingerprints_are_unique_and_stable_across_runs(project):
    first = items_of(project)
    again = items_of(project)
    assert len({i.fingerprint for i in first}) == len(first)
    assert {i.fingerprint for i in first} == {i.fingerprint for i in again}


def test_fingerprints_survive_line_shifts(project):
    def per_rule(items):
        result = {}
        for item in sorted((i for i in items if i.path == "app.py"), key=lambda i: i.line or 0):
            result.setdefault(item.rule, []).append(item.fingerprint)
        return result

    before = per_rule(items_of(project))
    write(project / "app.py", '"""Üstte yeni bir açıklama."""' + "\n\n\n" + APP)
    after_items = items_of(project)
    assert per_rule(after_items) == before and len(before) >= 5
    assert min(i.line for i in after_items if i.rule == "unused-import") == 4              # satırlar gerçekten kaydı


def test_identical_keys_get_distinct_fingerprints(project):
    write(project / "dup.py", "import os\nimport os\nx = 1\n")
    items = [i for i in items_of(project) if i.path == "dup.py"]
    assert len(items) == len({i.fingerprint for i in items})


# ---- planlama ------------------------------------------------------------------------------------------------------------

def test_tasks_are_ordered_by_wave_and_numbered_per_wave(project):
    tasks = plan_tasks(items_of(project), 15)
    waves = [t.wave for t in tasks]
    assert waves == sorted(waves) and tasks[0].wave == 0
    ids = [t.id for t in tasks if t.wave == 3]
    assert ids == [f"W3-{n:03d}" for n in range(1, len(ids) + 1)]
    assert len({t.id for t in tasks}) == len(tasks)


def test_batches_respect_the_size_limit_and_keep_files_together(tmp_path):
    root = tmp_path / "many"
    for n in range(8):
        write(root / f"m{n}.py", "import os\nimport sys\nimport re\nx = 1\n")          # dosya başına 3 öğe
    tasks = [t for t in plan_tasks(items_of(root), 7) if t.rule == "unused-import"]
    assert [len(t.items) for t in tasks] == [6, 6, 6, 6]                              # 2 dosya = 6 öğe, 3. dosya sığmaz
    for task in tasks:
        paths = [i.path for i in task.items]
        assert all(paths.count(p) == 3 for p in set(paths))                           # dosya bölünmedi


def test_a_single_file_larger_than_the_limit_is_split(tmp_path):
    root = tmp_path / "big"
    write(root / "a.py", "".join(f"import mod{n}\n" for n in range(10)) + "x = 1\n")
    tasks = [t for t in plan_tasks(items_of(root), 4) if t.rule == "unused-import"]
    assert [len(t.items) for t in tasks] == [4, 4, 2] and sum(len(t.items) for t in tasks) == 10


def test_invalid_batch_size_is_rejected(project):
    with pytest.raises(ValueError):
        plan_tasks(items_of(project), 0)


# ---- dışa aktarma ----------------------------------------------------------------------------------------------------------

def export(project: Path, tmp_path: Path, batch: int = 15):
    out = tmp_path / "agent-tasks"
    return service_for(project).export_agent_tasks(out, batch), out


def test_export_writes_json_markdown_readme_and_verify_script(project, tmp_path):
    summary, out = export(project, tmp_path)
    assert (out / "README.md").is_file() and (out / "verify.py").is_file() and (out / "tasks.json").is_file()
    data = json.loads((out / "tasks.json").read_text(encoding="utf-8"))
    assert data["version"] == 1 and len(data["tasks"]) == summary["tasks"]
    assert sum(len(t["items"]) for t in data["tasks"]) == summary["items"]
    for task in data["tasks"]:
        assert (out / task["file"]).is_file()
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "İnsan aksiyonu bekleyenler" in readme and "W0-" in readme and "verify.py" in readme


def test_task_file_has_instructions_constraints_and_evidence(project, tmp_path):
    _, out = export(project, tmp_path)
    task = next((out / "tasks").glob("W3-*unused-import*.md")).read_text(encoding="utf-8")
    for heading in ("## Ne yapılacak", "## Neleri yapma", "## Genel kısıtlar", "## Öğeler", "## Doğrulama", "## Commit önerisi"):
        assert heading in task
    assert "- [ ] `app.py:1`" in task and "1: import os" in task and "wave: 3" in task


def test_secret_values_never_reach_any_output_file(project, tmp_path):
    _, out = export(project, tmp_path)
    for path in out.rglob("*"):
        if path.is_file():
            assert SECRET not in path.read_text(encoding="utf-8"), path
    human = next((out / "tasks").glob("W0-*hardcoded-secret*.md")).read_text(encoding="utf-8")
    assert "İNSAN AKSİYONU" in human and "PASSWORD" not in human


def test_approximate_items_are_flagged_for_verification(tmp_path):
    root = tmp_path / "js"
    write(root / "a.js", "const x = eval(input);\n")
    _, out = export(root, tmp_path)
    task = next((out / "tasks").glob("W1-*.md")).read_text(encoding="utf-8")
    assert "yaklaşık" in task


def test_rerun_replaces_old_generated_tasks_but_keeps_other_files(project, tmp_path):
    summary, out = export(project, tmp_path)
    write(out / "tasks" / "W9-999-eski.md", "eski")
    write(out / "notlarim.md", "benim notum")
    write(out / "tasks" / "benim.txt", "dokunma")
    export(project, tmp_path)
    assert not (out / "tasks" / "W9-999-eski.md").exists()
    assert (out / "notlarim.md").read_text(encoding="utf-8") == "benim notum" and (out / "tasks" / "benim.txt").is_file()
    assert len(list((out / "tasks").glob("W*.md"))) == summary["tasks"]


def test_hostile_text_cannot_break_the_task_file(tmp_path):
    root = tmp_path / "evil"
    write(root / "a```b.py", "import os\n")
    _, out = export(root, tmp_path)
    task = next((out / "tasks").glob("W3-*.md")).read_text(encoding="utf-8")
    assert task.count("\n```") % 2 == 0 and "a```b.py" in task


def test_export_requires_a_project(tmp_path):
    with pytest.raises(ProjectNotSelectedError):
        ProjectService().export_agent_tasks(tmp_path / "x")
    with pytest.raises(ProjectNotSelectedError):
        ProjectService().verify_agent_tasks(tmp_path / "x")


# ---- doğrulama ---------------------------------------------------------------------------------------------------------------

def task_status(result, rule):
    return next(t for t in result["tasks"] if t["rule"] == rule)


def test_verify_reports_open_then_closed_after_fixing(project, tmp_path):
    summary, out = export(project, tmp_path)
    service = service_for(project)
    first = service.verify_agent_tasks(out)
    assert first["totals"]["closed"] == 0 and first["totals"]["open"] == summary["items"] and first["new_count"] == 0
    write(project / "app.py", APP.replace("import os\nimport json\n", ""))                 # iki import'u sil
    second = service.verify_agent_tasks(out)
    assert task_status(second, "unused-import")["closed"] == 2 and task_status(second, "unused-import")["open"] == 0
    assert task_status(second, "bare-except")["open"] == 1 and second["new_count"] == 0


def test_verify_lists_new_findings_introduced_by_the_fix(project, tmp_path):
    _, out = export(project, tmp_path)
    write(project / "extra.py", "import re\n")
    result = service_for(project).verify_agent_tasks(out)
    assert result["new_count"] == 1 and result["new_findings"][0]["rule"] == "unused-import"
    assert result["new_findings"][0]["path"] == "extra.py"


def test_verify_can_be_limited_to_given_task_ids(project, tmp_path):
    _, out = export(project, tmp_path)
    ids = [t["id"] for t in json.loads((out / "tasks.json").read_text(encoding="utf-8"))["tasks"]]
    result = service_for(project).verify_agent_tasks(out, only=ids[:1])
    assert [t["id"] for t in result["tasks"]] == ids[:1]


def test_verify_marks_reduced_when_only_some_occurrences_are_fixed(tmp_path):
    root = tmp_path / "r"
    write(root / "a.py", "def f():\n    try:\n        pass\n    except:\n        pass\n    try:\n        pass\n    except:\n        pass\n")
    _, out = export(root, tmp_path)
    write(root / "a.py", "def f():\n    try:\n        pass\n    except:\n        pass\n    try:\n        pass\n    except OSError:\n        pass\n")
    result = service_for(root).verify_agent_tasks(out)
    assert task_status(result, "bare-except")["reduced"] == 1 and task_status(result, "bare-except")["open"] == 0


def test_verify_warns_when_tasks_belong_to_another_project(project, tmp_path):
    _, out = export(project, tmp_path)
    other = tmp_path / "other"
    write(other / "x.py", "x = 1\n")
    assert "başka bir proje" in service_for(other).verify_agent_tasks(out)["warning"]


def test_verify_rejects_missing_or_foreign_task_files(project, tmp_path):
    service = service_for(project)
    with pytest.raises(GitCleanError):
        service.verify_agent_tasks(tmp_path / "yok")
    broken = tmp_path / "broken"
    write(broken / "tasks.json", "{ bozuk")
    with pytest.raises(GitCleanError):
        service.verify_agent_tasks(broken)
    future = tmp_path / "future"
    write(future / "tasks.json", json.dumps({"version": 99, "tasks": []}))
    with pytest.raises(GitCleanError):
        service.verify_agent_tasks(future)


def test_generated_verify_script_runs_end_to_end(project, tmp_path):
    summary, out = export(project, tmp_path)
    write(project / "app.py", APP.replace("import os\nimport json\n", ""))
    done = subprocess.run([sys.executable, str(out / "verify.py")], capture_output=True, timeout=120)
    assert done.returncode == 0, done.stderr.decode("utf-8", "replace")
    result = json.loads(done.stdout.decode("utf-8"))
    assert result["totals"]["closed"] == 2 and result["totals"]["total"] == summary["items"]
