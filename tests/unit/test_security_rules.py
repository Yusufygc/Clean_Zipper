import json
from pathlib import Path

import pytest

from src.analyzers.code_security_analyzer import CodeSecurityAnalyzer
from src.core.project_index import ProjectIndex
from src.core.security_rules import bundled_rules_dir, load_security_rules
from src.models.analysis_models import Severity

EXTENSIONS = {'python': '.py', 'javascript': '.jsx', 'typescript': '.ts', 'java': '.java', 'csharp': '.cs',
              'c': '.c', 'cpp': '.cpp', 'go': '.go', 'rust': '.rs'}

# kural kimliği -> (dil, olumlu örnekler, olumsuz örnekler)
SAMPLES = {
    'py-eval': ('python', ["x = eval(s)\n"], ["x = ast.literal_eval(s)\nmodel.eval()\n# eval(x)\ns = 'eval(x)'\n"]),
    'py-exec': ('python', ["exec(code)\n"], ["cursor.exec(code)\nexecute(q)\n"]),
    'py-pickle-load': ('python', ["d = pickle.loads(b)\n", "d = pickle.load(f)\n"], ["d = json.loads(b)\n"]),
    'py-yaml-load': ('python', ["yaml.load(f)\n", "yaml.load(f); loader = SafeLoader\n", "yaml.load(\n    open(p)\n)\n"],
                     ["yaml.safe_load(f)\nyaml.load(f, Loader=yaml.SafeLoader)\n",
                      "data = yaml.load(\n    open(p),\n    Loader=yaml.SafeLoader\n)\n"]),
    'py-subprocess-shell': ('python', ["subprocess.run(cmd, shell=True)\n",
                                       "subprocess.Popen(\n    build(cmd),\n    shell=True)\n"],
                            ["subprocess.run(['ls'], shell=False)\nsubprocess.run(['ls'])\n"]),
    'py-os-system': ('python', ["os.system('ls')\n"], ["os.path.join('a')\n"]),
    'py-weak-hash': ('python', ["h = hashlib.md5(b)\n"],
                     ["h = hashlib.sha256(b)\nh = hashlib.md5(b, usedforsecurity=False)\n",
                      "h = hashlib.sha1(\n    key.encode('utf-8'),\n    usedforsecurity=False,\n)\n"]),
    'py-verify-false': ('python', ["requests.get(u, verify=False)\n"], ["requests.get(u, verify=True)\n"]),
    'py-tempfile-mktemp': ('python', ["p = tempfile.mktemp()\n"], ["p = tempfile.mkstemp()\n"]),
    'py-sql-format': ('python', ['cur.execute(f"SELECT * FROM t WHERE id = {i}")\n',
                                 'cur.execute("SELECT * FROM t WHERE id = %s" % i)\n',
                                 'cur.execute("SELECT * FROM t WHERE id = {}".format(i))\n',
                                 'cur.execute("DELETE FROM t WHERE id = " + str(i))\n'],
                      ['cur.execute("SELECT * FROM t WHERE id = ?", (i,))\ncur.execute(f"no sql here {i}")\n']),
    'py-flask-debug': ('python', ["app.run(host='0', debug=True)\n"], ["app.run(debug=False)\n"]),
    'js-eval': ('javascript', ["eval(s);\n"], ["obj.eval(s);\nmyeval(s);\n"]),
    'js-new-function': ('javascript', ["const f = new Function('a', 'return a');\n"], ["const f = Function.prototype;\n"]),
    'js-timer-string': ('javascript', ["setTimeout('doIt()', 10);\n"], ["setTimeout(() => doIt(), 10);\n"]),
    'js-inner-html': ('javascript', ["el.innerHTML = userHtml;\n", "el.innerHTML += `<b>${x}</b>`;\n"],
                      ["el.innerHTML = '';\nel.innerHTML = '<p>sabit</p>';\nif (el.innerHTML == x) {}\n"]),
    'js-document-write': ('javascript', ["document.write(x);\n"], ["document.getElementById('a');\n"]),
    'js-dangerous-html': ('javascript', ["const a = <div dangerouslySetInnerHTML={{__html: h}} />;\n"], ["const a = 1;\n"]),
    'js-child-process-exec': ('javascript', ["child_process.exec(cmd);\n", "execSync(cmd);\n"],
                              ["child_process.execFile('ls');\nre.exec(s);\n"]),
    'js-tls-reject-unauthorized': ('javascript', ["const o = { rejectUnauthorized: false };\n"],
                                   ["const o = { rejectUnauthorized: true };\n"]),
    'js-weak-hash': ('javascript', ["crypto.createHash('md5').update(s);\n"], ["crypto.createHash('sha256').update(s);\n"]),
    'js-sql-concat': ('javascript', ["db.query('SELECT * FROM t WHERE id = ' + id);\n",
                                     "db.query(`SELECT * FROM t WHERE id = ${id}`);\n"],
                      ["db.query('SELECT * FROM t WHERE id = $1', [id]);\n"]),
    'java-runtime-exec': ('java', ["Runtime.getRuntime().exec(cmd);\n"], ["new ProcessBuilder(list);\n"]),
    'java-weak-hash': ('java', ['MessageDigest md = MessageDigest.getInstance("MD5");\n'],
                       ['MessageDigest.getInstance("SHA-256");\n']),
    'java-object-input-stream': ('java', ["ObjectInputStream in = new ObjectInputStream(s);\n"],
                                 ["new ObjectOutputStream(s);\n"]),
    'java-sql-concat': ('java', ['stmt.executeQuery("SELECT * FROM t WHERE id=" + id);\n'],
                        ['ps = c.prepareStatement("SELECT * FROM t WHERE id=?");\n']),
    'java-weak-cipher': ('java', ['Cipher.getInstance("DES");\n', 'Cipher.getInstance("AES");\n',
                                  'Cipher.getInstance("AES/ECB/PKCS5Padding");\n'],
                         ['Cipher.getInstance("AES/GCM/NoPadding");\n']),
    'cs-binary-formatter': ('csharp', ["var f = new BinaryFormatter();\n"], ["var f = new JsonSerializer();\n"]),
    'cs-weak-hash': ('csharp', ["var h = MD5.Create();\n", "var s = new SHA1Managed();\n"], ["var h = SHA256.Create();\n"]),
    'cs-sql-concat': ('csharp', ['var c = new SqlCommand("SELECT * FROM t WHERE id=" + id, conn);\n',
                                 'var d = new SqlCommand($"SELECT * FROM t WHERE id={id}", conn);\n'],
                      ['var c = new SqlCommand("SELECT * FROM t WHERE id=@id", conn);\n']),
    'cs-certificate-validation': ('csharp', ["ServicePointManager.ServerCertificateValidationCallback += (s, c, ch, e) => true;\n"],
                                  ["var x = 1;\n"]),
    'c-gets': ('c', ["gets(buf);\n"], ["fgets(buf, n, stdin);\nobj.gets(1);\n"]),
    'c-strcpy': ('c', ["strcpy(dst, src);\n", "strcat(dst, src);\n"], ["strncpy(dst, src, n);\n"]),
    'c-sprintf': ('c', ['sprintf(buf, "%d", x);\n'], ['snprintf(buf, n, "%d", x);\n']),
    'c-system': ('c', ["system(cmd);\n"], ["ecosystem(cmd);\nobj->system(cmd);\n"]),
    'c-scanf-unbounded': ('c', ['scanf("%s", buf);\n'], ['scanf("%9s", buf);\n']),
    'go-insecure-skip-verify': ('go', ["cfg := &tls.Config{InsecureSkipVerify: true}\n"], ["InsecureSkipVerify: false\n"]),
    'go-weak-hash': ('go', ["h := md5.New()\n", "s := sha1.Sum(b)\n"], ["h := sha256.New()\n"]),
    'go-shell-command': ('go', ['exec.Command("sh", "-c", cmd)\n'], ['exec.Command("ls", "-l")\n']),
    'rust-unsafe': ('rust', ["fn f() { unsafe { x() } }\n"], ["fn f() { safe() }\n"]),
}


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def scan(tmp_path: Path, language: str, code: str, name: str = "sample", **kwargs):
    write(tmp_path / f"{name}{EXTENSIONS[language]}", code)
    return CodeSecurityAnalyzer(**kwargs).analyze(ProjectIndex.build(tmp_path))


