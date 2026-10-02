"""Show notes as a document a listener can move around in (qc.md 5c).

Show notes are where a podcast says what an episode is, and Cast used to show
them as one block of text with the HTML stripped out: a five-hundred-word
description with three sections was a wall, every link was a string of
characters to read out and retype, and "12:34 -- the interview" was a number
somebody had to carry over to Go to Position by hand.

This module keeps what the HTML *meant*. It reads the notes into blocks
(headings, paragraphs, list items) made of runs (plain, bold, italic, linked),
lays them out as the text the Notes reader shows, and records where in that text
every heading, link and timestamp sits -- so the reader can move between them
with a key, and the copy formats in :mod:`quill.core.podcasts.notes_export` can
rebuild the notes as plain text, Markdown, HTML or RTF from one reading.

Three rules it keeps:

* **Positions are into ``NotesDocument.text``** with ``\\n`` line endings, which
  is how a Windows rich edit control counts them, so a mark's ``start`` is the
  caret position that lands on it.
* **Only addresses a browser can open become links** -- http and https, through
  :mod:`quill.core.text_links`, the same rule the Links window has always kept.
  A ``javascript:`` href in somebody else's notes is text here, never a link.
* **Nothing is fetched.** An image is counted and its address kept for the
  formats that reference images; this module never reads one.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser

from quill.core import text_links

__all__ = [
    "BLOCK_HEADING",
    "BLOCK_ITEM",
    "BLOCK_PARAGRAPH",
    "Block",
    "Mark",
    "NotesDocument",
    "Run",
    "parse_notes",
    "timestamp_spans",
]

BLOCK_HEADING = "heading"
BLOCK_PARAGRAPH = "paragraph"
BLOCK_ITEM = "item"

_HEADINGS = {f"h{level}": level for level in range(1, 7)}
#: Tags that start and end a paragraph of their own.
_PARAGRAPHS = frozenset({
    "p",
    "div",
    "blockquote",
    "section",
    "article",
    "pre",
    "tr",
    "table",
    "figure",
    "dd",
    "dt",
})
_SKIPPED = frozenset({"script", "style", "head", "title", "noscript", "template"})
_BOLD = frozenset({"b", "strong"})
_ITALIC = frozenset({"i", "em", "cite"})

#: A timestamp a listener would write: ``12:34``, ``1:02:03``, ``(05:00)``. Not
#: part of a longer run of digits and colons, and not a clock time -- "10:30 am"
#: is when something happens, not where in the episode.
_TIMESTAMP = re.compile(r"(?<![\d:/.])(?:(\d{1,2}):)?(\d{1,2}):([0-5]\d)(?![\d:])")
_CLOCK_SUFFIX = re.compile(r"\s*(?:[ap]\.?\s?m\b)", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class Run:
    """A stretch of text with one set of properties."""

    text: str
    href: str = ""
    bold: bool = False
    italic: bool = False
    #: An image's address; ``text`` is then its alternative text. Images take
    #: no room in the reader's text -- they are kept for the formats that
    #: reference them (formatted copy, View in Browser).
    image: str = ""


@dataclass(frozen=True, slots=True)
class Block:
    """One heading, paragraph or list item."""

    kind: str
    runs: tuple[Run, ...]
    level: int = 0
    #: ``"- "`` or ``"3. "`` (indented for a nested list) for a list item.
    marker: str = ""

    @property
    def text(self) -> str:
        return "".join(run.text for run in self.runs if not run.image)


@dataclass(frozen=True, slots=True)
class Mark:
    """Something at a place in the reader's text."""

    start: int
    end: int
    text: str
    #: A link's address.
    target: str = ""
    #: A timestamp's position in the episode, in milliseconds.
    position_ms: int = -1
    #: A heading's level, 1 to 6.
    level: int = 0


