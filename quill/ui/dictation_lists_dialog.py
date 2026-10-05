"""Two read-and-choose lists for dictation: the commands, and recent phrases.

Moved out of :mod:`quill.ui.windows_dictation_dialog` (GATE-11) when Dictation
Settings gained More Dictation Settings; that module still exports both names,
so nothing that opened them from there changes.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids, bind_close_button

__all__ = ["DictationCommandsDialog", "RecentPhrasesDialog"]

_PAD = 8


class DictationCommandsDialog(wx.Dialog):
    """Everything dictation understands, as read-only text to arrow through: a
    screen reader can only review text it can put a cursor in."""

    def __init__(self, parent: Any, body: str) -> None:
        super().__init__(
            parent, title="Dictation Commands", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        root = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self, label="&Commands:")
        self.text = wx.TextCtrl(
            self, value=body, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2
        )
        self.text.SetHelpText(
            "Every phrase dictation acts on and what it does. Read with the arrow "
            "keys; Escape closes. The same list is in the user guide."
        )
        close = wx.Button(self, wx.ID_CANCEL, "Close")
        close.SetHelpText("Close this list.")
        root.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.text, 1, wx.EXPAND | wx.ALL, _PAD)
        root.Add(close, 0, wx.ALL, _PAD)
        self.SetSizer(root)
        self.SetSize((640, 520))
        apply_modal_ids(self, cancel_id=wx.ID_CANCEL, escape_id=wx.ID_CANCEL)
        bind_close_button(self, close, modeless=False)
        self.text.SetFocus()
        self.text.SetInsertionPoint(0)


class RecentPhrasesDialog(wx.Dialog):
    """The last phrases dictated this session, newest first (dict.md 3.3).

    Insert Again (Enter) writes the chosen phrase as one undo step; Copy puts it
    on the clipboard. Memory only: it goes when the app closes.
    """

    def __init__(self, parent: Any, phrases: list[str]) -> None:
        super().__init__(
            parent, title="Recent Phrases", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.chosen: str | None = None
        self.verb = "insert"
        self._phrases = list(phrases)
        root = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(self, label="&Phrases, newest first:")
        self.list = wx.ListBox(self, choices=self._phrases)
        self.list.SetHelpText(
            "What you dictated this session, newest first. Enter inserts the one "
            "you are on at the cursor again; Copy puts it on the clipboard."
        )
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        insert = wx.Button(self, wx.ID_OK, "&Insert Again")
        insert.SetHelpText("Write this phrase at the cursor again, as one undo step.")
        copy = wx.Button(self, label="&Copy")
        copy.SetHelpText("Put this phrase on the clipboard without writing it.")
        close = wx.Button(self, wx.ID_CANCEL, "Close")
        close.SetHelpText("Close the list without inserting anything.")
        for button in (insert, copy, close):
            buttons.Add(button, 0, wx.RIGHT, _PAD)
        root.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.list, 1, wx.EXPAND | wx.ALL, _PAD)
        root.Add(buttons, 0, wx.ALL, _PAD)
        self.SetSizer(root)
        self.SetSize((560, 400))
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        bind_close_button(self, close, modeless=False)
        self.Bind(wx.EVT_BUTTON, self._on_insert, id=wx.ID_OK)
        copy.Bind(wx.EVT_BUTTON, self._on_copy)
        apply_listbox_activation(self.list, self._on_insert)  # Enter, Space and double-click
        if self._phrases:
            self.list.SetSelection(0)
        self.list.SetFocus()

    def _selected(self) -> str | None:
        index = self.list.GetSelection()
        return self._phrases[int(index)] if index != wx.NOT_FOUND else None

    def _on_insert(self, _event: Any) -> None:
        self.chosen, self.verb = self._selected(), "insert"
        self.EndModal(wx.ID_OK)

    def _on_copy(self, _event: Any) -> None:
        self.chosen, self.verb = self._selected(), "copy"
        self.EndModal(wx.ID_OK)
