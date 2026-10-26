"""Cell-by-cell navigation over a pipe (Markdown-style) table in document text.

A screen-reader user needs to move around a table cell by cell,
hearing each cell and its position, with "entering/out of table" cues and clear
edges ("no more cells", "no more rows"). QUILL presents tables -- Markdown
tables, and the linearized view of a real Word/HTML table -- as pipe rows in the
editor text, so the same experience is a pure function of that text: find the
table around the caret, work out which cell the caret is in, and compute where
each move lands.

Pure and wx-free: the UI layer reads the caret offset, calls in here, moves the
caret to the returned offset, and speaks the returned announcement. A separator
row (``| --- | --- |``) is structural and never a navigable row.

Cell text may contain escaped pipes (``\\|``) and backslashes (``\\\\``), the GFM
convention the Word importers emit when a cell's own text contains a pipe. Only
*unescaped* pipes divide cells, and the escapes are undone before a cell is
announced -- otherwise a single "|" typed into a Word table cell would fabricate
an extra column and misalign every row beneath it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: A row of only pipes, dashes, colons and spaces -- the header/body separator.
#: At least one dash: a row of empty cells ("|  |  |") is pipes and spaces too,
#: and until 2026-10-25 it was skipped as a separator, so every blank row of a
#: new table (or of a Word table with an empty row) was missing from the grid.
_SEPARATOR = re.compile(r"^\s*\|?(?=.*-)[\s:\-|]+\|?\s*$")


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
    #: The first row is a header row: a ``| --- |`` separator stands under it.
    header: bool = False
    #: A real (RichEdit) table read from the rich surface's aligned text
    #: (:mod:`quill.core.native_tables`), rather than rows of pipes. Moving is
    #: the same; changing it goes through the rich surface, not the text.
    native: bool = False

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


def _bar_positions(line: str) -> list[int]:
    """Indexes of the cell-dividing (unescaped) pipes in ``line``.

    A backslash consumes the character after it, so ``\\|`` is cell text and
    ``\\\\`` is a literal backslash -- neither divides a cell.
    """
    positions: list[int] = []
    index = 0
    while index < len(line):
        if line[index] == "\\":
            index += 2  # the escaped character, whatever it is, is not a divider
            continue
        if line[index] == "|":
            positions.append(index)
        index += 1
    return positions


def _unescape(text: str) -> str:
    """Undo the ``\\|`` / ``\\\\`` escapes so a cell is announced as authored."""
    out: list[str] = []
    index = 0
    while index < len(text):
        if text[index] == "\\" and index + 1 < len(text) and text[index + 1] in "\\|":
            out.append(text[index + 1])
            index += 2
            continue
        out.append(text[index])
        index += 1
    return "".join(out)


def _is_table_row(line: str) -> bool:
    return bool(_bar_positions(line)) and not _looks_blank(line)


def is_table_row(line: str) -> bool:
    """Whether *line* is a pipe row -- the same test navigation uses, shared with
    the RTF table conversion (:mod:`quill.io.rtf_tables`) so the two agree."""
    return _is_table_row(line)


def is_separator_row(line: str) -> bool:
    """Whether *line* is the ``| --- | --- |`` row under a header."""
    return bool(_SEPARATOR.match(line))


def split_row(line: str) -> list[str]:
    """The cell texts of one pipe row, escapes undone (``"| a | b |"`` -> a, b)."""
    return [text for text, _offset in _split_cells(line, 0)]


def _looks_blank(line: str) -> bool:
    return not line.strip()


def _split_cells(line: str, line_start: int) -> list[tuple[str, int]]:
    """Split one pipe row into ``(cell_text, text_offset)`` pairs. The offset is
    the absolute position of the first non-space character of the cell's text
    (where the caret should land), falling back to the cell's start when empty."""
    bars = _bar_positions(line)
    if not bars:
        return []
    # Drop one leading and one trailing pipe so "| a | b |" yields two cells.
    start = 0
    end = len(line)
    if not line[: bars[0]].strip():
        start = bars[0] + 1
        bars = bars[1:]
    if bars and not line[bars[-1] + 1 :].strip():
        end = bars[-1]
        bars = bars[:-1]
    cells: list[tuple[str, int]] = []
    pos = start
    for stop in [*bars, end]:
        piece = line[pos:stop]
        text = piece.strip()
        # Offset of the trimmed text within this piece (or the piece start).
        cells.append((_unescape(text), line_start + pos + piece.index(text)))
        pos = stop + 1  # + 1 for the consumed "|"
    return cells


