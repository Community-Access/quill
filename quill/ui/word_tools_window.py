"""The window an AI word tool answers in: the answer to listen to, and the choices to use.

Shared by QUILL and QUILL Lite, like every hosted-AI window (see
:mod:`quill.ui.hosted_ai_dialogs` for the rules: a modeless ``wx.Frame``, Close
bound by hand, nothing applied without a keystroke, GATE-13 one surface at a
time). What makes this one different from :class:`~quill.ui.hosted_ai_pad.AiResultFrame`
is the shape of the answer: a word tool returns prose **and** a list of
replacements, each with a note saying why, and the thing a listener does with
it is pick one -- so the answer is a read-only field focus lands on, and the
choices are a list box whose Enter is "use this one".

**Use This Word** replaces the word the tool was asked about, or inserts at the
cursor for the reverse dictionary, through the ordinary undo stack -- and only
while that word is still where it was, which the caller decides by passing
``on_use`` or not. Nothing here reads the document.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

import wx

from quill.core.ai.word_tools import INSERT, WordChoice
from quill.ui.dialog_contract import apply_listbox_activation
from quill.ui.hosted_ai_dialogs import _close_row, _read_only, focus_on

__all__ = ["WordAnswerFrame"]


def _plain_label(label: str) -> str:
    """A menu label as a window title: no mnemonic, no trailing dots."""
    return label.replace("&&", "\0").replace("&", "").replace("\0", "&").rstrip(". ")


class WordAnswerFrame(wx.Frame):
    """One word tool's answer: prose first, then the choices, then what to do."""

    def __init__(
        self,
        parent: wx.Window,
        *,
        tool_label: str,
        word: str,
        answer: str,
        choices: Sequence[WordChoice],
        action: str,
        on_use: Callable[[str], None] | None,
        announce: Callable[[str], None],
        on_ask_again: Callable[[], None] | None = None,
    ) -> None:
        title = _plain_label(tool_label)
        super().__init__(parent, title=f"{title}: {word}" if word else title)
        self._answer = answer
        self._choices = list(choices)
        self._announce = announce
        self._on_use = on_use

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(sizer)

        body = _read_only(
            panel,
            sizer,
            "The answer",
            answer or "The model sent nothing back.",
            "What the AI said about the word. Read-only; arrow through it, or "
            "Tab to the choices below to put one into your document.",
        )

        self._list: wx.ListBox | None = None
        if self._choices:
            # The label is created immediately before the list, which on wxMSW
            # is what gives the list its accessible name.
            caption = wx.StaticText(panel, label="Choice&s:")
            self._list = wx.ListBox(
                panel, choices=[c.spoken() for c in self._choices], style=wx.LB_SINGLE
            )
            self._list.SetHelpText(
                "Replacements that fit the sentence, best first, each with a note. "
                "Enter, or Use This Word, puts the selected one into your document; "
                "Control Z takes it back."
            )
            sizer.Add(caption, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)
            sizer.Add(self._list, 1, wx.EXPAND | wx.ALL, 8)
            self._list.SetSelection(0)
            apply_listbox_activation(self._list, lambda _e: self._use_selected())

        extra: list[wx.Button] = []
        if self._choices:
            verb = "&Insert This Word" if action == INSERT else "&Use This Word"
            use = wx.Button(panel, label=verb)
            if on_use is None:
                use.Enable(False)
                use.SetHelpText(
                    "Disabled: the word this answer was about is no longer where it "
                    "was in the document. Copy a choice instead."
                )
            else:
                use.SetHelpText(
                    "Puts the selected choice into your document -- in place of the "
                    "word, or at the cursor for Find the Word For. Control Z takes it back."
                )
            use.Bind(wx.EVT_BUTTON, lambda _e: self._use_selected())
            extra.append(use)
            copy_choice = wx.Button(panel, label="Copy &Choice")
            copy_choice.SetHelpText("Puts the selected choice on the clipboard.")
            copy_choice.Bind(wx.EVT_BUTTON, lambda _e: self._copy(self._selected_text()))
            extra.append(copy_choice)

        copy = wx.Button(panel, label="Copy &Answer")
        copy.SetHelpText("Puts the whole answer on the clipboard.")
        copy.Bind(wx.EVT_BUTTON, lambda _e: self._copy(self._answer))
        extra.append(copy)

        if on_ask_again is not None:
            again = wx.Button(panel, label="Ask Something &Else...")
            again.SetHelpText(
                "Closes this and opens the Dictionary menu for the same word, so you "
                "can ask a different question about it."
            )

            def _again(_event: wx.CommandEvent) -> None:
                self.Close()
                on_ask_again()

            again.Bind(wx.EVT_BUTTON, _again)
            extra.append(again)

        _close_row(self, sizer, *extra)
        self.SetInitialSize((640, 480))
        self.Centre()
        # Focus lands on the answer, so the reader reads it. Nothing is said on
        # top of that (GATE-13): the title and the focused field are both
        # things it already says.
        focus_on(self, body)

    # -- what the buttons do ------------------------------------------------ #

    def _selected_text(self) -> str:
        if self._list is None:
            return ""
        index = self._list.GetSelection()
        if index == wx.NOT_FOUND or index >= len(self._choices):
            return ""
        return self._choices[index].text

    def _use_selected(self) -> None:
        chosen = self._selected_text()
        if not chosen:
            self._announce("Choose a word in the list first.")
            return
        if self._on_use is None:
            self._announce(
                "The word this answer was about has moved or changed, so it cannot be "
                "replaced from here. Copy Choice puts it on the clipboard instead."
            )
            return
        self._on_use(chosen)
        self._announce(f"{chosen}. Press Control Z to undo.")
        self.Close()

    def _copy(self, text: str) -> None:
        if not text:
            self._announce("Nothing to copy.")
            return
        if wx.TheClipboard.Open():
            try:
                wx.TheClipboard.SetData(wx.TextDataObject(text))
            finally:
                wx.TheClipboard.Close()
            self._announce("Copied.")
