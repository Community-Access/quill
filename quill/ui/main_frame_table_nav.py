"""Table cell navigation commands.

Thin wx wiring over the pure ``quill.core.table_nav``: read the caret and the
document text, find the table around the caret, move to the target cell, and
speak the cell + its position (or "no more cells" / "no more rows" at an edge).
Works on pipe rows -- Markdown documents and the linearized view of a Word or
HTML table -- and on real tables in rich text, read from RichEdit's own row
marks (``quill.core.native_tables``) and edited through
``quill.ui.richedit_tables``, which QUILL Lite calls too.

Host requirements (provided by MainFrame): ``editor``, ``_announce``,
``_set_status``, ``_record_location_before_jump``, ``_location_ring``.
"""

from __future__ import annotations

from typing import Any

#: Navigate > Table, top to bottom: ``(command id, menu label, palette label,
#: handler)``. The moves carry their keys (keymap.py); the edits are keyless, as
#: in QUILL Lite and in Word, and Tab in the last cell adds a row.
_TABLE_ROWS: tuple[tuple[str, str, str, str], ...] = (
    ("table.next_cell", "&Next Cell", "Table: Next Cell", "table_next_cell"),
    ("table.previous_cell", "&Previous Cell", "Table: Previous Cell", "table_previous_cell"),
    ("table.cell_below", "Cell &Below", "Table: Cell Below", "table_cell_below"),
    ("table.cell_above", "Cell &Above", "Table: Cell Above", "table_cell_above"),
    ("table.row_start", "First Cell in &Row", "Table: First Cell in Row", "table_row_start"),
    ("table.row_end", "Last Cell in R&ow", "Table: Last Cell in Row", "table_row_end"),
    ("table.first_cell", "&First Cell", "Table: First Cell", "table_first_cell"),
    ("table.last_cell", "&Last Cell", "Table: Last Cell", "table_last_cell"),
    ("", "", "", ""),
    (
        "table.insert_row_below",
        "&Insert Row Below",
        "Table: Insert Row Below",
        "table_insert_row_below",
    ),
    (
        "table.insert_column_right",
        "Insert Colu&mn Right",
        "Table: Insert Column Right",
        "table_insert_column_right",
    ),
    ("table.delete_row", "&Delete Row", "Table: Delete Row", "table_delete_row"),
    ("table.delete_column", "Delete Col&umn", "Table: Delete Column", "table_delete_column"),
    ("table.tidy", "&Tidy Table", "Table: Tidy Table", "table_tidy"),
)


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
    _document_is_read_only: Any
    _refuse_edit_if_read_only: Any
    _current_editor_mode: Any
    _rich_capable: Any
    _prompt_table_shape: Any

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

    # -- editing the table (quill.core.table_edit), 2026-10-25 ----------------- #

    def table_insert_row_below(self) -> None:
        self._table_edit("insert_row_below")

    def table_insert_column_right(self) -> None:
        self._table_edit("insert_column_right")

    def table_delete_row(self) -> None:
        self._table_edit("delete_row")

    def table_delete_column(self) -> None:
        self._table_edit("delete_column")

    def table_tidy(self) -> None:
        self._table_edit("tidy_table")

    def _insert_real_table(self) -> bool:
        """Insert Table in rich text: RichEdit's own table, one undo step.

        ``False`` (nothing asked, nothing done) unless the document is native
        rich text; Markdown and HTML go on to their own tables.
        """
        if self._current_editor_mode() != "rich" or not self._rich_capable():
            return False
        from quill.ui.richedit_tables import insert_native_table

        shape = self._prompt_table_shape()
        if shape is None:
            self._set_status("Insert table cancelled")
            return True
        rows, columns, include_header = shape
        self._refuse_edit_if_read_only()
        first = insert_native_table(self.editor, rows, columns, header=include_header)
        self.editor.SetInsertionPoint(first)
        self.editor.SetFocus()
        header = ", with a header row" if include_header else ""
        self._announce(
            f"Inserted a table of {rows} rows and {columns} columns{header}. "
            "Tab moves to the next cell."
        )
        return True

    def _table_edit(self, name: str) -> None:
        """One table edit, as one undo step; land in the cell it names, say it."""
        from quill.core import table_edit
        from quill.ui.atomic_edit import replace_as_one_undo

        editor = getattr(self, "editor", None)
        if editor is None:
            return
        from quill.ui import richedit_tables

        text, caret = editor.GetValue(), editor.GetInsertionPoint()
        if "￹" in text:  # rich text holding a real table (RichEdit's row mark)
            self._refuse_edit_if_read_only()
            native = richedit_tables.native_edit(editor, text, caret, name)
            if native is not None:  # the caret is in it: rebuilt in place
                self._announce(native.announcement)
                return
        edit = getattr(table_edit, name)(text, caret)
        if edit.replacement is not None:
            self._refuse_edit_if_read_only()
            replace_as_one_undo(editor, edit.start, edit.end, edit.replacement)
            editor.SetInsertionPoint(edit.caret)
        self._announce(edit.announcement)

    def _table_arrow(self, event: Any) -> bool:
        """A plain arrow in or into a table: move by cell and say it. ``True``
        when it did, and the key is consumed -- and with it the screen reader's
        reading of the whole row as one line (``table_nav.arrow_move``, which
        QUILL Lite calls too).

        Only a bare arrow with a caret, not a selection, and no selection mode
        or F8 marker running: Shift selects, Ctrl moves by word, and the
        selection modes own the arrows while they are on.
        """
        import wx

        from quill.core import table_nav

        names = {
            wx.WXK_UP: "up",
            wx.WXK_NUMPAD_UP: "up",
            wx.WXK_DOWN: "down",
            wx.WXK_NUMPAD_DOWN: "down",
            wx.WXK_LEFT: "left",
            wx.WXK_NUMPAD_LEFT: "left",
            wx.WXK_RIGHT: "right",
            wx.WXK_NUMPAD_RIGHT: "right",
        }
        try:
            key = names.get(event.GetKeyCode())
            if key is None or event.ControlDown() or event.AltDown() or event.ShiftDown():
                return False
        except Exception:  # noqa: BLE001 - a stand-in event: not ours
            return False
        if getattr(self, "_extend_selection_mode", False):
            return False
        if getattr(self, "_selection_anchor", None) is not None:
            return False
        editor = getattr(self, "editor", None)
        if editor is None:
            return False
        try:
            start, end = editor.GetSelection()
            if start != end:
                return False
            step = table_nav.arrow_move(editor.GetValue(), start, key)
        except Exception:  # noqa: BLE001 - a non-text surface: the key is its own
            return False
        if step is None or step.offset is None:
            return False
        editor.SetInsertionPoint(step.offset)
        # The caret crossed into the table on our say-so, and the sentence gave
        # its shape: the structure cue must not say it again.
        sync = getattr(self, "sync_structure_announcer", None)
        if callable(sync):
            sync()
        self._announce(step.announcement)
        return True

    def _table_tab(self, *, backwards: bool) -> bool:
        """Tab and Shift+Tab inside a table: cell to cell. ``False`` outside one.

        Tab in the last cell adds a row, as in Word -- unless the document is
        read-only, where it says the table ends instead.
        """
        from quill.core import table_nav
        from quill.ui.atomic_edit import replace_as_one_undo

        editor = getattr(self, "editor", None)
        if editor is None:
            return False
        try:
            step = table_nav.tab_move(
                editor.GetValue(), editor.GetInsertionPoint(), backwards=backwards
            )
        except Exception:  # noqa: BLE001 - a non-text surface: Tab means Tab
            return False
        if step is None:
            return False
        if (step.insert is not None or step.add_row) and self._document_is_read_only():
            self._announce("No more cells, end of table")
            return True
        if step.add_row:  # a real table: RichEdit's own row, as in Word
            from quill.ui import richedit_tables

            landing = richedit_tables.native_tab_add_row(
                editor, editor.GetValue(), editor.GetInsertionPoint()
            )
            if landing is not None:
                editor.SetInsertionPoint(landing)
        if step.insert is not None:
            position, text = step.insert
            replace_as_one_undo(editor, position, position, text)
        if step.offset is not None:
            editor.SetInsertionPoint(step.offset)
        self._announce(step.announcement)
        return True

    # -- Navigate > Table ------------------------------------------------------ #

    def _table_menu_ids(self) -> dict[str, Any]:
        ids = getattr(self, "_table_row_ids", None)
        if ids is None:
            import wx

            ids = {row[0]: wx.NewIdRef() for row in _TABLE_ROWS if row[0]}
            self._table_row_ids = ids
        return ids

    def _append_table_submenu(self, navigate_menu: Any) -> None:
        """Navigate > Table: the eight moves and the five edits, as in QUILL Lite.

        The edits are registered here, beside their rows, so the whole table menu
        is one module; the moves are registered with the other navigation
        commands (main_frame_commands.py).
        """
        import wx

        from quill.core.i18n import _

        ids = self._table_menu_ids()
        submenu = wx.Menu()
        for command_id, label, palette, handler_name in _TABLE_ROWS:
            if not command_id:
                submenu.AppendSeparator()
                continue
            if command_id not in {"table." + n for n in _MOVES}:
                self.commands.try_register(  # type: ignore[attr-defined]
                    command_id,
                    palette,
                    getattr(self, handler_name),
                    self._binding_for(command_id),  # type: ignore[attr-defined]
                )
            submenu.Append(ids[command_id], self._menu_label(_(label), command_id))  # type: ignore[attr-defined]
        navigate_menu.AppendSubMenu(submenu, _("&Table"))
        if not getattr(self, "_table_rows_wired", False):
            self._table_rows_wired = True
            for command_id, _label, _palette, handler_name in _TABLE_ROWS:
                if command_id:
                    handler = getattr(self, handler_name)
                    self.frame.Bind(  # type: ignore[attr-defined]
                        wx.EVT_MENU, lambda _e, run=handler: run(), id=ids[command_id]
                    )

    def _command_to_menu_id_map(self) -> dict[str, int]:
        mapping: dict[str, int] = super()._command_to_menu_id_map()  # type: ignore[misc]
        mapping.update(self._table_menu_ids())
        return mapping


#: The command-id suffixes main_frame_commands.py already registers.
_MOVES = (
    "next_cell",
    "previous_cell",
    "cell_below",
    "cell_above",
    "row_start",
    "row_end",
    "first_cell",
    "last_cell",
)
