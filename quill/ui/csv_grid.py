from __future__ import annotations

import csv
import io
from collections.abc import Callable

import wx.grid as wx_grid

from quill.core.document import Document

# Stride large enough to avoid row*stride+col collisions for any realistic
# spreadsheet (Excel cap is 16384 columns; anything beyond that is unusual).
_CELL_POSITION_STRIDE = 16384


def detect_csv_delimiter(text: str, default: str = ",") -> str:
    sample = text[:8192]
    if not sample.strip():
        return default
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
    except csv.Error:
        return "\t" if "\t" in sample and sample.count("\t") >= sample.count(",") else default
    return dialect.delimiter


def parse_csv_rows(text: str, delimiter: str) -> list[list[str]]:
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows = [list(row) for row in reader]
    if not rows:
        return [[""]]
    width = max(len(row) for row in rows)
    return [row + [""] * (width - len(row)) for row in rows]


def serialize_csv_rows(rows: list[list[str]], delimiter: str) -> str:
    output = io.StringIO()
    writer = csv.writer(output, delimiter=delimiter, lineterminator="\n")
    writer.writerows(rows)
    return output.getvalue()


class CsvGridSurface:
    def __init__(
        self,
        wx_module: object,
        parent: object,
        document: Document,
        on_change: Callable[[], None],
    ) -> None:
        self._wx = wx_module
        self._document = document
        self._on_change = on_change
        self._suspend_sync = False
        self._delimiter = detect_csv_delimiter(document.text, ",")

        wx = self._wx
        self.panel = wx.Panel(parent)
        root = wx.BoxSizer(wx.VERTICAL)

        header = wx.BoxSizer(wx.HORIZONTAL)
        self._mode_button = wx.Button(self.panel, label="Use normal text editor")
        self._mode_button.Bind(wx.EVT_BUTTON, self._toggle_mode)
        header.Add(self._mode_button, 0, wx.RIGHT, 8)
        self._mode_label = wx.StaticText(self.panel, label="CSV grid mode")
        header.Add(self._mode_label, 0, wx.ALIGN_CENTER_VERTICAL)
        root.Add(header, 0, wx.ALL, 6)

        self._notebook = wx.Notebook(self.panel)
        self._notebook.SetName("CSV view")
        self._grid_page = wx.Panel(self._notebook)
        self._text_page = wx.Panel(self._notebook)
        self.grid = wx_grid.Grid(self._grid_page)
        self.text_ctrl = wx.TextCtrl(
            self._text_page,
            style=wx.TE_MULTILINE | wx.TE_RICH2 | wx.TE_NOHIDESEL,
        )

        grid_sizer = wx.BoxSizer(wx.VERTICAL)
        grid_sizer.Add(self.grid, 1, wx.EXPAND)
        self._grid_page.SetSizer(grid_sizer)

        text_sizer = wx.BoxSizer(wx.VERTICAL)
        text_sizer.Add(self.text_ctrl, 1, wx.EXPAND)
        self._text_page.SetSizer(text_sizer)

        self._notebook.AddPage(self._grid_page, "Grid")
        self._notebook.AddPage(self._text_page, "Text")
        self._notebook.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self._on_page_changed)
        root.Add(self._notebook, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
        self.panel.SetSizer(root)

        self._bind_events()
        self.ChangeValue(document.text)
        self.show_grid_mode()

    def __getattr__(self, name: str) -> object:
        active = self._active_control()
        if hasattr(active, name):
            return getattr(active, name)
        if hasattr(self.panel, name):
            return getattr(self.panel, name)
        raise AttributeError(name)

    def _active_control(self) -> object:
        return self.text_ctrl if self.is_text_mode() else self.grid

    def is_text_mode(self) -> bool:
        return self._notebook.GetSelection() == 1

    def show_grid_mode(self) -> None:
        self._notebook.ChangeSelection(0)
        self._mode_button.SetLabel("Use normal text editor")
        self._mode_label.SetLabel("CSV grid mode")
        self.grid.SetFocus()

    def show_text_mode(self) -> None:
        self._notebook.ChangeSelection(1)
        self._mode_button.SetLabel("Use CSV grid")
        self._mode_label.SetLabel("Normal text editor mode")
        self.text_ctrl.SetFocus()

    def toggle_mode(self) -> None:
        if self.is_text_mode():
            self.show_grid_mode()
        else:
            self.show_text_mode()

    def GetValue(self) -> str:
        return self.text_ctrl.GetValue()

    def ChangeValue(self, value: str) -> None:
        self._suspend_sync = True
        try:
            self.text_ctrl.ChangeValue(value)
            self._load_grid_from_text(value)
        finally:
            self._suspend_sync = False

    def SetEditable(self, editable: bool) -> None:
        self.text_ctrl.SetEditable(editable)
        if hasattr(self.grid, "EnableEditing"):
            self.grid.EnableEditing(editable)

    def SetFocus(self) -> None:
        self._active_control().SetFocus()

    def GetSelection(self) -> tuple[int, int]:
        if self.is_text_mode():
            return self.text_ctrl.GetSelection()
        row = getattr(self.grid, "GetGridCursorRow", lambda: 0)()
        col = getattr(self.grid, "GetGridCursorCol", lambda: 0)()
        position = max(0, row) * _CELL_POSITION_STRIDE + max(0, col)
        return position, position

    def SetSelection(self, start: int, end: int) -> None:
        if self.is_text_mode():
            self.text_ctrl.SetSelection(start, end)

    def GetInsertionPoint(self) -> int:
        if self.is_text_mode():
            return self.text_ctrl.GetInsertionPoint()
        return 0

    def SetInsertionPoint(self, position: int) -> None:
        if self.is_text_mode():
            self.text_ctrl.SetInsertionPoint(position)

    def Replace(self, start: int, end: int, value: str) -> None:
        if self.is_text_mode():
            self.text_ctrl.Replace(start, end, value)

    def Cut(self) -> None:
        if self.is_text_mode():
            self.text_ctrl.Cut()

    def Copy(self) -> None:
        if self.is_text_mode():
            self.text_ctrl.Copy()

    def Paste(self) -> None:
        if self.is_text_mode():
            self.text_ctrl.Paste()

    def Undo(self) -> None:
        if self.is_text_mode() and self.text_ctrl.CanUndo():
            self.text_ctrl.Undo()

    def Redo(self) -> None:
        if self.is_text_mode() and self.text_ctrl.CanRedo():
            self.text_ctrl.Redo()

    def bind_editor_events(self, frame: object) -> None:
        wx = self._wx
        self.text_ctrl.Bind(wx.EVT_TEXT, lambda _event: self._on_text_changed())
        self.text_ctrl.Bind(wx.EVT_KEY_DOWN, frame._on_editor_key_down)
        self.text_ctrl.Bind(wx.EVT_KEY_UP, frame._on_editor_key_up)
        self.text_ctrl.Bind(wx.EVT_LEFT_UP, frame._on_editor_caret_activity)
        self.text_ctrl.Bind(wx.EVT_SET_FOCUS, frame._on_editor_caret_activity)
        self.text_ctrl.Bind(wx.EVT_CONTEXT_MENU, frame._on_editor_context_menu)
        self.grid.Bind(wx_grid.EVT_GRID_CELL_CHANGED, lambda _event: self._on_grid_changed())
        self.grid.Bind(wx_grid.EVT_GRID_SELECT_CELL, frame._on_editor_caret_activity)
        self.grid.Bind(wx_grid.EVT_GRID_RANGE_SELECT, frame._on_editor_caret_activity)
        self.grid.Bind(wx_grid.EVT_GRID_LABEL_LEFT_CLICK, frame._on_editor_caret_activity)
        self.grid.Bind(wx.EVT_SET_FOCUS, frame._on_editor_caret_activity)
        self.grid.Bind(wx.EVT_CONTEXT_MENU, frame._on_editor_context_menu)

    def _bind_events(self) -> None:
        wx = self._wx
        self._mode_button.Bind(wx.EVT_BUTTON, self._toggle_mode)

    def _toggle_mode(self, _event: object) -> None:
        self.toggle_mode()

    def _on_page_changed(self, _event: object) -> None:
        if self.is_text_mode():
            self._mode_button.SetLabel("Use CSV grid")
            self._mode_label.SetLabel("Normal text editor mode")
        else:
            self._mode_button.SetLabel("Use normal text editor")
            self._mode_label.SetLabel("CSV grid mode")

    def _on_text_changed(self) -> None:
        if self._suspend_sync:
            return
        self._suspend_sync = True
        try:
            self._load_grid_from_text(self.text_ctrl.GetValue())
        finally:
            self._suspend_sync = False
        self._on_change()

    def _on_grid_changed(self) -> None:
        if self._suspend_sync:
            return
        self._suspend_sync = True
        try:
            self.text_ctrl.ChangeValue(self._grid_to_text())
        finally:
            self._suspend_sync = False
        self._on_change()

    def _load_grid_from_text(self, text: str) -> None:
        rows = parse_csv_rows(text, self._delimiter)
        row_count = len(rows)
        col_count = max((len(row) for row in rows), default=1)
        if not self.grid.IsCreated():
            self.grid.CreateGrid(row_count, col_count)
        else:
            existing_rows = self.grid.GetNumberRows()
            existing_cols = self.grid.GetNumberCols()
            if existing_rows < row_count:
                self.grid.AppendRows(row_count - existing_rows)
            elif existing_rows > row_count:
                self.grid.DeleteRows(0, existing_rows - row_count)
            if existing_cols < col_count:
                self.grid.AppendCols(col_count - existing_cols)
            elif existing_cols > col_count:
                self.grid.DeleteCols(0, existing_cols - col_count)
        for row_index, row in enumerate(rows):
            for col_index, value in enumerate(row):
                self.grid.SetCellValue(row_index, col_index, value)
        for col_index in range(col_count):
            self.grid.SetColLabelValue(col_index, f"{chr(65 + col_index)}")

    def _grid_to_text(self) -> str:
        if not self.grid.IsCreated():
            return self.text_ctrl.GetValue()
        rows: list[list[str]] = []
        for row_index in range(self.grid.GetNumberRows()):
            rows.append([
                self.grid.GetCellValue(row_index, col_index)
                for col_index in range(self.grid.GetNumberCols())
            ])
        return serialize_csv_rows(rows, self._delimiter)
