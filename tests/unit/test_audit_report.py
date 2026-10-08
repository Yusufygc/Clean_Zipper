import re
from datetime import datetime
from pathlib import Path

import pytest

from src.core.errors import ProjectNotSelectedError
from src.models.analysis_models import AnalysisResult, HealthStatus, ProjectAnalysis, Severity
from src.services import audit_catalog as catalog
from src.services.audit_report_service import DETAIL_LIMIT, DETAIL_PER_RULE, TABLE_LIMIT, AuditReportService
from src.services.project_service import ProjectService
from src.services.report_service import ReportService

SECRET = "AKIAIOSFODNN7EXAMPLE"


def make_analysis(project=Path("proj"), **kwargs):
    return ProjectAnalysis(project_path=project, analysis_time=datetime(2026, 10, 8, 12, 0), health_score=72.4,
                           health_status=HealthStatus.AVERAGE, **kwargs)


def finding(severity=Severity.MEDIUM, rule="function-metrics", category="complexity", title="Karmaşık Fonksiyon: f()",
            path=None, **metadata):
    metadata.setdefault("rule", rule)
    return AnalysisResult(analyzer_name="t", category=category, severity=severity, title=title,
                          description=f"{title} açıklaması", file_path=path, recommendation="Düzeltin.", metadata=metadata)


def add(analysis, *findings):
    for item in findings:
        bucket = analysis.issues if item.severity.value >= Severity.HIGH.value else \
            analysis.warnings if item.severity == Severity.MEDIUM else analysis.suggestions
        bucket.append(item)
    return analysis


def render(analysis):
    return AuditReportService().generate_report(analysis)


def section(report, letter):
    match = re.search(rf"^## {letter}\. .*?(?=^## |\Z)", report, re.S | re.M)
    assert match, f"{letter} bölümü yok"
    return match.group(0)


# ---- yapı -----------------------------------------------------------------------------------------------

def test_report_has_all_v2_sections_in_order():
    report = render(add(make_analysis(), finding()))
    headings = re.findall(r"^## ([A-F])\. ", report, re.M)
    assert headings == list("ABCDEF")
    assert report.startswith("# Denetim Raporu: proj") and "72/100 (B)" in report


def test_empty_analysis_still_renders_every_section():
    report = render(make_analysis())
    assert "Öncelikli bulgu yok." in section(report, "A") and "Ayrıntılı bulgu yok." in section(report, "D")
    assert "Belirgin bir olumlu tespit yok." in section(report, "B")
    assert "Öncelikli bulgu çıkmadı" in section(report, "F") and "Bu dilimde iş yok." in section(report, "E")


def test_summary_table_columns_and_counts():
    analysis = add(make_analysis(), finding(Severity.HIGH), finding(Severity.HIGH, path=Path("proj/a.py")),
                   finding(Severity.LOW, rule="magic-numbers", category="deadcode", title="Sihirli Sayılar: a.py"))
    summary = section(render(analysis), "A")
    assert "| # | Bulgu | Öncelik | Boyut | Efor | Etki |" in summary
    assert "🟠 YÜKSEK 2" in summary and "🟢 DÜŞÜK 1" in summary and "🔴 KRİTİK 0" in summary
    assert "| 1 | Karmaşık / uzun işlevler (2) | 🟠 YÜKSEK | Kod Kalitesi |" in summary


def test_same_rule_with_different_priorities_is_split_into_separate_groups():
    analysis = add(make_analysis(), finding(Severity.HIGH), finding(Severity.MEDIUM), finding(Severity.MEDIUM))
    rows = [line for line in section(render(analysis), "A").splitlines() if line.startswith("| ") and "işlevler" in line]
    assert len(rows) == 2 and "(1) | 🟠 YÜKSEK" in rows[0] and "(2) | 🟡 ORTA" in rows[1]


def test_info_findings_are_not_table_rows_or_details():
    analysis = add(make_analysis(), finding(Severity.INFO, rule="hotspot", category="git"))
    report = render(analysis)
    assert "Öncelikli bulgu yok." in section(report, "A") and "Ayrıntılı bulgu yok." in section(report, "D")


