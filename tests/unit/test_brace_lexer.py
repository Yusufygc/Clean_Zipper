"""Brace motorunun temizleme (yorum/string/char/regex) aşaması."""
import pytest

from src.languages import default_languages


def strip(language_id, source):
    lang = default_languages.get(language_id)
    no_comments, clean = lang._strip(source)
    assert len(no_comments) == len(clean) == len(source)          # ofsetler korunur
    assert no_comments.count("\n") == clean.count("\n") == source.count("\n")
    return no_comments, clean


@pytest.mark.parametrize("language_id", ["c", "cpp", "java", "csharp", "javascript", "typescript", "go", "rust"])
def test_comments_are_blanked_and_line_count_preserved(language_id):
    src = "a // line { \n/* block \n { } */ b\n"
    no_comments, clean = strip(language_id, src)
    assert "{" not in no_comments and "{" not in clean
    assert no_comments.split("\n")[0].strip() == "a"
    assert no_comments.split("\n")[2].strip() == "b"


def test_comment_markers_inside_strings_are_not_comments():
    no_comments, clean = strip("javascript", 'const u = "http://x.y/*z*/"; // gerçek yorum\n')
    assert 'http://x.y/*z*/' in no_comments          # string içeriği import için korunur
    assert 'http' not in clean and 'gerçek' not in no_comments


def test_unterminated_block_comment_blanks_to_end_of_file():
    _, clean = strip("c", "int a; /* açık kalan\nint b; {")
    assert clean.strip() == "int a;"


def test_unterminated_string_does_not_swallow_following_lines():
    _, clean = strip("javascript", "const a = 'it\nconst b = 1;\n")
    assert "const b = 1;" in clean


def test_js_regex_literal_with_quote_does_not_desync():
    src = "const re = /[\"']+/g;\nconst s = 'x';\nfoo();\n"
    _, clean = strip("javascript", src)
    assert "foo();" in clean and "[" not in clean.split("\n")[0].replace("const re =", "")


def test_js_division_is_not_a_regex():
    _, clean = strip("javascript", "const q = a / b / c; const t = 'x';\n")
    assert "a / b / c" in clean


def test_js_template_literal_multiline_is_blanked():
    _, clean = strip("javascript", "const t = `a\n{ b }\n`; run();\n")
    assert "{" not in clean and "run();" in clean


def test_rust_lifetimes_are_not_char_literals_but_chars_are():
    _, clean = strip("rust", "fn f<'a>(x: &'a str) -> &'a str { let c = '{'; x }\n")
    assert "'a" in clean                       # yaşam süresi kod olarak kalır
    assert clean.count("{") == 1               # '{' char sabiti silinir, fonksiyon gövdesi kalır


def test_rust_raw_string_with_hashes_and_quotes():
    _, clean = strip("rust", 'let s = r#"} { "quoted" "#; next();\n')
    assert "{" not in clean and "}" not in clean and "next();" in clean


def test_cpp_digit_separator_and_raw_string():
    _, clean = strip("cpp", 'int n = 1\'000\'000; auto s = R"d(} { // x)d"; end();\n')
    assert "1'000'000" in clean
    assert "{" not in clean and "end();" in clean


def test_csharp_verbatim_and_interpolated_strings():
    src = 'var a = @"C:\\dir\\ ""{q}"" "; var b = $"v {x}"; end();\n'
    _, clean = strip("csharp", src)
    assert "{" not in clean and "end();" in clean


def test_go_raw_string_multiline_and_rune():
    _, clean = strip("go", "x := `satır1 {\nsatır2 }`\ny := '}'\nz()\n")
    assert "{" not in clean and "}" not in clean and "z()" in clean


def test_java_text_block():
    _, clean = strip("java", 'String t = """\n  { metin }\n  """;\nrun();\n')
    assert "{" not in clean and "run();" in clean


def test_line_classification_counts():
    lang = default_languages.get("c")
    src = "// başlık\n\nint a; // sonda yorum\n/* iki\n satır */\nint b;\n"
    m = lang.analyze(src)
    assert (m.total_lines, m.blank_lines, m.comment_lines, m.code_lines) == (6, 1, 3, 2)


def test_crlf_and_trailing_newline_line_count():
    m = default_languages.get("java").analyze("class A {\r\n}\r\n")
    assert m.total_lines == 2
    assert default_languages.get("java").analyze("").total_lines == 0


def test_preprocessor_lines_with_braces_are_hidden_from_structure_but_includes_are_kept():
    lang = default_languages.get("c")
    src = '#include <stdio.h>\n#define BLOCK { \\\n  call(); }\nint f(int a) { return a; }\n'
    m = lang.analyze(src)
    assert m.imports == ["stdio.h"]
    assert [f.name for f in m.functions] == ["f"] and m.parse_ok
