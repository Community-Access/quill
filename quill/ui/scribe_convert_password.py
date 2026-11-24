"""Enter Password..., for a Scribe job waiting for its password (PRD 7.3 part 4, 7.4a).

Opened only by the person's own command on the job in Conversions on This Computer,
never by a background job. The field is never pre-filled, saved or logged;
"Show password" swaps in a plain field with its own label. After a wrong
password the first line says "Password not accepted. 2 tries left."
"""

from __future__ import annotations

from typing import Any

import wx

from quill.ui.dialog_contract import apply_modal_ids, bind_close_button, show_modal_dialog

MAX_TRIES = 3


def tries_sentence(tries_used: int) -> str:
    left = MAX_TRIES - tries_used
    if tries_used <= 0:
        return "Scribe for Documents needs this file's password to convert it."
    noun = "try" if left == 1 else "tries"
    return f"Password not accepted. {left} {noun} left."


class ScribePasswordDialog(wx.Dialog):
    def __init__(self, parent: Any, file_name: str, tries_used: int) -> None:
        super().__init__(parent, title=f"Password for {file_name}")
        self.SetName("scribe_password_dialog")  # F1 finds its topic by this name (topics.json)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label="&Message:"), 0, wx.LEFT | wx.TOP, 6)
        self.message = wx.TextCtrl(self, style=wx.TE_READONLY, value=tries_sentence(tries_used))
        self.message.SetHelpText("Why the password is asked for, and how many tries are left.")
        sizer.Add(self.message, 0, wx.EXPAND | wx.ALL, 6)
        self.label = wx.StaticText(self, label=f"&Password for {file_name}:")
        sizer.Add(self.label, 0, wx.LEFT, 6)
        self.field = wx.TextCtrl(self, style=wx.TE_PASSWORD)
        self.field.SetHelpText("Used for this one conversion; never saved or logged.")
        sizer.Add(self.field, 0, wx.EXPAND | wx.ALL, 6)
        self.plain_label = wx.StaticText(self, label=f"&Password for {file_name}:")
        sizer.Add(self.plain_label, 0, wx.LEFT, 6)
        self.plain = wx.TextCtrl(self)
        self.plain.SetHelpText("The password as plain text. Never saved or logged.")
        sizer.Add(self.plain, 0, wx.EXPAND | wx.ALL, 6)
        self.plain_label.Hide()
        self.plain.Hide()
        self.show = wx.CheckBox(self, label="Sh&ow password")
        self.show.SetHelpText("Shows the password as plain text so you can check it.")
        sizer.Add(self.show, 0, wx.ALL, 6)
        buttons = wx.StdDialogButtonSizer()
        ok = wx.Button(self, wx.ID_OK, label="OK")
        ok.SetHelpText("Sends the password to Scribe for Documents for this file.")
        ok.SetDefault()
        cancel = wx.Button(self, wx.ID_CANCEL, label="Cancel")
        cancel.SetHelpText("The file keeps waiting for its password.")
        buttons.AddButton(ok)
        buttons.AddButton(cancel)
        buttons.Realize()
        sizer.Add(buttons, 0, wx.EXPAND | wx.ALL, 6)
        self.SetSizerAndFit(sizer)
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        bind_close_button(self, cancel, modeless=False)
        self.show.Bind(wx.EVT_CHECKBOX, self._swap)
        self.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)
        self.field.SetFocus()

    def _swap(self, _event: Any) -> None:
        plain = self.show.GetValue()
        source, target = (self.field, self.plain) if plain else (self.plain, self.field)
        target.SetValue(source.GetValue())
        self.label.Show(not plain)
        self.field.Show(not plain)
        self.plain_label.Show(plain)
        self.plain.Show(plain)
        self.Layout()

    def value(self) -> str:
        return (self.plain if self.show.GetValue() else self.field).GetValue()

    def _on_destroy(self, event: wx.WindowDestroyEvent) -> None:
        if event.GetEventObject() is self:
            self.field.SetValue("")
            self.plain.SetValue("")
        event.Skip()


def ask_password(parent: Any, job: Any, announce: Any = None) -> str:
    tries = int(job.password_tries or 0)
    dialog = ScribePasswordDialog(parent, job.display_name, tries)
    if tries and announce is not None:
        wx.CallLater(250, announce, tries_sentence(tries))
    try:
        if show_modal_dialog(dialog, "Password") != wx.ID_OK:
            return ""
        return dialog.value()
    finally:
        dialog.Destroy()


__all__ = ["ScribePasswordDialog", "ask_password", "tries_sentence"]
