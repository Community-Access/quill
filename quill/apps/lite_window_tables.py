"""Moving through a table cell by cell, on QUILL's keys (2026-10-17).

QUILL has had table navigation since its Markdown tables learned to be read:
Ctrl+Alt+Right and Left for the next and previous cell in the row, Ctrl+Alt+Down
and Up for the cell below and above, Alt+Home and Alt+End for the ends of the
row, and Ctrl+Alt+Home and End for the first and last cell of the table. Each
move says where it landed -- "Row 2 of 4, column 3 of 5: Lead" -- and an edge
says so instead of moving ("No more cells", "No more rows, end of table").

QUILL Lite had none of it, which mattered once it opened Word documents to
edit: a Word table arrives as rows of cells divided by ``|``, in rich text and
in plain text alike, and so does every Markdown table. So it crosses whole, by
family rule 2 -- the command both products have keeps the chord -- with every
decision in the shared, wx-free :mod:`quill.core.table_nav` that QUILL's own
``quill.ui.main_frame_table_nav`` calls. What lives here is QUILL Lite's thin
side: read the text and the caret, move through ``_go_to`` (so Go Back returns
from a cell jump as from any other), and say the sentence the core wrote.

Outside a table every key says "Not in a table" and leaves the caret alone.
"""

from __future__ import annotations

from quill.core import table_nav

__all__ = ["DocumentTableNavMixin"]


class DocumentTableNavMixin:
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
