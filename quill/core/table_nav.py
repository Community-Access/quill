"""Cell-by-cell navigation over a pipe (Markdown-style) table in document text.

Leasey Word lets a screen-reader user move around a Word table cell by cell,
hearing each cell and its position, with "entering/out of table" cues and clear
edges ("no more cells", "no more rows"). QUILL presents tables -- Markdown
tables, and the linearized view of a real Word/HTML table -- as pipe rows in the
editor text, so the same experience is a pure function of that text: find the
table around the caret, work out which cell the caret is in, and compute where
each move lands.

Pure and wx-free: the UI layer reads the caret offset, calls in here, moves the
caret to the returned offset, and speaks the returned announcement. A separator
row (``| --- | --- |``) is structural and never a navigable row.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: A row of only pipes, dashes, colons and spaces -- the header/body separator.
_SEPARATOR = re.compile(r"^\s*\|?[\s:\-|]+\|?\s*$")


@dataclass(frozen=True, slots=True)
class Cell:
    """One navigable cell: its grid position, text, and where its text starts
    in the document (the caret offset to land on)."""

    row: int
    col: int
    text: str
    offset: int


@dataclass(frozen=True, slots=True)
class TableGrid:
    """A parsed pipe table: a rectangular grid of cells plus the ``[start, end)``
    character span it occupies in the source text."""

    rows: tuple[tuple[Cell, ...], ...]
    span_start: int
    span_end: int

    @property
    def row_count(self) -> int:
        return len(self.rows)

    @property
    def col_count(self) -> int:
        return max((len(r) for r in self.rows), default=0)

    def cell(self, row: int, col: int) -> Cell | None:
        if 0 <= row < len(self.rows) and 0 <= col < len(self.rows[row]):
            return self.rows[row][col]
        return None


def _is_table_row(line: str) -> bool:
    return "|" in line and not _looks_blank(line)


def _looks_blank(line: str) -> bool:
    return not line.strip()


def _split_cells(line: str, line_start: int) -> list[tuple[str, int]]:
    """Split one pipe row into ``(cell_text, text_offset)`` pairs. The offset is
    the absolute position of the first non-space character of the cell's text
    (where the caret should land), falling back to the cell's start when empty."""
    # Drop one leading and one trailing pipe so "| a | b |" yields two cells.
    body = line
    lead = 0
    if body.lstrip().startswith("|"):
        lead = body.index("|") + 1
        body = body[lead:]
    if body.rstrip().endswith("|"):
        body = body[: body.rstrip().rindex("|")]
    cells: list[tuple[str, int]] = []
    pos = line_start + lead
    for piece in body.split("|"):
        text = piece.strip()
        # Offset of the trimmed text within this piece (or the piece start).
        inner = pos + (piece.index(text) if text and text in piece else 0)
        cells.append((text, inner))
        pos += len(piece) + 1  # + 1 for the consumed "|"
    return cells


def find_table_at(text: str, offset: int) -> TableGrid | None:
    """The pipe table whose character span contains ``offset``, or ``None``.

    A table is a run of two or more consecutive pipe rows (a header row plus at
    least a separator, or plain rows). The separator row is parsed out; the
    remaining rows form the navigable grid.
    """
    if offset < 0 or offset > len(text):
        return None
    line_bounds: list[tuple[int, int, str]] = []
    start = 0
    for line in text.splitlines(keepends=True):
        end = start + len(line)
        line_bounds.append((start, end, line.rstrip("\n")))
        start = end
    # Which line holds the caret?
    caret_line = next(
        (i for i, (s, e, _) in enumerate(line_bounds) if s <= offset < e),
        len(line_bounds) - 1 if line_bounds else -1,
    )
    if caret_line < 0 or not _is_table_row(line_bounds[caret_line][2]):
        return None
    # Grow up and down over consecutive pipe rows.
    top = caret_line
    while top - 1 >= 0 and _is_table_row(line_bounds[top - 1][2]):
        top -= 1
    bottom = caret_line
    while bottom + 1 < len(line_bounds) and _is_table_row(line_bounds[bottom + 1][2]):
        bottom += 1
    if bottom == top:
        return None  # a single pipe line is not a table
    rows: list[tuple[Cell, ...]] = []
    for i in range(top, bottom + 1):
        line_start, _, raw = line_bounds[i]
        if _SEPARATOR.match(raw):
            continue  # structural separator, not a navigable row
        row_index = len(rows)
        cells = tuple(
            Cell(row_index, col, cell_text, cell_offset)
            for col, (cell_text, cell_offset) in enumerate(_split_cells(raw, line_start))
        )
        rows.append(cells)
    if not rows:
        return None
    return TableGrid(tuple(rows), line_bounds[top][0], line_bounds[bottom][1])


def locate_cell(grid: TableGrid, offset: int) -> tuple[int, int]:
    """The ``(row, col)`` of the cell the caret is in (nearest cell on its row).
    Clamped to the grid, so a caret anywhere inside the table resolves."""
    # Row: the last row whose first cell starts at or before the caret.
    row = 0
    for r, cells in enumerate(grid.rows):
        if cells and cells[0].offset <= offset:
            row = r
    cells = grid.rows[row]
    col = 0
    for c, cell in enumerate(cells):
        if cell.offset <= offset:
            col = c
    return row, col


#: (row-delta, col-delta) for the directional single-cell moves.
_STEPS = {
    "next": (0, 1),
    "previous": (0, -1),
    "down": (1, 0),
    "up": (-1, 0),
}


@dataclass(frozen=True, slots=True)
class Move:
    """The result of a navigation request: where to put the caret and what to
    say. ``offset`` is ``None`` when the move hit an edge (the caret stays put)."""

    offset: int | None
    announcement: str


def _say_cell(grid: TableGrid, cell: Cell) -> str:
    value = cell.text or "blank"
    return (
        f"Row {cell.row + 1} of {grid.row_count}, "
        f"column {cell.col + 1} of {grid.col_count}: {value}"
    )


def move(grid: TableGrid, offset: int, action: str) -> Move:
    """Compute a cell move from the caret at ``offset``.

    ``action`` is one of: ``next``/``previous`` (cell in row), ``up``/``down``
    (cell in column), ``row_start``/``row_end`` (first/last cell of the row),
    ``table_start``/``table_end`` (first/last cell of the table).
    """
    row, col = locate_cell(grid, offset)
    if action in _STEPS:
        d_row, d_col = _STEPS[action]
        target = grid.cell(row + d_row, col + d_col)
        if target is None:
            edge = "No more rows" if d_row else "No more cells"
            return Move(None, edge)
        return Move(target.offset, _say_cell(grid, target))
    if action == "row_start":
        target = grid.cell(row, 0)
    elif action == "row_end":
        target = grid.cell(row, len(grid.rows[row]) - 1)
    elif action == "table_start":
        target = grid.cell(0, 0)
    elif action == "table_end":
        last = grid.row_count - 1
        target = grid.cell(last, len(grid.rows[last]) - 1)
    else:
        return Move(None, "")
    if target is None:
        return Move(None, "No more cells")
    return Move(target.offset, _say_cell(grid, target))