def test_table_is_capped_with_a_note():
    analysis = make_analysis()
    add(analysis, *[finding(rule=f"r{i}", title=f"Başlık{i}: x") for i in range(TABLE_LIMIT + 4)])
    summary = section(render(analysis), "A")
    assert len([line for line in summary.splitlines() if re.match(r"\| \d+ \|", line)]) == TABLE_LIMIT
    assert "4 bulgu grubu daha var" in summary


def test_most_severe_group_comes_first():
    analysis = add(make_analysis(), finding(Severity.LOW, rule="a"), finding(Severity.CRITICAL, rule="b", title="Kritik: x"))
    rows = [line for line in section(render(analysis), "A").splitlines() if re.match(r"\| \d+ \|", line)]
    assert "🔴 KRİTİK" in rows[0] and "🟢 DÜŞÜK" in rows[1]


# ---- Markdown güvenliği --------------------------------------------------------------------------------------

def test_pipes_and_newlines_cannot_break_table_rows():
    analysis = add(make_analysis(), finding(rule="", title="Kötü | başlık\nikinci satır: x"))
    rows = [line for line in section(render(analysis), "A").splitlines() if re.match(r"\| \d+ \|", line)]
    assert len(rows) == 1 and "\n" not in rows[0] and "Kötü \\| başlık ikinci satır" in rows[0]


def test_evidence_with_backticks_gets_a_longer_fence(tmp_path):
    source = tmp_path / "a.py"
    source.write_text("x = '''```'''\ny = 1\n", encoding="utf-8")
    analysis = add(make_analysis(tmp_path), finding(path=source, line=1))
    detail = section(render(analysis), "D")
    assert "````\n1: x = '''```'''" in detail


# ---- kanıt ve sır güvenliği ------------------------------------------------------------------------------------

def test_evidence_shows_numbered_lines_from_the_finding(tmp_path):
    source = tmp_path / "pkg" / "mod.py"
    source.parent.mkdir()
    source.write_text("a = 1\nb = 2\nc = 3\nd = 4\n", encoding="utf-8")
    detail = section(render(add(make_analysis(tmp_path), finding(path=source, start_line=2))), "D")
    assert "`pkg/mod.py:2`" in detail and "2: b = 2\n3: c = 3\n4: d = 4" in detail and "1: a = 1" not in detail


@pytest.mark.parametrize("rule,filename", [("hardcoded-secret", "config.py"), ("provider-secret", "keys.py"),
                                           ("other", ".env"), ("other", "server.pem"), ("other", "id_rsa")])
def test_secret_bearing_findings_never_print_source_lines(tmp_path, rule, filename):
    source = tmp_path / filename
    source.write_text(f"TOKEN = '{SECRET}'\n", encoding="utf-8")
    analysis = add(make_analysis(tmp_path), finding(Severity.HIGH, rule=rule, category="security", path=source, line=1))
    report = render(analysis)
    assert SECRET not in report and "(kod parçası gösterilmiyor)" in section(report, "D")


def test_sensitive_file_finding_kind_is_never_quoted(tmp_path):
    source = tmp_path / "settings.txt"
    source.write_text(f"{SECRET}\n", encoding="utf-8")
    analysis = add(make_analysis(tmp_path), finding(Severity.CRITICAL, rule="", category="security", path=source, line=1,
                                                    kind="sensitive_file"))
    assert SECRET not in render(analysis)


def test_missing_oversized_or_directory_paths_give_no_evidence(tmp_path, monkeypatch):
    big = tmp_path / "big.py"
    big.write_text("x = 1\n", encoding="utf-8")
    monkeypatch.setattr("src.services.audit_evidence.EVIDENCE_MAX_BYTES", 2)
    analysis = add(make_analysis(tmp_path), finding(path=big, line=1), finding(rule="b", path=tmp_path / "gone.py", line=1),
                   finding(rule="c", path=tmp_path, line=1))
    assert section(render(analysis), "D").count("(kod parçası gösterilmiyor)") == 3


def test_locations_are_relative_to_the_project(tmp_path):
    analysis = add(make_analysis(tmp_path), finding(path=tmp_path / "src" / "a.py", line=7),
                   finding(rule="b", path=Path("D:/başka/x.py")))
    detail = section(render(analysis), "D")
    assert "`src/a.py:7`" in detail and "`D:/başka/x.py`" in detail


