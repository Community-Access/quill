"""Show notes as structure: headings, paragraphs, lists, links and timestamps.

qc.md 5c. Cast showed an episode's notes as one plain block with the HTML
stripped, so a five-hundred-word description with three sections was a wall,
and every link was a string of characters to read out and retype. This module
reads the HTML the podcast wrote and keeps what a listener navigates by:

* :class:`Block` -- one heading (with its level), paragraph, list item or
  preformatted block, with its text;
* :class:`Span` -- a link (``url``) or a timestamp (``ms``) inside the text, by
  absolute offset into :attr:`NotesDocument.text`, so a reader can move
  between them with Tab and act on them with Enter;
* :class:`NotesDocument` -- the whole thing: the flattened text one reader
  shows, the blocks the exporters walk, the links, the timestamps and the
  headings, and the two empty cases said in words.

wx-free and strict-typed, because the same document feeds the reader, the four
copy formats (:mod:`quill.core.podcasts.notes_export`) and the browser page.
A timestamp is ``h:mm:ss`` or ``m:ss`` with a sensible seconds field; a bare
``12:34`` in prose is far more often a time into the episode than a clock.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import unescape
from html.parser import HTMLParser

HEADING = "heading"
PARAGRAPH = "paragraph"
LIST_ITEM = "list_item"
PREFORMATTED = "pre"

_BULLET = "• "
_TIMESTAMP = re.compile(r"(?<![\d:])(?:(\d{1,2}):)?(\d{1,2}):(\d{2})(?![\d:])")
_IMAGE_TAGS = ("img", "picture", "video", "audio", "iframe", "figure")


@dataclass(frozen=True, slots=True)
class Span:
    """A link or a timestamp: where it sits in the text, and where it goes."""

    start: int
    end: int
    url: str = ""
    ms: int = -1

    @property
    def is_timestamp(self) -> bool:
        return self.ms >= 0


@dataclass(frozen=True, slots=True)
class Block:
    """One structural unit of the notes."""

    kind: str
    text: str
    level: int = 0
    #: Links within this block, offsets relative to ``text``.
    links: tuple[Span, ...] = ()
    #: Where this block's first character sits in the document text.
    offset: int = 0


@dataclass(frozen=True, slots=True)
class NotesDocument:
    """The notes, read."""

    text: str
    blocks: tuple[Block, ...]
    links: tuple[Span, ...]
    timestamps: tuple[Span, ...]
    #: The source HTML referenced an image or other media.
    had_media: bool = False
    link_count: int = field(default=0)

    @property
    def is_empty(self) -> bool:
        return not self.text.strip()

    @property
    def image_only(self) -> bool:
        return self.is_empty and self.had_media

    @property
    def headings(self) -> tuple[Block, ...]:
        return tuple(block for block in self.blocks if block.kind == HEADING)

    @property
    def word_count(self) -> int:
        return len(self.text.split())

    def unique_links(self) -> tuple[Span, ...]:
        """Links with duplicate addresses folded to the first occurrence."""
        seen: set[str] = set()
        kept: list[Span] = []
        for span in self.links:
            key = span.url.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            kept.append(span)
        return tuple(kept)

    def link_title(self, span: Span) -> str:
        """The link's own text, else its address."""
        title = " ".join(self.text[span.start : span.end].split())
        return title or span.url


def parse_timestamp_ms(text: str) -> int:
    """``"1:02:03"`` or ``"12:34"`` to milliseconds; ``-1`` when it is not one."""
    match = _TIMESTAMP.fullmatch(text.strip())
    if match is None:
        return -1
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2))
    seconds = int(match.group(3))
    if seconds >= 60 or (match.group(1) is not None and minutes >= 60):
        return -1
    return ((hours * 60 + minutes) * 60 + seconds) * 1000


def find_timestamps(text: str, base: int = 0) -> tuple[Span, ...]:
    """Every timestamp in *text*, as spans offset by *base*."""
    found: list[Span] = []
    for match in _TIMESTAMP.finditer(text):
        ms = parse_timestamp_ms(match.group(0))
        if ms < 0:
            continue
        found.append(Span(base + match.start(), base + match.end(), ms=ms))
    return tuple(found)


