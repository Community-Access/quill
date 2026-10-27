"""Real tables in a rich document, read from the editor's aligned text.

In rich text a table is a real table -- RichEdit's own, a grid on screen that
Word and WordPad open as a table -- not rows of pipes. The control keeps three
marks in its text for one: a row-start mark and a paragraph break before each
row, a cell mark after every cell, and a row-end mark and paragraph break after
the last. Its caret positions count those marks, so the rich surface hands
every feature the *aligned* text (:mod:`quill.ui.richedit_tables`): the
control's own text with the marks kept, paragraph breaks as ``\\n`` and cell
marks as ``\\t``, one character per position. One row reads::

    \\ufff9\\n Name \\t Role \\t \\ufffb\\n        (spaces added for reading)

This module finds the table around a position in that text and returns the same
:class:`~quill.core.table_nav.TableGrid` a pipe table gives, flagged ``native``,
so the table keys, the column headers and the "Table, 3 rows" cue work on a
real table exactly as on a Markdown one. The first row is taken as the header
row: RichEdit does not keep RTF's header-row mark, and a table's first row is
its header far more often than not -- and is what Save as Word marks as one.

Pure and wx-free.
"""

from __future__ import annotations

from quill.core.table_nav import Cell, TableGrid

__all__ = ["CELL", "ROW_END", "ROW_START", "find_native_table_at", "has_native_table"]

#: The marks, as they appear in the aligned text.
ROW_START = "￹"
ROW_END = "￻"
CELL = "\t"


def has_native_table(text: str) -> bool:
    """Whether *text* (aligned) holds a real table anywhere."""
    return ROW_START in text


def _row_at(text: str, offset: int) -> tuple[int, int] | None:
    """``(start, end)`` of the row holding *offset*: start at its row-start
    mark, end at its row-end mark. None when *offset* is in no row."""
    start = text.rfind(ROW_START, 0, offset + 1)
    if start == -1:
        return None
    end = text.find(ROW_END, start)
    # Up to and including the row-end mark's paragraph break is still the row.
    if end == -1 or offset > end + 1:
        return None
    return start, end


def _cells(text: str, start: int, end: int, row: int) -> tuple[Cell, ...]:
    """The cells of the row at ``text[start:end]``, each at its text's offset."""
    content_start = start + 2  # the row-start mark and its paragraph break
    content = text[content_start:end]
    pieces = content.split(CELL)
    if content.endswith(CELL):
        pieces = pieces[:-1]  # the last cell's own mark, not an empty cell
    cells: list[Cell] = []
    position = content_start
    for col, piece in enumerate(pieces):
        lead = len(piece) - len(piece.lstrip())
        spoken = " ".join(piece.split())
        cells.append(Cell(row, col, spoken, position + (lead if spoken else 0)))
        position += len(piece) + 1
    return tuple(cells)


def find_native_table_at(text: str, offset: int) -> TableGrid | None:
    """The real table whose rows hold *offset*, or None."""
    if offset < 0 or offset > len(text) or ROW_START not in text:
        return None
    here = _row_at(text, offset)
    if here is None:
        return None
    rows = [here]
    # Back over rows that end right before this one starts...
    while True:
        first_start = rows[0][0]
        if text[first_start - 2 : first_start] != ROW_END + "\n":
            break
        previous = _row_at(text, first_start - 2)
        if previous is None or previous == rows[0]:
            break
        rows.insert(0, previous)
    # ...and on over rows that start right after this one ends.
    while True:
        last_end = rows[-1][1]
        if text[last_end + 1 : last_end + 3] != "\n" + ROW_START:
            break
        following = _row_at(text, last_end + 2)
        if following is None or following == rows[-1]:
            break
        rows.append(following)
    grid_rows = tuple(_cells(text, s, e, index) for index, (s, e) in enumerate(rows))
    span_end = min(len(text), rows[-1][1] + 2)
    return TableGrid(grid_rows, rows[0][0], span_end, header=True, native=True)
