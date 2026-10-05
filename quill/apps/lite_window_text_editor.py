"""Preferences > Windows and your files: QUILL Lite's half of the text-editor group.

QUILL Lite's binding of the shared flows in
:mod:`quill.ui.text_editor_commands`, which QUILL runs too
(:mod:`quill.ui.main_frame_text_editor`). Both editors reach them from
Preferences only (:mod:`quill.ui.text_editor_prefs`), with no menu row and no
chord, since 2026-10-03. Nothing here decides anything: it
names QUILL Lite's profile and routes the dialog, the system seam and the
launcher through this module's own names, which is what QUILL Lite's tests
replace. A command added here instead of in the shared module would be QUILL
Lite ahead of QUILL again.
"""

from __future__ import annotations

from typing import Any

from quill.core import windows_editor as _shared_editor
from quill.platform.windows import editor_registration as system
from quill.ui.dialog_contract import show_message_box
from quill.ui.text_editor_commands import TextEditorCommandsMixin, launcher

__all__ = ["DocumentTextEditorMixin"]


def _launcher() -> tuple[list[str], str]:
    """``(argv that starts QUILL Lite, DefaultIcon string)`` for the running copy."""
    return launcher(_shared_editor.QUILL_LITE)


class DocumentTextEditorMixin(TextEditorCommandsMixin):
    """The two text-editor flows, as QUILL Lite's document window runs them."""

    def _text_editor_profile(self) -> _shared_editor.EditorProfile:
        return _shared_editor.QUILL_LITE

    def _text_editor_system(self) -> Any:
        return system

    def _text_editor_launcher(self) -> tuple[list[str], str]:
        return _launcher()

    def _text_editor_ask(self, text: str, caption: str, style: int) -> int:
        return show_message_box(text, caption, style, self._text_editor_owner())
