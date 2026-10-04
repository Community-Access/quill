"""Local Media's host-side plumbing: the library, saving it, and adding files.

Every Local Media surface -- the Browse branch, its context menus, the Local
Media window, the Command Palette -- reads and changes one library object held
on the app frame, and every change goes through :func:`commit`, which saves it
and tells every open surface to catch up. That is what keeps the window and the
tree from disagreeing about what a playlist holds: there is one copy, and one
door out of it.

**Adding is two steps, and the second is in the background.** Choosing twelve
files puts twelve rows in the playlist at once, named from their file names, so
nothing waits on anything. Reading the tags -- title, artist, album, length --
happens next, off the UI thread, and the rows quietly become richer when it
finishes. A folder of four thousand files is scanned off the UI thread too: a
window that freezes while it walks a disk reads as a crash.

wx is used through the app frame's own helpers (``_show_modal_dialog`` for
every modal), never at module scope.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from quill.core.radio import local_media
from quill.core.radio.local_media import LocalMediaLibrary, Playlist

__all__ = [
    "add_paths",
    "app_of",
    "ask_files",
    "ask_folder",
    "ask_text",
    "commit",
    "confirm",
    "library",
    "notify",
    "register_window",
    "rescan_folder",
    "unregister_window",
]

#: Where the library and the open windows live on the app frame.
_LIBRARY_ATTR = "_local_media_library"
_WINDOWS_ATTR = "_local_media_windows"


def app_of(host: Any) -> Any:
    """The app frame behind *host*: itself, or the frame a surface carries."""
    if host is None:
        return None
    if hasattr(host, "_radio_controller") or hasattr(host, "_radio_history"):
        return host
    for name in ("_download_host", "_host", "_transport_host", "_app_host", "_app"):
        candidate = getattr(host, name, None)
        if candidate is not None and candidate is not host:
            return candidate
    return host


def announce(host: Any, text: str) -> None:
    speak = getattr(app_of(host), "_announce", None) or getattr(host, "_announce", None)
    if callable(speak) and text:
        speak(text)


def library(host: Any) -> LocalMediaLibrary:
    """The one library, loaded on first use and kept on the app frame."""
    app = app_of(host)
    current = getattr(app, _LIBRARY_ATTR, None)
    if isinstance(current, LocalMediaLibrary):
        return current
    loaded = local_media.load_library()
    try:
        setattr(app, _LIBRARY_ATTR, loaded)
    except AttributeError:
        pass
    return loaded


def register_window(host: Any, window: Any) -> None:
    app = app_of(host)
    windows = getattr(app, _WINDOWS_ATTR, None)
    if windows is None:
        windows = []
        setattr(app, _WINDOWS_ATTR, windows)
    if window not in windows:
        windows.append(window)


def unregister_window(host: Any, window: Any) -> None:
    windows = getattr(app_of(host), _WINDOWS_ATTR, None) or []
    if window in windows:
        windows.remove(window)


def open_windows(host: Any) -> list[Any]:
    return list(getattr(app_of(host), _WINDOWS_ATTR, None) or [])


def notify(host: Any, *, browse_select: str = "", source: Any = None) -> None:
    """Tell every open surface the library changed. *source* already knows."""
    for window in open_windows(host):
        if window is source:
            continue
        refresh = getattr(window, "reload", None)
        if callable(refresh):
            try:
                refresh()
            except Exception:  # noqa: BLE001 - a closing window must not stop the rest
                pass
    try:
        from quill.ui.radio import browse_refresh

        app = app_of(host)
        dialog = getattr(app, "_radio_browse_dialog", None)
        if dialog is not None and browse_select:
            dialog._pending_select = browse_select
        browse_refresh.reload_open_browse(app, "localmedia")
    except Exception:  # noqa: BLE001 - the tree catching up is a courtesy
        pass


def commit(host: Any, *, browse_select: str = "", source: Any = None) -> bool:
    """Save the library and bring every surface up to date. False on failure.

    A failed save is said out loud: the change is still in front of the
    listener, and "it is not saved" is the one thing they need to know.
    """
    try:
        local_media.save_library(library(host))
    except OSError as error:
        announce(host, f"Local Media could not be saved: {error}.")
        notify(host, browse_select=browse_select, source=source)
        return False
    notify(host, browse_select=browse_select, source=source)
    return True


# --- asking -------------------------------------------------------------------


def _parent(host: Any) -> Any:
    for name in ("_win", "frame", "dialog"):
        window = getattr(host, name, None)
        if window is not None:
            return window
    return getattr(app_of(host), "frame", None)


def _show(host: Any, dialog: Any, label: str) -> int:
    shower = getattr(app_of(host), "_show_modal_dialog", None)
    if callable(shower):
        return int(shower(dialog, label))
    from quill.ui.dialog_contract import show_modal_dialog

    return show_modal_dialog(dialog, label)


def ask_files(host: Any, *, title: str = "Add Media Files") -> list[str]:
    """The files somebody picks, in the order the picker gives them, or []."""
    import wx

    with wx.FileDialog(
        _parent(host),
        title,
        wildcard=local_media.OPEN_WILDCARD,
        style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST | wx.FD_MULTIPLE,
    ) as chooser:
        if _show(host, chooser, title) != wx.ID_OK:
            return []
        return [str(path) for path in chooser.GetPaths()]


def ask_folder(host: Any, *, title: str = "Add a Folder") -> str:
    """A folder somebody picks, or ""."""
    import wx

    with wx.DirDialog(_parent(host), title, style=wx.DD_DIR_MUST_EXIST) as chooser:
        if _show(host, chooser, title) != wx.ID_OK:
            return ""
        return str(chooser.GetPath())


def ask_text(host: Any, prompt: str, title: str, value: str = "") -> str | None:
    """One line of text, or ``None`` when cancelled. The platform's own prompt."""
    import wx

    with wx.TextEntryDialog(_parent(host), prompt, title, value=value) as entry:
        if _show(host, entry, title) != wx.ID_OK:
            return None
        return str(entry.GetValue()).strip()


