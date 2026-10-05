"""Local Media: playlists of audio and video files on this computer.

Quill Radio could already play one file -- a recording, a downloaded episode, a
book chapter -- but it had nowhere to keep *your own* music, audiobooks and
talks, and no way to play forty of them in an order you chose. This module is
the shelf: named playlists, each an ordered list of files, kept in one small
versioned JSON file.

Three rules shape everything here.

**Paths, never contents.** A playlist stores where each file is, plus the tags
read from it once (title, artist, album, length) so a row can be spoken without
opening the file again. Nothing is copied, moved or written into the listener's
own files -- removing an item from a playlist never deletes anything from disk.

**A missing file is a fact, not an error.** A drive unplugged, a folder renamed:
the item stays where it was in the list and is *said* to be missing, so the
listener can Locate it or remove the missing items in one go. Silently dropping
it would lose their order the first time a USB stick was not in.

**Item ids are stable integers within a playlist.** Reordering, shuffling and
undo all address an item by id rather than by row, because the row an item is
on is exactly what an edit changes. Integers rather than strings because the
shared :class:`~quill.core.radio.play_queue.PlayQueue` -- the same shuffle and
repeat rules the Recordings list uses -- orders integers.

wx-free, strict-typed. No network: everything here is a path on this machine.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.radio.downloaded_books import AUDIO_SUFFIXES as _BOOK_AUDIO
from quill.core.radio.play_queue import (
    REPEAT_ALL,
    REPEAT_OFF,
    REPEAT_ONE,
    normalize_repeat_mode,
)

__all__ = [
    "AUDIO_SUFFIXES",
    "FILE_NAME",
    "MEDIA_SUFFIXES",
    "OPEN_WILDCARD",
    "REPEAT_LABELS",
    "SCHEMA_VERSION",
    "SOURCE_LABEL",
    "VIDEO_SUFFIXES",
    "LocalMediaLibrary",
    "MediaItem",
    "Playlist",
    "is_media_file",
    "load_library",
    "parse",
    "path_key",
    "save_library",
    "serialize",
    "summary",
    "title_from_filename",
]

#: The store, beside Quill Radio's other small files in the data folder.
FILE_NAME = "radio-local-media.json"

#: The on-disk shape this build writes. 1 is the first shipped shape; a file
#: with no stamp is the pre-release shape (bare path strings) and is migrated.
SCHEMA_VERSION = 1

#: ``RadioStation.source`` for anything played from here, so the details panel
#: and the status line say where it came from.
SOURCE_LABEL = "Local Media"

#: Everything Quill Radio's players can open as sound. The book list is the
#: base on purpose -- one list of "audio Quill Radio plays", not two that drift.
AUDIO_SUFFIXES: frozenset[str] = frozenset(
    _BOOK_AUDIO | {".aif", ".aiff", ".mka", ".ac3", ".mp2", ".m4r", ".ape", ".wv"}
)

#: Video files: mpv plays their sound, and Show Video (Ctrl+Shift+V) shows the
#: picture, exactly as it does for a YouTube video.
VIDEO_SUFFIXES: frozenset[str] = frozenset({
    ".mp4",
    ".m4v",
    ".mkv",
    ".webm",
    ".mov",
    ".avi",
    ".wmv",
    ".mpg",
    ".mpeg",
    ".ts",
})

MEDIA_SUFFIXES: frozenset[str] = AUDIO_SUFFIXES | VIDEO_SUFFIXES


def _wildcard_patterns(suffixes: Iterable[str]) -> str:
    return ";".join(f"*{suffix}" for suffix in sorted(suffixes))


#: The Add Media Files picker. "Audio and video" first because that is what
#: somebody opening it is looking for; each kind on its own after it.
OPEN_WILDCARD = (
    f"Audio and video files|{_wildcard_patterns(MEDIA_SUFFIXES)}"
    f"|Audio files|{_wildcard_patterns(AUDIO_SUFFIXES)}"
    f"|Video files|{_wildcard_patterns(VIDEO_SUFFIXES)}"
    "|All files (*.*)|*.*"
)

#: What each repeat mode is called out loud, for a playlist rather than for the
#: recordings list (whose labels name recordings).
REPEAT_LABELS: dict[str, str] = {
    REPEAT_OFF: "Repeat off",
    REPEAT_ALL: "Repeat the whole playlist",
    REPEAT_ONE: "Repeat this item",
}


def is_media_file(path: Path | str) -> bool:
    """Whether *path* has an extension Quill Radio can play (pure)."""
    return Path(path).suffix.lower() in MEDIA_SUFFIXES


def title_from_filename(path: Path | str) -> str:
    """A readable title from a file name: ``03_my-song.mp3`` -> ``03 my song``.

    The fallback for a file with no title tag. Underscores and dashes between
    words read as words; the number stays, because "3" in a track name is
    usually the order somebody meant.
    """
    stem = Path(path).stem
    cleaned = stem.replace("_", " ").replace(" - ", " -- ")
    words = " ".join(cleaned.split())
    return words or Path(path).name


def _speak_duration(seconds: float) -> str:
    from quill.core.speech_text import speak_duration

    return speak_duration(seconds)


def clock_length(seconds: int) -> str:
    """A length for a column: ``3:07`` or ``1:02:03``; blank when unknown."""
    if seconds <= 0:
        return ""
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


@dataclass(slots=True)
class MediaItem:
    """One file in one playlist, and what it said about itself."""

    id: int
    path: str
    title: str = ""
    artist: str = ""
    album: str = ""
    duration_seconds: int = 0
    added_at: float = 0.0

    @property
    def display_title(self) -> str:
        """The title tag, else a title made from the file name."""
        return self.title or title_from_filename(self.path)

    @property
    def file_name(self) -> str:
        return Path(self.path).name

    @property
    def folder(self) -> str:
        return str(Path(self.path).parent)

    def exists(self) -> bool:
        """Whether the file is still there. Never raises."""
        try:
            return Path(self.path).is_file()
        except OSError:
            return False

    @property
    def is_video(self) -> bool:
        return Path(self.path).suffix.lower() in VIDEO_SUFFIXES

    def spoken(self) -> str:
        """The title, and who it is by when that is known: "Song by Artist"."""
        return f"{self.display_title} by {self.artist}" if self.artist else self.display_title

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"id": self.id, "path": self.path}
        for name in ("title", "artist", "album"):
            value = getattr(self, name)
            if value:
                data[name] = value
        if self.duration_seconds:
            data["duration_seconds"] = self.duration_seconds
        if self.added_at:
            data["added_at"] = round(self.added_at, 3)
        return data


@dataclass(slots=True)
class Playlist:
    """A named, ordered list of files, and how it likes to be played."""

    id: str
    name: str
    items: list[MediaItem] = field(default_factory=list)
    next_item_id: int = 1
    #: The folder this playlist was made from, when it was. With ``watch`` on,
    #: new files that appear there are added whenever the playlist is opened.
    folder: str = ""
    watch: bool = False
    shuffle: bool = False
    repeat: str = REPEAT_OFF
    #: The item that last started playing, for Continue Where I Left Off.
    last_item_id: int = 0
    created_at: float = 0.0
    #: The Opened files list: what File Explorer last handed Quill Radio. The
    #: next files opened that way replace it, until Save as Playlist keeps it.
    temporary: bool = False

    # -- items ------------------------------------------------------------------

    def make_item(
        self,
        path: Path | str,
        *,
        title: str = "",
        artist: str = "",
        album: str = "",
        duration_seconds: int = 0,
        now: float | None = None,
    ) -> MediaItem:
        """A new item with the next free id. Not added to the list."""
        item = MediaItem(
            id=self.next_item_id,
            path=str(path),
            title=title,
            artist=artist,
            album=album,
            duration_seconds=max(0, int(duration_seconds)),
            added_at=time.time() if now is None else now,
        )
        self.next_item_id += 1
        return item

    def find(self, item_id: int) -> MediaItem | None:
        for item in self.items:
            if item.id == item_id:
                return item
        return None

    def index_of(self, item_id: int) -> int:
        for index, item in enumerate(self.items):
            if item.id == item_id:
                return index
        return -1

    def ids(self) -> list[int]:
        return [item.id for item in self.items]

    def paths(self) -> set[str]:
        return {path_key(item.path) for item in self.items}

    def total_seconds(self) -> int:
        return sum(item.duration_seconds for item in self.items)

    def missing(self) -> list[MediaItem]:
        return [item for item in self.items if not item.exists()]

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "items": [item.to_dict() for item in self.items],
            "next_item_id": self.next_item_id,
        }
        if self.folder:
            data["folder"] = self.folder
        if self.watch:
            data["watch"] = True
        if self.shuffle:
            data["shuffle"] = True
        if self.repeat != REPEAT_OFF:
            data["repeat"] = self.repeat
        if self.last_item_id:
            data["last_item_id"] = self.last_item_id
        if self.created_at:
            data["created_at"] = round(self.created_at, 3)
        if self.temporary:
            data["temporary"] = True
        return data


def path_key(path: str) -> str:
    """A path as Windows compares it: case-folded, one kind of slash."""
    return str(path).replace("/", "\\").casefold()


@dataclass(slots=True)
class LocalMediaLibrary:
    """Every playlist, in the listener's order."""

    playlists: list[Playlist] = field(default_factory=list)

    def find(self, playlist_id: str) -> Playlist | None:
        for playlist in self.playlists:
            if playlist.id == playlist_id:
                return playlist
        return None

    def index_of(self, playlist_id: str) -> int:
        for index, playlist in enumerate(self.playlists):
            if playlist.id == playlist_id:
                return index
        return -1

    def unique_name(self, wanted: str) -> str:
        """*wanted*, or "*wanted* 2" when a playlist already has that name."""
        base = " ".join((wanted or "").split()) or "My Playlist"
        taken = {playlist.name.casefold() for playlist in self.playlists}
        if base.casefold() not in taken:
            return base
        number = 2
        while f"{base} {number}".casefold() in taken:
            number += 1
        return f"{base} {number}"

    def add_playlist(self, name: str, *, now: float | None = None) -> Playlist:
        """A new, empty playlist at the end, with a name nobody else has."""
        playlist = Playlist(
            id=uuid.uuid4().hex[:12],
            name=self.unique_name(name),
            created_at=time.time() if now is None else now,
        )
        self.playlists.append(playlist)
        return playlist

    def total_items(self) -> int:
        return sum(len(playlist.items) for playlist in self.playlists)

    def playlists_with(self, path: str) -> list[Playlist]:
        """Every playlist holding *path*, in library order."""
        key = path_key(path)
        return [p for p in self.playlists if any(path_key(i.path) == key for i in p.items)]


