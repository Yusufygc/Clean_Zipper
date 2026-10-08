"""Yorumlardaki TODO / FIXME / HACK / XXX işaretleri. Yalnızca yorum metnine bakar (string içi sayılmaz)."""
import re
from dataclasses import dataclass
from typing import List

MARKER = re.compile(r'\b(TODO|FIXME|HACK|XXX)\b')
SNIPPET_LENGTH = 100


@dataclass(frozen=True)
class TodoItem:
    line: int
    marker: str
    text: str


def find_todos(raw: str, no_comments: str) -> List[TodoItem]:
    """`no_comments`: aynı uzunlukta, yorumları boşlukla değiştirilmiş metin. İşaret yorum içindeyse (orada boşluk
    var) öğe sayılır. `raw` ile `no_comments` uzunlukları farklıysa (satır sonu normalleştirme) `raw` hizalanır."""
    if len(raw) != len(no_comments):
        raw = raw.replace('\r\n', '\n').replace('\r', '\n')
    if len(raw) != len(no_comments):
        return []
    items = []
    for match in MARKER.finditer(raw):
        if no_comments[match.start():match.end()].strip():
            continue                                         # kod veya string içinde
        line_end = raw.find('\n', match.end())
        snippet = raw[match.end():line_end if line_end >= 0 else len(raw)].strip(' \t\r:-—)(*/#')
        items.append(TodoItem(raw.count('\n', 0, match.start()) + 1, match.group(1), snippet[:SNIPPET_LENGTH]))
    return items