def fired(results):
    return {r.metadata["rule"] for r in results}


# ---- kural dosyası ve yükleyici ----------------------------------------------------------------

def test_every_bundled_rule_has_samples_and_ids_are_unique():
    rules = load_security_rules([bundled_rules_dir()])
    ids = [r.id for r in rules]
    assert len(ids) == len(set(ids)) >= 30
    assert set(ids) == set(SAMPLES)


@pytest.mark.parametrize("rule_id", sorted(SAMPLES))
def test_rule_matches_positive_and_ignores_negative_samples(tmp_path, rule_id):
    language, positives, negatives = SAMPLES[rule_id]
    for number, code in enumerate(positives):
        results = scan(tmp_path / f"pos{number}", language, code)
        assert rule_id in fired(results), f"{rule_id} olumlu örnek {number} eşleşmedi: {code!r}"
    for number, code in enumerate(negatives):
        results = scan(tmp_path / f"neg{number}", language, code)
        assert rule_id not in fired(results), f"{rule_id} olumsuz örnek {number} yanlış eşleşti: {code!r}"


def test_rules_only_apply_to_their_languages(tmp_path):
    assert fired(scan(tmp_path / "a", 'javascript', "x = eval(s)\n")) == {'js-eval'}
    assert fired(scan(tmp_path / "b", 'python', "const y = new Function('a');\n")) == set()