# ---- ayrıntı sınırları -----------------------------------------------------------------------------------------

def test_detail_section_limits_examples_per_rule_and_total():
    analysis = make_analysis()
    add(analysis, *[finding(title=f"Aynı kural {i}: x") for i in range(10)])
    assert section(render(analysis), "D").count("### D") == DETAIL_PER_RULE
    many = add(make_analysis(), *[finding(rule=f"r{i}", title=f"T{i}: x") for i in range(40)])
    assert section(render(many), "D").count("### D") == DETAIL_LIMIT


def test_detail_block_has_every_v2_field():
    detail = section(render(add(make_analysis(), finding(Severity.HIGH, rule="import-cycle", category="architecture",
                                                         title="Döngü: a"))), "D")
    for label in ("Dosya / Konum", "Kategori", "Sorun", "Etki", "Kanıt", "Çözüm", "Efor", "Bağımlılık"):
        assert f"**{label}:**" in detail
    assert "Mimari" in detail and "L (1-3 gün)" in detail and "Ortak kodu ayıracak" in detail


# ---- iyi pratikler ---------------------------------------------------------------------------------------------

def test_good_practices_come_from_hygiene_tests_and_absent_problems():
    analysis = add(make_analysis(category_scores={"security": 100, "architecture": 100, "hygiene": 90}),
                   finding(Severity.INFO, rule="hygiene-summary", category="hygiene", present=["readme", "ci", "bilinmeyen"]),
                   finding(Severity.INFO, rule="test-summary", category="testing", test_functions=12, test_files=3, ratio=0.5))
    good = section(render(analysis), "B")
    for text in ("README var", "CI yapılandırması var", "Yüksek öncelikli güvenlik bulgusu yok", "Döngüsel bağımlılık yok",
                 "12 test işlevi, 3 test dosyası (test/kaynak satır oranı 0.50)"):
        assert text in good
    assert "bilinmeyen" not in good and "kod klonu" not in good               # 'duplicate' analizörü çalışmadı: iddia edilmez


def test_absence_is_not_praised_when_the_problem_exists_or_analyzer_did_not_run():
    analysis = add(make_analysis(category_scores={"architecture": 40, "security": 50}),
                   finding(Severity.MEDIUM, rule="import-cycle", category="architecture", title="Döngü: a"),
                   finding(Severity.HIGH, rule="py-eval", category="security", title="eval: a.py"))
    good = section(render(analysis), "B")
    assert "Döngüsel" not in good and "güvenlik bulgusu yok" not in good


# ---- incelenmeyenler -------------------------------------------------------------------------------------------

def test_not_reviewed_lists_skips_failures_gitignore_and_scope():
    analysis = make_analysis(skipped_files={"too_large": 3, "weird": 1}, failed_analyzers=["CloneAnalyzer"],
                             gitignore_applied=True, ignored_by_gitignore={"files": 9, "dirs": 2},
                             language_stats={"python": {}, "javascript": {}, "go": {}})
    text = section(render(analysis), "C")
    assert "Çok büyük dosya (2 MB üstü), içerik taranmadı: 3" in text and "weird: 1" in text
    assert "CloneAnalyzer" in text and "9 dosya, 2 klasör" in text
    assert "go, javascript" in text and "CVE" in text and "Git geçmişi" in text


def test_git_gap_note_disappears_when_git_findings_exist():
    analysis = add(make_analysis(), finding(Severity.INFO, rule="hotspot", category="git"))
    assert "Git geçmişi" not in section(render(analysis), "C")


# ---- aksiyon planı ---------------------------------------------------------------------------------------------

def test_action_plan_maps_priorities_to_time_slices():
    analysis = add(make_analysis(), finding(Severity.CRITICAL, rule="a", title="Kritik: x"), finding(Severity.HIGH, rule="b", title="Yüksek: x"),
                   finding(Severity.MEDIUM, rule="c", title="Orta: x"), finding(Severity.LOW, rule="d", title="Hafif: x"))
    plan = section(render(analysis), "E")
    slices = dict(re.findall(r"### (.+?) \(.+?\)\n\n(.*?)(?=\n###|\Z)", plan, re.S))
    assert "Kritik" in slices["24 saat içinde"] and "Yüksek" in slices["Bu hafta"] and "Orta" in slices["Bu ay"]
    assert "Eylem | Beklenen sonuç | Bağımlılık | Risk" in slices["Bu hafta"]
    assert "Hafif" in plan.split("### Fırsat oldukça")[1] and "Hafif" not in slices["Bu ay"]


