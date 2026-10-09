from pathlib import Path

from src.analyzers.code_complexity_analyzer import CodeComplexityAnalyzer
from src.analyzers.dead_weight_analyzer import DeadWeightAnalyzer
from src.analyzers.duplicate_finder import DuplicateFinder
from src.analyzers.empty_folder_finder import EmptyFolderFinder
from src.analyzers.security_analyzer import SecurityLeakAnalyzer
from src.analyzers.size_analyzer import SizeAnalyzer
from src.analyzers.structure_analyzer import StructureAnalyzer
from src.analyzers.type_analyzer import TypeAnalyzer
from src.core.project_index import ProjectIndex
from src.models.analysis_models import Severity


def write(path: Path, content="x", encoding="utf-8"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode(encoding) if isinstance(content, str) else content)
    return path


def titles(results):
    return sorted(r.title for r in results)


# ---- Size / Type / Structure / Empty -----------------------------------

def test_size_analyzer_reports_total_without_reclaimable_and_large_files(tmp_path):
    write(tmp_path / "big.bin", b"a" * 2048)
    write(tmp_path / "small.txt", "hi")
    results = SizeAnalyzer(large_file_threshold_mb=1 / 1024).analyze(ProjectIndex.build(tmp_path))
    total = next(r for r in results if r.metadata["kind"] == "total_size")
    assert total.size_impact is None and total.metadata["total_bytes"] == 2050
    large = [r for r in results if r.metadata["kind"] == "large_file"]
    assert [r.file_path.name for r in large] == ["big.bin"]


def test_type_analyzer_top_five_by_count(tmp_path):
    for ext, n in [(".py", 3), (".txt", 2), (".md", 1), (".js", 1), (".c", 1), (".h", 1)]:
        for i in range(n):
            write(tmp_path / f"f{i}{ext}")
    results = TypeAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert len(results) == 5
    assert results[0].title == "Dosya türü: .py" and results[0].description == "3 adet dosya"


def test_structure_analyzer_flags_only_deeper_than_ten(tmp_path):
    write(tmp_path.joinpath(*["d"] * 10) / "f.txt")
    assert StructureAnalyzer().analyze(ProjectIndex.build(tmp_path)) == []
    write(tmp_path.joinpath(*["d"] * 11) / "f.txt")
    results = StructureAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert titles(results) == ["Derin klasor yapisi: 11 seviye"]


def test_empty_folder_finder(tmp_path):
    (tmp_path / "empty").mkdir()
    write(tmp_path / "full" / "a.txt")
    write(tmp_path / "wrapper" / "venv" / "x.py")
    results = EmptyFolderFinder().analyze(ProjectIndex.build(tmp_path))
    assert titles(results) == ["Boş klasör: empty"]
    assert results[0].metadata["kind"] == "empty_dir"


# ---- Duplicates -------------------------------------------------------------

def test_duplicate_finder_groups_identical_content(tmp_path):
    write(tmp_path / "a" / "one.bin", b"Z" * 2048)
    write(tmp_path / "b" / "two.bin", b"Z" * 2048)
    results = DuplicateFinder().analyze(ProjectIndex.build(tmp_path))
    assert len(results) == 1
    r = results[0]
    assert r.size_impact == 2048 and r.metadata["reclaimable"] is True
    assert [p.name for p in r.metadata["paths"]] == ["one.bin", "two.bin"]
    assert r.file_path.name == "one.bin"


def test_duplicate_finder_ignores_same_size_different_content(tmp_path):
    write(tmp_path / "one.bin", b"A" * 2048)
    write(tmp_path / "two.bin", b"B" * 2048)
    assert DuplicateFinder().analyze(ProjectIndex.build(tmp_path)) == []


def test_duplicate_finder_separates_files_that_differ_after_first_64kb(tmp_path):
    head = b"H" * (64 * 1024)
    write(tmp_path / "x1.bin", head + b"tail-1")
    write(tmp_path / "x2.bin", head + b"tail-2")
    write(tmp_path / "x3.bin", head + b"tail-1")
    results = DuplicateFinder().analyze(ProjectIndex.build(tmp_path))
    assert len(results) == 1
    assert [p.name for p in results[0].metadata["paths"]] == ["x1.bin", "x3.bin"]