def test_comments_and_code_scope_strings_are_not_scanned(tmp_path):
    code = "# eval(x)\ns = 'os.system(1)'\n\"\"\"exec(code)\"\"\"\n"
    assert scan(tmp_path, 'python', code) == []


def test_one_finding_per_rule_per_file_lists_lines(tmp_path):
    code = "a = eval(x)\nb = 1\nc = eval(y)\n"
    (result,) = scan(tmp_path, 'python', code)
    assert result.metadata["lines"] == [1, 3] and result.metadata["count"] == 2
    assert result.severity == Severity.HIGH and result.category == "security"
    assert result.metadata["cwe"] == "CWE-95" and result.metadata["approximate"] is True
    assert "Satır: 1, 3" in result.description


def test_severities_follow_rule_definitions(tmp_path):
    code = "import hashlib\nh = hashlib.md5(b)\nos.system(c)\nx = eval(s)\n"
    severities = {r.metadata["rule"]: r.severity for r in scan(tmp_path, 'python', code)}
    assert severities == {'py-weak-hash': Severity.LOW, 'py-os-system': Severity.MEDIUM, 'py-eval': Severity.HIGH}


def test_disabled_rules_and_test_files_are_skipped(tmp_path):
    results = scan(tmp_path, 'python', "x = eval(s)\ny = os.system(c)\n", disabled_rules=['py-eval'])
    assert fired(results) == {'py-os-system'}
    write(tmp_path / "tests" / "test_x.py", "x = eval(s)\n")
    write(tmp_path / "other_test.py", "x = eval(s)\n")
    assert all(r.file_path.name == "sample.py" for r in CodeSecurityAnalyzer().analyze(ProjectIndex.build(tmp_path)))


def test_rust_unsafe_is_informational(tmp_path):
    (result,) = scan(tmp_path, 'rust', "fn f() { unsafe { x() } }\n")
    assert result.severity == Severity.INFO


def test_multiline_python_and_crlf_files_report_correct_lines(tmp_path):
    (tmp_path / "w.py").write_bytes(b"a = 1\r\nb = 2\r\nc = eval(x)\r\n")
    (result,) = CodeSecurityAnalyzer().analyze(ProjectIndex.build(tmp_path))
    assert result.metadata["lines"] == [3]


