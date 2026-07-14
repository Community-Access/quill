"""Resolve a caret offset to ``(page, line, cell)`` in a BRF.

The :class:`BraillePositionResolver` consumes a :class:`BRFPageMap` and
turns an arbitrary character offset (typically the caret position) into
the three numbers the status bar, the navigation commands, and the
print-page detector all need:

* ``page`` (1-based) — the braille page containing the offset
* ``line`` (1-based) — the line *within* that page
* ``cell`` (1-based) — the cell *within* that line (after stripping
  the CR/LF terminator)

A :class:`BraillePosition` is the immutable result.

This module is wx-free; it lives in ``quill/core`` and is consumed by
:mod:`quill.core.braille_status`, the UI status bar, and BR-013's
print-page detection. Strict-typed: mypy ``--strict`` must stay clean.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.brf_document import BRFDocument
from quill.core.brf_page_map import BRFPageMap, build_page_map


@dataclass(slots=True, frozen=True)
class BraillePosition:
    """1-based page/line/cell resolved from a caret offset."""

    page: int
    line: int
    cell: int
    page_offset: int  # 0-based char offset of the start of the page
    line_offset: int  # 0-based char offset of the start of the line
    page_count: int
    line_count_in_page: int
    cell_width: int

    def to_compact_string(self) -> str:
        """Return the brief form used by the status bar at verbosity=brief."""
        return f"Pg {self.page}/{self.page_count}"

    def to_normal_string(self) -> str:
        """Return the normal form used at verbosity=normal (default)."""
        return (
            f"BRF Pg {self.page}/{self.page_count} "
            f"Ln {self.line}/{self.line_count_in_page} "
            f"Cell {self.cell}/{self.cell_width}"
        )


class BraillePositionResolver:
    """Resolve caret offsets in a :class:`BRFPageMap`.

    The resolver is constructed against a single :class:`BRFDocument`
    (which owns the page map's source text) and reused for every
    position lookup. The document is the source of truth for cell
    counts; the page map is the source of truth for page/line geometry.
    """

    def __init__(self, document: BRFDocument) -> None:
        self._document = document
        self._page_map = build_page_map(document)

    @property
    def document(self) -> BRFDocument:
        return self._document

    @property
    def page_map(self) -> BRFPageMap:
        return self._page_map

    def resolve(self, char_offset: int) -> BraillePosition:
        """Return the 1-based ``(page, line, cell)`` for ``char_offset``."""
        if not self._page_map.pages:
            raise IndexError("page map is empty")
        page = self._page_map.page_containing(char_offset)
        line_idx = page.line_at_offset(char_offset)
        line_offset = page.line_start_offsets[line_idx]
        cell = _cell_in_line(self._document.text, char_offset, line_offset)
        return BraillePosition(
            page=page.index + 1,
            line=line_idx + 1,
            cell=cell,
            page_offset=page.start_offset,
            line_offset=line_offset,
            page_count=self._page_map.page_count,
            line_count_in_page=page.line_count,
            cell_width=self._page_map.cell_width,
        )

    def go_to_page(self, one_based_page: int) -> int:
        """Return the char offset of the start of ``one_based_page``."""
        page = self._page_map.page_index_for(one_based_page)
        return page.start_offset

    def next_page_offset(self, char_offset: int) -> int:
        """Return the start offset of the page after the one at ``char_offset``.

        Returns ``char_offset`` itself when already on the last page
        (so the caller can detect "no more pages" with a simple
        equality check).
        """
        page = self._page_map.page_containing(char_offset)
        if page.index + 1 >= self._page_map.page_count:
            return char_offset
        return self._page_map.pages[page.index + 1].start_offset

    def previous_page_offset(self, char_offset: int) -> int:
        """Return the start offset of the page before the one at ``char_offset``.

        Returns ``char_offset`` itself when already on the first page.
        """
        page = self._page_map.page_containing(char_offset)
        if page.index == 0:
            return char_offset
        return self._page_map.pages[page.index - 1].start_offset


def _cell_in_line(text: str, char_offset: int, line_offset: int) -> int:
    """Count cells from ``line_offset`` to ``char_offset``.

    The cell count is the number of NABCC characters between the line
    start and the caret. A caret that sits on the line terminator is
    treated as the *end* of the prior line, not the start of the next.
    """
    # Caret at or past EOF: report one past the last content cell of the
    # line so the status bar shows "Cell N+1/N" without a negative cell.
    if char_offset >= len(text):
        return (len(text) - line_offset) + 1
    # cell is 0-based; we add 1 to make it 1-based for the status bar.
    cell = char_offset - line_offset
    # Step back over the line terminator. The previous char is the LF
    # of the terminator; the one before that is the CR for CRLF.
    if cell > 0 and text[char_offset - 1] == "\n":
        cell -= 1
        if cell > 0 and text[char_offset - 2] == "\r":
            cell -= 1
    elif cell > 0 and text[char_offset - 1] == "\r":
        # Lone CR.
        cell -= 1
    return cell + 1
