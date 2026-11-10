"""Add a Folder: type or paste a folder's path, or browse for it.

Chris Nova, 2026-11-09: he wanted to type ``d:\\other files\\downloads`` and have
Quill Radio find every song in it. The Windows folder picker makes you walk a
tree to a place you can already name, so this small dialog puts a plain text
box first. Browse... is still there for anyone who would rather pick.

Two choices sit under the path:

- **Include subfolders** (on by default, as adding a folder has always been):
  off, only the files right in the folder are added, and the playlist keeps
  that choice whenever it looks at the folder again.
- **Keep up with the folder** (only when the folder makes a new playlist, on by
  default as before): new files in the folder are added whenever the playlist
  opens. The Follow the Folder command turns it off and on later.

A path that cannot be used is said next to the box and the dialog stays open,
so nothing is added from a typo. File Explorer's Copy as Path wraps the path in
quotes; those are taken off (:func:`quill.core.radio.local_media_files.clean_folder_text`).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from quill.core.radio.local_media_files import clean_folder_text, folder_problem
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button
from quill.ui.dpi import dip

__all__ = ["TITLE", "AddFolderDialog", "FolderChoice", "ask_folder_choice"]

TITLE = "Add a Folder"

#: The last folder added this session, offered again next time: people add a
#: few folders from the same place in a row.
_last_folder: dict[str, str] = {"path": ""}


@dataclass(frozen=True)
class FolderChoice:
    """What somebody chose in Add a Folder."""

    path: str
    subfolders: bool = True
    follow: bool = True


class AddFolderDialog:
    """The dialog itself, built and checked without showing it (for tests)."""

    def __init__(
        self,
        wx: Any,
        parent: Any,
        *,
        new_playlist: bool,
        start: str = "",
        announce: Any = None,
        show_modal: Any = None,
    ) -> None:
        self._wx = wx
        self._announce = announce
        self._show_modal = show_modal
        self.new_playlist = new_playlist
        self.dialog = wx.Dialog(parent, title=TITLE)
        dialog = self.dialog
        root = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(dialog, label="&Folder:")
        root.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, dip(dialog, 10))
        row = wx.BoxSizer(wx.HORIZONTAL)
        self.path = wx.TextCtrl(dialog, value=start)
        self.path.SetName("Folder")
        self.path.SetMinSize(wx.Size(dip(dialog, 380), -1))
        self.path.SetHelpText(
            "The folder to add, for example d:\\other files\\downloads. Type it, or "
            "paste it from File Explorer's Copy as Path; quotes around it are fine."
        )
        row.Add(self.path, 1, wx.EXPAND | wx.RIGHT, dip(dialog, 6))
        self.browse = wx.Button(dialog, label="&Browse...")
        self.browse.SetHelpText(
            "Pick the folder in the Windows folder picker instead of typing it."
        )
        row.Add(self.browse, 0)
        root.Add(row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, dip(dialog, 10))

        self.problem = wx.StaticText(dialog, label="")
        self.problem.SetHelpText("Says why a folder cannot be added, when it cannot.")
        root.Add(self.problem, 0, wx.LEFT | wx.RIGHT | wx.TOP, dip(dialog, 10))

        self.subfolders = wx.CheckBox(dialog, label="Include &subfolders")
        self.subfolders.SetValue(True)
        self.subfolders.SetHelpText(
            "Checked, the media in folders inside this one is added too, an album's "
            "discs in order. Unchecked, only the files right in this folder."
        )
        root.Add(self.subfolders, 0, wx.LEFT | wx.RIGHT | wx.TOP, dip(dialog, 10))

        self.follow = wx.CheckBox(dialog, label="&Keep up with the folder")
        self.follow.SetValue(True)
        self.follow.SetHelpText(
            "Checked, files that appear in the folder later are added whenever the "
            "playlist opens. Follow the Folder in the Local Media menu changes this later."
        )
        self.follow.Show(new_playlist)
        root.Add(self.follow, 0, wx.LEFT | wx.RIGHT | wx.TOP, dip(dialog, 10))

        buttons = wx.StdDialogButtonSizer()
        self.ok = wx.Button(dialog, wx.ID_OK, "OK")
        self.ok.SetHelpText("Look in the folder and add what is there.")
        self.ok.SetDefault()
        self.cancel = wx.Button(dialog, wx.ID_CANCEL, "Cancel")
        self.cancel.SetHelpText("Close without adding anything.")
        bind_close_button(dialog, self.cancel, modeless=False)
        buttons.AddButton(self.ok)
        buttons.AddButton(self.cancel)
        buttons.Realize()
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, dip(dialog, 10))

        dialog.SetSizerAndFit(root)
        apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        self.ok.Bind(wx.EVT_BUTTON, self._on_ok)
        self.browse.Bind(wx.EVT_BUTTON, self._on_browse)
        self.path.SetFocus()
        self.path.SelectAll()

    # -- behaviour ------------------------------------------------------------------

    def check(self) -> str:
        """Why the typed folder cannot be used ("" when it can), said next to the box."""
        problem = folder_problem(self.path.GetValue())
        self.problem.SetLabel(problem)
        if problem:
            # A label changed on text that does not have focus is something the
            # screen reader will not say by itself (GATE-12), so it is said once.
            if callable(self._announce):
                self._announce(problem)
            self.path.SetFocus()
        return problem

    def choice(self) -> FolderChoice:
        return FolderChoice(
            path=clean_folder_text(self.path.GetValue()),
            subfolders=bool(self.subfolders.GetValue()),
            follow=bool(self.follow.GetValue()) if self.new_playlist else False,
        )

    def _on_ok(self, _event: Any) -> None:
        if self.check():
            return
        self.dialog.EndModal(self._wx.ID_OK)

    def _on_browse(self, _event: Any) -> None:
        wx = self._wx
        typed = clean_folder_text(self.path.GetValue())
        start = typed if typed and Path(typed).is_dir() else ""
        with wx.DirDialog(
            self.dialog, "Choose a Folder", defaultPath=start, style=wx.DD_DIR_MUST_EXIST
        ) as chooser:
            shown = self._show_modal(chooser, "Choose a Folder") if self._show_modal else None
            if shown != wx.ID_OK:
                return
            self.path.SetValue(str(chooser.GetPath()))
        self.problem.SetLabel("")
        self.path.SetFocus()
        self.path.SetInsertionPointEnd()


def ask_folder_choice(host: Any, *, new_playlist: bool) -> FolderChoice | None:
    """Show Add a Folder. The choice, or ``None`` when cancelled."""
    import wx

    from quill.ui.radio import local_media_ui as ui

    def _show(dialog: Any, label: str) -> int:
        return ui.show_modal_dialog(host, dialog, label)

    built = AddFolderDialog(
        wx,
        ui._parent(host),
        new_playlist=new_playlist,
        start=_last_folder["path"],
        announce=lambda text: ui.announce(host, text),
        show_modal=_show,
    )
    try:
        if ui.show_modal_dialog(host, built.dialog, TITLE) != wx.ID_OK:
            return None
        picked = built.choice()
    finally:
        built.dialog.Destroy()
    _last_folder["path"] = picked.path
    return picked
