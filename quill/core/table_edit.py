"""Editing a pipe table: rows, columns, and lining it up.

The companion of :mod:`quill.core.table_nav`, which reads a table; this changes
one. Both editors call it the same way -- with the document text and the caret --
and get back an :class:`TableEdit`: the span of the table to replace, the new
table text, where the caret goes, and the sentence to say. One undo step in the
editor, because one replacement is one change.

Every edit rewrites the whole table in the tidy shape Insert Table makes -- one
space either side of each cell's text -- so a table that came in ragged comes out
even, and Tidy Table does only that: pads every column to its widest cell, so a
sighted reader sees columns and the table keys read the same cells as before.

A column's alignment (``:---``, ``:---:``, ``---:``) is kept through every edit.

Pure and wx-free.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.table_nav import (
    TableGrid,
    column_header,
    find_table_at,
    is_separator_row,
    locate_cell,
    split_row,
)

__all__ = [
    "TableEdit",
    "delete_column",
    "delete_row",
    "insert_column_right",
    "insert_row_below",
    "tidy_table",
]


@dataclass(frozen=True, slots=True)
class TableEdit:
    """Replace ``text[start:end]`` with ``replacement``, then put the caret at
    ``caret`` (an offset in the *new* text) and say ``announcement``. When the
    edit cannot be made, ``replacement`` is ``None`` and only the sentence counts."""

    start: int
    end: int
    replacement: str | None
    caret: int
    announcement: str


def _refuse(offset: int, sentence: str) -> TableEdit:
    return TableEdit(offset, offset, None, offset, sentence)


def _not_in_table(offset: int) -> TableEdit:
    return _refuse(offset, "Not in a table")


def _escape(cell: str) -> str:
    """A cell's text written back into a row: backslashes and pipes escaped."""
    return cell.replace("\\", "\\\\").replace("|", "\\|")


def _alignments(text: str, grid: TableGrid) -> list[str]:
    """Each column's separator cell (``---``, ``:---:`` ...), or [] with no header."""
    if not grid.header:
        return []
    lines = text[grid.span_start : grid.span_end].split("\n")
    separator = next((line for line in lines if is_separator_row(line)), "")
    return [cell.strip() for cell in split_row(separator)]


def _separator_cell(align: str, width: int) -> str:
    left, right = align.startswith(":"), align.endswith(":") and len(align) > 1
    dashes = "-" * max(3, width - left - right)
    return f"{':' if left else ''}{dashes}{':' if right else ''}"


def _render(
    rows: list[list[str]], header: bool, aligns: list[str], *, pad: bool = False
) -> tuple[str, list[list[int]]]:
    """The table's text, and each cell's text offset within it (for the caret)."""
    columns = max((len(r) for r in rows), default=1)
    grid = [[_escape(c) for c in r] + [""] * (columns - len(r)) for r in rows]
    aligns = (aligns + ["---"] * columns)[:columns]
    widths = [3] * columns
    if pad:
        for r in grid:
            for i, c in enumerate(r):
                widths[i] = max(widths[i], len(c))
    lines: list[str] = []
    offsets: list[list[int]] = []
    position = 0
    for index, r in enumerate(grid):
        cells = [c.ljust(widths[i]) if pad else c for i, c in enumerate(r)]
        line = "| " + " | ".join(cells) + " |"
        row_offsets, cursor = [], 2
        for c in cells:
            row_offsets.append(position + cursor)
            cursor += len(c) + 3
        offsets.append(row_offsets)
        lines.append(line)
        position += len(line) + 1
        if index == 0 and header:
            sep_cells = [_separator_cell(a, widths[i] if pad else 3) for i, a in enumerate(aligns)]
            separator = "| " + " | ".join(sep_cells) + " |"
            lines.append(separator)
            position += len(separator) + 1
    return "\n".join(lines), offsets


def _span(text: str, grid: TableGrid) -> tuple[int, int]:
    """The table's span without its final newline, so replacing it keeps the line."""
    end = grid.span_end
    if text[end - 1 : end] == "\n":
        end -= 1
    return grid.span_start, end


def _rows(grid: TableGrid) -> list[list[str]]:
    return [[cell.text for cell in row] for row in grid.rows]


