"""Read while it converts: Scribe's streamed HTML, as whole blocks (PRD 8.1.3).

Scribe pushes the free ``html_stream`` preview in ``chunk`` events that end
anywhere, often in the middle of a word or a tag. QUILL never shows a raw
chunk: a half-built line would change under the caret and on the braille
line. :class:`BlockAssembler` keeps what has arrived and hands back only
**complete blocks** -- a whole paragraph, heading, list item, table row or
quotation -- once its closing tag (or the next block's opening tag) has come.

The blocks are plain text, never Markdown: ``#`` and ``*`` would be spoken
(accessibility review, 2026-11-21). Headings and list items are simply their
own lines; :func:`block_lines` joins them with a blank line between blocks so
paragraph navigation finds each one.

Nothing here is logged: chunk text is document text (PRD 10.2.5). wx-free.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

#: Elements that make one block of their own.
BLOCK_TAGS = frozenset({
    "p",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "li",
    "blockquote",
    "pre",
    "tr",
    "figcaption",
    "caption",
    "dt",
    "dd",
    "div",
})
#: Elements whose text is never shown.
_SKIPPED = frozenset({"script", "style", "head", "title"})
_SPACES = re.compile(r"[ \t\r\n\f\v]+")


class BlockAssembler(HTMLParser):
    """Feed it chunks; it returns the blocks each chunk completed."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._text: list[str] = []
        self._ready: list[str] = []
        self._depth = 0  # inside script/style
        self._cell = False

    # -- the public side ------------------------------------------------------

    def push(self, chunk: str) -> list[str]:
        """Add *chunk*; return the blocks it completed, in order (may be none)."""
        if chunk:
            self.feed(chunk)
        return self._take()

    def finish(self) -> list[str]:
        """The stream has ended: whatever text is left is the last block."""
        self.close()
        self._end_block()
        return self._take()

    # -- HTMLParser ----------------------------------------------------------

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        name = tag.lower()
        if name in _SKIPPED:
            self._depth += 1
        elif name in BLOCK_TAGS:
            self._end_block()  # a new block closes any text left open
        elif name == "br":
            self._text.append("\n")
        elif name in ("td", "th"):
            if self._cell:
                self._text.append(", ")  # cells of one row read as one line
            self._cell = True
        elif name == "img":
            alt = dict(attrs).get("alt") or ""
            if alt.strip():
                self._text.append(f" {alt.strip()} ")

    def handle_endtag(self, tag: str) -> None:
        name = tag.lower()
        if name in _SKIPPED:
            self._depth = max(0, self._depth - 1)
        elif name in BLOCK_TAGS:
            self._end_block()

    def handle_data(self, data: str) -> None:
        if not self._depth:
            self._text.append(data)

    # -- helpers --------------------------------------------------------------

    def _end_block(self) -> None:
        self._cell = False
        raw = "".join(self._text)
        self._text = []
        lines = [_SPACES.sub(" ", line).strip() for line in raw.split("\n")]
        text = "\n".join(line for line in lines if line)
        if text:
            self._ready.append(text)

    def _take(self) -> list[str]:
        ready, self._ready = self._ready, []
        return ready


def block_lines(blocks: list[str], *, after_text: bool) -> str:
    """*blocks* as text to add at the end of a document: a blank line between
    blocks, and one before the first when the document already has text."""
    if not blocks:
        return ""
    body = "\n\n".join(blocks)
    return ("\n\n" + body) if after_text else body


def block_at(text: str, offset: int) -> str:
    """The block (paragraph) holding *offset*, for keeping the reading place."""
    start = text.rfind("\n\n", 0, max(0, offset))
    start = 0 if start < 0 else start + 2
    end = text.find("\n\n", offset)
    return text[start : len(text) if end < 0 else end].strip()


def offset_of_block(text: str, block: str) -> int:
    """Where *block* starts in *text* (matched by its words, not its index:
    the finished document may add a title or picture descriptions), else 0."""
    wanted = _SPACES.sub(" ", block).strip()
    if not wanted:
        return 0
    # Flatten runs of white space to one, remembering where each kept
    # character came from, so a match maps back to the original offset.
    flat: list[str] = []
    origin: list[int] = []
    for index, char in enumerate(text):
        if char.isspace():
            if flat and flat[-1] == " ":
                continue
            char = " "
        flat.append(char)
        origin.append(index)
    found = "".join(flat).find(wanted[:80])
    return origin[found] if found >= 0 else 0


__all__ = ["BLOCK_TAGS", "BlockAssembler", "block_at", "block_lines", "offset_of_block"]
