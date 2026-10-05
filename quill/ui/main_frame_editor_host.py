"""QUILL's answers to the shared editor hooks (:mod:`quill.ui.editor_host`).

QUILL's ``MainFrame`` is a controller that owns a notebook of tabs rather than
being the editor window itself, so each hook maps to the current tab's editor,
QUILL's status line (which speaks), and QUILL's modal entry. Nothing here does
any work of its own: the commands are the shared modules', and an override
that grew a command would be a second implementation of the first.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from quill.ui.editor_host import EditorHostMixin

__all__ = ["QuillEditorHostMixin"]


class QuillEditorHostMixin(EditorHostMixin):
    """Every hook, answered against QUILL's frame, current tab and settings."""

    def _host_parent(self) -> Any:
        return self.frame  # type: ignore[attr-defined]

    def _host_control(self) -> Any:
        return self.editor  # type: ignore[attr-defined]

    def _host_kind(self) -> str:
        try:
            kind = str(self._effective_markup_kind())  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001 - no document yet
            return "plain"
        return kind if kind in {"markdown", "html"} else "plain"

    def _host_path(self) -> Path | None:
        path = getattr(getattr(self, "document", None), "path", None)
        return Path(path) if path else None

    def _host_title(self) -> str:
        try:
            name = str(self._suggested_save_basename("Untitled"))  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            name = ""
        return name or super()._host_title()

    def _host_settings(self) -> Any:
        return self.settings  # type: ignore[attr-defined]

    def _host_data_dir(self) -> Path:
        from quill.core.paths import app_data_dir

        return app_data_dir()

    def _host_doc_key(self) -> int:
        return id(getattr(self, "document", None))

    def _host_say(self, message: str) -> None:
        # _set_status speaks as well as showing; a second _announce would
        # double-speak (#728).
        self._set_status(message)  # type: ignore[attr-defined]

    def _host_show_modal(self, dialog: Any, title: str) -> int:
        return int(self._show_modal_dialog(dialog, title))  # type: ignore[attr-defined]

    def _host_ask_yes_no(self, message: str, caption: str) -> bool:
        import wx

        answer = self._show_message_box(  # type: ignore[attr-defined]
            message, caption, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION
        )
        return answer in (wx.YES, wx.ID_YES)

    def _host_read_only(self) -> bool:
        try:
            return bool(self._document_is_read_only())  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            return False

    def _host_after_edit(self) -> None:
        self._browse_navigation_cache = None
        document = getattr(self, "document", None)
        if document is not None:
            document.set_text(self.editor.GetValue())  # type: ignore[attr-defined]
