from pathlib import Path

from src.core.base_analyzer import BaseAnalyzer
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
