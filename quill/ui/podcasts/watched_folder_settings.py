"""Folder Settings...: how one watched folder behaves (qc.md 5d, C2-02).

The page behind Add Folder and Folder Settings in the Watched Folders window.
Every choice is written out in words; nothing here is a path to type, because
the folder itself was chosen with the system's folder picker before this opens.
"""

from __future__ import annotations

from typing import Any

from quill.core.podcasts.local_import import SUPPORTED_AUDIO_EXTENSIONS
from quill.core.podcasts.speed_choices import OFFERED
from quill.core.podcasts.watched_folders import ARRIVALS, ORIGINALS, TELLS, WatchedFolder

__all__ = ["TITLE", "WatchedFolderSettingsDialog", "edit_folder_settings"]

TITLE = "Watched Folder Settings"
_SHARED_SPEED = "The shared speed"


def _index(table: tuple[tuple[str, str], ...], value: str) -> int:
    for index, (item, _label) in enumerate(table):
        if item == value:
            return index
    return 0


class WatchedFolderSettingsDialog:
    """``read()`` applies the controls to the folder after Save."""

    def __init__(self, parent: Any, folder: WatchedFolder) -> None:
        import wx

        from quill.ui.dialog_contract import apply_modal_ids

        self._folder = folder
        self.dialog = wx.Dialog(
            parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        root = wx.BoxSizer(wx.VERTICAL)
        where = wx.StaticText(self.dialog, label=f"Folder: {folder.path}")
        root.Add(where, 0, wx.ALL, 8)
        grid = wx.FlexGridSizer(cols=2, gap=(6, 8))
        grid.AddGrowableCol(1, 1)

        grid.Add(wx.StaticText(self.dialog, label="&Name:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._name = wx.TextCtrl(self.dialog, value=folder.display_name())
        self._name.SetHelpText(
            "What Personal Audio calls the files from this folder. It starts as the "
            "folder's own name."
        )
        grid.Add(self._name, 1, wx.EXPAND)

        grid.Add(
            wx.StaticText(self.dialog, label="What to do with the &original:"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._original = wx.Choice(self.dialog, choices=[label for _v, label in ORIGINALS])
        self._original.SetHelpText(
            "Leave it where it is keeps your file untouched and gives Cast its own "
            "copy. Move it takes the file into Cast's folder once the copy is checked. "
            "Play it from where it is makes no copy; if the drive goes away, the "
            "episode reads Unavailable and keeps your place."
        )
        self._original.SetSelection(_index(ORIGINALS, folder.original))
        grid.Add(self._original, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self.dialog, label="New &arrivals:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._arrivals = wx.Choice(self.dialog, choices=[label for _v, label in ARRIVALS])
        self._arrivals.SetHelpText(
            "What a new file does when it lands: join Personal Audio, also join the "
            "end of the Play Queue, or also start playing when nothing else is."
        )
        self._arrivals.SetSelection(_index(ARRIVALS, folder.arrivals))
        grid.Add(self._arrivals, 1, wx.EXPAND)

        grid.Add(wx.StaticText(self.dialog, label="&Tell me:"), 0, wx.ALIGN_CENTER_VERTICAL)
        self._tell = wx.Choice(self.dialog, choices=[label for _v, label in TELLS])
        self._tell.SetHelpText(
            "Say each new file by name and length, say only how many arrived, or "
            "say nothing. Every arrival is written to Notifications either way."
        )
        self._tell.SetSelection(_index(TELLS, folder.tell))
        grid.Add(self._tell, 1, wx.EXPAND)

        grid.Add(
            wx.StaticText(self.dialog, label="&Ignore files shorter than (seconds):"),
            0,
            wx.ALIGN_CENTER_VERTICAL,
        )
        self._min = wx.SpinCtrl(self.dialog, min=0, max=3600, initial=folder.min_seconds)
        self._min.SetHelpText(
            "A recording shorter than this is left out, so an accidental two-second "
            "file does not become an episode. 0 takes everything."
        )
        grid.Add(self._min, 0)

        grid.Add(wx.StaticText(self.dialog, label="S&peed:"), 0, wx.ALIGN_CENTER_VERTICAL)
        speeds = [_SHARED_SPEED, *[f"{value:g}x" for value in OFFERED]]
        self._speed = wx.Choice(self.dialog, choices=speeds)
        self._speed.SetHelpText(
            "The speed this folder's files play at. A lecture folder and an audiobook "
            "folder often want different ones. The shared speed follows Preferences."
        )
        chosen = 0
        for index, value in enumerate(OFFERED, start=1):
            if abs(value - folder.speed) < 1e-9:
                chosen = index
        self._speed.SetSelection(chosen)
        grid.Add(self._speed, 0)
        root.Add(grid, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        self._subfolders = wx.CheckBox(self.dialog, label="Include &subfolders")
        self._subfolders.SetHelpText(
            "Also watch every folder inside this one. Leave it on for a recorder "
            "that files by date."
        )
        self._subfolders.SetValue(folder.include_subfolders)
        root.Add(self._subfolders, 0, wx.LEFT | wx.TOP, 8)
        self._groups = wx.CheckBox(self.dialog, label="Each subfolder is its own &group")
        self._groups.SetHelpText(
            "Each folder inside this one becomes its own group in Personal Audio, so "
            "a folder of audiobooks becomes one group per book."
        )
        self._groups.SetValue(folder.subfolder_groups)
        root.Add(self._groups, 0, wx.LEFT | wx.TOP, 8)

        root.Add(
            wx.StaticText(self.dialog, label="File t&ypes to bring in:"), 0, wx.LEFT | wx.TOP, 8
        )
        types = wx.BoxSizer(wx.HORIZONTAL)
        self._types: list[Any] = []
        for ext in SUPPORTED_AUDIO_EXTENSIONS:
            box = wx.CheckBox(self.dialog, label=ext)
            box.SetHelpText(
                f"Bring in {ext} files from this folder. Uncheck it to leave those files "
                "alone, such as raw .wav recordings."
            )
            box.SetValue(ext in folder.extensions)
            types.Add(box, 0, wx.RIGHT, 8)
            self._types.append(box)
        root.Add(types, 0, wx.LEFT | wx.RIGHT, 8)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        buttons.AddStretchSpacer(1)
        save = wx.Button(self.dialog, wx.ID_OK, label="Save")
        save.SetHelpText("Keeps these settings. They apply from the next file that arrives.")
        cancel = wx.Button(self.dialog, wx.ID_CANCEL, label="Cancel")
        cancel.SetHelpText("Closes this window; nothing you changed here is kept.")
        buttons.Add(save, 0, wx.RIGHT, 6)
        buttons.Add(cancel, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        self.dialog.SetSizer(root)
        apply_modal_ids(
            self.dialog, affirmative_id=wx.ID_OK, affirmative_label="Save", cancel_id=wx.ID_CANCEL
        )
        self.dialog.SetSize((620, 560))
        self._name.SetFocus()

    def read(self) -> None:
        """Write the controls into the folder record."""
        folder = self._folder
        folder.name = self._name.GetValue().strip()
        folder.original = ORIGINALS[max(0, self._original.GetSelection())][0]
        folder.arrivals = ARRIVALS[max(0, self._arrivals.GetSelection())][0]
        folder.tell = TELLS[max(0, self._tell.GetSelection())][0]
        folder.min_seconds = int(self._min.GetValue())
        index = self._speed.GetSelection()
        folder.speed = OFFERED[index - 1] if index >= 1 else 0.0
        folder.include_subfolders = self._subfolders.GetValue()
        folder.subfolder_groups = self._groups.GetValue()
        pairs = zip(SUPPORTED_AUDIO_EXTENSIONS, self._types, strict=True)
        chosen = tuple(ext for ext, box in pairs if box.GetValue())
        folder.extensions = chosen or SUPPORTED_AUDIO_EXTENSIONS

    def show(self, host: Any) -> bool:
        """Through the host's dialog contract; True when Save was pressed (and applied)."""
        import wx

        try:
            if host._show_modal_dialog(self.dialog, TITLE) == wx.ID_OK:
                self.read()
                return True
            return False
        finally:
            self.dialog.Destroy()


def edit_folder_settings(host: Any, parent: Any, folder: WatchedFolder) -> bool:
    """Show the page for *folder*; True when Save was pressed (and applied)."""
    return WatchedFolderSettingsDialog(parent, folder).show(host)
