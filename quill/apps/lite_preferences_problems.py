"""Preferences: which files the Problems pane lists when it opens.

QUILL's setting ``problems_all_open_files`` (Settings, Editing), under QUILL's
name, default and wording. It is the default each window starts from: View >
Problems > This File Only or All Open Files, the pane's Files chooser and F in
the pane's list switch for now without changing it.

Its own module because ``lite_preferences.py`` sits at its line cap (GATE-11).
No access key: every letter in its label is already claimed in Preferences,
and a duplicate would make Windows cycle between two controls instead of
pressing either (GATE-14); Tab reaches it.
"""

from __future__ import annotations

from typing import Any

import wx

__all__ = ["LABEL", "ProblemsPanePrefs"]

LABEL = "Problems pane lists all open files at first"

HELP = (
    "Checked, the Problems pane starts by listing the problems in every open "
    "document; cleared, just the one in front of you. Either way, View > "
    "Problems > This File Only or All Open Files, the pane's Files chooser, or F "
    "in the pane's list switches for now without changing this. QUILL has the "
    "same setting."
)


class ProblemsPanePrefs:
    """The one check box, built into QUILL Lite's Preferences; :meth:`apply` on OK."""

    def __init__(self, dialog: Any, sizer: Any, settings: Any, *, pad: int = 8) -> None:
        self._settings = settings
        self.check = wx.CheckBox(dialog, label=LABEL)
        self.check.SetHelpText(HELP)
        self.check.SetValue(bool(getattr(settings, "problems_all_open_files", False)))
        sizer.Add(self.check, 0, wx.LEFT | wx.RIGHT | wx.TOP, pad)

    def apply(self) -> bool:
        """Write the choice back; ``True`` when it changed."""
        before = bool(getattr(self._settings, "problems_all_open_files", False))
        chosen = bool(self.check.GetValue())
        self._settings.problems_all_open_files = chosen
        return before != chosen
