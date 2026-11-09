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

from quill.ui.atomic_edit import replace_as_one_undo
from quill.ui.language_servers import LanguageServerMixin
from quill.ui.suggestion_list import SuggestionListMixin

__all__ = ["DocumentWordPredictionMixin"]


class DocumentWordPredictionMixin(LanguageServerMixin, SuggestionListMixin):
    """Word Prediction for one document window."""

    def cmd_word_prediction(self) -> None:
        """Word Prediction: suggestions for the word being typed, as a list."""
        if not self._show_intellisense_popup(manual=True):
            self._announce("No predictions available")

    def cmd_parameter_hints(self) -> None:
        """Parameter Hints: which parameter the caret is on, from the language server."""
        self._ls_parameter_hints()

    def cmd_language_servers(self) -> None:
        """Language Servers: which servers run, and what they are used for."""
        from quill.core.lsp.servers import forget_server_presence
        from quill.ui.dialog_contract import show_modal_dialog
        from quill.ui.language_servers_dialog import LanguageServersDialog

        window = LanguageServersDialog(self, self.app.settings)
        try:
            if show_modal_dialog(window.dialog, "Language Servers") != wx.ID_OK:
                return
            window.apply()
        finally:
            window.destroy()
        forget_server_presence()
        self.app._queue_settings_save()
        self._announce("Language server settings saved")

    def _ls_settings(self) -> Any:
        return self.app.settings

    def _word_prediction_key_down(self, event: Any) -> bool:
        """The control's key-down: True when the open list took the key."""
        if self._handle_intellisense_key_down(event):
            return True
        unicode_key = getattr(event, "GetUnicodeKey", lambda: 0)()
        if unicode_key in (ord("("), ord(",")):
            # Parameter hints as you type (off by default), once the key is in.
            wx.CallAfter(self._ls_after_char)
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
        # One undo step: Ctrl+Z takes the whole suggestion back, not a letter.
        replace_as_one_undo(self.control, start, end, text)

    def _suggest_set_caret(self, offset: int) -> None:
        self.control.SetInsertionPoint(offset)
        self.control.SetSelection(offset, offset)

    def _suggest_focus_editor(self) -> None:
        self.control.SetFocus()

    def _suggest_control(self) -> Any:
        return self.control

    def _suggest_window_alive(self) -> bool:
        # A closing window leaves the app's list before it is destroyed, so a
        # completion or hint that answers late finds it gone (QUILL Lite 3).
        frames = getattr(self.app, "frames", None)
        return frames is None or self in frames

    def _suggest_char_before_caret(self) -> str:
        caret = int(self.control.GetInsertionPoint())
        return str(self.control.GetRange(caret - 1, caret)) if caret > 0 else ""

    def _suggest_screen_position(self) -> tuple[int, int]:
        position = self.control.GetScreenPosition()
        return (position.x + 20, position.y + 40)

    def _suggest_dictionary(self) -> set[str]:
        dictionary = getattr(self, "_spell_dictionary", None)
        return set(dictionary()) if callable(dictionary) else set()

    def _suggest_path(self) -> Any:
        return getattr(self, "path", None)

    def _suggest_in_background(self, work: Any, done: Any) -> bool:
        from quill.apps.lite_window_open import app_task_manager

        app_task_manager(self.app).submit(
            "project-name-index",
            lambda **_kwargs: work(),
            on_success=lambda _op, result: done(result),
            on_failure=lambda _op, _error: done(None),
        )
        return True

    def _suggest_say(self, message: str) -> None:
        self._announce(message)

    def _suggest_announce(self, message: str) -> None:
        self._announce(message)