@dataclass(frozen=True, slots=True)
class NotesDocument:
    """The notes, read: their blocks, their text, and what is where in it."""

    blocks: tuple[Block, ...] = ()
    text: str = ""
    headings: tuple[Mark, ...] = ()
    links: tuple[Mark, ...] = ()
    timestamps: tuple[Mark, ...] = ()
    #: ``(start, end, style)`` with style "bold", "italic" or "heading".
    styles: tuple[tuple[int, int, str], ...] = ()
    image_count: int = 0
    images: tuple[str, ...] = field(default=())

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()

    @property
    def only_images(self) -> bool:
        """Notes that were nothing but a picture (the stripped case in 5c)."""
        return self.is_empty and self.image_count > 0

    def mark_at(self, marks: tuple[Mark, ...], position: int) -> Mark | None:
        """The mark the caret is on, if any (end-inclusive, so a caret just
        after a link still counts as on it -- where Tab leaves it)."""
        for mark in marks:
            if mark.start <= position <= mark.end:
                return mark
        return None

    def link_at(self, position: int) -> Mark | None:
        return self.mark_at(self.links, position)

    def timestamp_at(self, position: int) -> Mark | None:
        return self.mark_at(self.timestamps, position)

    def next_mark(self, marks: tuple[Mark, ...], position: int, *, forward: bool) -> Mark | None:
        """The next mark after *position*, or the previous one before it."""
        if forward:
            return next((mark for mark in marks if mark.start > position), None)
        return next((mark for mark in reversed(marks) if mark.start < position), None)

    def unique_links(self) -> list[text_links.Link]:
        """Every link once, in order, first title winning (the Links window's rows)."""
        seen: set[str] = set()
        kept: list[text_links.Link] = []
        for mark in self.links:
            key = mark.target.rstrip("/").lower()
            if key in seen:
                continue
            seen.add(key)
            title = mark.text if mark.text.strip() != mark.target else ""
            kept.append(text_links.Link(url=mark.target, text=title))
        return kept


def timestamp_spans(text: str) -> list[tuple[int, int, int]]:
    """``(start, end, milliseconds)`` for every timestamp written in *text*."""
    spans: list[tuple[int, int, int]] = []
    for match in _TIMESTAMP.finditer(text or ""):
        if _CLOCK_SUFFIX.match(text, match.end()):
            continue
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2))
        seconds = int(match.group(3))
        if match.group(1) is not None and minutes > 59:
            continue
        spans.append((match.start(), match.end(), ((hours * 60 + minutes) * 60 + seconds) * 1000))
    return spans


