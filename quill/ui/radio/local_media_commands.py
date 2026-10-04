"""Opening Local Media, and its Command Palette entries.

The doors in: Station > Local Media... (Ctrl+O), the Go To list, the Station
menu every peer window carries, the Browse branch's "Open the Local Media
Window" row and every Local Media row's "Open in Local Media Window". All of
them land here, so asking for the window when it is already open brings it to
the front -- on the playlist and item you asked from -- rather than opening a
second copy.
"""

from __future__ import annotations

from typing import Any

from quill.ui.radio import local_media_ui as ui

__all__ = ["COMMANDS", "open_window", "register"]


def open_window(host: Any, *, playlist_id: str = "", item_id: int = 0) -> Any:
    """Open the Local Media window, or bring the open one forward."""
    from quill.ui.radio.local_media_window import TITLE, LocalMediaWindow

    app = ui.app_of(host)
    for playlist in ui.library(app).playlists:
        if playlist.folder and playlist.watch:
            ui.rescan_folder(app, playlist.id, quiet=True)
    windows = getattr(app, "_windows", None)
    if windows is not None and windows.activate_title(TITLE):
        for window in ui.open_windows(app):
            if playlist_id:
                window.reload(select_playlist=playlist_id, select_item=item_id, focus="items")
        return None
    window = LocalMediaWindow(
        getattr(app, "frame", None),
        host=app,
        windows=windows,
        playlist_id=playlist_id,
        item_id=item_id,
    )
    window.show()
    return window


def _add(host: Any, *, folder: bool) -> None:
    from quill.ui.radio import local_media_browse

    local_media_browse.ACTIONS["localaddfolder" if folder else "localaddfiles"](host)


def _step(host: Any, direction: int) -> None:
    from quill.ui.radio import local_media_playback

    if not local_media_playback.step(host, direction):
        ui.announce(host, "Nothing from Local Media is playing.")


#: ``(command id, palette title, handler factory)``. Only the window has a key
#: of its own (Ctrl+O in Quill Radio); the rest are reached by name, and the
#: playing playlist's next and previous are also the chapter keys.
COMMANDS: tuple[tuple[str, str, Any], ...] = (
    ("radio.local_media", "Internet Radio: Local Media...", lambda host: open_window(host)),
    (
        "radio.local_media_add_files",
        "Local Media: Add Media Files...",
        lambda host: _add(host, folder=False),
    ),
    (
        "radio.local_media_add_folder",
        "Local Media: Add a Folder...",
        lambda host: _add(host, folder=True),
    ),
    ("radio.local_media_next", "Local Media: Next Item", lambda host: _step(host, 1)),
    ("radio.local_media_previous", "Local Media: Previous Item", lambda host: _step(host, -1)),
)


def register(host: Any) -> None:
    """Put Local Media in the Command Palette, and note the app for the player."""
    from quill.ui.radio import local_media_playback

    local_media_playback.remember_app(host)
    for command_id, title, factory in COMMANDS:
        host.commands.try_register(
            command_id,
            title,
            lambda f=factory: f(host),
            host._binding_for(command_id),
            feature_id="core.radio",
        )