class _NotesParser(HTMLParser):
    """HTML to blocks. Tolerant: podcast HTML is rarely well formed."""

    _BLOCK_TAGS = {"p", "div", "section", "article", "blockquote", "br", "hr", "tr", "table"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[Block] = []
        self.had_media = False
        self._parts: list[str] = []
        self._kind = PARAGRAPH
        self._level = 0
        self._links: list[tuple[int, int, str]] = []
        self._open_link: tuple[int, str] | None = None
        self._list_depth = 0
        self._pre = False
        self._skip = 0  # inside <script>/<style>

    # -- block boundaries ------------------------------------------------------

    def _current_len(self) -> int:
        return sum(len(part) for part in self._parts)

    def _flush(self) -> None:
        raw = "".join(self._parts)
        text = raw if self._pre else " ".join(raw.split())
        if self._open_link is not None:
            start, url = self._open_link
            self._links.append((start, self._current_len(), url))
            self._open_link = (0, url)
        links: list[Span] = []
        if text and not self._pre:
            # Re-map link offsets after whitespace collapsing by re-finding each
            # link's text; a link whose text vanished in the collapse is kept on
            # the nearest position so it is never lost.
            cursor = 0
            for start, end, url in self._links:
                fragment = " ".join(raw[start:end].split())
                if not fragment:
                    continue
                at = text.find(fragment, cursor)
                if at < 0:
                    at = text.find(fragment)
                if at < 0:
                    continue
                links.append(Span(at, at + len(fragment), url=url))
                cursor = at + len(fragment)
        elif text:
            links = [Span(s, e, url=u) for s, e, u in self._links if e > s]
        if text:
            if self._kind == LIST_ITEM:
                shift = len(_BULLET)
                text = _BULLET + text
                links = [Span(s.start + shift, s.end + shift, url=s.url) for s in links]
            self.blocks.append(Block(self._kind, text, self._level, tuple(links)))
        self._parts = []
        self._links = []
        if self._open_link is not None:
            self._open_link = (0, self._open_link[1])
        self._kind = LIST_ITEM if self._list_depth else PARAGRAPH
        self._level = 0

    # -- tags ------------------------------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in ("script", "style"):
            self._skip += 1
            return
        if tag in _IMAGE_TAGS:
            self.had_media = True
            return
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._flush()
            self._kind = HEADING
            self._level = int(tag[1])
            return
        if tag in ("ul", "ol"):
            self._flush()
            self._list_depth += 1
            self._kind = LIST_ITEM
            return
        if tag == "li":
            self._flush()
            self._kind = LIST_ITEM
            return
        if tag == "pre":
            self._flush()
            self._pre = True
            self._kind = PREFORMATTED
            return
        if tag in self._BLOCK_TAGS:
            self._flush()
            return
        if tag == "a":
            href = next((value or "" for name, value in attrs if name.lower() == "href"), "")
            href = href.strip()
            if href and not href.lower().startswith(("javascript:", "data:")):
                self._open_link = (self._current_len(), href)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in ("script", "style"):
            self._skip = max(0, self._skip - 1)
            return
        if tag in (
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "li",
            "p",
            "div",
            "section",
            "article",
            "blockquote",
            "tr",
        ):
            self._flush()
            return
        if tag in ("ul", "ol"):
            self._flush()
            self._list_depth = max(0, self._list_depth - 1)
            self._kind = LIST_ITEM if self._list_depth else PARAGRAPH
            return
        if tag == "pre":
            self._flush()
            self._pre = False
            return
        if tag == "a" and self._open_link is not None:
            start, url = self._open_link
            end = self._current_len()
            if end > start:
                self._links.append((start, end, url))
            self._open_link = None

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        self._parts.append(data)

    def close(self) -> None:
        super().close()
        self._flush()


def render_notes(html: str) -> NotesDocument:
    """Read *html* into a :class:`NotesDocument`. Never raises."""
    source = html or ""
    if "<" not in source:
        # Plain text notes: paragraphs on blank lines, every line otherwise.
        parser_blocks: list[Block] = []
        had_media = False
        for chunk in re.split(r"\n\s*\n", unescape(source)):
            text = " ".join(chunk.split())
            if text:
                parser_blocks.append(Block(PARAGRAPH, text))
        blocks = parser_blocks
    else:
        parser = _NotesParser()
        try:
            parser.feed(source)
            parser.close()
        except Exception:  # noqa: BLE001 - broken HTML is still notes
            parser._flush()
        blocks = parser.blocks
        had_media = parser.had_media
    return _assemble(blocks, had_media)


def _assemble(blocks: list[Block], had_media: bool) -> NotesDocument:
    pieces: list[str] = []
    placed: list[Block] = []
    links: list[Span] = []
    timestamps: list[Span] = []
    offset = 0
    for block in blocks:
        placed.append(Block(block.kind, block.text, block.level, block.links, offset=offset))
        for span in block.links:
            links.append(Span(offset + span.start, offset + span.end, url=span.url))
        timestamps.extend(find_timestamps(block.text, offset))
        pieces.append(block.text)
        offset += len(block.text) + 1
    text = "\n".join(pieces)
    link_spans = tuple(links)
    # A timestamp inside a link is the link's business (Enter opens it).
    inside_link = {
        (t.start, t.end)
        for t in timestamps
        for link in link_spans
        if link.start <= t.start and t.end <= link.end
    }
    kept = tuple(t for t in timestamps if (t.start, t.end) not in inside_link)
    return NotesDocument(
        text=text,
        blocks=tuple(placed),
        links=link_spans,
        timestamps=kept,
        had_media=had_media,
        link_count=len({s.url.strip().lower() for s in link_spans}),
    )


def empty_sentence(doc: NotesDocument, *, what: str = "This episode") -> str:
    """What to show instead of an empty field."""
    if doc.image_only:
        return "The show notes are an image with no text -- View in Browser will show it."
    return f"{what} has no show notes."


__all__ = [
    "HEADING",
    "LIST_ITEM",
    "PARAGRAPH",
    "PREFORMATTED",
    "Block",
    "NotesDocument",
    "Span",
    "empty_sentence",
    "find_timestamps",
    "parse_timestamp_ms",
    "render_notes",
]