def find_table_at(text: str, offset: int) -> TableGrid | None:
    """The pipe table whose character span contains ``offset``, or ``None``.

    A table is a run of two or more consecutive pipe rows (a header row plus at
    least a separator, or plain rows). The separator row is parsed out; the
    remaining rows form the navigable grid.
    """
    if offset < 0 or offset > len(text):
        return None
    if "￹" in text:  # a rich document with a real table: read that first
        from quill.core.native_tables import find_native_table_at

        native = find_native_table_at(text, offset)
        if native is not None:
            return native
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
    header = bottom > top and bool(_SEPARATOR.match(line_bounds[top + 1][2]))
    return TableGrid(tuple(rows), line_bounds[top][0], line_bounds[bottom][1], header)


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


def describe_position(grid: TableGrid, row: int, col: int) -> str:
    """The cell's place in the grid, spoken: "Row 2 of 4, column 3 of 5".

    Every landing announcement leads with this, so a screen-reader user always
    hears where they are as well as what is there.
    """
    return f"Row {row + 1} of {grid.row_count}, column {col + 1} of {grid.col_count}"


def is_last_cell(grid: TableGrid, row: int, col: int) -> bool:
    """True when ``(row, col)`` is the final cell of the final row."""
    last_row = grid.row_count - 1
    return row == last_row and col == len(grid.rows[last_row]) - 1


def column_header(grid: TableGrid, col: int) -> str:
    """The header row's text for *col*, or "" (no header row, or an empty one)."""
    if not grid.header:
        return ""
    cell = grid.cell(0, col)
    return cell.text if cell is not None else ""


def _say_cell(grid: TableGrid, cell: Cell, *, from_row: int, from_col: int) -> str:
    """What changed, then what is in the cell -- and nothing already known.

    Along a row the row has not changed, so only the column is said: "Column 3,
    Role: Lead". Down a column, only the row: "Row 4: Tester". Both change on a
    wrap or a jump: "Row 3, column 1, Name: Bo". The totals are not repeated --
    entering the table said its size -- and a new column in a table with a header
    row says its header, the way a screen reader does in Word (not on the header
    row itself, whose cells *are* the headers).
    """
    parts: list[str] = []
    if cell.row != from_row:
        parts.append(f"row {cell.row + 1}")
    if cell.col != from_col:
        parts.append(f"column {cell.col + 1}")
        header = column_header(grid, cell.col) if cell.row > 0 else ""
        if header:
            parts.append(header)
    where = ", ".join(parts)
    value = cell.text or "blank"
    if not where:
        return value
    return f"{where[0].upper()}{where[1:]}: {value}"


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
            # Distinguish "this row ends here" from "the table ends here": both
            # block the move, but only one means there is nothing further at all.
            if is_last_cell(grid, row, col):
                edge = f"{edge}, end of table"
            return Move(None, edge)
        return Move(target.offset, _say_cell(grid, target, from_row=row, from_col=col))
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
    return Move(target.offset, _say_cell(grid, target, from_row=row, from_col=col))


@dataclass(frozen=True, slots=True)
class TabMove:
    """Where Tab or Shift+Tab takes the caret inside a table.

    ``insert`` is ``(position, text)`` when Tab in the last cell adds a row: the
    caller inserts *text* at *position* first, then puts the caret at ``offset``
    (which already counts the inserted text).
    """

    offset: int | None
    announcement: str
    insert: tuple[int, str] | None = None
    #: A real table's last cell: the caller adds the row through the rich
    #: surface (a real table's rows are not text to insert), then lands in it.
    add_row: bool = False


def blank_row(columns: int) -> str:
    """An empty pipe row of *columns* cells, in the shape Insert Table writes."""
    return "| " + " | ".join("" for _ in range(max(1, columns))) + " |"


