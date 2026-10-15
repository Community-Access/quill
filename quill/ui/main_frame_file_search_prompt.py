"""The Search in Files / Replace Across Files dialog, on its own.

Split out of :mod:`quill.ui.main_frame_search` for GATE-11 (2026-09-10) and
because it is the one thing in there that is not a search: a hundred and fifty
lines of form building with two conditional rows, next to a file of one-screen
command handlers. The module it left is now commands, and this is the window
they open.

Since 2026-10-15 the window itself is ``quill/ui/file_search_prompt``, shared
with QUILL Lite; this mixin is what QUILL alone knows: the current document's
folder for the starting path, the frame for parentage, and the hardened
``_show_modal_dialog`` / ``_show_message_box`` every QUILL dialog goes through.
"""

from __future__ import annotations

from pathlib import Path

# The window and its request live in quill/ui/file_search_prompt now, shared
# with QUILL Lite (2026-10-15); the names stay importable from here.
from quill.ui.file_search_prompt import FileSearchRequest, prompt_file_search

__all__ = ["FileSearchPromptMixin", "FileSearchRequest"]


class FileSearchPromptMixin:
    """The one method, composed onto ``MainFrame`` beside the search commands."""

    def _prompt_file_search(self, *, replace: bool) -> FileSearchRequest | None:
        default_root = self.document.path.parent if self.document.path is not None else Path.cwd()
        return prompt_file_search(
            parent=self.frame,
            default_root=default_root,
            replace=replace,
            show_modal=self._show_modal_dialog,
            show_message=self._show_message_box,
            wx_module=getattr(self, "_wx", None),
        )
