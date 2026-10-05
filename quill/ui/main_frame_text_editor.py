"""Settings > General > Windows and your files: QUILL's half of the text-editor group.

QUILL Lite had Make My Text Editor and Open Instead of Notepad first, which the
family rule does not allow: a capability the small editor has and the big one
does not is invisible, because nobody opens QUILL and notices the absence of
something they have only seen elsewhere. So the flows live in
:mod:`quill.ui.text_editor_commands` and QUILL reaches them here, with its own
profile (``quill.core.windows_editor.QUILL``: ``Quill.Document``,
``quill.exe -m quill``, and the Word, OpenDocument and EPUB types QUILL opens and
QUILL Lite does not).

Since 2026-10-03 both editors reach them from Preferences only -- the group in
:mod:`quill.ui.text_editor_prefs` -- with no menu row and no chord: somebody
looking for "open my .txt files in this" goes to Preferences, and a thing done
once when a computer is set up does not need a key (rule 9).

This module has no command of its own; if it ever grows one, the capability has
forked.
"""

from __future__ import annotations

from typing import Any

from quill.core import windows_editor
from quill.ui.text_editor_commands import TextEditorCommandsMixin

__all__ = ["TextEditorMixin"]


class TextEditorMixin(TextEditorCommandsMixin):
    """QUILL's binding of the shared Windows text-editor flows."""

    def _text_editor_profile(self) -> windows_editor.EditorProfile:
        return windows_editor.QUILL

    def _text_editor_parent(self) -> Any:
        """``MainFrame`` is a controller; its frame is the window a dialog belongs to."""
        return self.frame

    def _text_editor_refocus(self) -> None:
        self._return_focus_to_editor()

    def _add_text_editor_prefs(self, dialog: Any, panel: Any, sizer: Any, on_change: Any) -> Any:
        """Settings > General: the same group QUILL Lite's Preferences has."""
        from quill.ui.text_editor_prefs import TextEditorPrefs

        return TextEditorPrefs(
            dialog, panel, sizer, self, make_key="x", notepad_key="o", on_change=on_change
        )
