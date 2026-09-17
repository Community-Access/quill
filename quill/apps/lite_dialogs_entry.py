"""The two dialogs that ask you to type something: a box, and a link.

Split out of :mod:`quill.apps.lite_dialogs` under GATE-11, and they belong
together: everything else in that module *offers* you a list to pick from, and
these two hand you an empty field.

``wx.TextEntryDialog`` would do the first of them in one line and is not used,
for the reason the other module's docstring gives: its prompt is not a
``wx.StaticText`` immediately before the field, so on wxMSW the field's
accessible name is whatever the reader can scrape -- which in practice is
nothing. A named field is the difference between "edit" and "Address, edit".
"""

from __future__ import annotations

import wx

from quill.apps.lite_dialogs import _PAD, _plain_label, _stack
from quill.ui.dialog_contract import apply_modal_ids, set_accessible_name, show_modal_dialog

__all__ = ["ask_link", "ask_text"]


def ask_text(
    parent: wx.Window,
    *,
    title: str,
    label: str,
    help_text: str,
    value: str = "",
) -> str | None:
    """One labelled box and an OK. Returns the text, or ``None`` on Escape.

    ``wx.TextEntryDialog`` would do this in one line and is not used, for the
    reason the module docstring gives: its prompt is not a ``wx.StaticText``
    immediately before the field, so on wxMSW the field's accessible name is
    whatever the reader can scrape -- which in practice is nothing. A named
    field is the difference between "edit" and "Optional attributes, edit".
    """
    dialog = wx.Dialog(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE)
    root = wx.BoxSizer(wx.VERTICAL)
    static = wx.StaticText(dialog, label=label)
    entry = wx.TextCtrl(dialog, value=value, style=wx.TE_PROCESS_ENTER)
    set_accessible_name(entry, _plain_label(label))
    entry.SetHelpText(help_text)
    _stack(root, static, entry)
    root.Add(dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALIGN_RIGHT | wx.ALL, _PAD)
    dialog.SetSizerAndFit(root)
    dialog.SetSize((480, dialog.GetSize().GetHeight()))
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
    entry.Bind(wx.EVT_TEXT_ENTER, lambda _e: dialog.EndModal(wx.ID_OK))
    entry.SetFocus()
    entry.SetInsertionPointEnd()
    try:
        if show_modal_dialog(dialog, title) != wx.ID_OK:
            return None
        return str(entry.GetValue())
    finally:
        dialog.Destroy()


def ask_link(parent: wx.Window, *, text: str = "") -> tuple[str, str] | None:
    """Two labelled boxes: the words to show, and where they go.

    Returns ``(display_text, url)``, or ``None`` on Escape. The display box is
    pre-filled with the selection, because the commonest way to make a link is
    to select the words first -- and a box that arrives already holding them
    saves retyping something the reader would then have to check.

    Its own function rather than two :func:`ask_text` calls: a wizard of two
    one-field dialogs is two Escape keys, two Enter keys and no way to go back
    and change the first answer.
    """
    dialog = wx.Dialog(parent, title="Insert Link", style=wx.DEFAULT_DIALOG_STYLE)
    root = wx.BoxSizer(wx.VERTICAL)

    display_label = wx.StaticText(dialog, label="Text to &show:")
    display = wx.TextCtrl(dialog, value=text)
    set_accessible_name(display, "Text to show")
    display.SetHelpText(
        "The words the link will read as. Leave it empty to show the address itself."
    )
    _stack(root, display_label, display)

    url_label = wx.StaticText(dialog, label="&Address:")
    url = wx.TextCtrl(dialog, value="https://", style=wx.TE_PROCESS_ENTER)
    set_accessible_name(url, "Address")
    url.SetHelpText("Where the link goes -- a web address, or a path to another file.")
    _stack(root, url_label, url)

    root.Add(dialog.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL), 0, wx.ALIGN_RIGHT | wx.ALL, _PAD)
    dialog.SetSizerAndFit(root)
    dialog.SetSize((520, dialog.GetSize().GetHeight()))
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
    url.Bind(wx.EVT_TEXT_ENTER, lambda _e: dialog.EndModal(wx.ID_OK))
    (url if text else display).SetFocus()
    url.SetInsertionPointEnd()
    try:
        if show_modal_dialog(dialog, "Insert Link") != wx.ID_OK:
            return None
        return str(display.GetValue()), str(url.GetValue())
    finally:
        dialog.Destroy()
