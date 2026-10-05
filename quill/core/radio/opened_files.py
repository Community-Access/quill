"""Files Windows hands Quill Radio: Open with, a double-click, a right-click verb.

Somebody browsing an external drive in File Explorer picks a song, chooses Open
with > Quill Radio (or just presses Enter, once Quill Radio is their media
player), and expects to hear it. Everything that turns that hand-off into
something playing is decided here, wx-free, so it can be tested without a
window, a player or a second process:

* :func:`parse_argv` reads ``quill-radio <file> [<file> ...]`` -- paths made
  absolute, app switches set aside, ``--enqueue`` noted.
* :func:`hand_over` is what a *second* launch does when Quill Radio is already
  running: it puts each path on the running copy's queue (``quill.core.ipc``,
  the radio slot, the same queue a bare second launch has always used to say
  "come forward") and exits.
* :func:`expand` sorts what was named into files to play, playlists to import,
  and the ones that cannot be played -- with :func:`problem_sentence` to say
  why, in one plain sentence.
* :class:`OpenBatch` decides when files belong together. Explorer opens a
  multiple selection by starting the app once *per file*, a fraction of a
  second apart, so "several files at once" arrives as several requests; files
  that arrive within :data:`BATCH_SECONDS` of the last join the same list
  rather than replacing it.
* :func:`replace_opened` and :func:`append_opened` keep the **Opened files**
  playlist in Local Media: a real playlist, so Next and Previous work, marked
  :attr:`~quill.core.radio.local_media.Playlist.temporary` so the next files
  opened from File Explorer replace it -- unless Save as Playlist kept it.

No network, no registry, no wx.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.radio.local_media import (
    LocalMediaLibrary,
    Playlist,
    is_media_file,
    path_key,
)
from quill.core.radio.play_queue import REPEAT_OFF
from quill.core.windows_media import ENQUEUE_FLAG, PLAYLIST_TYPES

__all__ = [
    "BATCH_SECONDS",
    "ENQUEUE",
    "OPENED_FILES_NAME",
    "PLAY",
    "Expanded",
    "LaunchRequest",
    "OpenBatch",
    "append_opened",
    "expand",
    "find_imported",
    "hand_over",
    "opened_playlist",
    "parse_argv",
    "problem_sentence",
    "replace_opened",
    "split_requests",
]

#: The temporary playlist's name, as Local Media lists it.
OPENED_FILES_NAME = "Opened files"

#: How close together two hand-offs must be to count as one selection.
BATCH_SECONDS = 3.0

#: The queue actions a hand-off uses (``quill.core.ipc`` lowercases them).
PLAY = "play"
ENQUEUE = "enqueue"


@dataclass(frozen=True, slots=True)
class LaunchRequest:
    """What a command line asked for: these paths, played now or added."""

    paths: tuple[str, ...] = ()
    enqueue: bool = False


def parse_argv(argv: Sequence[str], *, cwd: str | None = None) -> LaunchRequest:
    """The files on a Quill Radio command line, absolute, in the order given.

    Anything starting ``--`` is a switch (``--safe-mode`` and its kin), never a
    file, so a switch Quill Radio does not know is set aside rather than being
    reported as a missing file. A relative path is taken from *cwd*, the folder
    the command was typed in.
    """
    base = cwd if cwd is not None else os.getcwd()
    paths: list[str] = []
    enqueue = False
    for raw in argv:
        word = raw.strip().strip('"').strip()
        if not word:
            continue
        if word.lower() == ENQUEUE_FLAG:
            enqueue = True
            continue
        if word.startswith("--"):
            continue
        candidate = Path(word)
        if not candidate.is_absolute():
            candidate = Path(base) / candidate
        paths.append(os.path.normpath(str(candidate)))
    return LaunchRequest(tuple(paths), enqueue)


def hand_over(
    argv: Sequence[str],
    *,
    slot: str,
    enqueue: Callable[..., None] | None = None,
    cwd: str | None = None,
) -> int:
    """Pass a second launch's files to the running Quill Radio; how many.

    With no files it is the old request, "come forward". *enqueue* is
    ``quill.core.ipc.enqueue_open_request`` unless a test supplies its own.
    """
    if enqueue is None:
        from quill.core.ipc import enqueue_open_request

        enqueue = enqueue_open_request
    request = parse_argv(argv, cwd=cwd)
    if not request.paths:
        enqueue(None, slot=slot)
        return 0
    action = ENQUEUE if request.enqueue else PLAY
    for path in request.paths:
        enqueue(Path(path), action=action, slot=slot)
    return len(request.paths)


def split_requests(requests: Iterable[object]) -> tuple[bool, list[str], list[str]]:
    """``(come forward?, paths to play, paths to add)`` from drained requests.

    A ``None`` is a bare second launch; anything with a ``path`` is a file,
    played unless its action is :data:`ENQUEUE`.
    """
    show = False
    play: list[str] = []
    add: list[str] = []
    for request in requests:
        if request is None:
            show = True
            continue
        path = getattr(request, "path", None)
        if path is None:
            continue
        action = str(getattr(request, "action", PLAY) or PLAY).lower()
        (add if action == ENQUEUE else play).append(str(path))
    return show, play, add


# --- what was named -----------------------------------------------------------------


def _exists(path: Path) -> bool:
    try:
        return path.exists()
    except OSError:
        return False


def _is_dir(path: Path) -> bool:
    try:
        return path.is_dir()
    except OSError:
        return False


@dataclass(slots=True)
class Expanded:
    """What a set of named paths turned out to hold."""

    #: Files to play, folders opened in reading order, duplicates dropped.
    media: list[str] = field(default_factory=list)
    #: M3U, M3U8 and PLS files, to import into Local Media.
    playlists: list[str] = field(default_factory=list)
    #: Named, but not there (a drive unplugged, a file moved).
    missing: list[str] = field(default_factory=list)
    #: There, but nothing Quill Radio plays.
    unsupported: list[str] = field(default_factory=list)
    #: Folders with nothing playable in them.
    empty_folders: list[str] = field(default_factory=list)


def is_playlist_file(path: Path | str) -> bool:
    return Path(path).suffix.lower() in PLAYLIST_TYPES


def expand(
    paths: Sequence[str],
    *,
    find: Callable[[Sequence[str]], Sequence[Path | str]] | None = None,
) -> Expanded:
    """Sort *paths* into what to play, import, and report (touches the disk).

    A folder plays the way Local Media's Add a Folder adds it: every playable
    file inside, subfolders too, in the order a person reads them. *find* is
    :func:`quill.core.radio.local_media_files.find_media_files` unless a test
    supplies its own.
    """
    if find is None:
        from quill.core.radio.local_media_files import find_media_files

        find = find_media_files
    result = Expanded()
    seen: set[str] = set()

    def _keep(path: str) -> None:
        key = path_key(path)
        if key not in seen:
            seen.add(key)
            result.media.append(path)

    for raw in paths:
        path = Path(raw)
        if not _exists(path):
            result.missing.append(str(path))
        elif _is_dir(path):
            found = [str(item) for item in find([str(path)])]
            if not found:
                result.empty_folders.append(str(path))
            for item in found:
                _keep(item)
        elif is_playlist_file(path):
            result.playlists.append(str(path))
        elif is_media_file(path):
            _keep(str(path))
        else:
            result.unsupported.append(str(path))
    return result


def _name(path: str) -> str:
    return Path(path).name or path


def problem_sentence(expanded: Expanded) -> str:
    """What could not be played, in plain words; "" when everything could."""
    parts: list[str] = []
    if len(expanded.missing) == 1:
        parts.append(f"Quill Radio could not find {_name(expanded.missing[0])}.")
    elif expanded.missing:
        parts.append(f"Quill Radio could not find {len(expanded.missing)} of the files.")
    if len(expanded.unsupported) == 1:
        parts.append(f"Quill Radio cannot play {_name(expanded.unsupported[0])}.")
    elif expanded.unsupported:
        parts.append(f"Quill Radio cannot play {len(expanded.unsupported)} of the files.")
    for folder in expanded.empty_folders:
        parts.append(f"There is no music or video in {_name(folder)}.")
    return " ".join(parts)


# --- the Opened files list ------------------------------------------------------------


class OpenBatch:
    """Whether a hand-off joins the one before it. Times are monotonic seconds."""

    def __init__(self, window: float = BATCH_SECONDS) -> None:
        self.window = window
        self.last: float | None = None

    def joins(self, now: float) -> bool:
        return self.last is not None and 0 <= now - self.last <= self.window

    def touch(self, now: float) -> None:
        self.last = now


def opened_playlist(library: LocalMediaLibrary) -> Playlist | None:
    """The Opened files list, if there is one."""
    for playlist in library.playlists:
        if playlist.temporary:
            return playlist
    return None


def _opened(library: LocalMediaLibrary, now: float | None) -> Playlist:
    playlist = opened_playlist(library)
    if playlist is None:
        playlist = library.add_playlist(OPENED_FILES_NAME, now=now)
        playlist.temporary = True
    return playlist


def replace_opened(
    library: LocalMediaLibrary, files: Sequence[str], *, now: float | None = None
) -> tuple[Playlist, list[int]]:
    """Make the Opened files list exactly *files*; ``(playlist, new item ids)``.

    It starts afresh: in order, not shuffled, not repeating, with nowhere to
    continue from -- these are new files, not the old list's.
    """
    playlist = _opened(library, now)
    playlist.items = []
    playlist.shuffle = False
    playlist.repeat = REPEAT_OFF
    playlist.last_item_id = 0
    playlist.folder, playlist.watch = "", False
    return playlist, _add(playlist, files, now)


def append_opened(
    library: LocalMediaLibrary, files: Sequence[str], *, now: float | None = None
) -> tuple[Playlist, list[int]]:
    """Add *files* to the end of the Opened files list, skipping ones it has."""
    playlist = _opened(library, now)
    known = playlist.paths()
    return playlist, _add(playlist, [f for f in files if path_key(f) not in known], now)


def _add(playlist: Playlist, files: Sequence[str], now: float | None) -> list[int]:
    new = [playlist.make_item(path, now=now) for path in files]
    playlist.items.extend(new)
    return [item.id for item in new]


def find_imported(library: LocalMediaLibrary, name: str, paths: Sequence[str]) -> Playlist | None:
    """A playlist this same file was already imported as, so opening it twice
    plays the one copy rather than making another."""
    keys = [path_key(path) for path in paths]
    for playlist in library.playlists:
        if playlist.temporary or playlist.name.casefold() != name.casefold():
            continue
        if [path_key(item.path) for item in playlist.items] == keys:
            return playlist
    return None
