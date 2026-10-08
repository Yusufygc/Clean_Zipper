from src.languages.clones import CloneFinder, normalize

BLOCK = [
    "total = compute_total(items, discount_rate)",
    "if total > maximum_allowed_value:",
    "    raise ValueError('total exceeds the maximum allowed value')",
    "result = format_output(total, currency_code)",
    "logger.info('computed %s', result)",
    "cache[key] = result",
    "notify_listeners(key, result)",
    "return result",
]


def add(finder: CloneFinder, key: str, lines):
    cleaned, numbers = normalize("\n".join(lines))
    finder.add_file(key, cleaned, numbers)


def test_normalize_drops_blank_punctuation_and_import_lines_and_keeps_line_numbers():
    lines, numbers = normalize("import os\n\n{\nvalue = 1\n  value   =   2  \n}\nfrom a import b\n")
    assert lines == ["value = 1", "value = 2"]
    assert numbers == [4, 5]


def test_clone_between_two_files_with_surrounding_differences():
    finder = CloneFinder(window=8)
    add(finder, "a.py", ["alpha = 1", "beta = compute_something(alpha)"] + BLOCK + ["tail_a = finish_a_phase()"])
    add(finder, "b.py", ["gamma = 2", "delta = other_computation(gamma, 9)"] + BLOCK + ["tail_b = finish_b_phase()"])
    groups = finder.find()
    assert len(groups) == 1
    group = groups[0]
    assert group.lines == 8 and group.copies == 2
    assert [(loc.key, loc.start_line, loc.end_line) for loc in group.locations] == [
        ("a.py", 3, 10), ("b.py", 3, 10)]


def test_clone_is_extended_to_maximal_block():
    finder = CloneFinder(window=8)
    longer = BLOCK + ["extra_step_one = prepare_more(result)", "extra_step_two = prepare_even_more(extra_step_one)"]
    add(finder, "a.py", ["head_a = 1_a"] + longer + ["tail_a = 0"])
    add(finder, "b.py", ["head_b = 2_b"] + longer + ["tail_b = 9"])
    (group,) = finder.find()
    assert group.lines == 10
    assert [(loc.start_line, loc.end_line) for loc in group.locations] == [(2, 11), (2, 11)]


def test_different_string_or_number_values_are_not_clones():
    finder = CloneFinder(window=8)
    add(finder, "a.py", BLOCK)
    add(finder, "b.py", [line.replace("maximum", "minimum") for line in BLOCK])
    assert finder.find() == []


def test_identical_files_are_reported_separately_not_as_clones():
    finder = CloneFinder(window=8)
    add(finder, "a.py", BLOCK)
    add(finder, "b.py", BLOCK)
    assert finder.find() == []
    assert finder.identical_files == [("b.py", "a.py")]


def test_clone_inside_one_file():
    finder = CloneFinder(window=8)
    add(finder, "a.py", BLOCK + ["separator_statement = uniquely_named_call()", "another_one = distinct_call()"] + BLOCK)
    (group,) = finder.find()
    assert group.copies == 2 and group.lines == 8
    assert [(loc.start_line, loc.end_line) for loc in group.locations] == [(1, 8), (11, 18)]


def test_short_trivial_windows_are_not_clones():
    finder = CloneFinder(window=8)
    trivial = ["x = 0"] * 12
    add(finder, "a.py", trivial)
    add(finder, "b.py", trivial + ["unique_marker_statement_b = distinct_value_b"])
    assert finder.find() == []


def test_three_copies_form_one_group():
    finder = CloneFinder(window=8)
    for name in ("a.py", "b.py", "c.py"):
        add(finder, name, [f"unique_{name}_first = 1_{name}"] + BLOCK + [f"unique_{name}_last = 2_{name}"])
    (group,) = finder.find()
    assert group.copies == 3 and group.duplicated_lines == 16


def test_partial_overlap_keeps_shorter_partner_without_duplicate_groups():
    finder = CloneFinder(window=8)
    longer = BLOCK + ["extra_step_one = prepare_more(result)", "extra_step_two = prepare_even_more(extra_step_one)"]
    add(finder, "a.py", longer + ["a_only_statement = something_else_entirely_a()"])
    add(finder, "b.py", longer + ["b_only_statement = something_else_entirely_b()"])
    add(finder, "c.py", BLOCK + ["c_only_statement = something_else_entirely_c()"])
    groups = finder.find()
    assert len(groups) == 1
    lengths = sorted((loc.key, loc.end_line - loc.start_line + 1) for loc in groups[0].locations)
    assert lengths == [("a.py", 10), ("b.py", 10), ("c.py", 8)]
