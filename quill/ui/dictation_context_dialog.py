"""Dictation Context for This Document: what this document is, in a sentence.

dict.md 3.8 (gap 9). One short description -- "a formal letter to a client",
"notes to a friend, contractions fine" -- kept for this document by its path
(``quill/core/windows_dictation/contexts.py``). OpenAI dictation hears it as its
prompt and Tidy Dictated Text reads it with your instructions. The engines on
this computer take no prompt, and the window says so rather than pretending.

Shared by both editors (Tools > Dictation). Nothing is kept until OK.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.ui.dialog_contract import apply_modal_ids

__all__ = ["DictationContextDialog"]

_PAD = 8


class DictationContextDialog(wx.Dialog):
    """The context for one document. Read with :meth:`values` after OK."""

    def __init__(
        self, parent: Any, current: str, choices: dict[str, str], *, engine: str = ""
    ) -> None:
        super().__init__(parent, title="Dictation Context")
        self._choices = dict(choices)
        root = wx.BoxSizer(wx.VERTICAL)

        about_label = wx.StaticText(self, label="This &document is:")
        self.about = wx.TextCtrl(self, value=current, style=wx.TE_MULTILINE, size=(420, 80))
        self.about.SetName("This document is")
        self.about.SetHelpText(
            "A sentence or two about this document, in plain words: a formal letter to "
            "a client, notes to a friend, technical writing about software. OpenAI "
            "dictation uses it to get names, titles and style right, and Tidy Dictated "
            "Text follows it. Leave it empty for no context."
        )
        root.Add(about_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.about, 1, wx.EXPAND | wx.ALL, _PAD)

        saved_label = wx.StaticText(self, label="Start from a &saved context:")
        self.saved = wx.ListBox(self, choices=list(self._choices), style=wx.LB_SINGLE)
        self.saved.SetName("Start from a saved context")
        self.saved.SetHelpText(
            "Your saved contexts, then a few to start from. Choosing one puts its words "
            "in the box above, where you can change them. Saying dictation context and "
            "a name while dictating chooses one too."
        )
        self.saved.Bind(wx.EVT_LISTBOX, self._on_choose)
        root.Add(saved_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.saved, 0, wx.EXPAND | wx.ALL, _PAD)

        name_label = wx.StaticText(self, label="Also save it as a context &named:")
        self.name = wx.TextCtrl(self)
        self.name.SetName("Also save it as a context named")
        self.name.SetHelpText(
            "Optional. A short name, such as Client letter, to use this context again "
            "for other documents. Leave it empty to keep it for this document only."
        )
        root.Add(name_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.name, 0, wx.EXPAND | wx.ALL, _PAD)

        note_label = wx.StaticText(self, label="Who uses it:")
        self.note = wx.TextCtrl(self, value=self._note(engine), style=wx.TE_READONLY)
        self.note.SetName("Who uses it")
        self.note.SetHelpText(
            "Which of your dictation choices read the context. It never goes anywhere "
            "your speech or your text was not already going."
        )
        root.Add(note_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.note, 0, wx.EXPAND | wx.ALL, _PAD)

        buttons = self.CreateStdDialogButtonSizer(wx.OK | wx.CANCEL)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, _PAD)
        self.SetSizerAndFit(root)
        apply_modal_ids(self, affirmative_id=wx.ID_OK, cancel_id=wx.ID_CANCEL)
        self.about.SetFocus()

    @staticmethod
    def _note(engine: str) -> str:
        if engine == "openai":
            return "OpenAI dictation and Tidy Dictated Text."
        return (
            "Tidy Dictated Text, and OpenAI dictation if you choose it. The engines on "
            "this computer cannot be given a context."
        )

    def _on_choose(self, _event: Any) -> None:
        row = self.saved.GetSelection()
        if row == wx.NOT_FOUND:
            return
        name = self.saved.GetString(row)
        self.about.SetValue(self._choices.get(name, ""))

    def values(self) -> tuple[str, str]:
        """``(the context, the name to save it under or "")``."""
        return " ".join(self.about.GetValue().split()), " ".join(self.name.GetValue().split())
