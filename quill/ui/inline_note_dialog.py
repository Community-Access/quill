"""Accessible add/edit dialog for inline notes, shared by QUILL and QUILL Lite.

A labelled multi-line field (not a bare TextEntryDialog, so the control
announces its name on macOS too -- same lesson as #212), and above it a
read-only **Note on** line showing the first sentence of the text the note is
about, so you can check you picked the right place before saving. That line is
PlanCake's (Andre of Oire Software). It is a field rather than a label so it can
be reached with Tab and read again; nothing is announced for it, because the
screen reader reads the dialog (GATE-13).

When the document is Markdown or HTML, a check box chooses whether the note is
written **into the file** as a ``quill-note`` comment instead of the private
sidecar. In any other format the box is disabled and its help says why.

Returns ``(action, text, in_file)``: ``action`` is ``"save"``, ``"delete"``
(edit mode only) or ``"cancel"``. Routed through the host's modal entry with the
standard affirmative/escape ids so it is reliably keyboard-dismissable.
"""

from __future__ import annotations

from typing import Any

IN_FILE_HELP = (
    "Checked, the note is written into the document itself as a hidden HTML "
    "comment right after this text, so anyone who opens the file -- a colleague "
    "or an AI assistant -- can read it. Unchecked, the note stays private to "
    "you and the file is not changed."
)
IN_FILE_UNAVAILABLE_HELP = (
    "Notes can be written into Markdown and HTML documents only. In this "
    "document the note is kept privately, outside the file."
)


def show_inline_note_dialog(
    wx: Any,
    parent: Any,
    show_modal_dialog: Any,
    *,
    title: str,
    initial: str = "",
    allow_delete: bool = False,
    note_on: str = "",
    in_file: bool | None = None,
    in_file_available: bool = False,
) -> tuple[str, str, bool]:
    """Prompt for an inline note's text. Returns ``(action, text, in_file)``.

    ``in_file`` is the check box's starting state; ``None`` leaves the box
    out altogether (editing a note, whose kind does not change).
    """
    from quill.ui.dialog_contract import apply_modal_ids

    result: dict[str, Any] = {"action": "cancel", "text": initial, "in_file": bool(in_file)}
    dialog = wx.Dialog(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    dialog.SetSize((540, 400))
    sizer = wx.BoxSizer(wx.VERTICAL)

    if note_on:
        on_label = wx.StaticText(dialog, label="Note &on:")
        sizer.Add(on_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        on_field = wx.TextCtrl(dialog, value=note_on, style=wx.TE_READONLY)
        on_field.SetName("Note on")
        on_field.SetHelpText(
            "The first sentence of the text this note is about. Read-only: "
            "check it is the right place before you save."
        )
        sizer.Add(on_field, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

    label = wx.StaticText(dialog, label="&Note:")
    sizer.Add(label, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)
    field = wx.TextCtrl(dialog, value=initial, style=wx.TE_MULTILINE | wx.TE_WORDWRAP)
    field.SetName("Inline note text")
    field.SetHelpText(
        "What you want to say about this text. Notes are anchored to the text, "
        "so they follow it as the document is edited."
    )
    sizer.Add(field, 1, wx.EXPAND | wx.ALL, 10)

    in_file_box = None
    if in_file is not None:
        in_file_box = wx.CheckBox(dialog, label="&Write this note into the file")
        in_file_box.SetValue(bool(in_file) and in_file_available)
        in_file_box.SetHelpText(IN_FILE_HELP if in_file_available else IN_FILE_UNAVAILABLE_HELP)
        in_file_box.Enable(in_file_available)
        sizer.Add(in_file_box, 0, wx.LEFT | wx.RIGHT, 10)

    btns = wx.BoxSizer(wx.HORIZONTAL)
    save_btn = wx.Button(dialog, wx.ID_OK, label="&Save", name="inline_note_save")
    save_btn.SetHelpText("Save the note.")
    save_btn.SetDefault()
    btns.AddStretchSpacer()
    delete_btn = None
    if allow_delete:
        delete_btn = wx.Button(dialog, label="&Delete", name="inline_note_delete")
        delete_btn.SetHelpText("Delete this note. The text it was on is not changed.")
        btns.Add(delete_btn, 0, wx.RIGHT, 8)
    cancel_btn = wx.Button(dialog, wx.ID_CANCEL, label="Cancel")
    cancel_btn.SetHelpText("Close without changing anything.")
    btns.Add(save_btn, 0, wx.RIGHT, 8)
    btns.Add(cancel_btn, 0)
    sizer.Add(btns, 0, wx.EXPAND | wx.ALL, 10)

    def _on_save(_e: Any) -> None:
        result["action"] = "save"
        result["text"] = field.GetValue()
        result["in_file"] = bool(in_file_box.GetValue()) if in_file_box is not None else False
        dialog.EndModal(wx.ID_OK)

    def _on_delete(_e: Any) -> None:
        result["action"] = "delete"
        dialog.EndModal(wx.ID_OK)

    save_btn.Bind(wx.EVT_BUTTON, _on_save)
    if delete_btn is not None:
        delete_btn.Bind(wx.EVT_BUTTON, _on_delete)

    dialog.SetSizer(sizer)
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
    wx.CallAfter(field.SetFocus)
    try:
        show_modal_dialog(dialog, title)
    finally:
        dialog.Destroy()
    return (str(result["action"]), str(result["text"]), bool(result["in_file"]))
