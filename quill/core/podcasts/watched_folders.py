"""Watched folders: a folder Cast keeps an eye on, so what lands there arrives.

qc.md 5d. A listener points Cast at the folder their voice recorder syncs to, or
the one lectures are dropped into, once; from then on anything that lands there
is in Personal Audio before they go looking, announced once, never twice, never a
duplicate, and the original exactly where it was.

This module is the record and the work, with no ``wx``:

* :class:`WatchedFolder` -- one folder and its settings, stored in the library
  file (``watched_folders``), replacing the one ``watched_folder`` string a
  Personal Audio show used to carry. :func:`migrate` turns each of those into a
  record with the defaults, so nobody's folder stops being watched on upgrade.
* :func:`plan` -- the slow half, safe off the UI thread: find what is new,
  hash it, read its length, copy it (or not, by the folder's setting). It
  touches the library only to read which content it already has.
* :func:`apply` -- the quick half, on the UI thread: put the planned arrivals
  into their Personal Audio groups and remember what was seen.
* :class:`SettleTracker` -- the settled-file rule. A file still being written
  (a recorder writing a two-hour file over ten minutes) is "arriving" until its
  size has held still for five seconds and it can be opened for reading.

Never twice: a file is recognised by its content, not its name, so the same
recording renamed, or dropped into two watched folders, is one episode. A file
removed from the folder does not remove the episode -- the folder is a door in,
not a mirror -- except under *Play it from where it is*, where the episode reads
Unavailable (``personal_audio.unavailable_items`` already says so).

wx-free, strict-typed.
"""

from __future__ import annotations

import os
import sys
import time
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quill.core.podcasts.local_import import SUPPORTED_AUDIO_EXTENSIONS

__all__ = [
    "ARRIVALS",
    "ORIGINALS",
    "TELLS",
    "Arrival",
    "Plan",
    "SettleTracker",
    "WatchedFolder",
    "apply",
    "find",
    "is_network_path",
    "migrate",
    "parse",
    "plan",
    "serialise",
]

#: What to do with the original file: (value, label). Leave it is the default
#: because it is the only one that cannot surprise anybody.
ORIGINALS: tuple[tuple[str, str], ...] = (
    ("keep", "Leave it where it is (Cast keeps its own copy)"),
    ("move", "Move it into Cast's folder"),
    ("reference", "Play it from where it is (no copy)"),
)
#: What a new arrival does.
ARRIVALS: tuple[tuple[str, str], ...] = (
    ("add", "Add to Personal Audio"),
    ("queue", "Add to Personal Audio and the Play Queue"),
    ("play", "Add, and play it if nothing is playing"),
)
#: How Cast tells you. Every arrival is written to Notifications whatever this
#: says; it chooses what is spoken on top.
TELLS: tuple[tuple[str, str], ...] = (
    ("each", "Say each new file"),
    ("batch", "Say how many arrived"),
    ("quiet", "Quietly (Notifications only)"),
)

#: How long a file's size must hold still before it counts as arrived.
SETTLE_SECONDS = 5.0
#: How often a folder on a network drive is looked at, where the operating
#: system's change notices cannot be trusted.
NETWORK_POLL_MINUTES = 10