class _NotesParser(HTMLParser):
    """HTML to blocks of runs. Tolerant: somebody else's markup never raises."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[Block] = []
        self.images: list[str] = []
        self._runs: list[Run] = []
        self._kind = BLOCK_PARAGRAPH
        self._level = 0
        self._marker = ""
        self._lists: list[list[int]] = []  # [ordered (0/1), counter]
        self._hrefs: list[str] = []
        self._bold = 0
        self._italic = 0
        self._skip = 0
        self._pre = 0

    # -- blocks ---------------------------------------------------------------

    def _start(self, kind: str, *, level: int = 0, marker: str = "") -> None:
        self._flush()
        self._kind, self._level, self._marker = kind, level, marker

    def _flush(self) -> None:
        runs = _tidy_runs(self._runs)
        if any(run.text.strip() or run.image for run in runs):
            self.blocks.append(
                Block(kind=self._kind, runs=tuple(runs), level=self._level, marker=self._marker)
            )
        self._runs = []
        self._kind, self._level, self._marker = BLOCK_PARAGRAPH, 0, ""

    # -- HTMLParser -----------------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        values = {name.lower(): (value or "") for name, value in attrs}
        if tag in _SKIPPED:
            self._skip += 1
        elif tag in _HEADINGS:
            self._start(BLOCK_HEADING, level=_HEADINGS[tag])
        elif tag in _PARAGRAPHS:
            self._pre += tag == "pre"
            self._start(BLOCK_PARAGRAPH)
        elif tag in ("ul", "ol"):
            self._flush()
            start = values.get("start", "")
            first = int(start) - 1 if start.isdigit() else 0
            self._lists.append([1 if tag == "ol" else 0, first])
        elif tag == "li":
            if not self._lists:
                self._lists.append([0, 0])
            self._lists[-1][1] += 1
            ordered, count = self._lists[-1]
            indent = "  " * (len(self._lists) - 1)
            self._start(BLOCK_ITEM, marker=f"{indent}{count}. " if ordered else f"{indent}- ")
        elif tag == "br":
            self._runs.append(Run("\n"))
        elif tag == "hr":
            self._flush()
        elif tag == "a":
            href = text_links._tidy(values.get("href", ""))  # noqa: SLF001 - one rule
            self._hrefs.append(href if href.lower().startswith(("http://", "https://")) else "")
        elif tag in _BOLD:
            self._bold += 1
        elif tag in _ITALIC:
            self._italic += 1
        elif tag in ("td", "th"):
            self._runs.append(Run(" "))
        elif tag == "img":
            src = values.get("src", "").strip()
            if src.lower().startswith(("http://", "https://")):
                self.images.append(src)
                self._runs.append(Run(" ".join(values.get("alt", "").split()), image=src))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag.lower() not in ("br", "hr", "img"):
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in _SKIPPED:
            self._skip = max(0, self._skip - 1)
        elif tag in _HEADINGS or tag in _PARAGRAPHS or tag == "li":
            if tag == "pre":
                self._pre = max(0, self._pre - 1)
            self._flush()
        elif tag in ("ul", "ol"):
            self._flush()
            if self._lists:
                self._lists.pop()
        elif tag == "a":
            if self._hrefs:
                self._hrefs.pop()
        elif tag in _BOLD:
            self._bold = max(0, self._bold - 1)
        elif tag in _ITALIC:
            self._italic = max(0, self._italic - 1)

    def handle_data(self, data: str) -> None:
        if self._skip or not data:
            return
        text = data if self._pre else re.sub(r"\s+", " ", data)
        href = self._hrefs[-1] if self._hrefs else ""
        self._runs.append(Run(text, href=href, bold=self._bold > 0, italic=self._italic > 0))

    def close(self) -> None:
        super().close()
        self._flush()


def _tidy_runs(runs: list[Run]) -> list[Run]:
    """Collapse the whitespace HTML collapses, across run boundaries."""
    tidied: list[Run] = []
    previous = "\n"
    for run in runs:
        if run.image:
            tidied.append(run)
            continue
        text = run.text
        if text == "\n":
            if tidied and not tidied[-1].image:
                last = tidied[-1]
                tidied[-1] = Run(last.text.rstrip(" "), last.href, last.bold, last.italic)
            tidied.append(run)
            previous = "\n"
            continue
        if previous.endswith((" ", "\n")):
            text = text.lstrip(" ")
        if not text:
            continue
        tidied.append(Run(text, run.href, run.bold, run.italic))
        previous = text
    # Trim the block's own edges, and drop runs that became empty doing it.
    while tidied and not tidied[0].image and not tidied[0].text.strip():
        tidied.pop(0)
    while tidied and not tidied[-1].image and not tidied[-1].text.strip():
        tidied.pop()
    if tidied and not tidied[-1].image:
        last = tidied[-1]
        tidied[-1] = Run(last.text.rstrip(), last.href, last.bold, last.italic)
    if tidied and not tidied[0].image:
        first = tidied[0]
        tidied[0] = Run(first.text.lstrip(), first.href, first.bold, first.italic)
    return tidied


def _plain_blocks(text: str) -> list[Block]:
    """Notes that are not HTML: a blank line is a paragraph, a newline a line."""
    blocks: list[Block] = []
    for chunk in re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n")):
        lines = [" ".join(line.split()) for line in chunk.split("\n")]
        body = "\n".join(line for line in lines if line)
        if body:
            blocks.append(Block(kind=BLOCK_PARAGRAPH, runs=(Run(body),)))
    return blocks


def _split_bare_links(block: Block) -> Block:
    """Turn addresses typed into the text (most of them, in a hand-written note)
    into link runs, in place."""
    runs: list[Run] = []
    for run in block.runs:
        if run.href or run.image:
            runs.append(run)
            continue
        cursor = 0
        for start, end, url in text_links.bare_url_spans(run.text):
            if start > cursor:
                runs.append(Run(run.text[cursor:start], bold=run.bold, italic=run.italic))
            runs.append(Run(run.text[start:end], href=url, bold=run.bold, italic=run.italic))
            cursor = end
        if cursor < len(run.text):
            runs.append(Run(run.text[cursor:], bold=run.bold, italic=run.italic))
    return Block(kind=block.kind, runs=tuple(runs), level=block.level, marker=block.marker)


def parse_notes(content: str) -> NotesDocument:
    """Read *content* (HTML, or plain text) into a :class:`NotesDocument`."""
    content = content or ""
    if "<" in content and ">" in content:
        parser = _NotesParser()
        try:
            parser.feed(content)
            parser.close()
        except Exception:  # noqa: BLE001 - somebody else's HTML must never crash a reader
            parser._flush()  # noqa: SLF001 - keep what was read before the fault
        blocks = parser.blocks
        images = parser.images
    else:
        blocks = _plain_blocks(unescape(content))
        images = []
    return _lay_out([_split_bare_links(block) for block in blocks], images)


def _lay_out(blocks: list[Block], images: list[str]) -> NotesDocument:
    """Join the blocks into the reader's text, recording where everything went."""
    pieces: list[str] = []
    headings: list[Mark] = []
    links: list[Mark] = []
    timestamps: list[Mark] = []
    styles: list[tuple[int, int, str]] = []
    offset = 0
    previous: Block | None = None
    for block in blocks:
        if not block.text.strip():
            continue
        if previous is not None:
            joint = "\n" if previous.kind == block.kind == BLOCK_ITEM else "\n\n"
            pieces.append(joint)
            offset += len(joint)
        block_start = offset
        if block.marker:
            pieces.append(block.marker)
            offset += len(block.marker)
        for run in block.runs:
            if run.image:
                continue
            start = offset
            pieces.append(run.text)
            offset += len(run.text)
            if run.href:
                links.append(Mark(start, offset, run.text.strip(), target=run.href))
            else:
                for ts_start, ts_end, ms in timestamp_spans(run.text):
                    timestamps.append(
                        Mark(
                            start + ts_start,
                            start + ts_end,
                            run.text[ts_start:ts_end],
                            position_ms=ms,
                        )
                    )
            if run.bold:
                styles.append((start, offset, "bold"))
            if run.italic:
                styles.append((start, offset, "italic"))
        if block.kind == BLOCK_HEADING:
            headings.append(Mark(block_start, offset, block.text.strip(), level=block.level))
            styles.append((block_start, offset, "heading"))
        previous = block
    kept = tuple(
        block for block in blocks if block.text.strip() or any(r.image for r in block.runs)
    )
    full = "".join(pieces)
    return NotesDocument(
        blocks=kept,
        text=full,
        headings=tuple(headings),
        links=tuple(_merge_adjacent_links(links, full)),
        timestamps=tuple(timestamps),
        styles=tuple(styles),
        image_count=len(images),
        images=tuple(images),
    )


def _merge_adjacent_links(links: list[Mark], text: str) -> list[Mark]:
    """One link split into runs by its own bold or italic is still one link."""
    merged: list[Mark] = []
    for mark in links:
        if merged and merged[-1].target == mark.target and merged[-1].end == mark.start:
            last = merged[-1]
            merged[-1] = Mark(
                last.start, mark.end, text[last.start : mark.end].strip(), target=mark.target
            )
            continue
        merged.append(mark)
    return merged
