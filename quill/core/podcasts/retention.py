"""Retention policy: what happens to a downloaded episode's file over time.

Applied after every successful download (``keep_last_n`` pruning) and when
an episode finishes playing (``delete_after_play``). Pure/wx-free so the
policy logic is testable without a real download or a real file.

1.1.0 adds the two library-wide rules a per-show count cannot express: an
age limit (delete a download older than N days) and a storage cap (a ceiling
on total podcast storage, oldest played downloads evicted first). Both share
one hard rule -- **a queued or in-progress episode is never evicted**. Disk
pressure is not a reason to throw away the thing somebody is halfway through.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from quill.core.podcasts.models import PodcastEpisode, PodcastSettings, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary

#: Optional hook consulted before every retention deletion. Given the path,
#: it returns True when it has taken responsibility for the file (moved it
#: aside for one step of undo -- see :func:`quill.ui.undo_last_ui.capturing_deletes`)
#: and False to let the ordinary unlink proceed. None in every other case, so
#: the default behaviour is exactly what it was.
_delete_hook: Callable[[Path], bool] | None = None


def set_delete_hook(hook: Callable[[Path], bool] | None) -> Callable[[Path], bool] | None:
    """Install *hook*; return whatever it replaced (so a scope can restore it).

    Retention deletes files from several paths -- delete-after-play, keep-last-N,
    the storage cap -- and a destructive verb that wants to be undoable has to
    catch all of them without knowing which one fired. One hook, installed for
    the duration of that verb, does it.
    """
    global _delete_hook
    previous = _delete_hook
    _delete_hook = hook
    return previous


def _delete_file(path_str: str) -> None:
    if not path_str:
        return
    path = Path(path_str)
    if _delete_hook is not None:
        try:
            if _delete_hook(path):
                return
        except Exception:  # noqa: BLE001 - a hook bug must not strand the file
            pass
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def remove_downloaded_copy(episode: PodcastEpisode) -> bool:
    """Delete an episode's downloaded file, keeping the episode itself.

    Freeing space and unsubscribing are very different things to want, and this
    is the first: the episode stays in the library, keeps its played mark and
    its position, and can be downloaded again. Returns whether there was a copy
    to remove, so a bulk caller can count honestly rather than claiming work it
    did not do.
    """
    if not episode.downloaded_path:
        return False
    _delete_file(episode.downloaded_path)
    episode.downloaded_path = ""
    return True


def apply_keep_last_n(show: PodcastShow, settings: PodcastSettings) -> list[PodcastEpisode]:
    """For ``retention == "keep_last_n"``, delete the oldest downloaded
    episodes beyond ``retention_count``; returns the episodes pruned."""
    if settings.retention != "keep_last_n":
        return []
    downloaded = [e for e in show.episodes if e.downloaded_path]
    if len(downloaded) <= settings.retention_count:
        return []
    downloaded.sort(key=lambda e: e.published, reverse=True)
    to_prune = downloaded[settings.retention_count :]
    for episode in to_prune:
        _delete_file(episode.downloaded_path)
        episode.downloaded_path = ""
    return to_prune


def wants_delete_after_play(settings: PodcastSettings) -> bool:
    """Whether a finished episode's download should be removed (pure).

    Two ways to say the same thing, because it used to be a *retention mode*
    -- one of three, so choosing it meant giving up "keep the last N" -- and is
    now an independent switch that composes with the rest. A settings file
    written before the change still carries the mode, and it still means this.
    """
    return bool(
        getattr(settings, "delete_after_play", False) or settings.retention == "delete_after_play"
    )


def apply_delete_after_play(
    episode: PodcastEpisode,
    settings: PodcastSettings,
    *,
    download_in_progress: bool = False,
) -> bool:
    """Remove *episode*'s local file now that it has played, if asked to.

    Returns True if a file was removed.

    *download_in_progress* is the one refusal: an episode can finish playing
    from a partial file while the rest of it is still arriving (streamed
    playback writes into the cache as it goes), and deleting the target of a
    running download is how you get a half-written file nobody can play and a
    download that reports success. The caller knows; this asks.
    """
    if not wants_delete_after_play(settings) or not episode.downloaded_path:
        return False
    if download_in_progress:
        return False
    _delete_file(episode.downloaded_path)
    episode.downloaded_path = ""
    return True


def on_episode_played(library: Any, show: Any, episode: Any) -> bool:
    """Apply the delete-after-play rule to an episode just marked played.

    The one entry point every *"this is finished"* path shares -- the player's
    own end-of-episode callback, Mark as Played on a row, Mark All Played, and
    the positions Quill Radio hands back for episodes it finished. Before this
    existed only the first of those deleted anything, so whether the file went
    away depended on *how* you finished the episode, which is not a distinction
    anybody makes.

    Resolves the show's effective settings (a per-show override beats the
    global default here as everywhere else) and returns whether a file was
    removed, so the caller knows whether to save.
    """
    if show is None or episode is None:
        return False
    try:
        settings = library.effective_settings(show)
    except Exception:  # noqa: BLE001 - a settings lookup must never lose a mark
        return False
    return apply_delete_after_play(episode, settings)


# -- library-wide storage management (1.1.0) --------------------------------


def file_size(path_str: str) -> int:
    """Size on disk of a downloaded episode, 0 when it is gone or unreadable."""
    if not path_str:
        return 0
    try:
        return Path(path_str).stat().st_size
    except OSError:
        return 0


def _published_moment(episode: PodcastEpisode) -> datetime:
    try:
        parsed = datetime.fromisoformat((episode.published or "").strip())
    except ValueError:
        return datetime.min.replace(tzinfo=UTC)
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def downloaded_episodes(
    library: PodcastLibrary,
) -> list[tuple[PodcastShow, PodcastEpisode, int]]:
    """Every episode with a local file: ``(show, episode, bytes)``."""
    result: list[tuple[PodcastShow, PodcastEpisode, int]] = []
    for show in library.shows:
        for episode in show.episodes:
            if episode.downloaded_path:
                result.append((show, episode, file_size(episode.downloaded_path)))
    return result


def total_download_bytes(library: PodcastLibrary) -> int:
    """How much disk the podcast downloads are using right now."""
    return sum(size for _show, _episode, size in downloaded_episodes(library))


def per_show_usage(library: PodcastLibrary) -> list[tuple[PodcastShow, int, int]]:
    """``(show, files, bytes)`` per show, largest first -- the Downloads
    dialog's breakdown, and the answer to "what is using my disk"."""
    totals: dict[str, list[int]] = {}
    shows: dict[str, PodcastShow] = {}
    for show, _episode, size in downloaded_episodes(library):
        shows[show.id] = show
        entry = totals.setdefault(show.id, [0, 0])
        entry[0] += 1
        entry[1] += size
    rows = [(shows[sid], counts[0], counts[1]) for sid, counts in totals.items()]
    return sorted(rows, key=lambda row: row[2], reverse=True)


