"""Accessible profile picker dialog (issue #138).

A single, native dialog to switch feature profiles quickly (bound to
Alt+Shift+P). Lists built-in and custom profiles with a description pane, and
folds in the two startup conveniences:

* a checkbox to be asked for a profile every time Quill starts, and
* when a file is open, a checkbox to always use the chosen profile for that
  file's extension.

The dialog only collects choices; the caller applies them. That keeps the
profile-switching side effects in ``MainFrame`` and this surface thin.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

# One row in the picker: (kind, profile_id, name, description).
ProfileEntry = tuple[str, str, str, str]


@dataclass(slots=True)
class ProfilePickerResult:
    profile_kind: str
    profile_id: str
    profile_name: str
    prompt_on_startup: bool
    map_extension: bool


class ProfilePickerDialog:
    def __init__(
        self,
        parent: object,
        wx: object,
        *,
        entries: list[ProfileEntry],
        active_profile_id: str,
        current_extension: str = "",
        prompt_on_startup: bool = False,
    ) -> None:
        self._wx = wx
        self._entries = entries
        self._current_extension = current_extension
        self.result: ProfilePickerResult | None = None

        self.dialog = wx.Dialog(
            parent,
            title="Choose a Profile",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetSize((640, 600))
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(self.dialog, label="Profile"),
            0,
            wx.LEFT | wx.RIGHT | wx.TOP,
            10,
        )
        self.listbox = wx.ListBox(self.dialog, choices=[str(name) for _k, _i, name, _d in entries])
        self.listbox.SetName("Profile — arrow up and down to read about each one")
        active_index = next(
            (index for index, entry in enumerate(entries) if entry[1] == active_profile_id),
            0,
        )
        if entries:
            self.listbox.SetSelection(active_index)
        root.Add(self.listbox, 0, wx.EXPAND | wx.ALL, 10)

        root.Add(wx.StaticText(self.dialog, label="About this profile:"), 0, wx.LEFT | wx.RIGHT, 10)
        self.description = wx.TextCtrl(
            self.dialog,
            style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_WORDWRAP | wx.BORDER_SIMPLE,
            size=(-1, 220),
        )
        self.description.SetName("Profile description")
        root.Add(self.description, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.startup_check = wx.CheckBox(
            self.dialog, label="Ask me for a profile each time Quill starts"
        )
        self.startup_check.SetValue(prompt_on_startup)
        root.Add(self.startup_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.extension_check = None
        if current_extension:
            self.extension_check = wx.CheckBox(
                self.dialog,
                label=f"Always use the selected profile for {current_extension} files",
            )
            root.Add(self.extension_check, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer(1)
        buttons.Add(wx.Button(self.dialog, wx.ID_OK, label="Switch"), 0, wx.RIGHT, 8)
        buttons.Add(wx.Button(self.dialog, wx.ID_CANCEL, label="Cancel"), 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
        self.dialog.SetSizer(root)

        self.listbox.Bind(wx.EVT_LISTBOX, lambda _e: self._refresh_description())
        self._refresh_description()

    def _refresh_description(self) -> None:
        index = self.listbox.GetSelection()
        if index == self._wx.NOT_FOUND or index < 0 or index >= len(self._entries):
            self.description.SetValue("")
            return
        self.description.SetValue(str(self._entries[index][3]))
        self.description.SetInsertionPoint(0)

    def show(self) -> ProfilePickerResult | None:
        wx = self._wx
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
        try:
            if show_modal_dialog(self.dialog, "Choose a Profile") != wx.ID_OK:
                return None
            index = self.listbox.GetSelection()
            if index == wx.NOT_FOUND or index < 0 or index >= len(self._entries):
                return None
            kind, profile_id, name, _description = self._entries[index]
            self.result = ProfilePickerResult(
                profile_kind=kind,
                profile_id=profile_id,
                profile_name=name,
                prompt_on_startup=bool(self.startup_check.GetValue()),
                map_extension=bool(self.extension_check and self.extension_check.GetValue()),
            )
            return self.result
        finally:
            self.dialog.Destroy()
