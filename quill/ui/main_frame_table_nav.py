"""Table cell navigation commands.

Thin wx wiring over the pure ``quill.core.table_nav``: read the caret and the
document text, find the table around the caret, move to the target cell, and
speak the cell + its position (or "no more cells" / "no more rows" at an edge).
Works on any surface whose text presents tables as pipe rows -- Markdown
documents and the linearized view of a real Word/HTML table.

Host requirements (provided by MainFrame): ``editor``, ``_announce``,
``_set_status``, ``_record_location_before_jump``, ``_location_ring``.
"""

from __future__ import annotations

from typing import Any


class TableNavMixin:
    editor: Any
    _location_ring: Any
    # Host-provided by MainFrame. These MUST be type-only annotations, not method
    # stubs: a concrete ``def _set_status(...): ...`` here shadows the real
    # StatusBarMixin implementation via MRO (TableNavMixin precedes it in
    # MainFrame's bases), silently turning status messages, screen-reader
    # announcements, and location tracking into no-ops app-wide.
    _announce: Any
    _set_status: Any
    _record_location_before_jump: Any

    def table_next_cell(self) -> None:
        self._table_nav("next")

    def table_previous_cell(self) -> None:
        self._table_nav("previous")

    def table_cell_below(self) -> None:
        self._table_nav("down")

    def table_cell_above(self) -> None:
        self._table_nav("up")

    def table_row_start(self) -> None:
        self._table_nav("row_start")

    def table_row_end(self) -> None:
        self._table_nav("row_end")

    def table_first_cell(self) -> None:
        self._table_nav("table_start")

    def table_last_cell(self) -> None:
        self._table_nav("table_end")

    def _table_nav(self, action: str) -> None:
        """Shared handler: move to the ``action`` cell of the table at the caret.

        When the caret is not inside a table, say so and leave the caret where it
        is -- the chord is harmless outside a table.
        """
        from quill.core import table_nav

        editor = getattr(self, "editor", None)
        if editor is None:
            return
        try:
            text = editor.GetValue()
            caret = editor.GetInsertionPoint()
        except Exception:  # noqa: BLE001 - a non-text surface: nothing to do
            return
        grid = table_nav.find_table_at(text, caret)
        if grid is None:
            self._set_status("Not in a table")
            return
        result = table_nav.move(grid, caret, action)
        if result.offset is None:
            self._announce(result.announcement)  # "No more cells" / "No more rows"
            return
        self._record_location_before_jump()
        editor.SetInsertionPoint(result.offset)
        editor.SetSelection(result.offset, result.offset)
        editor.SetFocus()
        try:
            self._location_ring.record(result.offset)
        except Exception:  # noqa: BLE001 - the location ring is best-effort
            pass
        self._announce(result.announcement)