def test_duplicate_finder_skips_small_files(tmp_path):
    write(tmp_path / "a.txt", "same")
    write(tmp_path / "b.txt", "same")
    assert DuplicateFinder().analyze(ProjectIndex.build(tmp_path)) == []


# ---- Security -------------------------------------------------------------------

# Kaynak satırının kendisi sızıntı olarak işaretlenmesin diye parçalanmış.
LEAK = 'api_' + 'key = "ABC' + 'DEFGH12345678"\n'


def test_security_flags_sensitive_file_names_as_critical(tmp_path):
    write(tmp_path / ".env", "SECRET=1")
    results = SecurityLeakAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert [(r.severity, r.file_path.name) for r in results] == [(Severity.CRITICAL, ".env")]


def test_security_finds_secret_with_line_number(tmp_path):
    write(tmp_path / "cfg.py", "x = 1\n" + LEAK)
    results = SecurityLeakAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert len(results) == 1 and "Satır 2" in results[0].description
    assert results[0].severity == Severity.HIGH


def test_security_finds_passwords_with_special_characters(tmp_path):
    write(tmp_path / "cfg.py", 'pass' + 'word = "P@ssw0rd!#$2026"\n' + 'sec' + "ret = 'M$K!9#zL@82p'\n")
    results = SecurityLeakAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert ["Satır 1" in r.description or "Satır 2" in r.description for r in results] == [True, True]


def test_security_ignores_settings_keys_paths_and_templates(tmp_path):
    write(tmp_path / "keys.py", 'THEME_SETTINGS_KEY = "ui/theme_mode"\n'
                                'token = "${API_TOKEN}"\n'
                                'secret_file = "conf/app.secret"\n'
                                'password = f"{prefix}-{suffix}"\n')
    assert SecurityLeakAnalyzer().analyze(ProjectIndex.build(tmp_path)) == []


def test_security_scans_cp1254_files_that_used_to_be_skipped_as_binary(tmp_path):
    write(tmp_path / "ayar.py", "# şifre ayarları: öğrenci çalışması\n" + LEAK, encoding="cp1254")
    results = SecurityLeakAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert len(results) == 1


def test_security_skips_binary_files(tmp_path):
    write(tmp_path / "blob.dat", b"\x00\x01" + LEAK.encode())
    assert SecurityLeakAnalyzer().analyze(ProjectIndex.build(tmp_path)) == []


def test_security_detects_database_urls(tmp_path):
    write(tmp_path / "db.py", 'URL = "post' + 'gres://user:pw@host/db"\n')
    results = SecurityLeakAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert len(results) == 1 and "Veritabanı" in results[0].description


# ---- Dead weight -------------------------------------------------------------------

def test_dead_weight_reports_unused_requirement(tmp_path):
    write(tmp_path / "requirements.txt", "pathspec>=0.11\nnumpy==1.0\nPillow\n")
    write(tmp_path / "app.py", "import pathspec\nfrom PIL import Image\n")
    results = DeadWeightAnalyzer().analyze(ProjectIndex.build(tmp_path))
    unused = [r for r in results if r.metadata["rule"] == "unused-dependency"]
    assert titles(unused) == ["Kullanılmayan Kütüphane Tespit Edildi: numpy"]


def test_dead_weight_without_requirements_gives_info(tmp_path):
    write(tmp_path / "app.py", "import os\n")
    results = DeadWeightAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert [r.severity for r in results] == [Severity.INFO]


def test_dead_weight_ignores_imports_in_excluded_dirs(tmp_path):
    write(tmp_path / "requirements.txt", "numpy\n")
    write(tmp_path / "app.py", "x = 1\n")
    write(tmp_path / "venv" / "lib.py", "import numpy\n")
    results = DeadWeightAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert [r.metadata["rule"] for r in results if r.metadata["rule"] == "unused-dependency"] == ["unused-dependency"]


