"""File > Recent Documents... in QUILL Lite: the recent list as a window.

Reported 2026-10-04: "Unless I'm missing it, the ability to open recent
documents." QUILL Lite had File > Open Recent all along, as a submenu -- which is
found only by somebody who walks the File menu and arrows onto it. This is the
same list as a window with a chord of its own, Alt+Shift+0, beside the
Alt+Shift+1 to 9 that reopen the first nine.

QUILL's half is ``quill/ui/main_frame_recent_documents.py``, on the same chord.
Both open :mod:`quill.ui.recent_documents_dialog` and keep their lists by
:mod:`quill.core.recent_documents`, so there is one window and one set of rules.
The lists themselves stay apart: QUILL Lite's is in its own settings, a record
of this install, and nothing carries it to QUILL or back.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["DocumentRecentMixin"]


class DocumentRecentMixin:
    """The Recent Documents window, and saving what it changed."""

    def cmd_recent_documents(self) -> None:
        """Open, pin, remove or clear recent documents, and set how many to keep."""
        from quill.ui.recent_documents_dialog import show_recent_documents

        settings = self.app.settings
        answer = show_recent_documents(
            self,
            list(settings.recent_files),
            list(settings.pinned_recent_files),
            limit=settings.recent_files_limit,
            auto_clear_missing=settings.recent_files_auto_clear_missing,
            announce=self._announce,
        )
        before = (
            settings.recent_files,
            settings.pinned_recent_files,
            settings.recent_files_limit,
            settings.recent_files_auto_clear_missing,
        )
        settings.recent_files = list(answer.recent)
        settings.pinned_recent_files = list(answer.pinned)
        settings.recent_files_limit = answer.limit
        settings.recent_files_auto_clear_missing = answer.auto_clear_missing
        after = (
            settings.recent_files,
            settings.pinned_recent_files,
            settings.recent_files_limit,
            settings.recent_files_auto_clear_missing,
        )
        if after != before:
            self.app.save_settings()
            self.app.refresh_all_menus()
        if answer.open_path:
            self.app.open_path(Path(answer.open_path))
            return
        self.control.SetFocus()
