"""Real tables in rich text: aligned text, inserting, and editing them.

In a rich document a table is RichEdit's own -- a grid on screen, a table to
Word and WordPad -- and this module is what makes the rest of QUILL work on it.

**Aligned text.** RichEdit counts its table marks in every caret position, but
``GetValue`` leaves them out, so after a table every offset a feature computed
from the text (Find, headings, bookmarks, the table keys) would land a few
characters early. :func:`install_aligned_text` gives the control a ``GetValue``
that returns the Text Object Model's own text -- marks kept, paragraph breaks as
``\\n``, cell marks as ``\\t`` -- one character per position, whenever the
document holds a table; without one it is the control's own answer, unchanged
and as fast as before. :mod:`quill.core.native_tables` reads tables from it.

**Inserting** (:func:`insert_rtf`): an RTF fragment at the caret through
``EM_SETTEXTEX``, which RichEdit records as one undo step -- no stream callback,
which is the route that crashed msftedit (richedit_rtf_surface.py).

**Editing** (:func:`edit_native_table`): a row or column change rebuilds the
table from its cells through :mod:`quill.core.table_edit`, the same operations
a Markdown table uses, and puts it back in place as one undo step. Text inside
the cells is kept; character formatting inside the cells of an edited table is
not (a known cost of rebuilding, written in the user guides).
"""

from __future__ import annotations

import ctypes
from typing import Any

from quill.core import native_tables, table_edit, table_nav
from quill.io.rtf_tables import pipe_rows_to_rtf_tables

__all__ = [
    "aligned_text",
    "edit_native_table",
    "insert_native_table",
    "insert_rtf",
    "install_aligned_text",
    "rtf_escape",
]

_EM_SETTEXTEX = 0x0400 + 97
_ST_KEEPUNDO = 1
_ST_SELECTION = 2
#: tomStory: a range expanded to the whole document.
_TOM_STORY = 6


def aligned_text(tom_text: str, length: int) -> str:
    """The control's TOM text as one-character-per-position text (pure).

    *length* is the control's last position: the story's final paragraph mark
    lies beyond it and is dropped.
    """
    return tom_text[:length].replace("\r", "\n").replace("\x07", native_tables.CELL)


def install_aligned_text(surface: Any, document: Any) -> None:
    """Give *surface* a ``GetValue`` (and ``GetRange``) aligned with its positions.

    *document* is a callable returning the control's ``ITextDocument``. Only an
    instance attribute changes; the control itself is untouched, and anything
    that fails falls back to the control's own answer.
    """
    native_value = getattr(surface, "GetValue", None)
    native_range = getattr(surface, "GetRange", None)
    if native_value is None or native_range is None:
        return  # not a text control: nothing to align

    def get_value() -> str:
        value = native_value()
        try:
            last = int(surface.GetLastPosition())
        except Exception:  # noqa: BLE001 - a dying control: its own answer
            return value
        if len(value) == last:
            return value  # no table, no hidden text: already aligned
        try:
            story = document().Range(0, 0)
            story.Expand(_TOM_STORY)
            return aligned_text(str(story.Text), last)
        except Exception:  # noqa: BLE001 - TOM unavailable: the control's text
            return value

    def get_range(start: int, end: int) -> str:
        value = native_value()
        try:
            if len(value) == int(surface.GetLastPosition()):
                return str(native_range(start, end))
        except Exception:  # noqa: BLE001
            return str(native_range(start, end))
        return get_value()[start:end]

    surface.GetValue = get_value
    surface.GetRange = get_range


def insert_rtf(surface: Any, fragment: str) -> None:
    """Put the RTF *fragment* in place of the selection, as one undo step."""

    class _SetTextEx(ctypes.Structure):
        _fields_ = [("flags", ctypes.c_uint32), ("codepage", ctypes.c_uint)]

    info = _SetTextEx(_ST_SELECTION | _ST_KEEPUNDO, 0)  # CP_ACP: RTF is bytes
    data = ctypes.c_char_p(fragment.encode("ascii", errors="replace"))
    send = ctypes.windll.user32.SendMessageW  # type: ignore[attr-defined]
    send.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
    send(
        surface.GetHandle(),
        _EM_SETTEXTEX,
        ctypes.addressof(info),
        ctypes.cast(data, ctypes.c_void_p).value,
    )


def rtf_escape(text: str) -> str:
    """Plain cell text as RTF: braces and backslashes escaped, anything past
    ASCII as a Unicode escape (``\\uN?``), so no code page can garble it."""
    out: list[str] = []
    for char in text:
        if char in "\\{}":
            out.append("\\" + char)
        elif ord(char) < 128:
            out.append(char)
        else:
            code = ord(char)
            out.append(f"\\u{code - 65536 if code > 32767 else code}?")
    return "".join(out)


