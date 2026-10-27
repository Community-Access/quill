"""Moving through a table cell by cell, on QUILL's keys (2026-10-17).

QUILL has had table navigation since its Markdown tables learned to be read:
Ctrl+Alt+Right and Left for the next and previous cell in the row, Ctrl+Alt+Down
and Up for the cell below and above, Alt+Home and Alt+End for the ends of the
row, and Ctrl+Alt+Home and End for the first and last cell of the table. Each
move says where it landed -- "Row 2 of 4, column 3 of 5: Lead" -- and an edge
says so instead of moving ("No more cells", "No more rows, end of table").

QUILL Lite had none of it, which mattered once it opened Word documents to
edit: a Word table arrives as a real table in rich text and as rows of cells
divided by ``|`` in plain text, and so does every Markdown table. A real table
is read from RichEdit's own marks (:mod:`quill.core.native_tables`) and edited
through :mod:`quill.ui.richedit_tables`; the keys and the sentences are the
same for both. So it crosses whole, by
family rule 2 -- the command both products have keeps the chord -- with every
decision in the shared, wx-free :mod:`quill.core.table_nav` that QUILL's own
``quill.ui.main_frame_table_nav`` calls. What lives here is QUILL Lite's thin
side: read the text and the caret, move through ``_go_to`` (so Go Back returns
from a cell jump as from any other), and say the sentence the core wrote.

Outside a table every key says "Not in a table" and leaves the caret alone.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.apps.lite_window_insert_table import DocumentTableMixin
from quill.core import table_edit, table_nav
from quill.ui import richedit_tables
from quill.ui.atomic_edit import replace_as_one_undo

__all__ = ["DocumentTableNavMixin"]

#: The arrow keys a table answers, by name (table_nav.ARROWS).
_ARROW_NAMES = {
    wx.WXK_UP: "up",
    wx.WXK_NUMPAD_UP: "up",
    wx.WXK_DOWN: "down",
    wx.WXK_NUMPAD_DOWN: "down",
    wx.WXK_LEFT: "left",
    wx.WXK_NUMPAD_LEFT: "left",
    wx.WXK_RIGHT: "right",
    wx.WXK_NUMPAD_RIGHT: "right",
}


class DocumentTableNavMixin(DocumentTableMixin):  # and Insert > Table, its own module
    """The eight table moves. Composed onto ``DocumentFrame``."""

    def cmd_table_next_cell(self) -> None:
        self._table_move("next")

    def cmd_table_previous_cell(self) -> None:
        self._table_move("previous")

    def cmd_table_cell_below(self) -> None:
        self._table_move("down")

    def cmd_table_cell_above(self) -> None:
        self._table_move("up")

    def cmd_table_row_start(self) -> None:
        self._table_move("row_start")

    def cmd_table_row_end(self) -> None:
        self._table_move("row_end")

    def cmd_table_first_cell(self) -> None:
        self._table_move("table_start")

    def cmd_table_last_cell(self) -> None:
        self._table_move("table_end")

    def _table_move(self, action: str) -> None:
        """Move to the *action* cell of the table at the caret, and say where."""
        caret = self.control.GetInsertionPoint()
        grid = table_nav.find_table_at(self.doc_text.text, caret)
        if grid is None:
            self._announce("Not in a table")
            return
        result = table_nav.move(grid, caret, action)
        if result.offset is not None:
            self._go_to(result.offset)
        self._announce(result.announcement)

    # -- editing the table (quill.core.table_edit), 2026-10-25 ----------------- #

    def cmd_table_insert_row_below(self) -> None:
        self._table_edit(table_edit.insert_row_below)

    def cmd_table_delete_row(self) -> None:
        self._table_edit(table_edit.delete_row)

    def cmd_table_insert_column_right(self) -> None:
        self._table_edit(table_edit.insert_column_right)

    def cmd_table_delete_column(self) -> None:
        self._table_edit(table_edit.delete_column)

    def cmd_table_tidy(self) -> None:
        self._table_edit(table_edit.tidy_table)

    def _table_edit(self, edit_for: Callable[[str, int], table_edit.TableEdit]) -> None:
        """Make one table edit as one undo step, land in the cell it names, say it.

        The read-only guard sits in front of these handlers already (they are in
        ``TEXT_CHANGING_HANDLERS``), so this only ever runs on editable text.
        """
        text, caret = self.doc_text.text, self.control.GetInsertionPoint()
        native = richedit_tables.native_edit(self.control, text, caret, edit_for.__name__)
        if native is not None:  # a real table in rich text: rebuilt in place
            if native.replacement is not None:
                self.doc_text.invalidate()
                self._set_modified(True)
                self._touch_status()
            self._announce(native.announcement)
            return
        edit = edit_for(text, caret)
        if edit.replacement is not None:
            replace_as_one_undo(self.control, edit.start, edit.end, edit.replacement)
            self.doc_text.invalidate()  # as every rewrite here does: no stale snapshot
            self.control.SetInsertionPoint(edit.caret)
            self._set_modified(True)
            self._touch_status()
        self._announce(edit.announcement)

    def _table_arrow(self, event: Any) -> bool:
        """A plain arrow in or into a table: move by cell and say it. ``True``
        when it did, so the key is consumed -- and with it, the screen reader's
        reading of the whole row as one line (:func:`table_nav.arrow_move`).

        The key is the app's to answer only when nothing else wants it: no
        modifier (Shift selects, Ctrl moves by word), no F8 selection marker
        down (arrows extend it), and a caret that is not a selection.
        """
        key = _ARROW_NAMES.get(event.GetKeyCode())
        if key is None:
            return False
        held = [getattr(event, n, lambda: False)() for n in ("ControlDown", "AltDown", "ShiftDown")]
        if any(held) or getattr(self, "_selection_anchor", None) is not None:
            return False
        start, end = self.control.GetSelection()
        if start != end:
            return False
        step = table_nav.arrow_move(self.doc_text.text, start, key)
        if step is None or step.offset is None:
            return False
        self.control.SetInsertionPoint(step.offset)
        # The caret crossed into the table on our say-so, and the sentence
        # already gave its shape: the structure cue must not say it again.
        sync = getattr(self, "sync_structure_announcer", None)
        if callable(sync):
            sync()
        self._announce(step.announcement)
        return True

    def _table_tab(self, *, backwards: bool) -> bool:
        """Tab and Shift+Tab inside a table: cell to cell. ``False`` outside one.

        Tab in the very last cell adds a row, as in Word -- unless the document
        is guarded read-only, where it says the table ends instead of typing.
        """
        caret = self.control.GetInsertionPoint()
        step = table_nav.tab_move(self.doc_text.text, caret, backwards=backwards)
        if step is None:
            return False
        if (step.insert is not None or step.add_row) and self.read_only_active():
            self._announce("No more cells, end of table")
            return True
        if step.add_row:  # a real table: RichEdit's own row, as in Word
            landing = richedit_tables.native_tab_add_row(self.control, self.doc_text.text, caret)
            self.doc_text.invalidate()
            self._set_modified(True)
            self._touch_status()
            if landing is not None:
                self.control.SetInsertionPoint(landing)
        if step.insert is not None:
            position, text = step.insert
            replace_as_one_undo(self.control, position, position, text)
            self.doc_text.invalidate()
            self._set_modified(True)
            self._touch_status()
        if step.offset is not None:
            self.control.SetInsertionPoint(step.offset)
        self._announce(step.announcement)
        return True
