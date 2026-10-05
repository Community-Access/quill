"""Playing what File Explorer hands Quill Radio, in the running window.

The decisions -- what a command line names, which files belong together, what
the Opened files list holds -- are in :mod:`quill.core.radio.opened_files`.
This module only acts on them: it looks at the disk off the UI thread (an
external drive can take a moment to answer), puts the files in Local Media's
Opened files list, starts the first, and says what is playing **once**.

Two ways in, one path:

* :func:`open_launch_files` -- the files this copy of Quill Radio was started
  with, after its window is up.
* :func:`drain_requests` -- the radio IPC queue, polled by the running window:
  a second launch's files (Open with, a double-click, Play with Quill Radio),
  or a bare second launch asking the window to come forward.

Files opened while Quill Radio is already running do not pull its window in
front of File Explorer: somebody picking songs from a drive wants to keep
picking, and the speech tells them it worked.
"""

from __future__ import annotations

import time
from typing import Any

from quill.core.radio import opened_files
from quill.core.radio.local_media import Playlist
from quill.core.radio.opened_files import Expanded
from quill.ui.radio import local_media_ui as ui

__all__ = ["drain_requests", "open_launch_files", "open_paths"]

#: Where the batch clock lives on the app frame.
_BATCH_ATTR = "_opened_files_batch"


def _batch(app: Any) -> opened_files.OpenBatch:
    batch = getattr(app, _BATCH_ATTR, None)
    if not isinstance(batch, opened_files.OpenBatch):
        batch = opened_files.OpenBatch()
        try:
            setattr(app, _BATCH_ATTR, batch)
        except AttributeError:
            pass
    return batch


def drain_requests(app: Any, slot: str, *, drain: Any = None) -> None:
    """Act on everything a second launch queued since the last look."""
    if drain is None:
        from quill.core.ipc import drain_open_requests

        drain = drain_open_requests
    requests = drain(slot=slot)
    if not requests:
        return
    show, play, add = opened_files.split_requests(requests)
    if play:
        open_paths(app, play)
    if add:
        open_paths(app, add, enqueue=True)
    if show and not (play or add):
        app._foreground_window()


def open_launch_files(app: Any, request: opened_files.LaunchRequest) -> None:
    """The files Quill Radio was started with, once its window is up."""
    if request.paths:
        open_paths(app, list(request.paths), enqueue=request.enqueue)


def open_paths(app: Any, paths: list[str], *, enqueue: bool = False) -> None:
    """Look at *paths* off the UI thread, then play or add what is there."""
    arrived = time.monotonic()

    def _work(**_kwargs: Any) -> Expanded:
        return opened_files.expand(paths)

    def _ok(result: object) -> None:
        if isinstance(result, Expanded):
            place(app, result, enqueue=enqueue, now=arrived)

    ui._submit(app, "radio-opened-files", _work, _ok)


def _import(app: Any, path: str) -> Playlist | None:
    """An M3U, M3U8 or PLS as a Local Media playlist, or None when it holds no files.

    Opening the same playlist file again finds the copy it made last time.
    """
    from pathlib import Path

    from quill.core.radio.local_media_files import read_playlist_file

    source = Path(path)
    try:
        entries, _skipped = read_playlist_file(source)
    except OSError:
        return None
    if not entries:
        return None
    lib = ui.library(app)
    existing = opened_files.find_imported(lib, source.stem, [entry.path for entry in entries])
    if existing is not None:
        return existing
    playlist = lib.add_playlist(source.stem)
    for entry in entries:
        playlist.items.append(
            playlist.make_item(
                entry.path, title=entry.title, duration_seconds=entry.duration_seconds
            )
        )
    return playlist


def place(app: Any, expanded: Expanded, *, enqueue: bool = False, now: float = 0.0) -> None:
    """Put what was found where it belongs, start it, and say so once."""
    from quill.ui.radio import local_media_playback as playback

    lib = ui.library(app)
    problems = opened_files.problem_sentence(expanded)
    imported = [p for p in (_import(app, path) for path in expanded.playlists) if p is not None]
    if len(imported) < len(expanded.playlists):
        problems = _join(problems, "A playlist file named no music or video on this computer.")
    if not expanded.media:
        if not imported:
            ui.announce(app, problems or "There was nothing there Quill Radio can play.")
            return
        ui.commit(app, browse_select=f"localplaylist:{imported[0].id}")
        if playback.play_playlist(app, imported[0].id) and problems:
            ui.announce(app, problems)
        return
    for playlist in imported:
        problems = _join(problems, f"{playlist.name} is in Local Media too.")
    if enqueue:
        playlist, ids = opened_files.append_opened(lib, expanded.media)
        _save(app, playlist)
        if not ids:
            ui.announce(app, f"Those files are already in {playlist.name}.")
            return
        if _something_playing(app):
            where = (
                "to the end of the list playing now"
                if _opened_is_playing(app)
                else f"to {playlist.name} in Local Media. They play when you play that list"
            )
            # announce-punctuation: exempt -- each part is a whole sentence
            ui.announce(app, f"Added {_count(len(ids))} {where}.{_tail(problems)}")
            ui.read_tags_later(app, playlist.id, ids)
            return
    else:
        batch = _batch(app)
        joins = batch.joins(now)
        batch.touch(now)
        if joins:
            playlist, ids = opened_files.append_opened(lib, expanded.media)
            _save(app, playlist)
            if _something_playing(app):
                # The rest of one selection: already said, so only trouble is news.
                if problems:
                    ui.announce(app, problems)
                ui.read_tags_later(app, playlist.id, ids)
                return
        else:
            playlist, ids = opened_files.replace_opened(lib, expanded.media)
            _save(app, playlist)
    _start(app, playlist, ids, problems)


def _save(app: Any, playlist: Any) -> None:
    from quill.ui.radio import local_media_playback as playback

    ui.commit(app, browse_select=f"localplaylist:{playlist.id}")
    playback.sync(app, playlist.id)


def _join(first: str, second: str) -> str:
    return f"{first} {second}" if first else second


def _tail(problems: str) -> str:
    return f" {problems}" if problems else ""


def _start(app: Any, playlist: Any, ids: list[int], problems: str) -> None:
    """Play the first of *ids* that is there, and say what is playing, once."""
    from quill.ui.radio import local_media_playback as playback

    first = None
    for item_id in ids:
        item = playlist.find(item_id)
        if item is not None and item.exists():
            first = item
            break
    if first is None or not playback.play_item(app, playlist.id, first.id, quiet=True):
        ui.announce(app, problems or "None of those files could be played.")
        return
    lead = f"Playing {first.spoken()}"
    if len(ids) > 1:
        lead += f", the first of {len(ids)} in {playlist.name}"
    # announce-punctuation: exempt -- each part is a whole sentence
    ui.announce(app, f"{lead}.{_tail(problems)}")
    ui.read_tags_later(app, playlist.id, ids)


def _count(number: int) -> str:
    return f"{number} file{'' if number == 1 else 's'}"


def _something_playing(app: Any) -> bool:
    from quill.ui.radio import local_media_playback as playback

    controller = playback.controller_of(app)
    return controller is not None and playback.is_live(controller)


def _opened_is_playing(app: Any) -> bool:
    """Whether what plays now is an item of the Opened files list."""
    from quill.ui.radio import local_media_playback as playback

    playlist, _item = playback.current(app)
    return playlist is not None and playlist.temporary
