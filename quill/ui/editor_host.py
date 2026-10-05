"""The handful of questions shared editor commands ask "the editor".

Inline notes, Toggle Task Done and Export as HTML run the same code in QUILL
and QUILL Lite (the family rule: QUILL Lite is never ahead of QUILL, and a
second implementation is how that rule gets broken quietly). The two windows
differ in a few small ways -- which control the text is in, how a sentence is
spoken, how a question is asked -- and this mixin is those differences, named
once, so the shared modules never have to know which editor they are in.

The defaults are QUILL Lite's, because its document window *is* the editor:
``self.control``, ``self._announce``, ``self.app``. QUILL's ``MainFrame`` is a
controller that owns its editor, and answers each hook in
:mod:`quill.ui.main_frame_editor_host`. The same arrangement as the hosted AI
(:mod:`quill.ui.hosted_ai_commands`).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = ["EditorHostMixin"]


class EditorHostMixin:
    """Hooks with QUILL Lite's answers; QUILL overrides every one."""

    def _host_parent(self) -> Any:
        """The window dialogs are parented to."""
        return self

    def _host_control(self) -> Any:
        """The text control the document is in."""
        return self.control  # type: ignore[attr-defined]

    def _host_kind(self) -> str:
        """``"markdown"``, ``"html"`` or ``"plain"``: what the document is written in."""
        surface = self.markup_surface()  # type: ignore[attr-defined]
        return surface if surface in {"markdown", "html"} else "plain"

    def _host_path(self) -> Path | None:
        path = getattr(self, "path", None)
        return Path(path) if path else None

    def _host_title(self) -> str:
        """A name for the document, for a page title or an export heading."""
        path = self._host_path()
        return path.stem if path is not None else "Untitled"

    def _host_settings(self) -> Any:
        return self.app.settings  # type: ignore[attr-defined]

    def _host_data_dir(self) -> Path:
        return Path(self.app.data_dir)  # type: ignore[attr-defined]

    def _host_say(self, message: str) -> None:
        """Speak an outcome and show it in the status bar."""
        self._announce(message)  # type: ignore[attr-defined]

    def _host_show_modal(self, dialog: Any, title: str) -> int:
        from quill.ui.dialog_contract import show_modal_dialog

        return int(show_modal_dialog(dialog, title))

    def _host_ask_yes_no(self, message: str, caption: str) -> bool:
        """A Yes/No question with **No** as the default, so Enter is safe."""
        import wx

        from quill.ui.dialog_contract import show_message_box

        answer = show_message_box(
            message, caption, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION, self._host_parent()
        )
        return answer in (wx.YES, wx.ID_YES)

    def _host_read_only(self) -> bool:
        return False

    def _host_after_edit(self) -> None:
        """Mark the document changed after a programmatic edit."""
        set_modified = getattr(self, "_set_modified", None)
        if callable(set_modified):
            set_modified(True)
        touch = getattr(self, "_touch_status", None)
        if callable(touch):
            touch()

    def _host_language(self) -> str:
        """A BCP 47 language tag for an exported page's ``lang`` attribute."""
        settings = self._host_settings()
        for name in ("spell_language", "spellcheck_language", "language"):
            value = str(getattr(settings, name, "") or "").strip()
            if value and value.lower() not in {"auto", "system", "default"}:
                return value.replace("_", "-")
        return "en"
