"""Verbosity templates-library dialog (verbosity §19, §21).

Browse the template library (built-in / user / QVP-installed), with the v1 CRUD
set — Save, Rename, Delete — and per-verb Apply that strips tokens the target
verb can't track and announces which were removed. An "Install QVP..." button
opens the QVP install dialog. Backed by the pure
:class:`quill.core.verbosity.library.TemplateLibrary`. A11Y-4 hardened.
"""

from __future__ import annotations

from collections.abc import Callable

import wx

from quill.core.verbosity.library import TemplateLibrary
from quill.ui.dialog_contract import apply_modal_ids, show_message_box

__all__ = ["VerbosityLibraryDialog"]


class VerbosityLibraryDialog:
    """Browse and edit the verbosity template library."""

    def __init__(
        self,
        parent: object,
        library: TemplateLibrary | None = None,
        *,
        announce_cb: Callable[[str], None] | None = None,
        install_qvp: Callable[[], None] | None = None,
    ) -> None:
        self._library = library or TemplateLibrary()
        self._announce = announce_cb or (lambda _m: None)
        self._install_qvp = install_qvp

        self.dialog = wx.Dialog(
            parent, title="Verbosity templates", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize(wx.Size(560, 440))
        root = wx.BoxSizer(wx.VERTICAL)

        root.Add(wx.StaticText(self.dialog, label="&Templates:"), 0, wx.LEFT | wx.TOP, 8)
        self._list = wx.ListBox(self.dialog, style=wx.LB_SINGLE)
        self._list.SetName("Saved templates")
        self._list.SetMinSize(wx.Size(-1, 160))
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)

        root.Add(wx.StaticText(self.dialog, label="Template &body:"), 0, wx.LEFT | wx.TOP, 8)
        self._body = wx.TextCtrl(self.dialog, style=wx.TE_MULTILINE)
        self._body.SetName("Template body")
        self._body.SetMinSize(wx.Size(-1, 60))
        root.Add(self._body, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 4)

        name_row = wx.BoxSizer(wx.HORIZONTAL)
        name_row.Add(
            wx.StaticText(self.dialog, label="&Name:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6
        )
        self._name = wx.TextCtrl(self.dialog)
        self._name.SetName("Template name")
        name_row.Add(self._name, 1)
        root.Add(name_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        self._status = wx.StaticText(self.dialog, label="")
        self._status.SetName("Library status")
        root.Add(self._status, 0, wx.LEFT | wx.TOP, 8)

        btns = wx.BoxSizer(wx.HORIZONTAL)
        self._save_btn = wx.Button(self.dialog, label="&Save")
        self._rename_btn = wx.Button(self.dialog, label="Re&name")
        self._delete_btn = wx.Button(self.dialog, label="&Delete")
        self._install_btn = wx.Button(self.dialog, label="&Install QVP...")
        close_btn = wx.Button(self.dialog, id=wx.ID_CLOSE, label="C&lose")
        for b in (self._save_btn, self._rename_btn, self._delete_btn, self._install_btn):
            btns.Add(b, 0, wx.RIGHT, 6)
        btns.AddStretchSpacer()
        btns.Add(close_btn)
        root.Add(btns, 0, wx.EXPAND | wx.ALL, 8)

        self.dialog.SetSizer(root)
        self.dialog.Fit()
        apply_modal_ids(self.dialog)

        self._list.Bind(wx.EVT_LISTBOX, lambda _e: self._on_select())
        self._save_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_save())
        self._rename_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_rename())
        self._delete_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_delete())
        self._install_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_install())
        close_btn.Bind(wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_CLOSE))
        self.dialog.Bind(wx.EVT_CLOSE, lambda _e: self.dialog.EndModal(wx.ID_CLOSE))
        self._repopulate()

    def _set_status(self, message: str) -> None:
        self._status.SetLabel(message)
        if message:
            self._announce(message)

    def _repopulate(self, keep: str | None = None) -> None:
        self._list.Clear()
        names = [tpl.name for tpl in self._library.all()]
        for name in names:
            self._list.Append(name)
        if keep in names:
            self._list.SetSelection(names.index(keep))
            self._on_select()
        elif names:
            self._list.SetSelection(0)
            self._on_select()

    def _selected_name(self) -> str | None:
        index = self._list.GetSelection()
        return self._list.GetString(index) if index >= 0 else None

    def _on_select(self) -> None:
        name = self._selected_name()
        if name is None:
            return
        entry = self._library.get(name)
        if entry is None:
            return
        self._name.SetValue(entry.name)
        self._body.SetValue(entry.template)
        editable = "editable" if entry.editable else f"read-only ({entry.source})"
        self._set_status(f"{entry.name}: {editable}")

    def _on_save(self) -> None:
        name = self._name.GetValue().strip()
        if not name:
            self._set_status("Enter a name to save.")
            return
        try:
            self._library.save(name, self._body.GetValue())
        except ValueError as error:
            self._set_status(str(error))
            return
        self._repopulate(keep=name)
        self._set_status(f"Saved template {name}.")

    def _on_rename(self) -> None:
        old = self._selected_name()
        new = self._name.GetValue().strip()
        if old is None or not new or old == new:
            return
        try:
            self._library.rename(old, new)
        except (KeyError, ValueError) as error:
            self._set_status(str(error))
            return
        self._repopulate(keep=new)
        self._set_status(f"Renamed to {new}.")

    def _on_delete(self) -> None:
        name = self._selected_name()
        if name is None:
            return
        confirm = show_message_box(
            f"Delete template {name}?",
            "Delete template",
            wx.YES_NO | wx.ICON_QUESTION | wx.NO_DEFAULT,
            self.dialog,
        )
        if confirm != wx.ID_YES:
            return
        try:
            self._library.delete(name)
        except (KeyError, ValueError) as error:
            self._set_status(str(error))
            return
        self._repopulate()
        self._set_status(f"Deleted {name}.")

    def _on_install(self) -> None:
        if self._install_qvp is not None:
            self._install_qvp()
            self._repopulate()

    def show(self) -> int:
        result = self.dialog.ShowModal()
        self.dialog.Destroy()
        return result

    def close(self) -> None:
        self.dialog.EndModal(wx.ID_CLOSE)
