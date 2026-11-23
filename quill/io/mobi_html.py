"""Turn a Kindle book's HTML into a document a screen-reader user can move through.

The text inside a MOBI (:mod:`quill.io.mobi_read`) is Kindle HTML: paragraphs
dressed with ``height`` and ``width``, ``<font size="6">`` where a heading was,
``<mbp:pagebreak>`` between sections, and pictures as ``<img recindex=...>``.
This module cleans it into ordinary HTML and hands that to QUILL's own HTML
reader (:func:`quill.core.html_to_markdown.html_to_markdown`), so a Kindle book
opens the way an HTML page does: paragraphs, lists, tables, links and pictures.

**Headings are inferred, and conservatively.** A MOBI has no heading markup;
the book's maker wrote large, bold type instead. :func:`heading_levels` (pure,
tested on its own) makes a paragraph a heading only when all of its text is in
one font size of 4 or more (bold too, at size 4), it stands alone (not in a
list or a table, no picture in it), and it is short. The largest such size in
the book is heading 1, the next heading 2, and so on, so a book whose title is
size 7 and a book whose title is size 6 both start at heading 1. A size that
covers most of the book's paragraphs is its body text, not a heading. When the
book does carry real ``<h1>``-``<h6>`` tags, nothing is inferred.

A page break becomes nothing: it is where the Kindle turns the page, and a
line saying so between every section is noise to a listener.

wx-free; strict-typed.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable
from dataclasses import dataclass
from html.parser import HTMLParser

from quill.core.html_to_markdown import html_to_markdown

__all__ = [
    "HEADINGS_INFERRED_NOTE",
    "KindleParagraph",
    "heading_levels",
    "kindle_html_to_markdown",
]

#: Said once when a book opens with headings this module inferred.
HEADINGS_INFERRED_NOTE = (
    "This book has no real headings, so they were made from its large or bold text; "
    "some may be at the wrong level or missing."
)

#: A heading is at most this many words, and this many characters.
MAX_HEADING_WORDS = 20
MAX_HEADING_CHARS = 200
#: The Kindle's normal text size; headings are larger.
_BODY_SIZE = 3
#: A size used by more than this share of the book's paragraphs is its body text.
_BODY_SHARE = 0.5
#: Below this many paragraphs, the share above proves nothing.
_SHARE_MIN_PARAGRAPHS = 6

#: Tags kept as they are (attributes dropped); everything else keeps only its text.
_KEPT = frozenset({
    "p", "b", "strong", "i", "em", "ul", "ol", "li", "table", "tr", "td", "th",
    "br", "hr", "blockquote", "pre", "code", "sup", "sub",
    "h1", "h2", "h3", "h4", "h5", "h6",
})  # fmt: skip
_VOID = frozenset({"br", "hr", "img"})
#: Inside these, a ``<p>`` is unwrapped: a list item or a cell is one block.
_CONTAINERS = frozenset({"li", "td", "th"})
_LINK_SCHEMES = re.compile(r"^(?:https?:|mailto:)", re.IGNORECASE)
#: A block that starts here ends a ``<p>`` the book never closed.
_ENDS_A_PARAGRAPH = frozenset({
    "p", "ul", "ol", "li", "table", "div", "blockquote", "mbp:pagebreak",
    "h1", "h2", "h3", "h4", "h5", "h6",
})  # fmt: skip
#: An alt that only names the file, or says "image": no description at all.
_NOT_A_DESCRIPTION = re.compile(
    r"^(?:image|picture|img|photo|figure|[\w.-]+\.(?:jpe?g|png|gif|bmp|svg|webp))$",
    re.IGNORECASE,
)
_TRUE_HEADING = re.compile(r"<h[1-6]\b", re.IGNORECASE)

#: Gives a picture's link and default alt text by its ``recindex``, or ``None``.
PictureLink = Callable[[int], str | None]

_Token = tuple[str, str, dict[str, str]]  # (kind, tag or text, attributes)


@dataclass(frozen=True, slots=True)
class KindleParagraph:
    """What :func:`heading_levels` needs to know about one paragraph."""

    text: str
    #: The one font size all its text is in, or ``None`` when it is mixed.
    size: int | None = None
    bold: bool = False
    has_picture: bool = False
    #: Inside a list item or a table cell.
    nested: bool = False


def heading_levels(paragraphs: list[KindleParagraph]) -> list[int | None]:
    """The heading level of each paragraph, or ``None`` for an ordinary one."""
    candidates = [_is_candidate(paragraph) for paragraph in paragraphs]
    sizes = [p.size for p, ok in zip(paragraphs, candidates, strict=True) if ok and p.size]
    top_level = sum(1 for p in paragraphs if not p.nested)
    body_sizes = {
        size
        for size in set(sizes)
        if top_level >= _SHARE_MIN_PARAGRAPHS and sizes.count(size) > top_level * _BODY_SHARE
    }
    ranked = sorted(set(sizes) - body_sizes, reverse=True)
    levels: list[int | None] = []
    for paragraph, ok in zip(paragraphs, candidates, strict=True):
        if ok and paragraph.size in ranked:
            levels.append(min(ranked.index(paragraph.size) + 1, 6))
        else:
            levels.append(None)
    return levels


def _is_candidate(paragraph: KindleParagraph) -> bool:
    size = paragraph.size
    if size is None or size <= _BODY_SIZE or paragraph.nested or paragraph.has_picture:
        return False
    if size == _BODY_SIZE + 1 and not paragraph.bold:
        return False
    words = paragraph.text.split()
    return 0 < len(words) <= MAX_HEADING_WORDS and len(paragraph.text) <= MAX_HEADING_CHARS


def kindle_html_to_markdown(source: str, picture_link: PictureLink) -> tuple[str, int]:
    """The book as Markdown, and how many headings were inferred."""
    tokens = _tokenize(source)
    infer = not _TRUE_HEADING.search(source)
    paragraphs, starts = _paragraphs(tokens)
    levels = heading_levels(paragraphs) if infer else [None] * len(paragraphs)
    heading_at = {
        start: (level, paragraph.text)
        for start, level, paragraph in zip(starts, levels, paragraphs, strict=True)
        if level is not None
    }
    clean = _promote_header_rows(_serialize(tokens, heading_at, picture_link))
    return html_to_markdown(clean), len(heading_at)


class _Tokenizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tokens: list[_Token] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tokens.append(("start", tag, {k: v or "" for k, v in attrs}))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in _VOID:
            self.tokens.append(("end", tag, {}))

    def handle_endtag(self, tag: str) -> None:
        self.tokens.append(("end", tag, {}))

    def handle_data(self, data: str) -> None:
        self.tokens.append(("data", data, {}))


def _tokenize(source: str) -> list[_Token]:
    parser = _Tokenizer()
    parser.feed(source)
    parser.close()
    return parser.tokens


def _font_size(attrs: dict[str, str], inherited: int | None) -> int | None:
    value = attrs.get("size", "").strip()
    if not value:
        return inherited
    if value[0] in "+-" and value[1:].isdigit():
        return (inherited or _BODY_SIZE) + int(value)
    return int(value) if value.isdigit() else inherited


def _paragraphs(tokens: list[_Token]) -> tuple[list[KindleParagraph], list[int]]:
    """Every ``<p>``, with the token index it starts at."""
    paragraphs: list[KindleParagraph] = []
    starts: list[int] = []
    depth = 0  # open list items and cells
    sizes: list[int | None] = [None]
    bold = 0
    current: tuple[int, bool] | None = None  # (start token, nested)
    runs: list[tuple[int | None, bool]] = []
    text: list[str] = []
    picture = False

    def close() -> None:
        nonlocal current
        if current is None:
            return
        words = " ".join("".join(text).split())
        run_sizes = {size for size, _bold in runs}
        paragraphs.append(
            KindleParagraph(
                text=words,
                size=run_sizes.pop() if len(run_sizes) == 1 else None,
                bold=bool(runs) and all(is_bold for _size, is_bold in runs),
                has_picture=picture,
                nested=current[1],
            )
        )
        starts.append(current[0])
        current = None

    for index, (kind, value, attrs) in enumerate(tokens):
        if kind == "start":
            if value in _ENDS_A_PARAGRAPH and value != "p":
                close()  # a <p> never closed ends where the next block starts
            if value in _CONTAINERS:
                depth += 1
            elif value == "font":
                sizes.append(_font_size(attrs, sizes[-1]))
            elif value in {"b", "strong"}:
                bold += 1
            elif value == "img" and current is not None:
                picture = True
            elif value == "p":
                close()
                current, runs, text, picture = (index, depth > 0), [], [], False
        elif kind == "end":
            if value in _CONTAINERS:
                depth = max(0, depth - 1)
            elif value == "font" and len(sizes) > 1:
                sizes.pop()
            elif value in {"b", "strong"}:
                bold = max(0, bold - 1)
            elif value == "p":
                close()
        elif current is not None:
            text.append(value)
            if value.strip():
                runs.append((sizes[-1], bold > 0))
    close()
    return paragraphs, starts


def _serialize(
    tokens: list[_Token], heading_at: dict[int, tuple[int, str]], picture_link: PictureLink
) -> str:
    out: list[str] = []
    depth = 0
    skip_until_p_end = False
    links: list[bool] = []  # one per open <a>: whether it was kept
    pictures = 0
    for index, (kind, value, attrs) in enumerate(tokens):
        if skip_until_p_end:
            if kind == "end" and value == "p":
                skip_until_p_end = False
                continue
            if not (kind == "start" and value in _ENDS_A_PARAGRAPH):
                continue
            skip_until_p_end = False  # a <p> never closed: the next block ends it
        if kind == "data":
            out.append(html.escape(value, quote=False))
        elif kind == "start":
            if index in heading_at:
                level, words = heading_at[index]
                out.append(f"<h{level}>{html.escape(words, quote=False)}</h{level}>")
                skip_until_p_end = True
            elif value == "img":
                pictures += 1
                out.append(_picture(attrs, pictures, picture_link))
            elif value == "a":
                href = attrs.get("href", "").strip()
                keep = bool(_LINK_SCHEMES.match(href))
                links.append(keep)
                if keep:
                    out.append(f'<a href="{html.escape(href)}">')
            elif value == "p" and depth:
                continue  # unwrapped: its end leaves the space between two
            elif value in _KEPT:
                if value in _CONTAINERS:
                    depth += 1
                out.append(f"<{value}>")
        else:
            if value == "a":
                if links and links.pop():
                    out.append("</a>")
            elif value == "p" and depth:
                out.append(" ")
            elif value in _KEPT and value not in _VOID:
                if value in _CONTAINERS:
                    depth = max(0, depth - 1)
                out.append(f"</{value}>")
    return "".join(out)


def _promote_header_rows(clean: str) -> str:
    """A table whose first row is all bold cells has that row as its header.

    The Kindle writes a header row as ordinary cells in bold; read as it is, the
    table would have an empty header and its real one as the first data row.
    """

    def promote(match: re.Match[str]) -> str:
        bold = [_BOLD_CELL.match(cell) for cell in _CELL.findall(match.group(2))]
        words = [found.group(1) for found in bold if found is not None]
        if not bold or len(words) != len(bold):
            return match.group(0)
        return match.group(1) + "".join(f"<th>{word}</th>" for word in words) + "</tr>"

    return _FIRST_ROW.sub(promote, clean)


_FIRST_ROW = re.compile(r"(<table><tr>)(.*?)</tr>", re.DOTALL)
_CELL = re.compile(r"<td>(.*?)</td>", re.DOTALL)
_BOLD_CELL = re.compile(r"^\s*<(?:b|strong)>([^<]*)</(?:b|strong)>\s*$")


def _picture(attrs: dict[str, str], number: int, picture_link: PictureLink) -> str:
    """An ``<img>`` the HTML reader turns into ``![alt](src)``, or nothing."""
    index_text = attrs.get("recindex", "").strip()
    if not index_text.isdigit():
        return ""
    source = picture_link(int(index_text))
    if source is None:
        return ""
    alt = " ".join(attrs.get("alt", "").split())
    if not alt or _NOT_A_DESCRIPTION.match(alt):
        alt = f"Picture {number}"
    return f'<img src="{html.escape(source)}" alt="{html.escape(alt)}">'