def confirm(host: Any, question: str, title: str) -> bool:
    """Yes or No, with **No** already chosen: these questions remove things."""
    import wx

    with wx.MessageDialog(
        _parent(host), question, title, style=wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION
    ) as box:
        return _show(host, box, title) == wx.ID_YES


# --- adding ---------------------------------------------------------------------


def _submit(host: Any, name: str, work: Callable[..., Any], ok: Callable[[Any], None]) -> None:
    """Run *work* off the UI thread and *ok* on it; inline when no task manager."""
    manager = getattr(app_of(host), "_task_manager", None) or getattr(host, "_task_manager", None)
    if manager is None:
        ok(work())
        return

    def _done(_op: str, result: object) -> None:
        ok(result)

    def _failed(_op: str, error: BaseException) -> None:
        announce(host, f"That could not be finished: {error}.")

    manager.submit(name, work, on_success=_done, on_failure=_failed)


def add_paths(
    host: Any,
    paths: list[str],
    *,
    playlist_id: str = "",
    position: int | None = None,
    name: str = "",
    folder: str = "",
    then: Callable[[Playlist, list[int]], None] | None = None,
) -> None:
    """Add every playable file in *paths* (folders opened) to a playlist.

    With no *playlist_id*, a new playlist is made and named *name* -- or after
    the files' own folder, which is what anybody would have typed. *position*
    inserts before that row; ``None`` appends. *folder* makes the new playlist
    follow that folder for files added to it later.
    """
    if not paths:
        return
    if folder:
        announce(host, f"Looking for media in {Path(folder).name or folder}...")

    def _work(**_kwargs: Any) -> list[str]:
        from quill.core.radio.local_media_files import find_media_files

        return [str(path) for path in find_media_files(paths)]

    def _ok(found: object) -> None:
        files = [str(path) for path in found] if isinstance(found, list) else []
        _place(host, files, playlist_id, position, name, folder, then)

    _submit(host, "radio-local-media-scan", _work, _ok)


