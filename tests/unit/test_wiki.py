"""Wiki bütünlüğü: kırık link, öksüz sayfa ve indeks eksiği olmamalı (`docs/wiki/rules.md`: "Wiki'yi lint et")."""
import re
from pathlib import Path

WIKI = Path(__file__).resolve().parents[2] / "docs" / "wiki"
LINK = re.compile(r"\[\[([^\]\n]+)\]\]")
CODE_SPAN = re.compile(r"`[^`\n]*`")


def pages():
    return {p.stem: p.read_text(encoding="utf-8") for p in sorted(WIKI.glob("*.md"))}


def links(text: str):
    """Kod aralığı içindeki örnek sözdizimi sayılmaz."""
    return LINK.findall(CODE_SPAN.sub("", text))


def test_there_is_an_index_and_the_core_pages():
    assert {"index", "rules", "log", "architecture", "roadmap", "decisions", "analyzers", "backend-api", "testing"} <= set(pages())


def test_every_link_points_to_an_existing_page():
    existing = set(pages())
    broken = {(name, target) for name, text in pages().items() for target in links(text) if target not in existing}
    assert broken == set()


def test_every_page_is_listed_in_the_index():
    listed = set(links(pages()["index"]))
    assert set(pages()) - {"index"} <= listed


def test_every_page_is_linked_from_another_page():
    inbound = {name: set() for name in pages()}
    for name, text in pages().items():
        for target in links(text):
            if target in inbound and target != name:
                inbound[target].add(name)
    assert [name for name, sources in inbound.items() if not sources] == []


def test_claude_md_points_to_the_wiki_entry_points():
    claude = (WIKI.parents[1] / "CLAUDE.md").read_text(encoding="utf-8")
    for page in ("docs/wiki/index.md", "docs/wiki/rules.md", "docs/wiki/log.md"):
        assert page in claude