# ---- Complexity -----------------------------------------------------------------------

def branchy(n):
    body = "\n".join(f"    if x == {i}:\n        y = {i}" for i in range(n))
    return f"def f(x):\n    y = 0\n{body}\n    return y\n"


def test_complexity_flags_function_over_limit_only(tmp_path):
    write(tmp_path / "ok.py", branchy(9))        # 1 + 9 = 10 -> limit içinde
    write(tmp_path / "bad.py", branchy(10))      # 1 + 10 = 11
    results = CodeComplexityAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert [(r.file_path.name, r.severity) for r in results] == [("bad.py", Severity.MEDIUM)]
    assert "11" in results[0].description


def test_complexity_flags_god_class_and_bloated_file(tmp_path):
    methods = "".join(f"    def m{i}(self):\n        pass\n" for i in range(21))      # V2 sınırı: 20 metot
    write(tmp_path / "god.py", f"class God:\n{methods}")
    write(tmp_path / "long.py", "x = 1\n" * 501)                                      # V2 sınırı: 500 satır
    write(tmp_path / "fine.py", "class Ok:\n" + "".join(f"    def m{i}(self):\n        pass\n" for i in range(20)))
    results = CodeComplexityAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert sorted((r.file_path.name, r.severity) for r in results) == [
        ("god.py", Severity.HIGH), ("long.py", Severity.MEDIUM)]


def test_complexity_skips_broken_python(tmp_path):
    write(tmp_path / "broken.py", "def (:\n")
    assert CodeComplexityAnalyzer().analyze(ProjectIndex.build(tmp_path)) == []


def test_complexity_reads_utf8_bom_files(tmp_path):
    write(tmp_path / "bom.py", b"\xef\xbb\xbf" + branchy(10).encode())
    results = CodeComplexityAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert len(results) == 1


# ---- Dil istatistikleri -------------------------------------------------------------------

def test_language_stats_aggregates_per_language_sorted_by_code_lines(tmp_path):
    from src.analyzers.language_stats_analyzer import LanguageStatsAnalyzer
    write(tmp_path / "a.py", "# yorum\nx = 1\n\ny = 2\n")
    write(tmp_path / "b.py", "z = 3\n")
    write(tmp_path / "Main.java", "class A {\n  // c\n  void m() {}\n  int x;\n}\n")
    write(tmp_path / "notes.txt", "yok sayılır\n")
    write(tmp_path / "app.min.js", "var a=1;")
    results = LanguageStatsAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert [(r.title, r.severity) for r in results] == [("Dil: Java", Severity.INFO), ("Dil: Python", Severity.INFO)]
    by_lang = {r.metadata["language"]: r.metadata for r in results}
    assert set(by_lang) == {"python", "java"}                       # .txt ve .min.js sayılmaz
    py = by_lang["python"]
    assert (py["files"], py["total_lines"], py["code_lines"], py["comment_lines"], py["blank_lines"]) == (2, 5, 3, 1, 1)
    assert by_lang["java"]["approximate"] is True and by_lang["python"]["approximate"] is False
    codes = [r.metadata["code_lines"] for r in results]
    assert codes == sorted(codes, reverse=True)


# ---- Güvenlik: .gitignore ve git izleme farkındalığı (gerçek git depolarıyla) --------------------

import shutil
import subprocess

needs_git = __import__("pytest").mark.skipif(shutil.which("git") is None, reason="git kurulu değil")


def git(repo, *args):
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
                   cwd=repo, check=True, capture_output=True)


def make_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    write(repo / "app.py", "x = 1\n")
    return repo


def commit_all(repo, message="c"):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)


def sensitive_findings(root, **build_kwargs):
    results = SecurityLeakAnalyzer().analyze(ProjectIndex.build(root, **build_kwargs))
    return [r for r in results if r.metadata.get("kind") == "sensitive_file"]


