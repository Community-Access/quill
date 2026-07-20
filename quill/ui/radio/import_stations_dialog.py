"""Ask where to import a playlist's stations: an existing folder, a brand-new
folder path (any depth, e.g. "News/Local"), or the top level.

A small accessible dialog -- an editable combo pre-filled with the current
folders -- returned as the chosen folder path ("" for the top level) or None
when cancelled. wx is imported lazily so the module stays import-safe headless.
"""

from __future__ import annotations

_TOP_LEVEL = "(Top level)"


def prompt_import_target(parent: object, folders: list[str], station_count: int) -> str | None:
    """Return the folder path to import into ("" = top level), or None if the
    user cancels. *folders* seeds the combo; the user may also type a new path.
    """
    import wx

    from quill.ui.dialog_contract import apply_modal_ids

    dialog = wx.Dialog(parent, title="Import Stations")
    root = wx.BoxSizer(wx.VERTICAL)
    plural = "station" if station_count == 1 else "stations"
    root.Add(
        wx.StaticText(dialog, label=f"Import {station_count} {plural} into which folder?"),
        0,
        wx.ALL,
        10,
    )
    root.Add(
        wx.StaticText(
            dialog,
            label=(
                "&Folder -- choose one, or type a new path like News/Local "
                "(a new folder is created at whatever depth you type). Leave it "
                "on the top level to file them loose."
            ),
        ),
        0,
        wx.LEFT | wx.RIGHT,
        10,
    )
    combo = wx.ComboBox(dialog, choices=[_TOP_LEVEL, *folders], style=wx.CB_DROPDOWN)
    combo.SetName("Target folder")
    combo.SetValue(_TOP_LEVEL)
    root.Add(combo, 0, wx.EXPAND | wx.ALL, 10)

    buttons = dialog.CreateButtonSizer(wx.OK | wx.CANCEL)
    if buttons is not None:
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)
    dialog.SetSizerAndFit(root)
    apply_modal_ids(
        dialog,
        affirmative_id=wx.ID_OK,
        affirmative_label="OK",
        cancel_id=wx.ID_CANCEL,
        cancel_label="Cancel",
        escape_id=wx.ID_CANCEL,
    )
    wx.CallAfter(combo.SetFocus)

    chosen: str | None = None
    if dialog.ShowModal() == wx.ID_OK:
        value = combo.GetValue().strip()
        chosen = "" if value in ("", _TOP_LEVEL) else value.strip("/")
    dialog.Destroy()
    return chosen
