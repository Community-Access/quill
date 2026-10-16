"""Preferences: whether the clipboard collector saves as it collects.

QUILL's setting ``clipboard_collector_saves`` (Settings, Editing), under QUILL's
name and default, for the collector QUILL Lite gained on 2026-10-15
(``lite_clipboard_collector.py``). On: a document with a file name is saved
quietly after each clip and says "Collected and saved". Off: collected text
waits for Ctrl+S.

Its own module because ``lite_preferences.py`` sits at the line cap (GATE-11).
Built into that window directly under "Keep everything I copy in the clip
library", the other question about what happens to what you copy. Access key
Y, from "every": every other letter in the label is already claimed in
Preferences, and Windows cycles between two controls with one key instead of
pressing either (GATE-14).
"""

from __future__ import annotations

from typing import Any

import wx

__all__ = ["CollectorSavePrefs"]

LABEL = "Save after ever&y clip the clipboard collector adds"

HELP = (
    "On: while the clipboard collector is on, each piece of text it adds is "
    "followed by a quiet save, and you hear one sentence, Collected and saved. "
    "Only a document that already has a file name is saved; an untitled one "
    "just collects, and no Save As window ever opens. If the save cannot happen "
    "you are told why, and collecting carries on. Off: collected text waits for "
    "you to save. QUILL has the same setting."
)


class CollectorSavePrefs:
    """The one check box, built into QUILL Lite's Preferences; :meth:`apply` on OK."""

    def __init__(self, dialog: Any, sizer: Any, settings: Any, *, pad: int = 8) -> None:
        self._settings = settings
        self.check = wx.CheckBox(dialog, label=LABEL)
        self.check.SetHelpText(HELP)
        self.check.SetValue(bool(getattr(settings, "clipboard_collector_saves", True)))
        sizer.Add(self.check, 0, wx.LEFT | wx.RIGHT, pad)

    def apply(self) -> bool:
        """Write the box back; ``True`` when it changed."""
        before = bool(getattr(self._settings, "clipboard_collector_saves", True))
        self._settings.clipboard_collector_saves = bool(self.check.GetValue())
        return before != self._settings.clipboard_collector_saves
