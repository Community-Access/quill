"""A Properties sheet: one notebook page per sheet page, every fact a focusable field.

GitHub PRD section 15.2, provider-neutral: the sheet's shape is a
:class:`quill.core.workbench.properties.SheetSpec` and its values a mapping,
so GitHub and WordPress sheets are the same window. Read-only facts are
read-only text boxes, never bare static text, so Tab reaches them, the screen
reader reads them and a braille display can pan through them. Ctrl+Tab and
Ctrl+Page Down move between pages (the notebook's own keys).

The Phase 1 spike shows read-only sheets with Copy as Text and Close. Editing,
OK and Apply, the fresh load and the conflict check come with the editing
phases; nothing here sends anything.

Opening says nothing: the reader says the title and the first field (GATE-13).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from quill.core.workbench.properties import FieldKind, SheetSpec, as_text
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button, show_modal_dialog
from quill.ui.dpi import dip_size

__all__ = ["WorkbenchPropertiesDialog", "field_text"]


def field_text(value: object) -> str:
    """How a value reads in its field: lists joined, flags as yes or no, gaps as none."""
    if isinstance(value, tuple):
        return ", ".join(str(v) for v in value) if value else "none"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if value is None or value == "":
        return "none"
    return str(value)


class WorkbenchPropertiesDialog:
    """The sheet window, parented to the Workbench so it never blocks the editor."""

    def __init__(
        self,
        parent: Any,
        sheet: SheetSpec,
        values: Mapping[str, object],
        *,
        title: str,
        copy_text: Callable[[str], None],
    ) -> None:
        import wx

        self._wx = wx
        self.sheet = sheet
        self.values = dict(values)
        self.title = title
        self._copy_text = copy_text
        self.dialog = wx.Dialog(
            parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetSize(dip_size(self.dialog, 560, 480))
        root = wx.BoxSizer(wx.VERTICAL)
        self.notebook = wx.Notebook(self.dialog)
        self.notebook.SetHelpText("The sheet's pages. Ctrl+Tab moves to the next page.")
        self.fields: dict[str, Any] = {}
        for page in sheet.pages:
            panel = wx.Panel(self.notebook)
            grid = wx.FlexGridSizer(cols=2, vgap=6, hgap=8)
            grid.AddGrowableCol(1, 1)
            for spec in page.fields:
                label = wx.StaticText(panel, label=f"{spec.label}:")
                style = wx.TE_READONLY
                if spec.kind is FieldKind.MULTILINE:
                    style |= wx.TE_MULTILINE | wx.TE_WORDWRAP
                box = wx.TextCtrl(panel, value=field_text(self.values.get(spec.key)), style=style)
                box.SetName(spec.label)
                box.SetHelpText(spec.help or f"{spec.label}. Read only on this sheet for now.")
                if spec.kind is FieldKind.MULTILINE:
                    box.SetMinSize(dip_size(panel, 360, 160))
                grid.Add(label, 0, wx.ALIGN_TOP | wx.TOP, 3)
                grid.Add(box, 1, wx.EXPAND)
                self.fields[spec.key] = box
            outer = wx.BoxSizer(wx.VERTICAL)
            outer.Add(grid, 1, wx.EXPAND | wx.ALL, 10)
            panel.SetSizer(outer)
            self.notebook.AddPage(panel, page.title)
        root.Add(self.notebook, 1, wx.EXPAND | wx.ALL, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        copy_button = wx.Button(self.dialog, label="Copy as &Text")
        copy_button.SetHelpText("Copy every page of this sheet as plain text.")
        copy_button.Bind(wx.EVT_BUTTON, lambda _e: self.copy_as_text())
        close_button = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        close_button.SetHelpText("Close the sheet. Escape does the same.")
        bind_close_button(self.dialog, close_button, modeless=False)
        buttons.Add(copy_button, 0, wx.RIGHT, 8)
        buttons.AddStretchSpacer()
        buttons.Add(close_button)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizer(root)
        apply_modal_ids(self.dialog, escape_id=wx.ID_CANCEL)

    def text(self) -> str:
        return as_text(self.sheet, self.values, title=self.title)

    def copy_as_text(self) -> None:
        self._copy_text(self.text())

    def show(self) -> None:
        try:
            show_modal_dialog(self.dialog, self.title)
        finally:
            self.dialog.Destroy()
