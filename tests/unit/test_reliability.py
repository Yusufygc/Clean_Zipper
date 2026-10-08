import ast
import textwrap
from pathlib import Path

from src.analyzers.reliability_analyzer import ReliabilityAnalyzer
from src.core.project_index import ProjectIndex
from src.core.thresholds import QualityThresholds
from src.languages import brace_reliability as br
from src.languages import python_reliability as pr
from src.languages.catalog import default_languages
from src.languages.todo_markers import find_todos
from src.models.analysis_models import Severity
from src.services.project_service import ProjectService


def facts(code: str, comment_lines=frozenset()):
    return pr.analyze(ast.parse(textwrap.dedent(code)), comment_lines)


# ---- except ----------------------------------------------------------------------------------

def test_bare_except_flagged_unless_it_reraises():
    result = facts("""
        try:
            a()
        except:
            pass
        try:
            b()
        except:
            log()
            raise
    """)
    assert result.bare_excepts == [4] and result.swallowed == []


def test_broad_silent_except_is_swallowed_but_specific_or_logging_is_not():
    result = facts("""
        try:
            a()
        except Exception:
            pass
        try:
            a()
        except (ValueError, BaseException):
            ...
        try:
            a()
        except Exception:
            return None
        try:
            a()
        except KeyError:
            pass
        try:
            a()
        except Exception as e:
            logger.exception(e)
        try:
            a()
        except Exception:
            raise
    """)
    assert result.swallowed == [4, 8, 12] and result.bare_excepts == []


def test_comment_justified_swallow_is_not_reported():
    code = """
        try:
            a()
        except Exception:
            pass  # kapatma sırasında hata önemsiz
    """
    assert facts(code).swallowed == [4]
    assert facts(code, comment_lines={5}).swallowed == []


# ---- open / datetime / debug / print --------------------------------------------------------------

def test_open_without_encoding_cases():
    result = facts("""
        open('a.txt')
        open('a.txt', 'r')
        open('a.txt', mode='w')
        open('a.bin', 'rb')
        open('a.txt', encoding='utf-8')
        open('a.txt', 'r', -1, 'utf-8')
        open('a.txt', mode)
        open('a.txt', **kw)
        p.read_text()
        p.read_text('utf-8')
        p.write_text('x')
        p.write_text('x', encoding='utf-8')
        p.write_text('x', 'utf-8')
    """)
    assert result.open_without_encoding == [2, 3, 4, 10, 12]


def test_naive_datetime_variants():
    result = facts("""
        import datetime
        datetime.now()
        datetime.now(timezone.utc)
        datetime.datetime.now()
        datetime.utcnow()
        datetime.today()
        date.today()
        time.now()
    """)
    assert result.naive_datetimes == [3, 5, 6, 7]


def test_debug_flag_only_at_module_level():
    result = facts("""
        DEBUG = True
        PROD = True
        def f():
            DEBUG = True
        DEBUG2 = False
    """)
    assert result.debug_flags == [2]


def test_prints_outside_main_block_only():
    result = facts("""
        print('a')
        def f():
            print('b')
        if __name__ == '__main__':
            print('c')
            main()
    """)
    assert result.prints == [2, 4]


# ---- brace diller -------------------------------------------------------------------------------------

def brace(language: str, code: str):
    text = textwrap.dedent(code)
    source = default_languages.get(language).stripped(text)
    return text, source


def test_empty_catch_variants_and_comment_exemption():
    text, source = brace('javascript', """
        try { a(); } catch (e) {}
        try { a(); } catch {}
        try { a(); } catch (e) { /* bilerek */ }
        try { a(); } catch (e) { log(e); }
        p.catch(() => {});
        p.catch(() => { /* yut */ });
        p.catch(err => handle(err));
    """)
    assert br.find_empty_catches('javascript', source.clean, text) == [2, 3, 6]
    assert br.find_empty_catches('go', source.clean, text) == []


def test_debugger_and_prints_per_language():
    _, js = brace('typescript', "debugger;\nconsole.log(1);\nconsole.error(2);\nconst a = 'console.log(3)';\n")
    assert br.find_debugger('typescript', js.clean) == [1]
    assert br.find_prints('typescript', js.clean) == [2, 3]
    _, java = brace('java', "System.out.println(1);\ne.printStackTrace();\nSystem.err.print(2);\nlogger.info(3);\n")
    assert br.find_prints('java', java.clean) == [1, 2, 3]
    _, cs = brace('csharp', 'Console.WriteLine("a");\nlog.Info("b");\n')
    assert br.find_prints('csharp', cs.clean) == [1]
    _, rust = brace('rust', 'println!("a");\ndbg!(x);\nlog::info!("b");\n')
    assert br.find_prints('rust', rust.clean) == [1, 2]
    _, c = brace('c', 'printf("a");\n')
    assert br.find_prints('c', c.clean) == []