@needs_git
def test_gitignored_untracked_env_is_correct_practice_and_not_reported(tmp_path):
    repo = make_repo(tmp_path)
    write(repo / ".gitignore", ".env\n")
    write(repo / ".env", "SECRET=1")
    commit_all(repo)
    assert sensitive_findings(repo) == []
    assert SecurityLeakAnalyzer().analyze(ProjectIndex.build(repo)) == []


@needs_git
def test_untracked_env_missing_from_gitignore_is_flagged_as_risk(tmp_path):
    repo = make_repo(tmp_path)
    commit_all(repo)
    write(repo / ".env", "SECRET=1")
    [finding] = sensitive_findings(repo)
    assert finding.severity == Severity.CRITICAL and finding.metadata["committed"] is False
    assert finding.metadata["tracking_known"] is True
    assert ".gitignore'a eklenmemiş" in finding.description and "kökte" not in finding.description


@needs_git
def test_committed_env_is_reported_as_committed(tmp_path):
    repo = make_repo(tmp_path)
    write(repo / "config" / ".env", "SECRET=1")
    commit_all(repo)
    [finding] = sensitive_findings(repo)
    assert finding.metadata["committed"] is True and finding.metadata["gitignored"] is False
    assert "commit edilmiş" in finding.title and "git rm --cached config/.env" in finding.recommendation


@needs_git
def test_env_committed_then_gitignored_is_still_reported(tmp_path):
    """.gitignore izlenen dosyayı geçmişten silmez: ignore'lu ama izlenen .env sessizce kaybolmamalı."""
    repo = make_repo(tmp_path)
    write(repo / ".env", "SECRET=1")
    commit_all(repo)
    write(repo / ".gitignore", ".env\n")                              # sonradan eklendi
    [finding] = sensitive_findings(repo)
    assert finding.metadata["committed"] is True and finding.metadata["gitignored"] is True
    assert finding.file_path == repo.resolve() / ".env" and ".gitignore'da olmasına rağmen" in finding.description


@needs_git
def test_nested_gitignore_protects_nested_env(tmp_path):
    repo = make_repo(tmp_path)
    write(repo / "backend" / ".gitignore", ".env\n")
    write(repo / "backend" / ".env", "SECRET=1")
    write(repo / "frontend" / ".env", "SECRET=2")
    commit_all(repo)
    git(repo, "rm", "-q", "--cached", "frontend/.env")                 # frontend: izlenmeyen ve ignore'sız
    findings = sensitive_findings(repo)
    assert [f.file_path.relative_to(repo.resolve()).as_posix() for f in findings] == ["frontend/.env"]


@needs_git
def test_secret_patterns_are_not_scanned_in_gitignored_files(tmp_path):
    repo = make_repo(tmp_path)
    write(repo / ".gitignore", "local/\n")
    write(repo / "local" / "creds.py", LEAK)
    write(repo / "src" / "creds.py", LEAK)
    results = SecurityLeakAnalyzer().analyze(ProjectIndex.build(repo))
    assert [r.file_path.relative_to(repo.resolve()).as_posix() for r in results] == ["src/creds.py"]


PEM_KEY = "-----BEGIN " + "PRIV" + "ATE KEY-----\nMIIB\n-----END " + "PRIV" + "ATE KEY-----\n"
PEM_CERT = "-----BEGIN CERTIFICATE-----\nMIIB\n-----END CERTIFICATE-----\n"


def test_private_keys_and_keystores_in_working_copy_are_sensitive_files(tmp_path):
    """Yalnızca adıyla tanınan anahtarlar (ikilik anahtar deposu dahil) içerik taramasına kalmaz."""
    write(tmp_path / "id_rsa", "opaque")
    write(tmp_path / "app.jks", b"\xfe\xed\xfe\xed\x00\x00")
    write(tmp_path / "server.key", PEM_KEY)
    write(tmp_path / ".env.local", "A=1")
    write(tmp_path / ".env.example", "A=")
    findings = sensitive_findings(tmp_path)
    assert sorted(f.file_path.name for f in findings) == [".env.local", "app.jks", "id_rsa", "server.key"]
    assert {f.metadata["rule"] for f in findings} == {"sensitive-file"}


