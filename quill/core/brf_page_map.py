"""BRF page map engine.

The page map splits a :class:`~quill.core.brf_document.BRFDocument` into
:const:`BRFPage` records. Two page-boundary strategies are supported:

1. **Form-feed aware** — every ``\x0c`` (FF) ends a page. The FF itself
   is part of the prior page (it is the terminator). This is the
   correct strategy for any BRF produced by a real transcription tool
   (Duxbury, BrailleBlaster, liblouis, etc.) and for the corpus
   fixture in ``tests/corpus/braille/one_crazy_night.brf`` (69 FFs,
   70 pages).
2. **Calculated** — when the file has no FFs, the page map falls back
   to a fixed grid: ``cell_width`` × ``line_height`` per page. Every
   ``line_height`` logical lines ends a page. This is the *last-resort*
   fallback for hand-edited or foreign BRFs that lost their FFs in
   transit. A file with no FFs and zero lines produces a single empty
   page so the status bar still has a position to announce.

This module is wx-free; it lives in ``quill/core`` and is consumed by
:mod:`quill.core.braille_position`, the status string composer, and the
UI status bar. Strict-typed: mypy ``--strict`` must stay clean.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from quill.core.brf_document import BRFDocument

PageBreakMode = Literal["form_feed", "calculated", "hybrid"]

# Default page break mode. ``"hybrid"`` tries form-feed first and falls
# back to calculated when no FFs are present, so the status bar never
# shows "page 0 of 0" on a well-formed BRF.
DEFAULT_PAGE_BREAK_MODE: PageBreakMode = "hybrid"


@dataclass(slots=True)
class BRFPage:
    """A single page in the page map.

    All offsets are **character offsets** into the source
    :class:`BRFDocument`'s ``text`` (the page map is text-based; the
    document model is text-based; we never deal in byte offsets after
    the loader).
    """

    index: int
    start_offset: int
    end_offset: int
    line_start_offsets: list[int] = field(default_factory=list)
    line_count: int = 0
    max_cell_count: int = 0
    has_form_feed: bool = False

    @property
    def length(self) -> int:
        return self.end_offset - self.start_offset

    def line_at_offset(self, char_offset: int) -> int:
        """Return the 0-based line index containing ``char_offset``."""
        if not self.line_start_offsets:
            return 0
        if char_offset < self.line_start_offsets[0]:
            return 0
        # Binary search would be nice; lists are small (≤ line_height).
        for line_idx, start in enumerate(self.line_start_offsets):
            next_start = (
                self.line_start_offsets[line_idx + 1]
                if line_idx + 1 < len(self.line_start_offsets)
                else self.end_offset + 1
            )
            if start <= char_offset < next_start:
                return line_idx
        return len(self.line_start_offsets) - 1


@dataclass(slots=True)
class BRFPageMap:
    """A read-only page map built from a :class:`BRFDocument`."""

    pages: list[BRFPage] = field(default_factory=list)
    mode: PageBreakMode = DEFAULT_PAGE_BREAK_MODE
    cell_width: int = 40
    line_height: int = 25

    @property
    def page_count(self) -> int:
        return len(self.pages)

    def page_containing(self, char_offset: int) -> BRFPage:
        """Return the page that contains ``char_offset``.

        Clamps to the first / last page when ``char_offset`` falls
        outside the document (a common case when the caret is at EOF).
        """
        if not self.pages:
            raise IndexError("page map is empty")
        if char_offset <= self.pages[0].start_offset:
            return self.pages[0]
        for page in self.pages:
            if page.start_offset <= char_offset <= page.end_offset:
                return page
        return self.pages[-1]

    def page_index_for(self, one_based_page: int) -> BRFPage:
        """Return the 1-based ``one_based_page`` page, clamped to the valid range."""
        if not self.pages:
            raise IndexError("page map is empty")
        idx = max(0, min(one_based_page - 1, len(self.pages) - 1))
        return self.pages[idx]

    def page_offset(self, one_based_page: int) -> tuple[int, int]:
        """Return ``(start_offset, end_offset)`` for the 1-based page.

        Clamps to the valid range when ``one_based_page`` falls outside the
        document (the first or last page is returned). Used by the page-
        detection helpers in :mod:`quill.core.brf_page_detection` to slice
        the document text without re-walking the page list.
        """
        page = self.page_index_for(one_based_page)
        return page.start_offset, page.end_offset


def _split_on_form_feeds(doc: BRFDocument) -> list[BRFPage]:
    """Form-feed aware split. The FF is part of the prior page (it is the
    terminator); the first page always starts at offset 0.
    """
    text = doc.text
    pages: list[BRFPage] = []
    cursor = 0
    page_index = 0
    # Walk FF by FF. We do not pre-count FFs because the page index
    # depends on the position of the FF, not the total count.
    for ff_offset in range(len(text)):
        if text[ff_offset] != "\x0c":
            continue
        end_offset = ff_offset  # the FF is the terminator; exclusive end
        page = _build_page(doc, page_index, cursor, end_offset, has_form_feed=True)
        pages.append(page)
        page_index += 1
        cursor = ff_offset + 1
    # Trailing page: anything after the last FF, if any. Empty files
    # produce a single zero-length page so callers always have one.
    if cursor <= len(text):
        page = _build_page(doc, page_index, cursor, len(text), has_form_feed=False)
        pages.append(page)
    return pages


def _split_calculated(doc: BRFDocument) -> list[BRFPage]:
    """Calculated grid split. Every ``line_height`` lines ends a page.

    Long lines are not split: a 200-cell line in a 40-cell-wide layout
    is *one* line, and the page is flagged as over-wide so the
    validator (BR-018) can warn. The save path never truncates.
    """
    text = doc.text
    pages: list[BRFPage] = []
    if not text:
        # Always produce at least one page so the status bar has
        # something to announce.
        return [_build_page(doc, 0, 0, 0, has_form_feed=False)]

    line_starts = _line_start_offsets(text)
    page_index = 0
    cursor_line = 0
    while cursor_line < len(line_starts):
        page_lines = line_starts[cursor_line : cursor_line + doc.line_height]
        start_offset = page_lines[0]
        if cursor_line + doc.line_height < len(line_starts):
            # The last line in this page has a successor; the page ends
            # right before that successor (so the trailing CR/LF lives
            # on the next page).
            end_offset = line_starts[cursor_line + doc.line_height]
        else:
            # No successor: this is the trailing page; run to EOF.
            end_offset = len(text)
        page = _build_page(
            doc,
            page_index,
            start_offset,
            end_offset,
            has_form_feed=False,
            line_start_offsets=page_lines,
        )
        pages.append(page)
        page_index += 1
        cursor_line += doc.line_height
    return pages


def _split_hybrid(doc: BRFDocument) -> list[BRFPage]:
    """FF-aware if any FF is present; calculated otherwise."""
    if doc.form_feed_count > 0:
        return _split_on_form_feeds(doc)
    return _split_calculated(doc)


def build_page_map(
    doc: BRFDocument,
    *,
    mode: PageBreakMode = DEFAULT_PAGE_BREAK_MODE,
) -> BRFPageMap:
    """Build a :class:`BRFPageMap` for ``doc``.

    The chosen ``mode`` is stored on the result so the status string
    composer can announce *why* a page count was chosen (the user
    wants to know when the engine fell back to calculated).
    """
    if mode == "form_feed":
        pages = _split_on_form_feeds(doc)
    elif mode == "calculated":
        pages = _split_calculated(doc)
    else:
        pages = _split_hybrid(doc)
    return BRFPageMap(
        pages=pages,
        mode=mode,
        cell_width=doc.cell_width,
        line_height=doc.line_height,
    )


def _line_start_offsets(text: str) -> list[int]:
    """Return the offset of the first character of every line in ``text``.

    A line starts at 0, after every ``\n`` (LF), after every lone
    ``\r`` (old-Mac), and after every ``\r\n`` (CRLF) is treated as
    *one* line break (the LF consumes the CR). Form feeds are *not*
    line breaks: they are page terminators, and the page map handles
    them separately.
    """
    starts = [0]
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\n":
            starts.append(i + 1)
            i += 1
        elif ch == "\r":
            if i + 1 < n and text[i + 1] == "\n":
                starts.append(i + 2)
                i += 2
            else:
                starts.append(i + 1)
                i += 1
        else:
            i += 1
    return starts


def _build_page(
    doc: BRFDocument,
    index: int,
    start_offset: int,
    end_offset: int,
    *,
    has_form_feed: bool,
    line_start_offsets: list[int] | None = None,
) -> BRFPage:
    """Build a single :class:`BRFPage` for the slice ``[start, end)``."""
    text = doc.text
    page_text = text[start_offset:end_offset]
    if line_start_offsets is None:
        local = _line_start_offsets(page_text)
        # Translate local offsets to document offsets.
        line_start_offsets = [start_offset + off for off in local]
    # The local _line_start_offsets helper emits a sentinel at
    # ``len(page_text)`` when the slice ends with a newline (and the
    # text contains at least one newline). That sentinel corresponds
    # to the start of the line *after* this page; drop it so the page
    # only reports its own lines.
    if (
        line_start_offsets
        and line_start_offsets[-1] == end_offset
        and page_text
        and page_text[-1] in "\r\n"
    ):
        line_start_offsets = line_start_offsets[:-1]
    # Line count: number of line-start markers in the slice. A page
    # with one line has 1 marker; an empty slice has 0.
    if not page_text:
        line_count = 0
    else:
        line_count = len(line_start_offsets)
    # maxCellCount: longest line in the page, in cells, after stripping
    # a trailing CR/LF. NABCC is one cell per ASCII char for our
    # purposes.
    max_cell = 0
    for line_idx in range(len(line_start_offsets)):
        line_start = line_start_offsets[line_idx]
        if line_idx + 1 < len(line_start_offsets):
            line_end = line_start_offsets[line_idx + 1]
        else:
            line_end = end_offset
        if line_end > line_start and text[line_end - 1] in "\r\n":
            line_end -= 1
        cell_count = line_end - line_start
        if cell_count > max_cell:
            max_cell = cell_count
    return BRFPage(
        index=index,
        start_offset=start_offset,
        end_offset=end_offset,
        line_start_offsets=line_start_offsets,
        line_count=line_count,
        max_cell_count=max_cell,
        has_form_feed=has_form_feed,
    )