# ---- TODO işaretleri -------------------------------------------------------------------------------------

def test_todos_only_from_comments():
    code = textwrap.dedent('''
        # TODO: ilk iş
        x = "FIXME inside string"
        y = 1  # HACK geçici çözüm
        z = TODO_LIST
        """docstring XXX"""
    ''')
    source = default_languages.get('python').stripped(code)
    items = find_todos(code, source.no_comments)
    assert [(i.line, i.marker, i.text) for i in items] == [(2, 'TODO', 'ilk iş'), (4, 'HACK', 'geçici çözüm')]


def test_todos_in_brace_languages_with_crlf():
    code = "int a;\r\n// FIXME: sızıntı\r\n/* XXX burası */\r\nconst s = \"TODO\";\r\n"
    source = default_languages.get('java').stripped(code)
    items = find_todos(code, source.no_comments)
    assert [(i.line, i.marker) for i in items] == [(2, 'FIXME'), (3, 'XXX')]


# ---- analizör ------------------------------------------------------------------------------------------------

def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run(root: Path, analyzer=None):
    return (analyzer or ReliabilityAnalyzer()).analyze(ProjectIndex.build(root))


def by_rule(results):
    return {r.metadata["rule"]: r for r in results}


def test_analyzer_python_findings_and_severities(tmp_path):
    write(tmp_path / "svc.py", "import datetime\n\n\ndef f(p):\n    try:\n        open(p)\n    except:\n        pass\n"
                               "    return datetime.datetime.now()\n")
    found = by_rule(run(tmp_path))
    assert set(found) == {"bare-except", "open-without-encoding", "naive-datetime"}
    assert found["bare-except"].severity == Severity.HIGH and found["bare-except"].category == "reliability"
    assert found["open-without-encoding"].severity == Severity.MEDIUM
    assert found["naive-datetime"].severity == Severity.LOW and found["naive-datetime"].metadata["approximate"] is False
    assert found["bare-except"].metadata["lines"] == [7]


def test_print_density_threshold_and_main_block(tmp_path):
    body = "def f():\n" + "".join("    print(1)\n" for _ in range(5))
    write(tmp_path / "a.py", body)
    assert run(tmp_path) == []                                  # 5 çağrı: eşik aşılmadı
    write(tmp_path / "a.py", body + "    print(2)\n")
    (finding,) = run(tmp_path)
    assert finding.metadata["rule"] == "print-density" and finding.metadata["count"] == 6
    analyzer = ReliabilityAnalyzer()
    analyzer.thresholds = QualityThresholds(print_calls=6)
    assert run(tmp_path, analyzer) == []


def test_test_files_skip_rules_but_not_todo_inventory(tmp_path):
    write(tmp_path / "tests" / "test_x.py", "# TODO: yaz\ntry:\n    a()\nexcept:\n    pass\n")
    results = run(tmp_path)
    assert [r.metadata["rule"] for r in results] == ["todo-inventory"]


def test_todo_inventory_is_single_info_finding(tmp_path):
    write(tmp_path / "a.py", "# TODO: bir\n# FIXME: iki\n")
    write(tmp_path / "b.js", "// TODO: üç\n")
    (summary,) = run(tmp_path)
    assert summary.severity == Severity.INFO and summary.metadata["total"] == 3
    assert summary.metadata["by_marker"] == {"TODO": 2, "FIXME": 1} and summary.metadata["files"] == 2
    assert {(i["path"], i["line"], i["text"]) for i in summary.metadata["items"]} == {
        ("a.py", 1, "bir"), ("a.py", 2, "iki"), ("b.js", 1, "üç")}


def test_javascript_findings_are_approximate(tmp_path):
    write(tmp_path / "app.js", "try { a(); } catch (e) {}\ndebugger;\n")
    found = by_rule(run(tmp_path))
    assert set(found) == {"empty-catch", "debugger-statement"}
    assert found["empty-catch"].metadata["approximate"] is True and found["empty-catch"].severity == Severity.MEDIUM


def test_unparsable_python_is_skipped_and_service_scores_category(tmp_path):
    write(tmp_path / "broken.py", "def (:\n    except:\n")
    write(tmp_path / "ok.py", "DEBUG = True\n")
    found = by_rule(run(tmp_path))
    assert set(found) == {"debug-flag"}
    analysis = ProjectService().doctor.diagnose(tmp_path)
    assert analysis.category_scores["reliability"] < 100 and not analysis.failed_analyzers