def test_public_certificate_pem_is_not_a_sensitive_file(tmp_path):
    write(tmp_path / "ca.pem", PEM_CERT)
    write(tmp_path / "bundle.pem", PEM_CERT + PEM_KEY)
    assert [f.file_path.name for f in sensitive_findings(tmp_path)] == ["bundle.pem"]


@needs_git
def test_committed_and_still_tracked_private_key_is_reported(tmp_path):
    """Geçmiş analizörü izlenen dosyayı atlar; izlenen anahtarı güvenlik analizörü raporlamalı."""
    repo = make_repo(tmp_path)
    write(repo / "deploy" / "id_ed25519", "opaque")
    commit_all(repo)
    [finding] = sensitive_findings(repo)
    assert finding.metadata["committed"] is True and "git rm --cached deploy/id_ed25519" in finding.recommendation


@needs_git
def test_tracked_but_gitignored_keystore_is_reported(tmp_path):
    repo = make_repo(tmp_path)
    write(repo / "release.keystore", b"\x00\x01")
    commit_all(repo)
    write(repo / ".gitignore", "*.keystore\n")
    [finding] = sensitive_findings(repo)
    assert finding.metadata["committed"] is True and finding.metadata["gitignored"] is True


def test_outside_git_repo_behaviour_without_gitignore_is_unchanged(tmp_path):
    write(tmp_path / ".env", "SECRET=1")
    [finding] = sensitive_findings(tmp_path)
    assert finding.severity == Severity.CRITICAL
    assert finding.metadata["tracking_known"] is False and "git bilgisi alınamadı" in finding.description


def test_gitignored_env_outside_git_repo_is_not_reported(tmp_path):
    write(tmp_path / ".gitignore", ".env\n")
    write(tmp_path / ".env", "SECRET=1")
    assert sensitive_findings(tmp_path) == []


def test_with_gitignore_support_disabled_ignore_status_is_unknown_so_file_is_flagged(tmp_path):
    write(tmp_path / ".gitignore", ".env\n")
    write(tmp_path / ".env", "SECRET=1")
    [finding] = sensitive_findings(tmp_path, respect_gitignore=False)
    assert finding.severity == Severity.CRITICAL                       # eski, ihtiyatlı davranış


# ---- V2 eşikleri: birleşik fonksiyon bulgusu, şiddet, yapılandırma -------------------------------

from src.core.thresholds import QualityThresholds


def analyzer_with(**overrides):
    analyzer = CodeComplexityAnalyzer()
    analyzer.thresholds = QualityThresholds(**overrides)
    return analyzer


def function_findings(tmp_path, source, name="m.py", **overrides):
    target = write(tmp_path / name, source)
    results = analyzer_with(**overrides).analyze(ProjectIndex.build(target.parent))   # yalnızca bu dosyanın klasörü
    return [r for r in results if r.metadata.get("rule") == "function-metrics"]


def test_function_exceeding_several_metrics_gets_one_combined_finding(tmp_path):
    params = ", ".join(f"p{i}" for i in range(7))                            # 7 > 5
    body = "\n".join(f"    if p0 == {i}:\n        pass" for i in range(11))  # siklomatik 12, bilişsel 11
    [finding] = function_findings(tmp_path, f"def big({params}):\n{body}\n")
    assert finding.metadata["violations"] == {"cyclomatic": 12, "params": 7}
    assert "siklomatik karmaşıklık 12 (Eşik: 10)" in finding.description and "parametre sayısı 7 (Eşik: 5)" in finding.description
    assert finding.severity == Severity.MEDIUM                               # en yüksek metrik: siklomatik ORTA
    assert "Extract Method" in finding.recommendation and "Parameter Object" in finding.recommendation


