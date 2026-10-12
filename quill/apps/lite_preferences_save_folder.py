"""The default document folder control in QUILL Lite's Preferences."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import wx

from quill.ui.dialog_contract import show_modal_dialog

__all__ = ["DocumentFolderPrefs"]


class DocumentFolderPrefs:
    """Edit the folder used by document dialogs when no file folder applies."""

    def __init__(self, dialog: Any, sizer: Any, settings: Any, *, pad: int = 8) -> None:
        self._settings = settings
        label = wx.StaticText(dialog, label="Default document folder:")
        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, pad)

        self.folder = wx.TextCtrl(dialog, value=str(getattr(settings, "startup_folder", "")))
        self.folder.SetName("Default document folder")
        self.folder.SetHint("Blank uses the Windows Documents folder")
        self.folder.SetHelpText(
            "Where Open and Save As start for a new document. Leave blank to use "
            "the Windows Documents folder. A document already saved keeps using "
            "its own folder."
        )

        row = wx.BoxSizer(wx.HORIZONTAL)
        row.Add(self.folder, 1, wx.EXPAND | wx.RIGHT, pad)
        self.choose = wx.Button(dialog, label="Choose default folder...")
        self.choose.SetName("Choose default document folder")
        self.choose.SetHelpText("Choose an existing folder for new documents.")
        self.choose.Bind(wx.EVT_BUTTON, self._choose)
        row.Add(self.choose, 0)
        sizer.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, pad)

    def _choose(self, _event: object) -> None:
        default_path = self.folder.GetValue().strip()
        if not Path(default_path).is_dir():
            default_path = wx.StandardPaths.Get().GetDocumentsDir()
        with wx.DirDialog(
            self.folder.GetParent(),
            "Choose default document folder",
            defaultPath=default_path,
            style=wx.DD_DEFAULT_STYLE | wx.DD_DIR_MUST_EXIST,
        ) as picker:
            if show_modal_dialog(picker, "Default document folder") == wx.ID_OK:
                self.folder.SetValue(picker.GetPath())

    def apply(self) -> bool:
        before = str(getattr(self._settings, "startup_folder", ""))
        self._settings.startup_folder = self.folder.GetValue().strip()
        return before != self._settings.startup_folder
