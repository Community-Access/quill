"""Never overwrite a change you have not seen (2026-10-04).

Both editors re-check the file on disk -- size, modification time and a hash of
its bytes -- right before Save writes it. If another program changed it since
it was opened or last saved, Save stops and asks this question instead of
writing over the other program's work. QUILL's external-change watcher already
asked between polls; a change landing after the last poll was overwritten in
silence, and QUILL Lite had no check at all. PlanCake (Andre, Oire Software)
refuses that write outright, for the case it was built for: an AI assistant
rewriting a plan while you read it.

**Enter is Save As, not Overwrite.** The reflexive answer must lose nothing,
and Save As keeps both versions. Escape is Cancel. Overwrite is its own
button with its own letter, so choosing it is a decision rather than a habit.
"""

from __future__ import annotations

import wx

from quill.ui.dialog_contract import apply_modal_ids, show_modal_dialog

__all__ = ["CANCEL", "OVERWRITE", "RELOAD", "SAVE_AS", "ask_save_conflict"]

OVERWRITE = "overwrite"
RELOAD = "reload"
SAVE_AS = "save_as"
CANCEL = "cancel"

_PAD = 8


def ask_save_conflict(parent: object, file_name: str, *, app_name: str = "QUILL") -> str:
    """Ask what Save should do now that *file_name* changed on disk."""
    dialog = wx.Dialog(parent, title="File Changed Since You Opened It")
    root = wx.BoxSizer(wx.VERTICAL)
    story = wx.StaticText(
        dialog,
        label=(
            f"'{file_name}' was changed by another program since {app_name} opened "
            "or last saved it. Saving now would replace those changes.\n\n"
            "Save As keeps both. Reload shows the version on disk and discards "
            "your unsaved edits. Overwrite replaces the version on disk with yours."
        ),
    )
    story.SetHelpText(
        "Why Save stopped: the file on disk is not the one you opened, and what each answer does."
    )
    root.Add(story, 0, wx.ALL, _PAD)

    buttons = wx.BoxSizer(wx.HORIZONTAL)
    save_as = wx.Button(dialog, wx.ID_OK, "Save &As...")
    save_as.SetHelpText("Save your version under a new name. The file on disk is left alone.")
    reload = wx.Button(dialog, wx.ID_NO, "&Reload from Disk")
    reload.SetHelpText(
        "Show the version that is on disk now. Your unsaved edits in this document are discarded."
    )
    overwrite = wx.Button(dialog, wx.ID_YES, "&Overwrite")
    overwrite.SetHelpText(
        "Save your version over the file on disk. The other program's changes are lost."
    )
    cancel = wx.Button(dialog, wx.ID_CANCEL, "Cancel")
    cancel.SetHelpText("Do not save. Nothing changes, on disk or here.")
    for button in (save_as, reload, overwrite, cancel):
        buttons.Add(button, 0, wx.RIGHT, _PAD)
    root.Add(buttons, 0, wx.EXPAND | wx.ALL, _PAD)

    def _end(code: int) -> None:
        dialog.EndModal(code)

    reload.Bind(wx.EVT_BUTTON, lambda _e: _end(wx.ID_NO))
    overwrite.Bind(wx.EVT_BUTTON, lambda _e: _end(wx.ID_YES))

    dialog.SetSizerAndFit(root)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
    save_as.SetFocus()
    try:
        result = show_modal_dialog(dialog, "File Changed Since You Opened It")
    finally:
        dialog.Destroy()
    if result == wx.ID_OK:
        return SAVE_AS
    if result == wx.ID_NO:
        return RELOAD
    if result == wx.ID_YES:
        return OVERWRITE
    return CANCEL