def test_severity_escalates_at_twice_the_threshold(tmp_path):
    body = "\n".join(f"    if x == {i}:\n        pass" for i in range(20))   # siklomatik 21 >= 2 x 10
    [finding] = function_findings(tmp_path, f"def f(x):\n{body}\n")
    assert finding.severity == Severity.HIGH


def test_only_low_priority_metrics_give_low_severity(tmp_path):
    many_params = "def f(" + ", ".join(f"a{i}" for i in range(6)) + "):\n    pass\n"
    [finding] = function_findings(tmp_path, many_params)
    assert finding.severity == Severity.LOW and finding.metadata["violations"] == {"params": 6}


def test_function_length_and_nesting_and_cognitive_thresholds(tmp_path):
    long_body = "    x = 0\n" * 50                                              # 52 satır > 50
    deep = "def deep(a):\n    if a:\n        if a:\n            if a:\n                if a:\n                    if a:\n                        pass\n"
    results = function_findings(tmp_path, f"def long_one():\n{long_body}\n{deep}")
    by_name = {r.metadata["function"]: r.metadata["violations"] for r in results}
    assert by_name["long_one"] == {"length": 51}          # def satırı dahil 51 satır > 50
    assert by_name["deep"] == {"nesting": 5}               # bilişsel 1+2+3+4+5 = 15: eşiğin kendisi aşım değil


def test_thresholds_are_configurable_and_exact_boundary_is_not_a_violation(tmp_path):
    source = "def f(a, b, c):\n    if a:\n        pass\n"
    assert function_findings(tmp_path, source, name="a/m.py") == []           # varsayılan: 3 parametre sorun değil
    [finding] = function_findings(tmp_path, source, name="b/m.py", parameters=2)
    assert finding.metadata["violations"] == {"params": 3}
    assert function_findings(tmp_path, source, name="c/m.py", parameters=3) == []  # eşiğin kendisi aşım sayılmaz


def test_module_import_count_threshold(tmp_path):
    imports = "\n".join(f"import mod{i}" for i in range(26))
    write(tmp_path / "many.py", imports + "\nx = 1\n")
    write(tmp_path / "few.py", "import os\nimport sys\n")
    results = [r for r in analyzer_with().analyze(ProjectIndex.build(tmp_path)) if r.metadata.get("rule") == "module-imports"]
    assert [(r.file_path.name, r.severity, r.metadata["imports"]) for r in results] == [("many.py", Severity.LOW, 26)]


def test_project_doctor_passes_thresholds_to_analyzers(tmp_path):
    from src.doctors.project_doctor import ProjectDoctor
    write(tmp_path / "m.py", "def f(a, b, c):\n    pass\n")
    doctor = ProjectDoctor([CodeComplexityAnalyzer()], thresholds=QualityThresholds(parameters=2))
    analysis = doctor.diagnose(tmp_path)
    assert [f.metadata["violations"] for f in analysis.all_findings if f.metadata.get("rule") == "function-metrics"] == [{"params": 3}]


def test_project_service_thresholds_option(tmp_path):
    from src.services.project_service import ProjectService
    write(tmp_path / "m.py", "def f(a, b, c):\n    pass\n")
    service = ProjectService(thresholds=QualityThresholds(parameters=2))
    service.set_project(tmp_path)
    titles = [i.title for i in service.analyze_project()["all_issues"]] + \
             [f.title for f in service.doctor.diagnose(tmp_path).all_findings]
    assert any(t.startswith("Karmaşık Fonksiyon: f()") for t in titles)


def test_brace_languages_report_the_same_combined_findings(tmp_path):
    branches = "\n".join(f"  if (x == {i}) {{ y = {i}; }}" for i in range(11))
    write(tmp_path / "App.java", f"class App {{\n void f(int x, int y) {{\n{branches}\n }}\n}}\n")
    results = analyzer_with().analyze(ProjectIndex.build(tmp_path))
    [finding] = [r for r in results if r.metadata.get("rule") == "function-metrics"]
    assert finding.metadata["language"] == "java" and finding.metadata["approximate"] is True
    assert finding.metadata["violations"]["cyclomatic"] == 12
