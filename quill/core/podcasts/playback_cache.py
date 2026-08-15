"""A streamed episode is a fully capable episode.

Through 1.1.0 QUILL Cast quietly had two classes of episode. A downloaded one
could have its chapters found, its bookmarks anchored, its position resumed
exactly, and its audio analysed. A streamed one could do none of that, and a
listener had to know which kind they were holding before they knew which
features they had. That is the two-tier system this module removes.

The mechanism is unremarkable on purpose: while a streamed episode plays, the
bytes are also written to a managed cache, so the episode becomes byte-backed
without anyone asking for a download. What the bytes buy is the point:

* **A dropped connection stops being an interruption.** Whatever has already
  arrived keeps playing -- the player falls back to the local file at the
  position it was at, instead of re-buffering into silence.
* **"Keep this one" costs nothing.** Deciding halfway through that you want the
  episode is a :func:`promote` -- a move on the same volume -- not a second
  download of bytes you already have.
* **The analysis tiers get something to analyse.** Chapter inference and Deep
  transcription both need a file; the moment one exists they work on a streamed
  episode exactly as they do on a downloaded one.

Two rules keep it invisible rather than infuriating:

* **The cache is never content.** It is bounded, evicted least-recently-used,
  and losing all of it costs nothing but bandwidth. Downloads, positions,
  bookmarks and notes are content and live elsewhere.
* **The episode you are listening to is never evicted.** :func:`evict_to_cap`
  takes the in-use paths and skips them, the same instinct as
  :func:`quill.core.podcasts.retention.is_protected`.

wx-free, strict-typed, no network: this module owns *where the bytes live* and
*which of them may be thrown away*. Fetching them is the download queue's job.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

__all__ = [
    "CACHE_DIRNAME",
    "DEFAULT_CAP_MB",
    "PART_SUFFIX",
    "CacheEntry",
    "cache_root",
    "cached_audio",
    "cached_bytes",
    "clear",
    "entries",
    "evict_to_cap",
    "finalize",
    "forget",
    "is_cache_path",
    "local_audio_path",
    "partial_path",
    "playback_path",
    "promote",
    "total_bytes",
    "touch",
]

#: Under the app data dir, beside the other managed caches.
CACHE_DIRNAME = "podcast-playback-cache"

#: A fetch in progress carries this suffix, so an interrupted one can never be
#: mistaken for a complete file. Completion is an ``os.replace`` onto the real
#: name, which is atomic on every platform QUILL targets.
PART_SUFFIX = ".part"

#: The default ceiling, in megabytes. Deliberately modest: this is a
#: convenience cache for episodes the listener chose to *stream*, and a large
#: default would be the same surprise as auto-downloading for a stream-mode
#: show (see acquisition.episodes_to_auto_download).
DEFAULT_CAP_MB = 1024

#: Extensions worth preserving so the player and ffmpeg can sniff the format
#: from the name. Anything else becomes ``.audio`` rather than trusting a URL.
_KNOWN_SUFFIXES = frozenset({
    ".aac",
    ".flac",
    ".m4a",
    ".m4b",
    ".mp3",
    ".mp4",
    ".oga",
    ".ogg",
    ".opus",
    ".wav",
    ".wma",
})


@dataclass(frozen=True, slots=True)
class CacheEntry:
    """One file in the playback cache."""

    path: Path
    size: int
    #: Seconds since the epoch, last used (read for playback or written).
    used_at: float
    #: True while the fetch is still running (a ``.part`` file).
    partial: bool


def cache_root() -> Path:
    """Where cached playback files live."""
    from quill.core.paths import app_data_dir

    return app_data_dir() / CACHE_DIRNAME


def _suffix_for(url: str) -> str:
    """A safe extension for *url*, or ``.audio`` when it does not offer one."""
    try:
        name = Path(urlparse(url).path).suffix.lower()
    except ValueError:
        return ".audio"
    return name if name in _KNOWN_SUFFIXES else ".audio"


def playback_path(show_id: str, episode_guid: str, url: str = "") -> Path:
    """The cache path for one episode, complete or not yet written.

    Keyed by show and episode guid rather than by URL, so a feed that moves its
    enclosures does not orphan every cached file -- and hashed, because a guid
    is publisher-supplied text that has no business being a filename.
    """
    digest = hashlib.sha256(f"{show_id}\n{episode_guid}".encode()).hexdigest()[:32]
    return cache_root() / f"{digest}{_suffix_for(url)}"


def partial_path(show_id: str, episode_guid: str, url: str = "") -> Path:
    """Where the in-progress fetch for one episode writes."""
    complete = playback_path(show_id, episode_guid, url)
    return complete.with_name(complete.name + PART_SUFFIX)


def is_cache_path(path: Path | str) -> bool:
    """Whether *path* is inside the playback cache.

    Used wherever something must not treat a cached file as a download -- the
    difference between "this is here for now" and "the listener keeps this".
    """
    try:
        return Path(path).resolve().parent == cache_root().resolve()
    except (OSError, ValueError):
        return False


def cached_audio(show_id: str, episode_guid: str, url: str = "") -> Path | None:
    """The complete cached file for one episode, or None.

    A ``.part`` file is deliberately *not* returned: it is enough to keep
    playing from after a drop (see :func:`cached_bytes`) but it is not the
    whole episode, and handing a partial file to the chapter scan would produce
    a chapter list for two-thirds of a programme with no way to tell.
    """
    path = playback_path(show_id, episode_guid, url)
    try:
        if path.stat().st_size > 0:
            return path
    except OSError:
        return None
    return None


def cached_bytes(show_id: str, episode_guid: str, url: str = "") -> tuple[Path | None, int, bool]:
    """``(path, bytes_on_disk, complete)`` for one episode's cached audio.

    Reports the partial file too, because that is exactly what makes a dropped
    connection survivable: the bytes already here are playable even though the
    episode is not finished arriving.
    """
    complete = playback_path(show_id, episode_guid, url)
    try:
        size = complete.stat().st_size
    except OSError:
        size = 0
    if size > 0:
        return complete, size, True
    part = complete.with_name(complete.name + PART_SUFFIX)
    try:
        part_size = part.stat().st_size
    except OSError:
        return None, 0, False
    if part_size <= 0:
        return None, 0, False
    return part, part_size, False


def finalize(show_id: str, episode_guid: str, url: str = "") -> Path | None:
    """Promote a finished ``.part`` file to the complete name.

    The one step that turns "bytes are arriving" into "this episode is
    byte-backed", and an ``os.replace`` so there is no instant at which a
    reader could see a half-written file under the complete name. Returns the
    complete path, or None when there was nothing to finalize.
    """
    complete = playback_path(show_id, episode_guid, url)
    part = complete.with_name(complete.name + PART_SUFFIX)
    try:
        if part.stat().st_size <= 0:
            return None
    except OSError:
        return None
    try:
        os.replace(part, complete)
    except OSError:
        return None
    return complete


def local_audio_path(show: object, episode: object) -> Path | None:
    """The best local file for an episode: its download, else its cache entry.

    The single place anything that needs *bytes* should ask, so a streamed
    episode reaches the same features a downloaded one does. Returns None when
    neither exists, which every caller already handles as "no audio yet".
    """
    downloaded = str(getattr(episode, "downloaded_path", "") or "")
    if downloaded:
        path = Path(downloaded)
        try:
            if path.exists():
                return path
        except OSError:
            return None
        return None
    return cached_audio(
        str(getattr(show, "id", "") or ""),
        str(getattr(episode, "guid", "") or ""),
        str(getattr(episode, "audio_url", "") or ""),
    )


def touch(path: Path) -> None:
    """Mark a cache file as used now, so eviction sees it as recent.

    Best effort: a cache whose timestamp cannot be updated still works, it just
    looks older than it is to :func:`evict_to_cap`.
    """
    try:
        os.utime(path, None)
    except OSError:
        return


def entries() -> list[CacheEntry]:
    """Everything in the cache, least recently used first."""
    root = cache_root()
    found: list[CacheEntry] = []
    try:
        children = list(root.iterdir())
    except OSError:
        return []
    for child in children:
        try:
            stat = child.stat()
        except OSError:
            continue
        if not child.is_file():
            continue
        found.append(
            CacheEntry(
                path=child,
                size=stat.st_size,
                used_at=stat.st_mtime,
                partial=child.name.endswith(PART_SUFFIX),
            )
        )
    found.sort(key=lambda entry: entry.used_at)
    return found


def total_bytes() -> int:
    """How much disk the playback cache is using right now."""
    return sum(entry.size for entry in entries())


def evict_to_cap(cap_bytes: int, *, keep: frozenset[Path] = frozenset()) -> list[CacheEntry]:
    """Delete least-recently-used cache files until the total fits *cap_bytes*.

    ``keep`` is the set of files that must survive whatever happens -- in
    practice the episode currently playing and anything mid-fetch. A cap that
    cannot be reached without touching one of those is simply not reached, and
    the caller is told what was freed rather than the rule quietly winning.

    ``cap_bytes <= 0`` means no cap, and nothing is evicted.
    """
    if cap_bytes <= 0:
        return []
    all_entries = entries()
    total = sum(entry.size for entry in all_entries)
    if total <= cap_bytes:
        return []
    protected = {p.resolve() for p in keep if p is not None}
    removed: list[CacheEntry] = []
    for entry in all_entries:
        if total <= cap_bytes:
            break
        try:
            if entry.path.resolve() in protected:
                continue
        except OSError:
            continue
        try:
            entry.path.unlink(missing_ok=True)
        except OSError:
            continue
        total -= entry.size
        removed.append(entry)
    return removed


def promote(show_id: str, episode_guid: str, url: str, destination: Path) -> Path | None:
    """Turn a cached episode into a kept download by moving it.

    This is the whole of "keep this one": the bytes are already here, so the
    usual shape -- change your mind, download the entire episode a second time
    -- is simply not necessary. Returns the destination on success, or None
    when there is no complete cache entry to promote (the caller then falls
    back to an ordinary download).

    A same-volume move is a rename; across volumes it is a copy, which
    :func:`shutil.move` handles. Either way the cache entry is gone afterwards,
    because the file is now content and content is not cache.
    """
    source = cached_audio(show_id, episode_guid, url)
    if source is None:
        return None
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return None
    try:
        import shutil

        shutil.move(str(source), str(destination))
    except (OSError, shutil.Error):
        return None
    return destination


def forget(show_id: str, episode_guid: str, url: str = "") -> int:
    """Drop one episode's cached audio (complete and partial). Bytes freed."""
    freed = 0
    complete = playback_path(show_id, episode_guid, url)
    for path in (complete, complete.with_name(complete.name + PART_SUFFIX)):
        try:
            size = path.stat().st_size
        except OSError:
            continue
        try:
            path.unlink(missing_ok=True)
        except OSError:
            continue
        freed += size
    return freed


def clear(*, keep: frozenset[Path] = frozenset()) -> int:
    """Empty the cache; returns the bytes freed.

    Nothing here is content, so this is always safe -- but the in-use files are
    still spared, because emptying a cache should not stop the audio.
    """
    protected = {p.resolve() for p in keep if p is not None}
    freed = 0
    for entry in entries():
        try:
            if entry.path.resolve() in protected:
                continue
        except OSError:
            continue
        try:
            entry.path.unlink(missing_ok=True)
        except OSError:
            continue
        freed += entry.size
    return freed
