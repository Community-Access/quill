"""Table Studio / CSV Studio — an accessible grid surface (experimental).

A virtual ``wx.ListCtrl`` (SysListView32) in report mode, backed by the wx-free
:mod:`quill.core.table_studio` model/controller. Up/Down move rows natively;
Left/Right track an active column announced through the MSAA provider in
:mod:`quill.ui.table_studio_accessible`, so NVDA and JAWS speak the column as you
arrow across a row. F2/Enter edit a cell; Alt+arrows move rows/columns;
Ctrl+Insert / Delete add or clear. The table can be inserted into the document
as Markdown or HTML, and CSV files open straight into the grid (CSV Studio).

Ported from the retired Table Studio prototype (its macOS NSAccessibility
design note survives at ``docs/design/table-studio-macos-nsaccessibility.md``).
This is an experimental opt-in (Preferences > Experimental); the MSAA cell
navigation still needs real screen-reader validation on a packaged build.
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.core.table_studio import Change, TableController, TableDocumentModel
from quill.ui import table_studio_native
from quill.ui.table_studio_accessible import attach_list_accessibility, fire_focus_child


class TableListCtrl(wx.ListCtrl):
    """Virtual, column-tracked, accessible table grid."""

    def __init__(
        self,
        parent: wx.Window,
        model: TableDocumentModel,
        ctrl: TableController,
        announce: Callable[[str], None],
    ) -> None:
        super().__init__(
            parent,
            style=wx.LC_REPORT | wx.LC_VIRTUAL | wx.WANTS_CHARS | wx.LC_SINGLE_SEL | wx.LC_HRULES,
        )
        self._model = model
        self._ctrl = ctrl
        self._announce = announce
        self._active_col = 0
        self._prev_ann_row: int | None = None
        self._prev_ann_col: int | None = None
        self._setup_columns()
        self.SetItemCount(model.row_count)
        self.SetName(f"{model.caption or 'Table'} grid")
        self._acc = attach_list_accessibility(
            self,
            {
                "row_count": lambda: self.GetItemCount(),
                "col_count": lambda: self._model.col_count,
                "caption": lambda: self._model.caption or "Table",
                "active": lambda: (self.GetFirstSelected(), self._active_col),
                "describe": self._describe_cell,
                "cell_rect": self._screen_cell_rect,
            },
        )
        # Prefer the compiled native UIA provider (cell-level focus + header
        # relationships) when it is present; otherwise the MSAA provider above
        # carries navigation. Both are best-effort and never required.
        self._native = table_studio_native.attach(
            int(self.GetHandle()),
            get_dims=lambda: (self._model.row_count, self._model.col_count),
            get_value=self._model.value,
            get_col_header=self._model.col_header,
            get_row_header=self._model.row_header,
            get_focus=lambda: (self._active_display_row(), self._active_col),
            set_focus=self._goto,
            is_editable=self._model.is_editable,
            caption=model.caption or "Table",
        )
        if model.row_count:
            self._select_row(0)
        self.Bind(wx.EVT_KEY_DOWN, self._on_key)
        self.Bind(wx.EVT_CONTEXT_MENU, self._on_context_menu)
        self.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)
        model.add_listener(self._on_model_change)

    def _on_context_menu(self, _evt: wx.ContextMenuEvent) -> None:
        self.show_context_menu()

    def _on_destroy(self, evt: wx.WindowDestroyEvent) -> None:
        native = getattr(self, "_native", None)
        if native is not None:
            native.detach()
        evt.Skip()

    # -- virtual data ----------------------------------------------------- #

    def OnGetItemText(self, item: int, col: int) -> str:
        return self._model.value(item, col)

    # -- columns ---------------------------------------------------------- #

    def _setup_columns(self) -> None:
        self.ClearAll()
        for ci, column in enumerate(self._model.columns):
            self.InsertColumn(ci, self._model.col_header(ci), width=max(column.width_hint, 90))

    # -- navigation ------------------------------------------------------- #

    def _active_display_row(self) -> int:
        di = self.GetFirstSelected()
        return di if di >= 0 else 0

    def _select_row(self, di: int) -> None:
        di = max(0, min(di, self.GetItemCount() - 1))
        cur = self.GetFirstSelected()
        if cur != di and cur >= 0:
            self.SetItemState(cur, 0, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)
        self.SetItemState(
            di,
            wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED,
            wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED,
        )
        self.EnsureVisible(di)

    def _goto(self, di: int, col: int) -> None:
        di = max(0, min(di, self.GetItemCount() - 1))
        self._active_col = max(0, min(col, self._model.col_count - 1))
        self._select_row(di)
        self._announce_cell(fire=False)

    def _on_key(self, evt: wx.KeyEvent) -> None:
        key = evt.GetKeyCode()
        mod = evt.GetModifiers()
        ctrl = bool(mod & wx.MOD_CONTROL)
        alt = bool(mod & wx.MOD_ALT)
        shft = bool(mod & wx.MOD_SHIFT)
        plain = not ctrl and not alt and not shft

        if self.GetItemCount() == 0:
            # Empty table (a headers-only CSV): navigation/edit would clamp to
            # row 0 and assert inside wx.ListCtrl (#802 review). Only row
            # insertion makes sense until a first row exists.
            if ctrl and key == wx.WXK_INSERT:
                self.insert_row_below()
            else:
                evt.Skip()
            return

        if plain and key == wx.WXK_UP:
            self._goto(self._active_display_row() - 1, self._active_col)
        elif plain and key == wx.WXK_DOWN:
            self._goto(self._active_display_row() + 1, self._active_col)
        elif not ctrl and not alt and key == wx.WXK_LEFT:
            if self._active_col > 0:
                self._active_col -= 1
                self._announce_cell()
        elif not ctrl and not alt and key == wx.WXK_RIGHT:
            if self._active_col < self._model.col_count - 1:
                self._active_col += 1
                self._announce_cell()
        elif not ctrl and not alt and key == wx.WXK_HOME:
            self._active_col = 0
            self._announce_cell()
        elif not ctrl and not alt and key == wx.WXK_END:
            self._active_col = max(0, self._model.col_count - 1)
            self._announce_cell()
        elif ctrl and key == wx.WXK_HOME:
            self._goto(0, 0)
        elif ctrl and key == wx.WXK_END:
            self._goto(self.GetItemCount() - 1, self._model.col_count - 1)
        elif plain and key == wx.WXK_PAGEUP:
            self._goto(self._active_display_row() - self._page_size(), self._active_col)
        elif plain and key == wx.WXK_PAGEDOWN:
            self._goto(self._active_display_row() + self._page_size(), self._active_col)
        elif alt and key == wx.WXK_UP:
            self._move_row(-1)
        elif alt and key == wx.WXK_DOWN:
            self._move_row(1)
        elif alt and key == wx.WXK_LEFT:
            self._move_col(-1)
        elif alt and key == wx.WXK_RIGHT:
            self._move_col(1)
        elif plain and key in (wx.WXK_F2, wx.WXK_RETURN):
            self.edit_active_cell()
        elif ctrl and key == wx.WXK_INSERT:
            self.insert_row_below()
        elif plain and key == wx.WXK_DELETE:
            self.clear_active_cell()
        elif key == wx.WXK_WINDOWS_MENU or (shft and key == wx.WXK_F10):
            self.show_context_menu()
        else:
            evt.Skip()

    # -- operations ------------------------------------------------------- #

    def _page_size(self) -> int:
        """Rows skipped per Page Up/Down — the model's AnnounceConfig owns it."""
        size = getattr(getattr(self._model, "announce_config", None), "page_size", 10)
        return max(1, int(size))

    def _row_col(self) -> tuple[int, int]:
        return self._active_display_row(), self._active_col

    def edit_active_cell(self) -> None:
        row, col = self._row_col()
        current = self._model.value(row, col)
        header = self._model.col_header(col)
        with wx.TextEntryDialog(
            self, f"Edit cell — {header}, row {row + 1}:", "Edit Cell", value=current
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                if self._model.set_value(row, col, dlg.GetValue()):
                    self._announce("Edit committed.")
                    self._announce_cell(fire=False)

    def clear_active_cell(self) -> None:
        row, col = self._row_col()
        if self._model.set_value(row, col, ""):
            self._announce("Cell cleared.")

    def insert_row_below(self) -> None:
        row, _col = self._row_col()
        self._model.insert_row(row + 1)
        self._announce("Row inserted.")

    def insert_row_above(self) -> None:
        row, _col = self._row_col()
        self._model.insert_row(row)
        self._announce("Row inserted.")

    def delete_row(self) -> None:
        if self._model.row_count <= 1:
            self._announce("Cannot delete the only row.")
            return
        row, _col = self._row_col()
        self._model.delete_row(row)
        self._announce("Row deleted.")

    def insert_column(self) -> None:
        _row, col = self._row_col()
        self._model.insert_col(col + 1)
        self._announce("Column inserted.")

    def delete_column(self) -> None:
        if self._model.col_count <= 1:
            self._announce("Cannot delete the only column.")
            return
        _row, col = self._row_col()
        self._model.delete_col(col)
        self._active_col = max(0, col - 1)
        self._announce("Column deleted.")

    def _move_row(self, delta: int) -> None:
        row, _col = self._row_col()
        if self._model.move_row(row, row + delta):
            self._announce("Row moved up." if delta < 0 else "Row moved down.")

    def _move_col(self, delta: int) -> None:
        _row, col = self._row_col()
        if self._model.move_col(col, col + delta):
            self._active_col = col + delta
            self._announce("Column moved left." if delta < 0 else "Column moved right.")

    def move_row_up(self) -> None:
        self._move_row(-1)

    def move_row_down(self) -> None:
        self._move_row(1)

    def sort_ascending(self) -> None:
        _row, col = self._row_col()
        if self._model.sort_by_column(col, ascending=True):
            self._announce(f"Sorted by {self._model.col_header(col)}, ascending.")

    def sort_descending(self) -> None:
        _row, col = self._row_col()
        if self._model.sort_by_column(col, ascending=False):
            self._announce(f"Sorted by {self._model.col_header(col)}, descending.")

    def toggle_row_headers(self) -> None:
        enabled = not self._model.has_row_header()
        self._model.set_first_column_as_row_header(enabled)
        self._announce(
            "First column is now a row header."
            if enabled
            else "First column is no longer a row header."
        )

    def rename_column_header(self) -> None:
        _row, col = self._row_col()
        current = self._model.col_header(col)
        with wx.TextEntryDialog(
            self, f"Header for column {col + 1}:", "Rename Column Header", value=current
        ) as dlg:
            if dlg.ShowModal() == wx.ID_OK and dlg.GetValue().strip():
                self._model.set_col_label_override(col, dlg.GetValue())
                self._announce(f"Column header set to {dlg.GetValue()}.")

    def promote_first_row_to_header(self) -> None:
        if self._model.promote_first_row_to_header():
            self._announce("First row promoted to column headers.")
        else:
            self._announce("Nothing to promote.")

    # -- context menu ----------------------------------------------------- #

    def show_context_menu(self) -> None:
        """The right-click / Apps / Shift+F10 menu — every grid action, spoken."""
        menu = wx.Menu()
        has_row_header = self._model.has_row_header()
        entries = [
            ("Edit Cell (F2)", self.edit_active_cell),
            ("Rename Column Header...", self.rename_column_header),
            (None, None),
            ("Sort Ascending", self.sort_ascending),
            ("Sort Descending", self.sort_descending),
            (None, None),
            ("Insert Row Above", self.insert_row_above),
            ("Insert Row Below", self.insert_row_below),
            ("Delete Row", self.delete_row),
            ("Move Row Up", self.move_row_up),
            ("Move Row Down", self.move_row_down),
            (None, None),
            ("Insert Column", self.insert_column),
            ("Delete Column", self.delete_column),
            (None, None),
            ("Promote First Row to Header", self.promote_first_row_to_header),
            (
                "Use First Column as Row Headers" + ("  (on)" if has_row_header else ""),
                self.toggle_row_headers,
            ),
        ]
        for label, handler in entries:
            if label is None:
                menu.AppendSeparator()
                continue
            item = menu.Append(wx.ID_ANY, label)
            self.Bind(wx.EVT_MENU, lambda _e, h=handler: h(), item)
        self.PopupMenu(menu)
        menu.Destroy()

    # -- announcements ---------------------------------------------------- #

    def _announce_cell(self, fire: bool = True) -> None:
        row = self._active_display_row()
        text = self._compose(row, self._active_col)
        native = getattr(self, "_native", None)
        if native is not None and native.active:
            # The native UIA provider raises the cell focus event itself.
            wx.CallAfter(lambda: native.notify_focus(row, self._active_col))
        elif fire:
            wx.CallAfter(lambda: fire_focus_child(self._acc, self._active_display_row() + 1))
        wx.CallAfter(self._announce, text)

    def _compose(self, row: int, col: int) -> str:
        prev_col = "" if self._prev_ann_col is None else self._model.col_header(self._prev_ann_col)
        prev_row = "" if self._prev_ann_row is None else self._model.row_header(self._prev_ann_row)
        text = self._ctrl.formatter.cell(
            self._model, row, col, prev_col_hdr=prev_col, prev_row_hdr=prev_row
        )
        self._prev_ann_row, self._prev_ann_col = row, col
        return text

    def _describe_cell(self, display_idx: int, col: int) -> str | None:
        if not (0 <= display_idx < self._model.row_count):
            return None
        col = max(0, min(col, self._model.col_count - 1))
        return self._ctrl.formatter.cell(self._model, display_idx, col)

    def _screen_cell_rect(self, display_idx: int, col: int) -> wx.Rect | None:
        try:
            rect = self.GetItemRect(display_idx, wx.LIST_RECT_BOUNDS)
        except Exception:  # noqa: BLE001 - off-screen/invalid item
            return None
        x = rect.x
        for ci in range(col):
            x += self.GetColumnWidth(ci)
        width = self.GetColumnWidth(col) or rect.width
        client = wx.Rect(x, rect.y, width, rect.height)
        return wx.Rect(self.ClientToScreen(client.GetTopLeft()), client.GetSize())

    # -- model listener --------------------------------------------------- #

    def _on_model_change(self, change: Change, kwargs: dict) -> None:
        native = getattr(self, "_native", None)
        if native is not None and native.active:
            if change == Change.CELL_VALUE:
                native.notify_value(
                    int(kwargs.get("row_idx", 0)),
                    int(kwargs.get("col_idx", 0)),
                    str(kwargs.get("new", "")),
                )
            else:
                native.notify_structure()
        if change == Change.HEADER_LABEL:
            wx.CallAfter(self._setup_columns)
            return
        if change in (Change.COL_INSERTED, Change.COL_DELETED, Change.COL_MOVED):
            wx.CallAfter(self._setup_columns)
        wx.CallAfter(lambda: self.SetItemCount(self._model.row_count))
        wx.CallAfter(lambda: self.RefreshItems(0, max(0, self._model.row_count - 1)))
        wx.CallAfter(lambda: self._select_row(self._active_display_row()))


class TableStudioDialog(wx.Dialog):
    """A modal Table Studio: the accessible grid plus row/column and export tools."""

    def __init__(
        self,
        parent: wx.Window,
        model: TableDocumentModel,
        announce: Callable[[str], None],
        *,
        title: str = "Table Studio",
        save_csv_cb: Callable[[TableDocumentModel, str | None], bool] | None = None,
    ) -> None:
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.SetSize(wx.Size(900, 560))
        self.model = model
        self._announce = announce
        self._save_csv_cb = save_csv_cb
        self.result_markdown = ""
        self.result_html = ""

        controller = TableController(model)
        controller.set_announce_callback(announce)
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            self,
            label=(
                "Arrow keys move by cell (Left/Right speak the column). F2 or Enter "
                "edits. Alt+arrows move a row or column. Ctrl+Insert adds a row; "
                "Delete clears a cell. Shift+F10 opens a menu to sort, insert, "
                "remove, move rows, rename headers, and set row headers."
            ),
        )
        intro.Wrap(860)
        root.Add(intro, 0, wx.ALL, 8)

        self.grid = TableListCtrl(self, model, controller, announce)
        root.Add(self.grid, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        tools = wx.WrapSizer(wx.HORIZONTAL)
        for label, handler in (
            ("Insert &Row", lambda _e: self.grid.insert_row_below()),
            ("&Delete Row", lambda _e: self.grid.delete_row()),
            ("Insert &Column", lambda _e: self.grid.insert_column()),
            ("Delete Colu&mn", lambda _e: self.grid.delete_column()),
            ("&Edit Cell", lambda _e: self.grid.edit_active_cell()),
        ):
            button = wx.Button(self, label=label)
            button.Bind(wx.EVT_BUTTON, handler)
            tools.Add(button, 0, wx.RIGHT | wx.BOTTOM, 6)
        if self._save_csv_cb is not None:
            save_csv_button = wx.Button(self, label="&Save to CSV...")
            save_csv_button.Bind(wx.EVT_BUTTON, self._on_save_csv)
            tools.Add(save_csv_button, 0, wx.RIGHT | wx.BOTTOM, 6)
        root.Add(tools, 0, wx.ALL, 6)

        btns = wx.StdDialogButtonSizer()
        insert_md = wx.Button(self, wx.ID_OK, label="Insert as &Markdown")
        insert_html = wx.Button(self, wx.ID_APPLY, label="Insert as &HTML")
        cancel = wx.Button(self, wx.ID_CANCEL, label="Close")
        insert_md.SetDefault()
        btns.AddButton(insert_md)
        btns.AddButton(insert_html)
        btns.AddButton(cancel)
        btns.Realize()
        root.Add(btns, 0, wx.EXPAND | wx.ALL, 8)

        self.SetSizer(root)
        insert_md.Bind(wx.EVT_BUTTON, self._on_markdown)
        insert_html.Bind(wx.EVT_BUTTON, self._on_html)
        cancel.Bind(wx.EVT_BUTTON, lambda _e: self.EndModal(wx.ID_CANCEL))
        from quill.ui.dialog_contract import apply_modal_ids

        apply_modal_ids(self, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        wx.CallAfter(self.grid.SetFocus)

    def _on_markdown(self, _event: object) -> None:
        self.result_markdown = self.model.to_markdown()
        self.EndModal(wx.ID_OK)

    def _on_html(self, _event: object) -> None:
        self.result_html = self.model.to_html()
        self.EndModal(wx.ID_APPLY)

    def _on_save_csv(self, _event: object) -> None:
        if self._save_csv_cb is None:
            return
        default_path = getattr(self.model, "csv_source_path", None)
        if self._save_csv_cb(self.model, default_path):
            self._announce("Saved to CSV.")


__all__ = ["TableListCtrl", "TableStudioDialog"]