@dataclass
class WatchedFolder:
    """One watched folder and how it behaves."""

    path: str
    name: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    #: The Personal Audio group (a local show) its files arrive in.
    show_id: str = ""
    include_subfolders: bool = True
    #: Each first-level subfolder becomes its own group -- a folder of
    #: audiobooks becomes one group per book.
    subfolder_groups: bool = False
    #: Subfolder name -> the group (local show) id it fills.
    group_shows: dict[str, str] = field(default_factory=dict)
    extensions: tuple[str, ...] = SUPPORTED_AUDIO_EXTENSIONS
    original: str = "keep"
    arrivals: str = "add"
    tell: str = "each"
    #: Ignore anything shorter than this, so a recorder's accidental
    #: two-second file does not become an episode.
    min_seconds: int = 30
    #: This folder's own speed for its groups; 0 is the shared default.
    speed: float = 0.0
    paused: bool = False
    #: ISO-8601 UTC of the last arrival ("" = none yet).
    last_arrival: str = ""
    #: Relative path -> "size:mtime" of every file already dealt with, so a
    #: scan does not hash a thousand old files again.
    seen: dict[str, str] = field(default_factory=dict)

    def display_name(self) -> str:
        return self.name.strip() or Path(self.path).name or self.path

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "path": self.path,
            "name": self.name,
            "show_id": self.show_id,
            "include_subfolders": self.include_subfolders,
            "subfolder_groups": self.subfolder_groups,
            "group_shows": dict(self.group_shows),
            "extensions": list(self.extensions),
            "original": self.original,
            "arrivals": self.arrivals,
            "tell": self.tell,
            "min_seconds": self.min_seconds,
            "speed": self.speed,
            "paused": self.paused,
            "last_arrival": self.last_arrival,
            "seen": dict(self.seen),
        }

    @classmethod
    def from_dict(cls, data: object) -> WatchedFolder | None:
        if not isinstance(data, dict) or not str(data.get("path", "")).strip():
            return None

        def _choice(key: str, table: tuple[tuple[str, str], ...], default: str) -> str:
            value = str(data.get(key, default))
            return value if value in {v for v, _ in table} else default

        extensions = data.get("extensions")
        exts = (
            tuple(
                str(e).lower() for e in extensions if str(e).lower() in SUPPORTED_AUDIO_EXTENSIONS
            )
            if isinstance(extensions, list)
            else SUPPORTED_AUDIO_EXTENSIONS
        )
        groups = data.get("group_shows")
        seen = data.get("seen")
        try:
            min_seconds = max(0, int(data.get("min_seconds", 30)))
        except (TypeError, ValueError):
            min_seconds = 30
        try:
            speed = max(0.0, float(data.get("speed", 0.0)))
        except (TypeError, ValueError):
            speed = 0.0
        return cls(
            path=str(data["path"]),
            name=str(data.get("name", "")),
            id=str(data.get("id") or uuid.uuid4().hex),
            show_id=str(data.get("show_id", "")),
            include_subfolders=bool(data.get("include_subfolders", True)),
            subfolder_groups=bool(data.get("subfolder_groups", False)),
            group_shows=(
                {str(k): str(v) for k, v in groups.items()} if isinstance(groups, dict) else {}
            ),
            extensions=exts,
            original=_choice("original", ORIGINALS, "keep"),
            arrivals=_choice("arrivals", ARRIVALS, "add"),
            tell=_choice("tell", TELLS, "each"),
            min_seconds=min_seconds,
            speed=speed,
            paused=bool(data.get("paused", False)),
            last_arrival=str(data.get("last_arrival", "")),
            seen=({str(k): str(v) for k, v in seen.items()} if isinstance(seen, dict) else {}),
        )


def parse(raw: object) -> list[WatchedFolder]:
    """The stored list, skipping anything unreadable."""
    folders: list[WatchedFolder] = []
    for entry in raw if isinstance(raw, list) else []:
        folder = WatchedFolder.from_dict(entry)
        if folder is not None:
            folders.append(folder)
    return folders


def serialise(folders: Iterable[WatchedFolder]) -> list[dict[str, Any]]:
    return [folder.to_dict() for folder in folders]


def find(library: Any, folder_id: str) -> WatchedFolder | None:
    folders: list[WatchedFolder] = getattr(library, "watched_folders", [])
    for folder in folders:
        if folder.id == folder_id:
            return folder
    return None


def migrate(library: Any) -> int:
    """Turn each Personal Audio show's old ``watched_folder`` string into a
    record with the defaults. Files the show already has are marked seen by
    name, so the first scan after upgrading imports nothing twice. Returns how
    many were migrated."""
    folders: list[WatchedFolder] = library.watched_folders
    known = {f.show_id for f in folders}
    moved = 0
    for show in library.shows:
        path = str(getattr(show, "watched_folder", "") or "").strip()
        if not getattr(show, "is_local", False) or not path or show.id in known:
            continue
        record = WatchedFolder(path=path, name=show.title, show_id=show.id)
        names = {Path(ep.downloaded_path).name for ep in show.episodes if ep.downloaded_path}
        names |= {ep.source_filename for ep in show.episodes if getattr(ep, "source_filename", "")}
        for file in _candidates(record):
            if file.name in names:
                record.seen[_key(record, file)] = _signature(file)
        folders.append(record)
        show.watched_folder = ""
        moved += 1
    return moved