def _place(
    host: Any,
    files: list[str],
    playlist_id: str,
    position: int | None,
    name: str,
    folder: str,
    then: Callable[[Playlist, list[int]], None] | None,
) -> None:
    lib = library(host)
    playlist = lib.find(playlist_id) if playlist_id else None
    if not files:
        where = "that folder" if folder else "what you chose"
        announce(host, f"No music or video files were found in {where}. Nothing was added.")
        return
    from quill.core.radio.local_media_files import name_for_files

    made = playlist is None
    if playlist is None:
        playlist = lib.add_playlist(name or name_for_files(files))
        if folder:
            playlist.folder = folder
            playlist.watch = True
    from quill.core.radio import local_media_edit

    new_items = [playlist.make_item(path, title="") for path in files]
    at = len(playlist.items) if position is None else position
    playlist.items, rows = local_media_edit.insert_at(playlist.items, new_items, at)
    ids = [item.id for item in new_items]
    _remember_add(host, playlist.id, ids, made)
    commit(host, browse_select=f"localplaylist:{playlist.id}")
    count = len(new_items)
    noun = f"{count} item{'' if count == 1 else 's'}"
    if made:
        announce(host, f"Made a playlist called {playlist.name}, with {noun}.")
    elif position is None:
        announce(host, f"Added {noun} to the end of {playlist.name}.")
    else:
        announce(host, f"Inserted {noun} at {rows[0] + 1} of {len(playlist.items)}.")
    if then is not None:
        then(playlist, ids)
    read_tags_later(host, playlist.id, ids)


def _remember_add(host: Any, playlist_id: str, ids: list[int], made: bool) -> None:
    """Ctrl+Z takes an add back: the items, or the whole new playlist."""
    from quill.ui import undo_last_ui

    lib = library(host)
    playlist = lib.find(playlist_id)
    if playlist is None:
        return
    name = playlist.name

    def _undo() -> None:
        current = library(host)
        if made:
            current.playlists = [p for p in current.playlists if p.id != playlist_id]
        else:
            target = current.find(playlist_id)
            if target is not None:
                gone = set(ids)
                target.items = [item for item in target.items if item.id not in gone]
        commit(host)

    subject = f"{name} as it was" if not made else "Local Media without it"
    undo_last_ui.remember("Add", subject, "", _undo)


def read_tags_later(host: Any, playlist_id: str, ids: list[int]) -> None:
    """Read title, artist, album and length for *ids*, off the UI thread."""
    playlist = library(host).find(playlist_id)
    if playlist is None or not ids:
        return
    wanted = set(ids)
    targets = [(item.id, item.path) for item in playlist.items if item.id in wanted]

    def _work(**_kwargs: Any) -> dict[int, Any]:
        from quill.core.podcasts.local_tags import read_tags

        return {item_id: read_tags(path) for item_id, path in targets}

    def _ok(result: object) -> None:
        current = library(host).find(playlist_id)
        if current is None or not isinstance(result, dict):
            return
        changed = False
        for item in current.items:
            tags = result.get(item.id)
            if tags is None or tags.is_empty:
                continue
            item.title = tags.title or item.title
            item.artist = tags.artist or item.artist
            item.album = tags.album or item.album
            item.duration_seconds = tags.duration_seconds or item.duration_seconds
            changed = True
        if changed:
            commit(host)

    _submit(host, "radio-local-media-tags", _work, _ok)


def rescan_folder(host: Any, playlist_id: str, *, quiet: bool = False) -> None:
    """Add files that appeared in the playlist's folder since it last looked."""
    playlist = library(host).find(playlist_id)
    if playlist is None or not playlist.folder:
        return
    snapshot = Playlist(id=playlist.id, name=playlist.name, items=list(playlist.items))
    snapshot.folder = playlist.folder

    def _work(**_kwargs: Any) -> list[str]:
        from quill.core.radio.local_media_files import new_files_in

        return [str(path) for path in new_files_in(snapshot)]

    def _ok(found: object) -> None:
        files = [str(path) for path in found] if isinstance(found, list) else []
        current = library(host).find(playlist_id)
        if current is None:
            return
        if not files:
            if not quiet:
                announce(host, f"Nothing new in the folder for {current.name}.")
            return
        new_items = [current.make_item(path) for path in files]
        current.items.extend(new_items)
        commit(host)
        count = len(new_items)
        announce(
            host,
            f"{count} new file{'' if count == 1 else 's'} from the folder added to {current.name}.",
        )
        read_tags_later(host, playlist_id, [item.id for item in new_items])

    _submit(host, "radio-local-media-rescan", _work, _ok)
