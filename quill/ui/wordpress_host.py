"""What an editor gives the WordPress commands, so one implementation serves both.

QUILL and QUILL Lite each wrap themselves in a :class:`WordPressHost` (QUILL in
``main_frame_wordpress.py``, QUILL Lite in ``lite_window_wordpress.py``) and the
commands in :mod:`quill.ui.wordpress_commands` only ever talk to that. This is
the hosted-AI pattern again: the capability lives once, in the shared layer,
and each editor has an adapter with no commands of its own -- because a second
implementation is how "QUILL Lite may never be ahead of QUILL" gets broken
quietly (CLAUDE.md).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol


class WordPressHost(Protocol):
    #: The window dialogs are parented to.
    parent: Any

    def show_modal(self, dialog: Any, label: str) -> int:
        """Run *dialog* through the editor's own modal path."""

    def announce(self, text: str) -> None:
        """Speak and braille an outcome the screen reader would not say itself."""

    def run_task(
        self,
        name: str,
        func: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_failure: Callable[[BaseException], None],
    ) -> None:
        """Run *func* off the UI thread; call back on the UI thread."""

    def current_path(self) -> Path | None:
        """The file behind the document in front of the person, if any."""

    def current_text(self) -> str: ...

    def replace_text(self, text: str) -> None:
        """Replace the whole document as one undo step."""

    def insert_text(self, text: str) -> None:
        """Insert at the caret, replacing any selection, as one undo step."""

    def selected_text(self) -> str: ...

    def caret_offset(self) -> int: ...

    def go_to_offset(self, offset: int) -> None: ...

    def open_path(self, path: Path) -> None:
        """Open *path* in the editor, or switch to it when it is already open."""

    def save_current(self) -> bool:
        """The editor's own Save. True when the document is saved."""

    def clipboard_text(self) -> str: ...

    def set_clipboard_text(self, text: str) -> None: ...

    def open_in_browser(self, url: str) -> None: ...

    def clipboard_image_png(self) -> bytes | None:
        """The picture on the clipboard as PNG bytes, or None (wordpress.md 6.2)."""

    def ai_describe_image(
        self,
        path: Path,
        question: str,
        on_done: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> bool:
        """Ask the editor's chosen AI about a picture (6.8, 10). False: nothing was sent,
        and the editor has already said why."""

    def ai_editor(self) -> Any:
        """The editor object carrying ``HostedAiMixin`` (QUILL's main frame, a QUILL Lite
        window), for a text request to the chosen AI and its own key (6.9, 6.11)."""

    def start_repeating(self, seconds: float, callback: Callable[[], None]) -> Callable[[], None]:
        """Call *callback* on the UI thread every *seconds* until the returned stop is
        called or the window closes (autosaves and the offline queue, 9.3, 5.10)."""
