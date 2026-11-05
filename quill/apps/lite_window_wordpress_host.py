"""QUILL Lite's window, as the shared WordPress commands see it (wordpress.md 11).

Split from ``lite_window_wordpress.py`` under GATE-11: the host is how the
shared commands reach a Lite window; the rows that hand off to them are there.
"""

from __future__ import annotations

import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any


class LiteWordPressHost:
    """A QUILL Lite document window, as the shared WordPress commands see it."""

    def __init__(self, window: Any) -> None:
        self._w = window

    @property
    def parent(self) -> Any:
        return self._w

    def show_modal(self, dialog: Any, label: str) -> int:
        from quill.ui.dialog_contract import show_modal_dialog

        return int(show_modal_dialog(dialog, label))

    def announce(self, text: str) -> None:
        self._w._announce(text)

    def run_task(
        self,
        name: str,
        func: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_failure: Callable[[BaseException], None],
    ) -> None:
        from quill.apps.lite_window_open import app_task_manager

        app_task_manager(self._w.app).submit(
            name,
            lambda **_kw: func(),
            on_success=lambda _op, result: on_success(result),
            on_failure=lambda _op, exc: on_failure(exc),
        )

    def current_path(self) -> Path | None:
        path = getattr(self._w, "path", None)
        return Path(path) if path else None

    def current_text(self) -> str:
        return str(self._w.control.GetValue())

    def replace_text(self, text: str) -> None:
        control = self._w.control
        control.SetSelection(0, control.GetLastPosition())
        control.WriteText(text)

    def insert_text(self, text: str) -> None:
        self._w.control.WriteText(text)

    def selected_text(self) -> str:
        return str(self._w.control.GetStringSelection())

    def caret_offset(self) -> int:
        return int(self._w.control.GetInsertionPoint())

    def go_to_offset(self, offset: int) -> None:
        control = self._w.control
        control.SetInsertionPoint(offset)
        control.ShowPosition(offset)
        control.SetFocus()

    def open_path(self, path: Path) -> None:
        self._w.app.open_path(path)

    def save_current(self) -> bool:
        self._w.cmd_save()
        control = self._w.control
        is_modified = getattr(control, "IsModified", None)
        return not bool(is_modified()) if callable(is_modified) else True

    def clipboard_text(self) -> str:
        from quill.ui.main_frame_wordpress import read_clipboard_text

        return read_clipboard_text()

    def set_clipboard_text(self, text: str) -> None:
        from quill.ui.main_frame_wordpress import write_clipboard_text

        write_clipboard_text(text)

    def open_in_browser(self, url: str) -> None:
        webbrowser.open(url)

    def clipboard_image_png(self) -> bytes | None:
        from quill.ui.wordpress_media_host import read_clipboard_png

        return read_clipboard_png()

    def ai_describe_image(
        self,
        path: Path,
        question: str,
        on_done: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> bool:
        from quill.ui.wordpress_media_host import ask_editor_ai

        return ask_editor_ai(self._w, path, question, on_done, on_error)

    def ai_editor(self) -> Any:
        return self._w

    def start_repeating(self, seconds: float, callback: Callable[[], None]) -> Callable[[], None]:
        from quill.ui.main_frame_wordpress import start_wx_repeating

        return start_wx_repeating(self._w, seconds, callback)
