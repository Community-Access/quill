"""QUILL Transcribe's Practice Dictation window (D-25).

A window with a field of QUILL Transcribe's own that dictation types into
directly, so somebody new can make a first dictation, and test how well they
are heard, without writing into another program.

* **Why it is allowed.** From QUILL Transcribe's own window, a start normally
  waits for the next program you switch to: the window is never dictated into
  (:meth:`~quill.apps.transcribe_dictation.TranscribeDictationMixin._arm_start`).
  The practice field is the one exception. Start Dictation Here points the
  shared controller at :class:`PracticeFieldDocument` -- an editor-port target,
  written into with one undo step a phrase, never through keystrokes -- and
  starts it at once, after the same refusals as any start (Safe Mode, the
  owner lock, the microphone, the model). When dictation stops, by any route,
  the controller goes back to the locked-field document
  (:meth:`~quill.apps.transcribe_coach.TranscribeCoachMixin._practice_state_changed`).
* **Read This Sentence** clears the field, shows one of
  :data:`quill.core.transcribe.practice.SENTENCES`, and starts dictation in the
  field if it is off. The first phrase written is compared with the sentence,
  word for word, with the benchmark's own scorer, and the outcome is said once
  and kept in the Result field. Score the Field compares everything in the
  field again, for a sentence said in more than one breath.
* **Keys** (the window's own table): Ctrl+F11 starts or stops dictation in the
  field (the editors' chord; the main window's Ctrl+F11 waits for another
  program instead); Escape closes. The buttons carry the rest.
* **What is said** (GATE-13): nothing on opening -- the title and the focused
  field are the reader's -- and after that only outcomes: the score.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import wx

from quill.core.transcribe.practice import SENTENCES
from quill.ui.dialog_contract import bind_close_button
from quill.ui.dictation_review_frame import ReviewBoxDocument

__all__ = ["TITLE", "PracticeDictationFrame", "PracticeFieldDocument"]

TITLE = "Practice Dictation"
_PAD = 8


class PracticeFieldDocument(ReviewBoxDocument):
    """The practice field as dictation's document port.

    Plain text: a profile that formats (Document, Email) says headings and bold
    work in QUILL documents, and Markdown types its marks, exactly as they would
    in Notepad -- which is what the practice is for."""

    def unavailable_reason(self, *, writing: bool) -> str:
        del writing
        try:
            if not self._control or not self._control.IsEditable():
                return "The Practice Dictation window has closed."
        except RuntimeError:
            return "The Practice Dictation window has closed."
        return ""

    def formatting(self) -> str:
        return ""


class PracticeDictationFrame(wx.Frame):
    """The sentence to read, the practice field, the result, and four buttons."""

    def __init__(
        self,
        parent: Any,
        *,
        start_or_stop: Callable[[], None],
        read_sentence: Callable[[], None],
        score_field: Callable[[], None],
        next_sentence: Callable[[], None],
    ) -> None:
        super().__init__(parent, title=TITLE)
        panel = wx.Panel(self)
        root = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(root)

        sentence_label = wx.StaticText(panel, label="Sentence to &read aloud:")
        self.sentence = wx.TextCtrl(panel, value=SENTENCES[0], style=wx.TE_READONLY)
        self.sentence.SetName("Sentence to read aloud")
        self.sentence.SetHelpText(
            "The sentence for the recognition test. Press Read This Sentence, then "
            "read it aloud at your usual pace. Next Sentence gives you another."
        )
        root.Add(sentence_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, _PAD)
        root.Add(self.sentence, 0, wx.EXPAND | wx.ALL, _PAD)

        field_label = wx.StaticText(panel, label="&Practice field:")
        self.field = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_RICH2)
        self.field.SetName("Practice field")
        self.field.SetHelpText(
            "QUILL Transcribe's own field. While dictation is on here, what you say "
            "is written into this field and nowhere else. You can type and edit in "
            "it too; Control F11 starts and stops dictation here."
        )
        self.field.SetMinSize((-1, self.field.GetCharHeight() * 6))
        root.Add(field_label, 0, wx.LEFT | wx.RIGHT, _PAD)
        root.Add(self.field, 1, wx.EXPAND | wx.ALL, _PAD)

        result_label = wx.StaticText(panel, label="Res&ult:")
        self.result = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.result.SetName("Result")
        self.result.SetHelpText(
            "The last recognition test: how many words were right, and any that "
            "were heard differently. It is said once when the test finishes."
        )
        root.Add(result_label, 0, wx.LEFT | wx.RIGHT, _PAD)
        root.Add(self.result, 0, wx.EXPAND | wx.ALL, _PAD)

        row = wx.BoxSizer(wx.HORIZONTAL)
        self.start = self._button(
            panel,
            row,
            "Start Dictation &Here",
            "Starts dictation in the practice field, or stops it. Nothing you say "
            "goes into another program while it is on here.",
            start_or_stop,
        )
        self.read = self._button(
            panel,
            row,
            "Read &This Sentence",
            "Clears the practice field, starts dictation in it if it is off, and "
            "scores the first thing you say against the sentence above.",
            read_sentence,
        )
        self.score = self._button(
            panel,
            row,
            "&Score the Field",
            "Compares everything in the practice field with the sentence, for a "
            "sentence you said in more than one breath.",
            score_field,
        )
        self.next = self._button(
            panel,
            row,
            "&Next Sentence",
            "Shows another sentence to read.",
            next_sentence,
        )
        close = wx.Button(panel, wx.ID_CLOSE, "Close")
        close.SetHelpText(
            "Closes the window. Dictation in the practice field stops; nothing is kept."
        )
        row.Add(close, 0)
        bind_close_button(self, close, modeless=True)
        root.Add(row, 0, wx.ALL, _PAD)

        self._start_or_stop = start_or_stop
        self._keys()
        self.SetInitialSize((640, 480))
        self.Centre()

    def _button(
        self, panel: Any, row: Any, label: str, help_text: str, run: Callable[[], None]
    ) -> Any:
        button = wx.Button(panel, label=label)
        button.SetHelpText(help_text)
        button.Bind(wx.EVT_BUTTON, lambda _e: run())
        row.Add(button, 0, wx.RIGHT, _PAD)
        return button

    def _keys(self) -> None:
        entries = []
        for flags, key, run in (
            (wx.ACCEL_CTRL, wx.WXK_F11, self._start_or_stop),
            (wx.ACCEL_NORMAL, wx.WXK_ESCAPE, self.Close),
        ):
            ident = wx.NewIdRef()
            self.Bind(wx.EVT_MENU, lambda _e, run=run: run(), id=ident)
            entries.append(wx.AcceleratorEntry(flags, key, ident))
        self.SetAcceleratorTable(wx.AcceleratorTable(entries))

    def set_listening(self, on: bool) -> None:
        """The start button says what pressing it will do."""
        label = "Stop Dictation &Here" if on else "Start Dictation &Here"
        if self.start.GetLabel() != label:
            self.start.SetLabel(label)