def test_service_passes_disabled_rules_to_analyzer(tmp_path):
    from src.services.project_service import ProjectService
    write(tmp_path / "a.py", "x = eval(s)\n")
    on = ProjectService().doctor.diagnose(tmp_path)
    off = ProjectService(disabled_rules=['py-eval']).doctor.diagnose(tmp_path)
    assert any(f.metadata.get("rule") == "py-eval" for f in on.all_findings)
    assert not any(f.metadata.get("rule") == "py-eval" for f in off.all_findings)


# ---- yükleyici -----------------------------------------------------------------------------------

def rule_json(**overrides):
    rule = {"id": "t-1", "title": "Test", "severity": "LOW", "languages": ["python"], "scope": "code",
            "pattern": "foo\\(", "cwe": "CWE-1", "advice": "yap"}
    rule.update(overrides)
    return rule


def test_user_rules_override_bundled_and_invalid_rules_are_skipped(tmp_path, caplog):
    bundled = tmp_path / "bundled"
    user = tmp_path / "user"
    write(bundled / "a.json", json.dumps({"rules": [rule_json(), rule_json(id="t-2")]}))
    write(user / "b.json", json.dumps({"rules": [
        rule_json(title="Kullanıcı"), rule_json(id="bad-1", pattern="("), rule_json(id="bad-2", severity="NOPE"),
        rule_json(id="bad-3", scope="file"), rule_json(id="bad-4", languages=[]), "metin"]}))
    write(user / "c.json", "{ bozuk")
    rules = {r.id: r for r in load_security_rules([bundled, user])}
    assert set(rules) == {"t-1", "t-2"} and rules["t-1"].title == "Kullanıcı"
    assert "bad-1" in caplog.text and "bad-2" in caplog.text and "c.json" in caplog.text


def test_custom_rules_can_be_injected_and_case_insensitive_flag_works(tmp_path):
    write(tmp_path / "r" / "r.json", json.dumps({"rules": [rule_json(pattern="forbidden_call", flags="i")]}))
    rules = load_security_rules([tmp_path / "r"])
    results = scan(tmp_path / "p", 'python', "FORBIDDEN_CALL(1)\n", rules=rules)
    assert fired(results) == {"t-1"}


# ---- sağlayıcı sırları ----------------------------------------------------------------------------

SECRETS = {
    "AWS erişim anahtarı": "AK" + "IA" + "ABCDEFGHIJKLMNOP",
    "GitHub token": "gh" + "p_" + "a" * 36,
    "Slack token": "xo" + "xb-" + "1234567890-abcdef",
    "Google API anahtarı": "AI" + "za" + "A" * 35,
    "Stripe canlı anahtar": "sk_" + "live_" + "a" * 24,
    "JWT": "ey" + "J" + "hbGciOiJIUzI1NiJ9." + "ey" + "J" + "zdWIiOiIxMjM0NTY3ODkwIn0." + "abcdefghijklmnop",
    "Özel anahtar (PEM)": "-----BEGIN RSA PRIV" + "ATE KEY-----",
}


@pytest.mark.parametrize("provider", sorted(SECRETS))
def test_provider_secret_detected_and_value_is_never_printed(tmp_path, provider):
    from src.analyzers.security_analyzer import SecurityLeakAnalyzer
    value = SECRETS[provider]
    write(tmp_path / "config.txt", f"first line\nvalue_here = {value}\n")
    results = [r for r in SecurityLeakAnalyzer().analyze(ProjectIndex.build(tmp_path))
               if r.metadata.get("rule") == "provider-secret"]
    assert [r.metadata["provider"] for r in results] == [provider]
    assert results[0].metadata["line"] == 2
    assert value not in results[0].description and value not in results[0].title
    assert results[0].severity in (Severity.CRITICAL, Severity.HIGH)


def test_example_keys_and_plain_text_are_not_flagged(tmp_path):
    from src.analyzers.security_analyzer import SecurityLeakAnalyzer
    write(tmp_path / "docs.md", "AWS example: " + "AK" + "IA" + "IOSFODNN7EXAMPLE\nnothing here\n")
    assert SecurityLeakAnalyzer().analyze(ProjectIndex.build(tmp_path)) == []