def is_network_path(path: str) -> bool:
    """Whether *path* is on a network drive, where change notices are unreliable."""
    if path.startswith(("\\\\", "//")):
        return True
    if not sys.platform.startswith("win") or len(path) < 2 or path[1] != ":":
        return False
    try:
        import ctypes

        drive_remote = 4
        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined,unused-ignore]
        return bool(kernel32.GetDriveTypeW(f"{path[0]}:\\") == drive_remote)
    except Exception:  # noqa: BLE001 - unknown is treated as local
        return False


# -- finding ------------------------------------------------------------------


def _key(folder: WatchedFolder, file: Path) -> str:
    try:
        return str(file.relative_to(folder.path))
    except ValueError:
        return str(file)


def _signature(file: Path) -> str:
    try:
        stat = file.stat()
    except OSError:
        return ""
    return f"{stat.st_size}:{int(stat.st_mtime)}"


def _candidates(folder: WatchedFolder) -> list[Path]:
    root = Path(folder.path)
    if not root.is_dir():
        return []
    wanted = {e.lower() for e in folder.extensions}
    walker = root.rglob("*") if folder.include_subfolders else root.iterdir()
    files: list[Path] = []
    try:
        for path in walker:
            if path.suffix.lower() in wanted and path.is_file():
                files.append(path)
    except OSError:
        return files
    return sorted(files)


def _group_of(folder: WatchedFolder, file: Path) -> str:
    """The first-level subfolder a file is in, when subfolders are groups."""
    if not folder.subfolder_groups:
        return ""
    try:
        parts = file.relative_to(folder.path).parts
    except ValueError:
        return ""
    return parts[0] if len(parts) > 1 else ""


def _openable(file: Path) -> bool:
    try:
        with file.open("rb") as handle:
            handle.read(1)
    except OSError:
        return False
    return True


# -- the slow half ----------------------------------------------------------------


@dataclass
class Arrival:
    """One file that came in, ready to become an episode."""

    group: str
    episode: Any
    key: str
    signature: str


@dataclass
class Plan:
    """What one look at a folder found."""

    folder_id: str
    arrivals: list[Arrival] = field(default_factory=list)
    #: Files dealt with that add nothing (a duplicate, too short): key -> signature.
    seen: dict[str, str] = field(default_factory=dict)
    #: Why the folder could not be read, in a sentence; "" when it could.
    problem: str = ""
    #: Files that were not finished yet and are left for the next look.
    still_arriving: int = 0


def known_hashes(library: Any) -> set[str]:
    return {
        ep.content_hash
        for show in library.shows
        for ep in show.episodes
        if getattr(ep, "content_hash", "")
    }


def plan(
    folder: WatchedFolder,
    known: set[str],
    *,
    now: float | None = None,
    dest_root: Path | None = None,
) -> Plan:
    """Find, check and (by the folder's setting) copy what is new in *folder*.

    *known* is every content hash the library already has; it is updated as
    files are planned, so one file dropped twice in the same look is one
    arrival. Safe off the UI thread: it reads the library only through *known*.
    """
    from quill.core.podcasts.local_duplicates import content_hash
    from quill.core.podcasts.local_import import (
        _episode_for,
        _slug,
        _staged_copy,
        local_podcasts_root,
    )
    from quill.core.podcasts.local_tags import read_tags

    result = Plan(folder_id=folder.id)
    root = Path(folder.path)
    if not root.exists():
        result.problem = (
            f"{folder.display_name()} is unavailable: the folder or its drive is not there."
        )
        return result
    if not root.is_dir() or not os.access(root, os.R_OK):
        result.problem = f"{folder.display_name()} cannot be read: Windows did not allow it."
        return result
    clock = time.time() if now is None else now
    base = (dest_root or local_podcasts_root()) / _slug(folder.display_name())
    for file in _candidates(folder):
        key = _key(folder, file)
        signature = _signature(file)
        if not signature or folder.seen.get(key) == signature:
            continue
        try:
            recent = clock - file.stat().st_mtime < SETTLE_SECONDS
        except OSError:
            continue
        if recent or not _openable(file):
            result.still_arriving += 1
            continue
        digest = content_hash(file)
        if digest and digest in known:
            result.seen[key] = signature
            continue
        length = read_tags(file).duration_seconds
        if length and length < folder.min_seconds:
            result.seen[key] = signature
            continue
        group = _group_of(folder, file)
        if folder.original == "reference":
            dest: Path | None = file
        else:
            target = base / _slug(group) if group else base
            try:
                target.mkdir(parents=True, exist_ok=True)
            except OSError:
                result.problem = f"Cast could not make room for {folder.display_name()}'s files."
                return result
            dest = _staged_copy(file, target)
        if dest is None:
            continue
        episode = _episode_for(file, dest)
        if folder.original == "move" and dest != file:
            try:
                file.unlink()
            except OSError:
                pass  # the copy is verified; a locked original simply stays
        if digest:
            known.add(digest)
        result.arrivals.append(Arrival(group, episode, key, signature))
    return result