def table_fragment(rows: list[list[str]], *, header: bool = True, lead_break: bool = False) -> str:
    """An RTF fragment holding one real table of *rows* (plain cell text)."""
    lines = []
    for index, row in enumerate(rows):
        lines.append(
            "\\pard | "
            + " | ".join(rtf_escape(c).replace("|", "\\\\|") for c in row)
            + " |\\par\r\n"
        )
        if index == 0 and header:
            lines.append("\\pard | " + " | ".join("---" for _ in row) + " |\\par\r\n")
    body = ("\\pard\\par\r\n" if lead_break else "") + "".join(lines)
    converted = pipe_rows_to_rtf_tables("{\\rtf1\\ansi\\deff0\r\n" + body + "}")
    # The table ends the fragment: nothing after it, so no empty paragraph.
    return converted


def insert_native_table(surface: Any, rows: int, columns: int, *, header: bool) -> int:
    """Insert a real table of *rows* x *columns* at the caret; returns the offset
    of its first cell, ready to type in."""
    start, _end = surface.GetSelection()
    text = surface.GetValue()
    line_start = text[:start].rsplit("\n", 1)[-1] == ""
    names = [f"Column {i}" for i in range(1, columns + 1)] if header else [""] * columns
    grid = [names, *[[""] * columns for _ in range(rows)]]
    insert_rtf(surface, table_fragment(grid, header=header, lead_break=not line_start))
    after = surface.GetValue()
    search_from = start + (0 if line_start else 1)
    found = native_tables.find_native_table_at(
        after, after.find(native_tables.ROW_START, search_from) + 2
    )
    return (
        found.rows[0][0].offset if found is not None and found.rows else surface.GetInsertionPoint()
    )


def _pipe_text(grid: table_nav.TableGrid) -> str:
    rows = [[cell.text for cell in row] for row in grid.rows]
    columns = grid.col_count
    lines = []
    for index, row in enumerate(rows):
        padded = row + [""] * (columns - len(row))
        lines.append("| " + " | ".join(c.replace("|", "\\|") for c in padded) + " |")
        if index == 0 and grid.header:
            lines.append("| " + " | ".join("---" for _ in range(columns)) + " |")
    return "\n".join(lines) + "\n"


def edit_native_table(
    surface: Any, grid: table_nav.TableGrid, caret: int, operation: str
) -> table_edit.TableEdit:
    """Apply a :mod:`quill.core.table_edit` *operation* to the real table *grid*.

    The table is rebuilt from its cells with the change made and put back in
    place, as one undo step, and the caret lands in the cell the operation
    names. The returned edit carries the sentence to say; ``replacement`` is
    None when the operation refused (nothing was changed).
    """
    if operation == "tidy_table":
        # A real table keeps its own columns; rebuilding it would only cost
        # the formatting inside its cells.
        return table_edit.TableEdit(caret, caret, None, caret, "A real table is already lined up")
    row, col = table_nav.locate_cell(grid, caret)
    pipe = _pipe_text(grid)
    pipe_grid = table_nav.find_table_at(pipe, 0)
    if pipe_grid is None:
        return table_edit.TableEdit(caret, caret, None, caret, "Not in a table")
    target = pipe_grid.cell(row, col) or pipe_grid.cell(row, 0)
    edit = getattr(table_edit, operation)(pipe, target.offset if target else 0)
    if edit.replacement is None:
        return table_edit.TableEdit(caret, caret, None, caret, edit.announcement)
    new_pipe = pipe[: edit.start] + edit.replacement + pipe[edit.end :]
    new_grid = table_nav.find_table_at(new_pipe, edit.caret)
    if new_grid is None:
        return table_edit.TableEdit(caret, caret, None, caret, edit.announcement)
    land_row, land_col = table_nav.locate_cell(new_grid, edit.caret)
    rows = [[cell.text for cell in r] for r in new_grid.rows]
    surface.SetSelection(grid.span_start, grid.span_end)
    insert_rtf(surface, table_fragment(rows, header=new_grid.header))
    after = surface.GetValue()
    rebuilt = native_tables.find_native_table_at(after, grid.span_start + 2)
    landing = caret
    if rebuilt is not None:
        cell = rebuilt.cell(land_row, land_col) or rebuilt.cell(land_row, 0)
        landing = cell.offset if cell is not None else rebuilt.span_start
    surface.SetInsertionPoint(landing)
    return table_edit.TableEdit(grid.span_start, grid.span_end, "", landing, edit.announcement)


def add_row_at_end(surface: Any, grid: table_nav.TableGrid) -> int:
    """Tab in a real table's last cell: a blank row under it; returns the new
    row's first cell."""
    last_row = grid.rows[-1]
    caret = last_row[0].offset if last_row else grid.span_start
    edit = edit_native_table(surface, grid, caret, "insert_row_below")
    return edit.caret


def native_edit(surface: Any, text: str, caret: int, operation: str) -> table_edit.TableEdit | None:
    """*operation* on the real table at *caret*, or ``None`` when the caret is
    not in one (the caller edits pipe rows as before). Both editors' table
    commands come through here, so the two cannot drift."""
    grid = table_nav.find_table_at(text, caret)
    if grid is None or not grid.native:
        return None
    return edit_native_table(surface, grid, caret, operation)


def native_tab_add_row(surface: Any, text: str, caret: int) -> int | None:
    """Tab in a real table's last cell: add the row, return where to land."""
    grid = table_nav.find_table_at(text, caret)
    if grid is None or not grid.native:
        return None
    return add_row_at_end(surface, grid)
