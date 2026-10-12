"""Detached storage reports and deletion proposals; never a live library owner."""

from __future__ import annotations

import logging
import os
import stat
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from quill.core.podcasts import expiration, inbox, playback_cache, retention
from quill.core.podcasts.models import ExpiredEntry, PodcastEpisode, QueueItem
from quill.core.podcasts.show_policy import is_pinned
from quill.core.podcasts.subscriptions import PodcastLibrary

logger = logging.getLogger(__name__)
EpisodeKey = tuple[str, str]
Mode = Literal["maintenance", "free", "show"]


def path_key(path: str) -> str:
    """Compare Windows paths without resolving or touching the filesystem."""
    return os.path.normcase(os.path.abspath(path))


@dataclass(frozen=True, slots=True)
class FileIdentity:
    device: int
    inode: int
    size: int
    modified_ns: int

    @classmethod
    def read(cls, path: Path) -> FileIdentity:
        stat = path.stat()
        return cls(stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)


@dataclass(frozen=True, slots=True)
class DownloadTarget:
    path: str
    references: tuple[EpisodeKey, ...]
    identity: FileIdentity | None
    reason: str

    @property
    def size(self) -> int:
        return self.identity.size if self.identity is not None else 0


@dataclass(frozen=True, slots=True)
class QueueChange:
    index: int
    before: QueueItem
    after: QueueItem | None
    expired: ExpiredEntry | None


@dataclass(frozen=True, slots=True)
class ExpiredChange:
    index: int
    before: ExpiredEntry
    path: str


@dataclass(frozen=True, slots=True)
class InboxChange:
    key: EpisodeKey
    assignment: str | None
    published: str


@dataclass(slots=True)
class StoragePlan:
    mode: Mode
    queue: tuple[QueueChange, ...]
    expired: tuple[ExpiredChange, ...]
    inbox: tuple[InboxChange, ...]
    downloads: tuple[DownloadTarget, ...]
    pinned: dict[str, bool]
    protected: int = 0
    unreadable: int = 0
    size: int = 0
    omitted: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class UsageRow:
    show_id: str
    title: str
    files: int
    size: int
    unheard_files: int
    unheard_size: int


@dataclass(frozen=True, slots=True)
class StorageUsage:
    rows: tuple[UsageRow, ...]
    unheard_rows: tuple[UsageRow, ...]
    files: int
    size: int
    streamed_size: int
    missing: int
    unreadable: int


@dataclass(frozen=True, slots=True)
class Deletion:
    target: DownloadTarget
    status: Literal["removed", "missing", "changed", "failed"]
    size: int = 0


def _measure(
    library: PodcastLibrary,
) -> tuple[dict[str, FileIdentity | None], set[str]]:
    identities: dict[str, FileIdentity | None] = {}
    unreadable: set[str] = set()
    for show in library.shows:
        for episode in show.episodes:
            if not episode.downloaded_path:
                continue
            key = path_key(episode.downloaded_path)
            if key in identities:
                continue
            try:
                identities[key] = FileIdentity.read(Path(episode.downloaded_path))
            except FileNotFoundError:
                identities[key] = None
            except OSError:
                logger.warning("Could not inspect a podcast download", exc_info=True)
                identities[key] = None
                unreadable.add(key)
    return identities, unreadable


def storage_usage(library: PodcastLibrary) -> StorageUsage:
    """Stat each distinct download once, including both filters in one report."""
    identities, unreadable = _measure(library)
    rows: list[UsageRow] = []
    count = 0
    for show in library.shows:
        files = size = unheard_files = unheard_size = 0
        for episode in show.episodes:
            if not episode.downloaded_path:
                continue
            identity = identities[path_key(episode.downloaded_path)]
            used = identity.size if identity is not None else 0
            files += 1
            size += used
            if not episode.played:
                unheard_files += 1
                unheard_size += used
        if files:
            count += files
            rows.append(UsageRow(show.id, show.title, files, size, unheard_files, unheard_size))
    rows.sort(key=lambda row: row.size, reverse=True)
    return StorageUsage(
        tuple(rows),
        tuple(
            sorted(
                (row for row in rows if row.unheard_files),
                key=lambda row: row.unheard_size,
                reverse=True,
            )
        ),
        count,
        sum(identity.size for identity in identities.values() if identity is not None),
        _streamed_size(),
        sum(identity is None and key not in unreadable for key, identity in identities.items()),
        len(unreadable),
    )


def _streamed_size() -> int:
    """Read cache usage strictly; best-effort cache APIs hide inspection errors."""
    try:
        children = os.scandir(playback_cache.cache_root())
    except FileNotFoundError:
        return 0
    total = 0
    with children:
        for child in children:
            try:
                measured = child.stat()
            except FileNotFoundError:
                continue
            if stat.S_ISREG(measured.st_mode):
                total += measured.st_size
    return total


