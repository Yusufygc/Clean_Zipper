from pathlib import Path

from src.core.base_analyzer import BaseAnalyzer
from src.analyzers.dead_code_analyzer import DeadCodeAnalyzer
from src.analyzers.duplicate_finder import DuplicateFinder
from src.analyzers.empty_folder_finder import EmptyFolderFinder
from src.analyzers.size_analyzer import SizeAnalyzer
from src.doctors.project_doctor import ProjectDoctor
from src.models.analysis_models import Severity


class BoomAnalyzer(BaseAnalyzer):
    category = "security"

    @property
    def name(self):
        return "Boom"

    def analyze(self, project_path):
        raise RuntimeError("patladı")


def make_project(root: Path):
    (root / "a").mkdir()
    (root / "b").mkdir()
    (root / "empty").mkdir()
    payload = "x" * 2048
    (root / "a" / "one.txt").write_text(payload)
    (root / "b" / "two.txt").write_text(payload)
    return root


def doctor(*analyzers):
    d = ProjectDoctor()
    for a in analyzers:
        d.register_analyzer(a)
    return d


def test_duplicates_and_empty_dirs_are_populated_and_penalised(tmp_path):
    make_project(tmp_path)
    analysis = doctor(DuplicateFinder(), EmptyFolderFinder()).diagnose(tmp_path)

    assert [p.name for p in analysis.empty_dirs] == ["empty"]
    assert len(analysis.duplicate_files) == 1
    assert {p.name for p in analysis.duplicate_files[0]} == {"one.txt", "two.txt"}
    assert analysis.category_scores["duplicate"] < 100
    assert analysis.category_scores["structure"] < 100
    assert analysis.health_score < 100
    assert analysis.potential_savings_bytes == 2048


def test_total_size_finding_is_not_counted_as_savings(tmp_path):
    make_project(tmp_path)
    analysis = doctor(SizeAnalyzer()).diagnose(tmp_path)
    assert analysis.potential_savings_bytes == 0
    assert any(f.metadata.get("kind") == "total_size" for f in analysis.all_findings)


def test_crashing_analyzer_is_recorded_and_excluded_from_score(tmp_path):
    make_project(tmp_path)
    analysis = doctor(BoomAnalyzer(), EmptyFolderFinder()).diagnose(tmp_path)
    assert analysis.failed_analyzers == ["Boom"]
    assert "security" not in analysis.category_scores
    assert "structure" in analysis.category_scores


def test_all_analyzers_crashing_gives_zero_not_a_clean_score(tmp_path):
    analysis = doctor(BoomAnalyzer()).diagnose(tmp_path)
    assert analysis.health_score == 0
    assert analysis.failed_analyzers == ["Boom"]


def test_quick_scan_exposes_category_scores_and_failures(tmp_path):
    make_project(tmp_path)
    scan = doctor(BoomAnalyzer(), EmptyFolderFinder()).quick_scan(tmp_path)
    assert scan["failed_analyzers"] == ["Boom"]
    assert "structure" in scan["category_scores"]
    assert scan["issues_count"] == 0  # LOW boş klasör bulgusu sorun sayılmaz


class SkippedAnalyzer(BaseAnalyzer):
    category = "security"
    calls = 0

    @property
    def name(self):
        return "Skipped"

    def can_analyze(self, index):
        return False

    def analyze(self, index):
        SkippedAnalyzer.calls += 1
        return []


def test_stats_come_from_index_and_exclude_venv_and_git(tmp_path):
    make_project(tmp_path)
    (tmp_path / "venv").mkdir()
    (tmp_path / "venv" / "big.bin").write_bytes(b"0" * 100_000)
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_text("ref")
    analysis = doctor(EmptyFolderFinder()).diagnose(tmp_path)
    assert analysis.total_files == 2
    assert analysis.total_size == 4096
    assert analysis.file_type_distribution == {".txt": 2}
    assert analysis.file_type_sizes == {".txt": 4096}


def test_can_analyze_false_skips_analyzer_without_failing_or_scoring(tmp_path):
    make_project(tmp_path)
    SkippedAnalyzer.calls = 0
    analysis = doctor(SkippedAnalyzer(), EmptyFolderFinder()).diagnose(tmp_path)
    assert SkippedAnalyzer.calls == 0
    assert analysis.failed_analyzers == []
    assert "security" not in analysis.category_scores


def test_progress_is_reported_in_order_and_stays_within_bounds(tmp_path):
    make_project(tmp_path)
    seen = []
    doctor(DuplicateFinder(), EmptyFolderFinder()).diagnose(tmp_path, progress=lambda p, t: seen.append((p, t)))
    percents = [p for p, _ in seen]
    assert percents == sorted(percents) and 0 <= percents[0] and percents[-1] < 100
    assert any("Cift Dosya Bulucu" in t for _, t in seen)


def test_project_service_registers_all_builtin_analyzers_without_ui(tmp_path):
    from src.services.project_service import ProjectService
    service = ProjectService()
    assert len(service.doctor.get_registered_analyzers()) == 18
    assert len(ProjectService(disabled_analyzers=["SizeAnalyzer"]).doctor.get_registered_analyzers()) == 17
    make_project(tmp_path)
    service.set_project(tmp_path)
    seen = []
    result = service.analyze_project(progress=lambda p, t: seen.append(p))
    assert result["total_files"] == 2 and seen


def test_gitignore_is_respected_and_reported_by_service(tmp_path):
    from src.services.project_service import ProjectService
    (tmp_path / ".gitignore").write_text("generated/\n*.log\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "run.log").write_text("log", encoding="utf-8")
    (tmp_path / "generated").mkdir()
    (tmp_path / "generated" / "big.py").write_text("y = 2\n" * 50, encoding="utf-8")

    with_ignore = ProjectService()
    with_ignore.set_project(tmp_path)
    result = with_ignore.analyze_project()
    assert result["gitignore_applied"] is True and result["ignored_by_gitignore"] == {"files": 1, "dirs": 1}
    assert result["language_stats"]["python"]["files"] == 1

    without = ProjectService(respect_gitignore=False)
    without.set_project(tmp_path)
    result = without.analyze_project()
    assert result["gitignore_applied"] is False and result["language_stats"]["python"]["files"] == 2


def test_disabled_rules_filter_findings_of_every_analyzer_and_the_score(tmp_path):
    (tmp_path / "a.py").write_text("import os\nimport sys\nx = 1\n", encoding="utf-8")
    full = ProjectDoctor(analyzers=[DeadCodeAnalyzer()]).diagnose(tmp_path)
    muted = ProjectDoctor(analyzers=[DeadCodeAnalyzer()], disabled_rules=["unused-import"]).diagnose(tmp_path)
    assert any(f.metadata.get("rule") == "unused-import" for f in full.all_findings)
    assert not any(f.metadata.get("rule") == "unused-import" for f in muted.all_findings)
    assert muted.category_scores["deadcode"] > full.category_scores["deadcode"]
