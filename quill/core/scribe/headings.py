"""The headings of a Scribe result, for "Save a Beacon Place" (PRD 8.1.7, 8.7).

A Beacon place can point into a Scribe result at a heading. QUILL's Next Steps
offer the result's headings to choose from, so this reads them from the two
formats a place points into: accessible HTML (``h1`` to ``h6``) and Word
(paragraphs styled Title or Heading 1 to 9). Nothing is installed for it, and
a file that cannot be read simply has no headings.

The rows are written for a list a screen reader reads (accessibility review,
2026-11-21): the heading's own words first, so first-letter navigation works,
then its level in words, and a repeated heading says which one it is
("Results, heading level 2, second").

wx-free.
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

START = "The start of the document"
_ORDINALS = ("first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth")
_WORD = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


@dataclass(frozen=True, slots=True)
class Heading:
    level: int
    text: str


class _HtmlHeadings(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.found: list[Heading] = []
        self._level = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if re.fullmatch(r"h[1-6]", tag):
            self._level = int(tag[1])
            self._parts = []

    def handle_endtag(self, tag: str) -> None:
        if self._level and tag == f"h{self._level}":
            text = " ".join("".join(self._parts).split())
            if text:
                self.found.append(Heading(self._level, text))
            self._level = 0

    def handle_data(self, data: str) -> None:
        if self._level:
            self._parts.append(data)


def html_headings(html: str) -> list[Heading]:
    parser = _HtmlHeadings()
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # noqa: BLE001 - somebody else's HTML never stops the list
        pass
    return parser.found


def docx_headings(path: Path) -> list[Heading]:
    from quill.core.safe_xml import ParseError, fromstring

    try:
        with zipfile.ZipFile(path) as archive:
            root = fromstring(archive.read("word/document.xml"))
    except (OSError, KeyError, zipfile.BadZipFile, ParseError):
        return []
    found: list[Heading] = []
    for paragraph in root.iter(f"{_WORD}p"):
        style = paragraph.find(f"{_WORD}pPr/{_WORD}pStyle")
        name = (style.get(f"{_WORD}val", "") if style is not None else "").replace(" ", "").lower()
        if name == "title":
            level = 1
        elif match := re.fullmatch(r"heading([1-9])", name):
            level = int(match.group(1))
        else:
            continue
        text = " ".join("".join(t.text or "" for t in paragraph.iter(f"{_WORD}t")).split())
        if text:
            found.append(Heading(level, text))
    return found


def document_headings(path: Path) -> list[Heading]:
    """The headings of an HTML or Word file, in order; ``[]`` for anything else."""
    suffix = path.suffix.lower()
    if suffix in (".html", ".htm", ".xhtml"):
        try:
            return html_headings(path.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            return []
    if suffix == ".docx":
        return docx_headings(path)
    return []


def heading_rows(headings: list[Heading]) -> list[str]:
    """The choice list: the start, then each heading, words first."""
    seen: dict[tuple[int, str], int] = {}
    totals: dict[tuple[int, str], int] = {}
    for heading in headings:
        key = (heading.level, heading.text.lower())
        totals[key] = totals.get(key, 0) + 1
    rows = [START]
    for heading in headings:
        key = (heading.level, heading.text.lower())
        seen[key] = seen.get(key, 0) + 1
        row = f"{heading.text}, heading level {heading.level}"
        if totals[key] > 1:
            count = seen[key]
            row += f", {_ORDINALS[count - 1] if count <= len(_ORDINALS) else f'number {count}'}"
        rows.append(row)
    return rows


def heading_path(headings: list[Heading], index: int) -> list[str]:
    """The heading at *index* with the headings it sits under, outermost first."""
    if not 0 <= index < len(headings):
        return []
    path = [headings[index]]
    for heading in reversed(headings[:index]):
        if heading.level < path[0].level:
            path.insert(0, heading)
    return [heading.text for heading in path]


__all__ = [
    "START",
    "Heading",
    "document_headings",
    "heading_path",
    "heading_rows",
    "html_headings",
]
