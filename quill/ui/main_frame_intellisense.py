"""QUILL's side of Word Prediction (Ctrl+.): the hooks the shared list needs.

The list, its keys and what it says are :mod:`quill.ui.suggestion_list`,
shared with QUILL Lite. This adapter supplies the editor, the spelling
dictionary, the "as you type" setting and QUILL's status line, and nothing
else: a second implementation here is how the two editors would drift.
"""

from __future__ import annotations

from typing import Any

from quill.platform.sr_announce import announce
from quill.ui.suggestion_list import SuggestionListMixin


class IntellisensePopupMixin(SuggestionListMixin):
    # Host-provided by MainFrame: type-only annotations, never method stubs.
    _wx: Any
    frame: Any
    editor: Any
    settings: Any
    _set_status: Any
    _spell_dictionary: Any

    def _suggest_wx(self) -> Any:
        return self._wx

    def _suggest_parent(self) -> Any:
        return self.frame

    def _suggest_text(self) -> str:
        return str(self.editor.GetValue())

    def _suggest_caret(self) -> int:
        return int(self.editor.GetInsertionPoint())

    def _suggest_replace(self, start: int, end: int, text: str) -> None:
        self.editor.Replace(start, end, text)

    def _suggest_set_caret(self, offset: int) -> None:
        self.editor.SetInsertionPoint(offset)
        self.editor.SetSelection(offset, offset)

    def _suggest_focus_editor(self) -> None:
        if self.editor is not None:
            self.editor.SetFocus()

    def _suggest_screen_position(self) -> tuple[int, int]:
        editor_pos = self.editor.GetScreenPosition()
        return (editor_pos.x + 20, editor_pos.y + 40)

    def _suggest_dictionary(self) -> set[str]:
        return set(self._spell_dictionary())

    def _suggest_path(self) -> Any:
        return getattr(getattr(self, "document", None), "path", None)

    def _suggest_as_you_type(self) -> bool:
        if not getattr(self.settings, "intellisense_as_you_type", False):
            return False
        # A list that opens on its own is the part a profile can switch off;
        # the one you ask for with Ctrl+. is in every profile (decision 1).
        feature_enabled = getattr(self, "_feature_enabled", None)
        return not callable(feature_enabled) or bool(feature_enabled("core.intellisense"))

    def _suggest_in_background(self, work: Any, done: Any) -> bool:
        manager = getattr(self, "_task_manager", None)
        if manager is None:
            return False
        manager.submit(
            name="project-name-index",
            func=lambda **_kwargs: work(),
            on_success=lambda _op, result: done(result),
            on_failure=lambda _op, _error: done(None),
        )
        return True

    def _suggest_say(self, message: str) -> None:
        self._set_status(message)

    def _suggest_announce(self, message: str) -> None:
        announce(message)