# --- the file ------------------------------------------------------------------


def _int(value: object, default: int = 0) -> int:
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def _float(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return 0.0
    return 0.0


def _parse_playlist(raw: object, used_ids: set[str]) -> Playlist | None:
    if not isinstance(raw, dict):
        return None
    name = str(raw.get("name") or "").strip() or "My Playlist"
    playlist_id = str(raw.get("id") or "").strip()
    if not playlist_id or playlist_id in used_ids:
        playlist_id = uuid.uuid4().hex[:12]
    used_ids.add(playlist_id)
    playlist = Playlist(
        id=playlist_id,
        name=name,
        folder=str(raw.get("folder") or ""),
        watch=bool(raw.get("watch", False)),
        shuffle=bool(raw.get("shuffle", False)),
        repeat=normalize_repeat_mode(raw.get("repeat")),
        last_item_id=_int(raw.get("last_item_id")),
        created_at=_float(raw.get("created_at")),
        temporary=bool(raw.get("temporary", False)),
    )
    # The pre-release shape kept bare path strings under "files"; the shipped
    # shape keeps dicts under "items". Both are read, and either way an item
    # with no usable id (or a duplicate one) is given a fresh one.
    entries = raw.get("items")
    if not isinstance(entries, list):
        legacy = raw.get("files")
        entries = legacy if isinstance(legacy, list) else []
    seen: set[int] = set()
    pending: list[dict[str, Any]] = []
    for entry in entries:
        if isinstance(entry, str):
            entry = {"path": entry}
        if not isinstance(entry, dict) or not str(entry.get("path") or "").strip():
            continue
        pending.append(entry)
        item_id = _int(entry.get("id"))
        if item_id > 0:
            seen.add(item_id)
    next_id = max([_int(raw.get("next_item_id"), 1), *(i + 1 for i in seen)], default=1)
    claimed: set[int] = set()
    for entry in pending:
        item_id = _int(entry.get("id"))
        if item_id <= 0 or item_id in claimed:
            item_id = next_id
            next_id += 1
        claimed.add(item_id)
        playlist.items.append(
            MediaItem(
                id=item_id,
                path=str(entry.get("path")).strip(),
                title=str(entry.get("title") or ""),
                artist=str(entry.get("artist") or ""),
                album=str(entry.get("album") or ""),
                duration_seconds=max(0, _int(entry.get("duration_seconds"))),
                added_at=_float(entry.get("added_at")),
            )
        )
    playlist.next_item_id = max(next_id, 1)
    return playlist


def parse(raw: dict[str, object]) -> LocalMediaLibrary:
    """The library from any shape this store has ever written (pure)."""
    library = LocalMediaLibrary()
    used: set[str] = set()
    entries = raw.get("playlists")
    for entry in entries if isinstance(entries, list) else []:
        playlist = _parse_playlist(entry, used)
        if playlist is not None:
            library.playlists.append(playlist)
    return library


def serialize(library: LocalMediaLibrary) -> dict[str, object]:
    """The canonical on-disk form, stamped with :data:`SCHEMA_VERSION` (pure)."""
    return {
        "schema_version": SCHEMA_VERSION,
        "playlists": [playlist.to_dict() for playlist in library.playlists],
    }


def is_legacy(raw: dict[str, object]) -> bool:
    """A file from before the version stamp: worth backing up before rewriting."""
    version = raw.get("schema_version")
    return not isinstance(version, int) or version < SCHEMA_VERSION


def is_future(raw: dict[str, object]) -> bool:
    """A file a newer Quill Radio wrote: read it, never downgrade it."""
    version = raw.get("schema_version")
    return isinstance(version, int) and version > SCHEMA_VERSION


def _store_path(data_dir: Path | None) -> Path:
    if data_dir is None:
        from quill.core.paths import app_data_dir

        data_dir = app_data_dir()
    return data_dir / FILE_NAME


def load_library(data_dir: Path | None = None) -> LocalMediaLibrary:
    """Read the library, migrating an older file once (with a backup).

    A missing or unreadable file reads as an empty library; the versioned-store
    machinery quarantines a corrupt one first, so it is never overwritten.
    """
    from quill.core.versioned_store import load_with_migration

    return load_with_migration(
        _store_path(data_dir),
        store_name="radio-local-media",
        parse=parse,
        serialize=serialize,
        is_legacy=is_legacy,
        default=LocalMediaLibrary,
        is_future=is_future,
    )


def save_library(library: LocalMediaLibrary, data_dir: Path | None = None) -> None:
    """Write the whole library, atomically. Raises ``OSError`` on failure."""
    from quill.core.storage import write_json_atomic

    write_json_atomic(_store_path(data_dir), serialize(library))


def summary(playlist: Playlist) -> str:
    """ "12 items, 47 minutes" -- the playlist in one breath (pure)."""
    count = len(playlist.items)
    if not count:
        return "empty"
    words = f"{count} item{'' if count == 1 else 's'}"
    seconds = playlist.total_seconds()
    if seconds > 0:
        rounded = seconds if seconds < 60 else int(round(seconds / 60.0)) * 60
        words += f", {_speak_duration(rounded)}"
    missing = sum(1 for item in playlist.items if not item.exists())
    if missing:
        words += f", {missing} missing"
    if playlist.temporary:
        words += ", not saved"
    return words
