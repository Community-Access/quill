"""Preferences: the two typing assists QUILL Lite shares with QUILL.

QUILL's settings ``autocorrect_misspellings`` and ``continue_lists_in_plain_text``
(Settings, Editing), under QUILL's names and defaults -- both off -- for the
behaviour QUILL Lite gained on 2026-10-16 (``lite_window_typing_assist.py``).

Its own module because ``lite_preferences.py`` sits at the line cap (GATE-11).
Built into that window directly under "Turn two hyphens into an em dash", the
other questions about text the app changes as you type. **No access keys**:
every letter in either label is already claimed in Preferences, and a
duplicate makes Windows cycle between two controls instead of pressing either
(GATE-14); Tab still arrives, and the labels are read on arrival.
"""

from __future__ import annotations

from typing import Any

import wx

__all__ = ["TypingAssistPrefs"]

AUTOCORRECT_LABEL = "Correct common misspellings as I type"
AUTOCORRECT_HELP = (
    "A space or Enter after a common misspelling replaces it with the right "
    "word -- teh becomes the -- and you hear the corrected word. Control Z "
    "straight afterwards puts back what you typed, and that word is then left "
    "alone. Never in a source or settings file, a web or email address, or a "
    "word in capitals. Autocorrect also has to be switched on in Tools, "
    "Customize Features. Tools, AutoCorrect Entries, Alt+Shift+9, lists the "
    "corrections and adds your own. QUILL has the same setting."
)

LISTS_LABEL = "Continue lists in plain text"
LISTS_HELP = (
    "In a plain text document, Enter at the end of a line that starts with a "
    "hyphen, an asterisk or a number such as 1. or 1) starts the next line with "
    "the next marker, and Enter on an empty item ends the list. Markdown "
    "documents always do this. Never in a source or settings file, or in rich "
    "text. QUILL has the same setting."
)


class TypingAssistPrefs:
    """The two check boxes, built into QUILL Lite's Preferences; :meth:`apply` on OK."""

    def __init__(self, dialog: Any, sizer: Any, settings: Any, *, pad: int = 8) -> None:
        self._settings = settings
        self.autocorrect = wx.CheckBox(dialog, label=AUTOCORRECT_LABEL)
        self.autocorrect.SetHelpText(AUTOCORRECT_HELP)
        self.autocorrect.SetValue(bool(getattr(settings, "autocorrect_misspellings", False)))
        sizer.Add(self.autocorrect, 0, wx.LEFT | wx.RIGHT, pad)
        self.lists = wx.CheckBox(dialog, label=LISTS_LABEL)
        self.lists.SetHelpText(LISTS_HELP)
        self.lists.SetValue(bool(getattr(settings, "continue_lists_in_plain_text", False)))
        sizer.Add(self.lists, 0, wx.LEFT | wx.RIGHT, pad)

    def apply(self) -> bool:
        """Write both boxes back; ``True`` when either changed."""
        before = (
            bool(getattr(self._settings, "autocorrect_misspellings", False)),
            bool(getattr(self._settings, "continue_lists_in_plain_text", False)),
        )
        self._settings.autocorrect_misspellings = bool(self.autocorrect.GetValue())
        self._settings.continue_lists_in_plain_text = bool(self.lists.GetValue())
        return before != (
            self._settings.autocorrect_misspellings,
            self._settings.continue_lists_in_plain_text,
        )
