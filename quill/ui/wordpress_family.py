"""WordPress for the family apps with no editor: QUILL Cast, QUILL Studio, Quill Converter.

The same shared commands QUILL and QUILL Lite run (wordpress.md 15 item 9),
through a host whose window is the app's own and whose "open this document"
hands the finished draft to QUILL. There is no second implementation here: an
app calls :func:`post_episode` or :func:`upload_to_wordpress`, and the work is
:meth:`~quill.ui.wordpress_listen_pages.WordPressListenPages.post_episode` and
:meth:`~quill.ui.wordpress_listen_pages.WordPressListenPages.upload_file`.

These apps cannot open a QUILL editor window in their own process, so a post
is written as an ordinary **local WordPress draft** -- the same file QUILL and
QUILL Lite list under File > WordPress > Open Local Draft -- and QUILL is
started with it when it is installed. When it is not, the app says where the
draft waits.
"""

from __future__ import annotations

import webbrowser
from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.wordpress.episode import Episode

WHERE_THE_DRAFT_IS = (
    "The draft is waiting in QUILL and QUILL Lite, under File, WordPress, Open Local Draft."
)


class FamilyWordPressHost:
    """An app built on ``AppShellFrame``, as the shared WordPress commands see it."""

    def __init__(self, app: Any, *, launch: Callable[[Path], bool] | None = None) -> None:
        self._app = app
        self._launch = launch or _open_in_quill

    @property
    def parent(self) -> Any:
        return self._app.frame

    def show_modal(self, dialog: Any, label: str) -> int:
        return int(self._app._show_modal_dialog(dialog, label))

    def announce(self, text: str) -> None:
        self._app._announce(text)

    def run_task(
        self,
        name: str,
        func: Callable[[], Any],
        on_success: Callable[[Any], None],
        on_failure: Callable[[BaseException], None],
    ) -> None:
        self._app._task_manager.submit(
            name,
            lambda **_kw: func(),
            on_success=lambda _op, result: on_success(result),
            on_failure=lambda _op, exc: on_failure(exc),
        )

    # -- no editor here ----------------------------------------------------- #

    def current_path(self) -> Path | None:
        return None

    def current_text(self) -> str:
        return ""

    def replace_text(self, text: str) -> None:
        del text

    def insert_text(self, text: str) -> None:
        del text

    def selected_text(self) -> str:
        return ""

    def caret_offset(self) -> int:
        return 0

    def go_to_offset(self, offset: int) -> None:
        del offset

    def open_path(self, path: Path) -> None:
        """Hand a finished draft to QUILL, or say where it waits."""
        if not self._launch(path):
            self.announce(WHERE_THE_DRAFT_IS)

    def save_current(self) -> bool:
        return True

    def clipboard_text(self) -> str:
        from quill.ui.main_frame_wordpress import read_clipboard_text

        return str(read_clipboard_text())

    def set_clipboard_text(self, text: str) -> None:
        from quill.ui.main_frame_wordpress import write_clipboard_text

        write_clipboard_text(text)

    def open_in_browser(self, url: str) -> None:
        webbrowser.open(url)


def _open_in_quill(path: Path) -> bool:
    from quill.core.app_launcher import launch_app

    return bool(launch_app("quill", extra_args=(str(path),)))


def commands_for(app: Any) -> Any:
    """The shared commands on *app*, made once and kept on it."""
    commands = getattr(app, "_wordpress_family_commands", None)
    if commands is None:
        from quill.ui.wordpress_commands import WordPressCommands

        commands = WordPressCommands(FamilyWordPressHost(app))
        app._wordpress_family_commands = commands
    return commands


SAFE_MODE_SENTENCE = "WordPress is off in Safe Mode. Start the app normally to use it."


def post_episode(app: Any, episode: Episode | None) -> None:
    if getattr(app, "_safe_mode", False):
        app._announce(SAFE_MODE_SENTENCE)
        return
    if episode is None:
        app._announce("Choose an episode first, then Post This Episode.")
        return
    commands_for(app).post_episode(episode)


def upload_to_wordpress(app: Any, paths: list[Path] | None) -> None:
    if getattr(app, "_safe_mode", False):
        app._announce(SAFE_MODE_SENTENCE)
        return
    if not paths:
        app._announce("Choose a file first, then Upload to WordPress.")
        return
    commands_for(app).upload_files(list(paths))
