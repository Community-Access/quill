"""Preferences: what QUILL Lite does when the caret reaches a noted line.

QUILL's setting ``inline_note_line_cue`` (Settings, Editing), under QUILL's
name, default and wording (:mod:`quill.core.inline_note_cue`): play a soft
sound, say "note", or do nothing when the caret arrives on a line that carries
an inline note.

Its own module because ``lite_preferences.py`` sits at the line cap (GATE-11).
Built into that window directly under "Write new inline notes into the file",
the other question about notes. No access key: every letter in its label is
already claimed in Preferences, and a duplicate would make Windows cycle
between two controls instead of pressing either (GATE-14); Tab reaches it.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core.inline_note_cue import (
    NOTE_LINE_CUE_CHOICES,
    NOTE_LINE_CUE_LABELS,
    coerce_note_line_cue,
)
from quill.ui.dialog_contract import set_accessible_name

__all__ = ["NoteLineCuePrefs"]

LABEL = "When the caret reaches a line with an inline note:"

HELP = (
    "What happens as you arrow onto a line that carries an inline note. Play a "
    "sound gives a soft two-tap tone; Say note speaks the word note; Nothing "
    "keeps quiet. It happens once as you arrive, never while you move along the "
    "same line. With the sound chosen and no clip in your sound pack, the word "
    "is said instead, and a braille display shows note either way. QUILL has "
    "the same setting."
)


class NoteLineCuePrefs:
    """The one chooser, built into QUILL Lite's Preferences; :meth:`apply` on OK."""

    def __init__(self, dialog: Any, sizer: Any, settings: Any, *, pad: int = 8) -> None:
        self._settings = settings
        label = wx.StaticText(dialog, label=LABEL)
        self.choice = wx.Choice(
            dialog, choices=[NOTE_LINE_CUE_LABELS[key] for key in NOTE_LINE_CUE_CHOICES]
        )
        set_accessible_name(self.choice, LABEL.rstrip(":"))
        self.choice.SetHelpText(HELP)
        current = coerce_note_line_cue(getattr(settings, "inline_note_line_cue", "sound"))
        self.choice.SetSelection(NOTE_LINE_CUE_CHOICES.index(current))
        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.TOP, pad)
        sizer.Add(self.choice, 0, wx.LEFT | wx.RIGHT, pad)

    def apply(self) -> bool:
        """Write the choice back; ``True`` when it changed."""
        before = coerce_note_line_cue(getattr(self._settings, "inline_note_line_cue", "sound"))
        chosen = NOTE_LINE_CUE_CHOICES[max(0, self.choice.GetSelection())]
        self._settings.inline_note_line_cue = chosen
        return before != chosen
