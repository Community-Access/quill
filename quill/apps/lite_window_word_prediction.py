"""Edit > Word Prediction... (Ctrl+.) in QUILL Lite: QUILL's list, shared.

The list, its keys and what it says are :mod:`quill.ui.suggestion_list`, the
same module QUILL's Word Prediction runs, on the same chord (rule 2). This
window supplies its text control, its spelling dictionary and its voice.

QUILL Lite opens the list only when you press the key. QUILL also has a
setting to open it as you type, off by default; QUILL Lite has no such
setting, which keeps it level with QUILL rather than ahead of it.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.ui.suggestion_list import SuggestionListMixin

__all__ = ["DocumentWordPredictionMixin"]


class DocumentWordPredictionMixin(SuggestionListMixin):
    """Word Prediction for one document window."""

    def cmd_word_prediction(self) -> None:
        """Word Prediction: suggestions for the word being typed, as a list."""
        if not self._show_intellisense_popup(manual=True):
            self._announce("No predictions available")

    def _word_prediction_key_down(self, event: Any) -> bool:
        """The control's key-down: True when the open list took the key."""
        if self._handle_intellisense_key_down(event):
            return True
        popup = self._suggest_popup(create=False)
        if popup is not None and popup.is_visible():
            # Typing or deleting with the list open narrows it, once the key
            # has reached the text.
            wx.CallAfter(self._refresh_intellisense_popup)
        return False

    # -- the shared list's hooks --------------------------------------------- #

    def _suggest_wx(self) -> Any:
        return wx

    def _suggest_parent(self) -> Any:
        return self

    def _suggest_text(self) -> str:
        return str(self.control.GetValue())

    def _suggest_caret(self) -> int:
        return int(self.control.GetInsertionPoint())

    def _suggest_replace(self, start: int, end: int, text: str) -> None:
        self.control.Replace(start, end, text)

    def _suggest_set_caret(self, offset: int) -> None:
        self.control.SetInsertionPoint(offset)
        self.control.SetSelection(offset, offset)

    def _suggest_focus_editor(self) -> None:
        self.control.SetFocus()

    def _suggest_screen_position(self) -> tuple[int, int]:
        position = self.control.GetScreenPosition()
        return (position.x + 20, position.y + 40)

    def _suggest_dictionary(self) -> set[str]:
        dictionary = getattr(self, "_spell_dictionary", None)
        return set(dictionary()) if callable(dictionary) else set()

    def _suggest_say(self, message: str) -> None:
        self._announce(message)

    def _suggest_announce(self, message: str) -> None:
        self._announce(message)