def _edit(
    text: str,
    grid: TableGrid,
    rows: list[list[str]],
    header: bool,
    aligns: list[str],
    at: tuple[int, int],
    sentence: str,
    *,
    pad: bool = False,
) -> TableEdit:
    start, end = _span(text, grid)
    replacement, offsets = _render(rows, header, aligns, pad=pad)
    row = min(at[0], len(offsets) - 1)
    col = min(at[1], len(offsets[row]) - 1)
    return TableEdit(start, end, replacement, start + offsets[row][col], sentence)


def insert_row_below(text: str, offset: int) -> TableEdit:
    """A blank row under the caret's row (under the header row too, never in it)."""
    grid = find_table_at(text, offset)
    if grid is None:
        return _not_in_table(offset)
    row, _col = locate_cell(grid, offset)
    rows = _rows(grid)
    rows.insert(row + 1, [""] * grid.col_count)
    sentence = f"Added row {row + 2}"
    return _edit(text, grid, rows, grid.header, _alignments(text, grid), (row + 1, 0), sentence)


def delete_row(text: str, offset: int) -> TableEdit:
    """Delete the caret's row. Deleting the header row makes the next row the
    header; the last row of a table is not deleted (delete the table instead)."""
    grid = find_table_at(text, offset)
    if grid is None:
        return _not_in_table(offset)
    # A table is two or more lines (table_nav): the rows left, plus the separator.
    if grid.row_count - 1 + int(grid.header) < 2:
        return _refuse(
            offset, "A table needs two rows. Select the table and press Delete to remove it"
        )
    row, col = locate_cell(grid, offset)
    rows = _rows(grid)
    del rows[row]
    target = min(row, len(rows) - 1)
    sentence = f"Deleted row {row + 1}. {len(rows)} rows left"
    return _edit(text, grid, rows, grid.header, _alignments(text, grid), (target, col), sentence)


def insert_column_right(text: str, offset: int) -> TableEdit:
    """A blank column to the right of the caret's column, in every row."""
    grid = find_table_at(text, offset)
    if grid is None:
        return _not_in_table(offset)
    row, col = locate_cell(grid, offset)
    rows = [r + [""] * (grid.col_count - len(r)) for r in _rows(grid)]
    for r in rows:
        r.insert(col + 1, "")
    aligns = _alignments(text, grid)
    if aligns:
        aligns = (aligns + ["---"] * grid.col_count)[: grid.col_count]
        aligns.insert(col + 1, "---")
    columns = grid.col_count + 1
    sentence = f"Added a column. Column {col + 2} of {columns}"
    return _edit(text, grid, rows, grid.header, aligns, (row, col + 1), sentence)


def delete_column(text: str, offset: int) -> TableEdit:
    """Delete the caret's column from every row; a table keeps at least one column."""
    grid = find_table_at(text, offset)
    if grid is None:
        return _not_in_table(offset)
    if grid.col_count <= 1:
        return _refuse(offset, "A table needs a column. Select the table and press Delete")
    row, col = locate_cell(grid, offset)
    name = column_header(grid, col)
    rows = [r + [""] * (grid.col_count - len(r)) for r in _rows(grid)]
    for r in rows:
        del r[col]
    aligns = _alignments(text, grid)
    if aligns:
        aligns = (aligns + ["---"] * grid.col_count)[: grid.col_count]
        del aligns[col]
    columns = grid.col_count - 1
    which = f"column {col + 1}" + (f", {name}" if name else "")
    sentence = f"Deleted {which}. {columns} columns left"
    return _edit(text, grid, rows, grid.header, aligns, (row, min(col, columns - 1)), sentence)


def tidy_table(text: str, offset: int) -> TableEdit:
    """Pad every column to its widest cell, so the table lines up on screen."""
    grid = find_table_at(text, offset)
    if grid is None:
        return _not_in_table(offset)
    row, col = locate_cell(grid, offset)
    sentence = f"Lined up the table: {grid.row_count} rows, {grid.col_count} columns"
    return _edit(
        text,
        grid,
        _rows(grid),
        grid.header,
        _alignments(text, grid),
        (row, col),
        sentence,
        pad=True,
    )