def plan_storage(
    library: PodcastLibrary,
    *,
    mode: Mode,
    protected: Iterable[EpisodeKey] = (),
    show_id: str = "",
    now: datetime | None = None,
    allowed: tuple[DownloadTarget, ...] | None = None,
) -> StoragePlan:
    """Run the existing policies on a detached generation, intercepting deletion.

    A proposal carries the original file identity, not permission to delete it.
    The UI must revalidate commitments before handing it to a file worker.
    """
    moment = now or datetime.now(UTC)
    identities, unreadable = _measure(library)
    original_queue = list(library.queue)
    queue_before = [replace(item) for item in original_queue]
    original_expired = list(library.recently_expired)
    assignments = dict(library.inbox_assignments)
    episodes: dict[EpisodeKey, PodcastEpisode] = {}
    paths: dict[str, list[EpisodeKey]] = {}
    sizes: dict[str, int] = {}
    pinned = {show.id: is_pinned(library, show) for show in library.shows}
    extra = set(protected)
    for show in library.shows:
        for episode in show.episodes:
            key = (show.id, episode.guid)
            episodes[key] = episode
            if episode.downloaded_path:
                canonical = path_key(episode.downloaded_path)
                paths.setdefault(canonical, []).append(key)
                identity = identities[canonical]
                sizes[episode.downloaded_path] = identity.size if identity is not None else 0
                if canonical in unreadable:
                    extra.add(key)
    queued = {(item.show_id, item.episode_guid) for item in library.queue} | extra
    for show in library.shows:
        for episode in show.episodes:
            if episode.downloaded_path and retention.is_protected(
                library, show, episode, queued=queued, pinned=pinned[show.id]
            ):
                extra.update(paths[path_key(episode.downloaded_path)])
    original_ids = {id(item) for item in original_queue}
    library.queue.extend(QueueItem(sid, guid, added_at=moment.isoformat()) for sid, guid in extra)
    proposed: dict[str, tuple[str, str]] = {}
    reason = "expired"

    def observe(_episode: PodcastEpisode, path: str) -> None:
        proposed[path_key(path)] = (path, reason)

    previous_hook = retention.set_delete_hook(lambda _path: True)
    previous_observer = retention.set_delete_observer(observe)
    expired: list[ExpiredEntry] = []
    dropped: list[ExpiredEntry] = []
    trimmed: list[InboxChange] = []
    protected_count = 0
    try:
        if mode == "maintenance":
            expiration.stamp_missing_added_at(library, now=moment.isoformat())
            expired = expiration.expire_stale_queue_items(library, now=moment)
            dropped, _deleted = expiration.sweep_recently_expired(library, now=moment)
            # Storage-only protection is not membership in the listener's queue.
            policy_queue = library.queue
            library.queue = [item for item in policy_queue if id(item) in original_ids]
            try:
                trimmed_pairs = inbox.trim_inbox(library, now=moment)
            finally:
                library.queue = policy_queue
            trimmed = [
                InboxChange(
                    (show.id, episode.guid),
                    assignments.get(inbox.inbox_key(show.id, episode.guid)),
                    episode.published,
                )
                for show, episode in trimmed_pairs
            ]
        if mode == "show":
            reason = "show"
            queued = retention.protection_keys(library)
            for show in library.shows:
                if show.id != show_id:
                    continue
                for episode in show.episodes:
                    if not episode.downloaded_path:
                        continue
                    if retention.is_protected(
                        library, show, episode, queued=queued, pinned=pinned[show.id]
                    ):
                        protected_count += 1
                        continue
                    retention.remove_downloaded_copy(episode)
        else:
            reason = "age"
            retention.apply_age_limit(library, now=moment, sizes=sizes)
            reason = "cap"
            retention.enforce_storage_cap(library, sizes=sizes)
    finally:
        retention.set_delete_observer(previous_observer)
        retention.set_delete_hook(previous_hook)
    retained = {id(item) for item in library.queue if id(item) in original_ids}
    expiry = {(entry.show_id, entry.episode_guid): entry for entry in expired}
    queue_changes = tuple(
        QueueChange(
            index,
            before,
            replace(item) if id(item) in retained else None,
            expiry.get((item.show_id, item.episode_guid)) if id(item) not in retained else None,
        )
        for index, (item, before) in enumerate(zip(original_queue, queue_before, strict=True))
        if id(item) not in retained or item != before
    )
    targets: list[DownloadTarget] = []
    permitted = (
        {path_key(target.path): target for target in allowed} if allowed is not None else None
    )
    for canonical, (path, cause) in proposed.items():
        references = tuple(paths[canonical])
        # A shared file must not strand a different, ineligible episode.
        if any(episodes[key].downloaded_path for key in references):
            continue
        identity = identities[canonical]
        if permitted is not None:
            previous = permitted.get(canonical)
            if (
                previous is None
                or previous.identity != identity
                or previous.references != references
            ):
                continue
        targets.append(DownloadTarget(path, references, identity, cause))
    original_paths = {
        key: canonical for canonical, references in paths.items() for key in references
    }
    dropped_ids = {id(entry) for entry in dropped}
    expired_changes = tuple(
        ExpiredChange(
            index, replace(entry), original_paths.get((entry.show_id, entry.episode_guid), "")
        )
        for index, entry in enumerate(original_expired)
        if id(entry) in dropped_ids
    )
    accepted = {path_key(target.path) for target in targets}
    return StoragePlan(
        mode,
        queue_changes,
        expired_changes,
        tuple(trimmed),
        tuple(targets),
        pinned,
        protected_count,
        len(unreadable),
        sum(target.size for target in targets),
        tuple(canonical for canonical in permitted if canonical not in accepted)
        if permitted is not None
        else (),
    )


def delete_files(
    targets: tuple[DownloadTarget, ...], *, cancelled: Callable[[], bool] | None = None
) -> tuple[Deletion, ...]:
    """Delete only the inspected generation of each file, counting actual outcomes."""
    results: list[Deletion] = []
    for target in targets:
        if cancelled is not None and cancelled():
            results.append(Deletion(target, "changed"))
            continue
        path = Path(target.path)
        try:
            current = FileIdentity.read(path)
            if current != target.identity:
                results.append(Deletion(target, "changed"))
                continue
            if cancelled is not None and cancelled():
                results.append(Deletion(target, "changed"))
                continue
            path.unlink()
        except FileNotFoundError:
            results.append(Deletion(target, "missing"))
        except OSError:
            logger.warning(
                "Could not remove a podcast download; metadata will be kept", exc_info=True
            )
            results.append(Deletion(target, "failed"))
        else:
            results.append(Deletion(target, "removed", current.size))
    return tuple(results)