# -- the quick half -------------------------------------------------------------


def _group_show(library: Any, folder: WatchedFolder, group: str) -> Any:
    """The local show *group* fills, made on first use."""
    from quill.core.podcasts.models import PodcastShow

    show_id = folder.group_shows.get(group, "") if group else folder.show_id
    show = library.find_show(show_id) if show_id else None
    if show is not None:
        return show
    show = PodcastShow(
        id=uuid.uuid4().hex,
        title=group or folder.display_name(),
        feed_url="",
        is_local=True,
    )
    library.add_show(show)
    if group:
        folder.group_shows[group] = show.id
    else:
        folder.show_id = show.id
    if folder.speed:
        _apply_speed(library, show, folder.speed)
    return show


def _apply_speed(library: Any, show: Any, speed: float) -> None:
    try:
        from quill.core.podcasts import settings_catalog
        from quill.core.podcasts.settings_resolver import set_value
        from quill.core.podcasts.settings_types import LEVEL_SHOW

        definition = settings_catalog.definition("speed")
        if definition is not None:
            set_value(library, definition, speed, level=LEVEL_SHOW, scope_id=show.id)
    except Exception:  # noqa: BLE001 - a speed is a preference, never a failure
        return


def apply(library: Any, folder: WatchedFolder, result: Plan) -> list[tuple[Any, Any]]:
    """Put *result*'s arrivals into their groups. Returns (show, episode) pairs."""
    folder.seen.update(result.seen)
    added: list[tuple[Any, Any]] = []
    for arrival in result.arrivals:
        show = _group_show(library, folder, arrival.group)
        show.episodes.append(arrival.episode)
        folder.seen[arrival.key] = arrival.signature
        added.append((show, arrival.episode))
    if added:
        folder.last_arrival = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return added


def set_speed(library: Any, folder: WatchedFolder) -> None:
    """Give every group this folder fills the folder's speed (0 = leave alone)."""
    if not folder.speed:
        return
    for show_id in [folder.show_id, *folder.group_shows.values()]:
        show = library.find_show(show_id) if show_id else None
        if show is not None:
            _apply_speed(library, show, folder.speed)


# -- the settled-file rule ---------------------------------------------------------


class SettleTracker:
    """Files that are arriving, until their size holds still and they open."""

    def __init__(
        self,
        quiet_seconds: float = SETTLE_SECONDS,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._quiet = quiet_seconds
        self._clock = clock
        self._pending: dict[str, tuple[int, float]] = {}

    def note(self, path: str) -> None:
        """A change was seen at *path*; start (or restart) its quiet period."""
        try:
            size = os.path.getsize(path)
        except OSError:
            size = -1
        self._pending[path] = (size, self._clock())

    def pending(self) -> int:
        return len(self._pending)

    def due(self) -> list[str]:
        """Paths that have settled since the last call."""
        now = self._clock()
        settled: list[str] = []
        for path, (size, since) in list(self._pending.items()):
            try:
                current = os.path.getsize(path)
            except OSError:
                self._pending.pop(path, None)  # gone again: a temporary file
                continue
            if current != size:
                self._pending[path] = (current, now)
            elif now - since >= self._quiet and _openable(Path(path)):
                settled.append(path)
                self._pending.pop(path, None)
        return settled
