"""Two read-and-choose lists for dictation: the commands, and recent phrases.

Moved out of :mod:`quill.ui.windows_dictation_dialog` (GATE-11) when Dictation
Settings gained More Dictation Settings; that module still exports both names,
so nothing that opened them from there changes.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
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
    """The last phrases dictated this session, newest first (dict.md 3.3), then
    the words kept on disk (D-5): not written last time, a review that did not
    finish, and, with dictation history on, earlier phrases.

    Insert Again (Enter) writes the chosen phrase as one undo step; Copy puts it
    on the clipboard. Discard deletes a kept entry; Clear History deletes the
    whole history after a question whose default is No. This session's phrases
    are memory only: they go when the app closes.
    """

    def __init__(
        self,
        parent: Any,
        phrases: list[str],
        *,
        saved: Sequence[Any] = (),
        say: Callable[[str], None] | None = None,
        clear_history: Callable[[], None] | None = None,
        confirm: Callable[[str], bool] | None = None,
    ) -> None:
        super().__init__(
            parent, title="Recent Phrases", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.chosen: str | None = None
        #: The kept entry chosen (``None`` for one of this session's phrases).
        self.chosen_row: Any = None
        self.verb = "insert"
        self._phrases = list(phrases)
        self._rows: list[Any] = [None] * len(self._phrases) + list(saved)
        self._say = say or (lambda _text: None)
        self._clear_history = clear_history
        self._confirm = confirm or self._ask
        root = wx.BoxSizer(wx.VERTICAL)
        label = wx.StaticText(
            self,
            label=(
                "&Phrases, newest first, then words kept from before:"
                if saved
                else "&Phrases, newest first:"
            ),
        )
        self.list = wx.ListBox(
            self, choices=self._phrases + [str(row.label) for row in self._rows if row is not None]
        )
        self.list.SetHelpText(
            "What you dictated this session, newest first, then words kept from "
            "before: phrases that were not written, a review that did not finish, and "
            "with dictation history on, earlier phrases. Enter inserts the one you are "
            "on at the cursor again; Copy puts it on the clipboard."
        )
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        insert = wx.Button(self, wx.ID_OK, "&Insert Again")
        insert.SetHelpText(
            "Write this phrase at the cursor again, as one undo step. Words kept from "
            "before are deleted from this computer once they are written."
        )
        copy = wx.Button(self, label="&Copy")
        copy.SetHelpText("Put this phrase on the clipboard without writing it.")
        discard = wx.Button(self, label="&Discard")
        discard.SetHelpText(
            "Delete these kept words from this computer without writing them. This "
            "session's own phrases are not kept, so there is nothing to discard for them."
        )
        discard.Bind(wx.EVT_BUTTON, lambda _e: self.discard())
        listed = [insert, copy, discard]
        if clear_history is not None:
            clear = wx.Button(self, label="Clear &History")
            clear.SetHelpText(
                "Delete the whole dictation history from this computer, after a "
                "question whose answer is No unless you choose Yes. Words not written "
                "last time are not part of the history and stay until you discard them."
            )
            clear.Bind(wx.EVT_BUTTON, lambda _e: self.clear_history())
            listed.append(clear)
        close = wx.Button(self, wx.ID_CANCEL, "Close")
        close.SetHelpText("Close the list without inserting anything.")
        for button in (*listed, close):
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
        if self._rows:
            self.list.SetSelection(0)
        self.list.SetFocus()

    def _selected(self) -> tuple[str | None, Any]:
        index = self.list.GetSelection()
        if index == wx.NOT_FOUND or not 0 <= int(index) < len(self._rows):
            return None, None
        row = self._rows[int(index)]
        return (self._phrases[int(index)] if row is None else str(row.text)), row

    def _on_insert(self, _event: Any) -> None:
        (self.chosen, self.chosen_row), self.verb = self._selected(), "insert"
        self.EndModal(wx.ID_OK)

    def _on_copy(self, _event: Any) -> None:
        (self.chosen, self.chosen_row), self.verb = self._selected(), "copy"
        self.EndModal(wx.ID_OK)

    # -- kept words (D-5) ------------------------------------------------------ #

    def discard(self) -> None:
        """Delete the kept entry the list is on; the list stays open."""
        index = self.list.GetSelection()
        text, row = self._selected()
        if text is None:
            return
        if row is None:
            self._say("This session's phrases are not kept, so there is nothing to discard.")
            return
        row.discard()
        del self._rows[int(index)]
        self.list.Delete(int(index))
        if self._rows:
            self.list.SetSelection(min(int(index), len(self._rows) - 1))
        self._say("Discarded.")  # the list says the next row; only this says the deletion

    def clear_history(self) -> None:
        """Delete the whole history, after a question whose default is No."""
        if self._clear_history is None:
            return
        if not self._confirm(
            "Delete the whole dictation history from this computer? Words not written "
            "last time stay until you discard them."
        ):
            return
        self._clear_history()
        for index in range(len(self._rows) - 1, -1, -1):
            row = self._rows[index]
            if row is not None and getattr(row, "kind", "") == "history":
                del self._rows[index]
                self.list.Delete(index)
        if self._rows:
            self.list.SetSelection(0)
        self._say("Dictation history cleared.")

    def _ask(self, question: str) -> bool:
        from quill.ui.dialog_contract import show_message_box

        answer = show_message_box(
            question, "Clear Dictation History", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_WARNING, self
        )
        return answer == wx.YES