def is_protected(library: PodcastLibrary, show: PodcastShow, episode: PodcastEpisode) -> bool:
    """Whether this download is exempt from age limits and the storage cap.

    Queued or in progress. Both mean the listener has committed to it, and
    an automatic rule must never undo a deliberate choice.
    """
    if episode.position_ms > 0 and not episode.played:
        return True
    return any(
        item.show_id == show.id and item.episode_guid == episode.guid for item in library.queue
    )


def apply_age_limit(
    library: PodcastLibrary, *, now: datetime | None = None
) -> list[tuple[PodcastShow, PodcastEpisode, int]]:
    """Delete downloads older than ``download_retention_days``.

    Per-show overridable like every other setting, so one archival show can
    keep everything while the rest expire. Returns what was deleted, with the
    bytes reclaimed, so the caller can announce a real number.
    """
    moment = now or datetime.now(UTC)
    removed: list[tuple[PodcastShow, PodcastEpisode, int]] = []
    for show in library.shows:
        days = max(0, int(library.effective_settings(show).download_retention_days))
        if days <= 0:
            continue
        cutoff = moment - timedelta(days=days)
        for episode in show.episodes:
            if not episode.downloaded_path or is_protected(library, show, episode):
                continue
            if _published_moment(episode) >= cutoff:
                continue
            size = file_size(episode.downloaded_path)
            _delete_file(episode.downloaded_path)
            episode.downloaded_path = ""
            removed.append((show, episode, size))
    return removed


def enforce_storage_cap(
    library: PodcastLibrary, *, cap_bytes: int | None = None
) -> list[tuple[PodcastShow, PodcastEpisode, int]]:
    """Evict downloads until total storage fits under the cap.

    Eviction order is deliberate and, more importantly, *explainable*: played
    episodes go first, oldest first, and only then unplayed ones, still oldest
    first. Protected episodes are never touched, which means the cap can be
    genuinely unreachable -- a queue larger than the cap simply stays, and
    the caller reports what it could not free rather than deleting something
    the listener is relying on.
    """
    cap = library.settings.storage_cap_mb * 1024 * 1024 if cap_bytes is None else cap_bytes
    if cap <= 0:
        return []
    entries = downloaded_episodes(library)
    total = sum(size for _s, _e, size in entries)
    if total <= cap:
        return []
    evictable = [
        (show, episode, size)
        for show, episode, size in entries
        if not is_protected(library, show, episode)
    ]
    evictable.sort(key=lambda row: (not row[1].played, _published_moment(row[1])))
    removed: list[tuple[PodcastShow, PodcastEpisode, int]] = []
    for show, episode, size in evictable:
        if total <= cap:
            break
        _delete_file(episode.downloaded_path)
        episode.downloaded_path = ""
        total -= size
        removed.append((show, episode, size))
    return removed


def format_bytes(size: int) -> str:
    """A size in words a screen reader reads well: "1.4 GB", "812 MB"."""
    value = float(max(0, size))
    for unit in ("bytes", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            if unit == "bytes":
                return f"{int(value)} bytes"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


__all__ = [
    "apply_age_limit",
    "apply_delete_after_play",
    "on_episode_played",
    "wants_delete_after_play",
    "apply_keep_last_n",
    "downloaded_episodes",
    "enforce_storage_cap",
    "file_size",
    "format_bytes",
    "is_protected",
    "per_show_usage",
    "total_download_bytes",
]