def test_next_step_asks_about_the_top_group():
    step = section(render(add(make_analysis(), finding(Severity.HIGH))), "F")
    assert "**Karmaşık / uzun işlevler** (1 bulgu)" in step and step.rstrip().endswith("istersiniz?")


# ---- katalog -------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("rule,severity,count,expected", [
    ("unused-import", Severity.LOW, 1, "S"), ("unused-import", Severity.LOW, 4, "M"), ("unused-import", Severity.LOW, 25, "L"),
    ("no-tests", Severity.MEDIUM, 1, "XL"), ("no-tests", Severity.MEDIUM, 99, "XL"), ("bilinmeyen", Severity.LOW, 1, "S"),
    ("bilinmeyen", Severity.HIGH, 1, "M")])
def test_effort_estimate_grows_with_count_and_is_capped(rule, severity, count, expected):
    assert catalog.effort_of(rule, severity, count) == expected


def test_every_catalog_rule_key_is_known_to_the_labels():
    for table in (catalog.RULE_EFFORT, catalog.RULE_IMPACT, catalog.RULE_DEPENDENCY, catalog.RULE_RISK):
        assert set(table) <= set(catalog.RULE_LABELS), set(table) - set(catalog.RULE_LABELS)
    assert set(catalog.RULE_EFFORT.values()) <= set(catalog.EFFORT_STEPS)


# ---- dışa aktarma ve servis ------------------------------------------------------------------------------------

def test_export_writes_utf8_and_reports_failure(tmp_path):
    analysis = add(make_analysis(), finding(title="Türkçe İğŞüç: x"))
    target = tmp_path / "rapor.md"
    assert AuditReportService().export_report(analysis, target) is True
    assert "Türkçe İğŞüç" in target.read_text(encoding="utf-8")
    assert AuditReportService().export_report(analysis, tmp_path / "yok" / "r.md") is False


def test_project_service_exports_audit_report_without_leaking_secrets(tmp_path):
    project = tmp_path / "app"
    project.mkdir()
    (project / "settings.py").write_text(f"AWS_KEY = '{SECRET}'\nresult = eval(input())\n", encoding="utf-8")
    service = ProjectService()
    service.set_project(project)
    output = tmp_path / "audit.md"
    assert service.export_audit_report(output) is True
    report = output.read_text(encoding="utf-8")
    assert SECRET not in report and list(re.findall(r"^## ([A-F])\. ", report, re.M)) == list("ABCDEF")
    assert "settings.py" in report


def test_project_service_requires_a_project_for_the_audit_report(tmp_path):
    with pytest.raises(ProjectNotSelectedError):
        ProjectService().export_audit_report(tmp_path / "x.md")


# ---- HTML rapor: yeni kategoriler ------------------------------------------------------------------------------

def test_html_report_shows_category_scores_lowest_first_and_escaped():
    analysis = make_analysis(category_scores={"testing": 80, "security": 20, "<b>x</b>": 50})
    html = ReportService().generate_report(analysis)
    assert "KATEGORİ PUANLARI" in html and html.index("Güvenlik") < html.index("Test")
    assert "<b>x</b>" not in html and "&lt;b&gt;x&lt;/b&gt;" in html


def test_html_report_omits_category_section_without_scores():
    assert "KATEGORİ PUANLARI" not in ReportService().generate_report(make_analysis())


def test_impact_falls_back_to_the_category_then_to_a_generic_text():
    assert catalog.impact_of("function-metrics", "complexity") == catalog.RULE_IMPACT["function-metrics"]
    assert "güvenlik" in catalog.impact_of("py-eval", "security")
    assert catalog.impact_of("bilinmeyen", "bilinmeyen") == catalog.DEFAULT_IMPACT


def test_minified_files_are_listed_with_a_readable_reason():
    text = section(render(make_analysis(skipped_files={"minified": 2})), "C")
    assert "Minify edilmiş (okunamaz) dosya, yapı analizi atlandı: 2" in text and "minified:" not in text