def tab_move(text: str, offset: int, *, backwards: bool = False) -> TabMove | None:
    """Tab and Shift+Tab in a table, or ``None`` outside one (Tab means Tab).

    Tab goes to the next cell, on to the first cell of the next row, and in the
    very last cell adds a row and goes to its first cell -- what Tab does in a
    Word table. Shift+Tab goes back the same way and stops at the first cell.
    """
    grid = find_table_at(text, offset)
    if grid is None:
        return None
    row, col = locate_cell(grid, offset)
    if backwards:
        target = grid.cell(row, col - 1)
        if target is None and row > 0:
            target = grid.cell(row - 1, len(grid.rows[row - 1]) - 1)
        if target is None:
            return TabMove(None, "No more cells, start of table")
        return TabMove(target.offset, _say_cell(grid, target, from_row=row, from_col=col))
    target = grid.cell(row, col + 1)
    if target is None and row + 1 < grid.row_count:
        target = grid.cell(row + 1, 0)
    if target is not None:
        return TabMove(target.offset, _say_cell(grid, target, from_row=row, from_col=col))
    # The last cell: add a row under the table, and go to its first cell.
    count = grid.row_count + 1
    if grid.native:
        return TabMove(None, f"Added row {count}, column 1", add_row=True)
    last_line_end = grid.span_end
    if text[last_line_end - 1 : last_line_end] == "\n":
        last_line_end -= 1
    new_row = blank_row(grid.col_count)
    said = f"Added row {count}, column 1"
    return TabMove(last_line_end + 3, said, (last_line_end, "\n" + new_row))


#: The four arrow keys :func:`arrow_move` answers, by name.
ARROWS = ("up", "down", "left", "right")


def arrow_move(text: str, offset: int, key: str) -> TabMove | None:
    """A plain arrow key in or into a table, or ``None`` to leave it to the editor.

    The editor's own arrows read a table badly: Up and Down land somewhere in
    the next row and the screen reader reads the whole row, every cell, as one
    line; Left and Right cross from one cell to the next in silence. So inside
    a table the arrows move by cell and the app says the cell -- the same words
    as the table keys (:func:`_say_cell`), only what changed:

    * Up and Down go to the cell above and below, in the same column. Past the
      first or last row they are the editor's again, and leave the table.
    * Left at the start of a cell goes to the end of the cell before it (the
      row before's last cell, at a row's start); Right at the end of a cell goes
      to the start of the next one. Inside a cell's text they are the editor's,
      so a word can still be read letter by letter.
    * Arriving -- Down from the line above, Up from the line below -- lands in
      the first cell of the row arrived at, and says the table's shape once:
      "Table, 3 rows, 2 columns. Name".

    ``offset`` of the result is where the caret goes; ``None`` there never
    happens (an edge is the editor's), so the caller only has to move and say.
    """
    if key not in ARROWS:
        return None
    grid = find_table_at(text, offset)
    if grid is None:
        return _arrive(text, offset, key)
    row, col = locate_cell(grid, offset)
    here = grid.rows[row][col]
    target: Cell | None = None
    land_at_end = False
    if key in ("up", "down"):
        new_row = row + (1 if key == "down" else -1)
        if 0 <= new_row < grid.row_count and grid.rows[new_row]:
            target = grid.cell(new_row, min(col, len(grid.rows[new_row]) - 1))
    elif key == "left" and offset <= here.offset:
        target = grid.cell(row, col - 1)
        if target is None and row > 0:
            target = grid.cell(row - 1, len(grid.rows[row - 1]) - 1)
        land_at_end = True
    elif key == "right" and offset >= here.offset + len(here.text):
        target = grid.cell(row, col + 1)
        if target is None and row + 1 < grid.row_count:
            target = grid.cell(row + 1, 0)
    if target is None:
        return None
    landing = target.offset + (len(target.text) if land_at_end else 0)
    return TabMove(landing, _say_cell(grid, target, from_row=row, from_col=col))


def _arrive(text: str, offset: int, key: str) -> TabMove | None:
    """Down onto a table's first row, or Up onto its last, from just outside it."""
    if key == "down":
        line_end = text.find("\n", offset)
        if line_end < 0:
            return None
        probe = line_end + 1
    elif key == "up":
        line_start = text.rfind("\n", 0, offset)
        if line_start <= 0:
            return None
        probe = line_start - 1
    else:
        return None
    if probe >= len(text) and key == "down":
        return None
    grid = find_table_at(text, probe)
    if grid is None or not grid.rows:
        return None
    row = grid.rows[0] if key == "down" else grid.rows[-1]
    if not row:
        return None
    cell = row[0]
    shape = f"Table, {grid.row_count} rows, {grid.col_count} columns"
    return TabMove(cell.offset, f"{shape}. {cell.text or 'blank'}")
