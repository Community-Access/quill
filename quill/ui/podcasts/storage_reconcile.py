"""Bounded UI-owned patches for completed podcast storage work."""

from __future__ import annotations

from collections.abc import Callable, Generator, Iterator
from dataclasses import dataclass
from typing import Any

from quill.core.podcasts import expiration, inbox, retention
from quill.core.podcasts.models import ExpiredEntry
from quill.core.podcasts.storage_maintenance import Deletion, DownloadTarget, StoragePlan, path_key
from quill.ui.podcasts.storage_snapshot import StorageCapture, transfer_protected

FILES_PER_BATCH = 16


@dataclass(slots=True)
class StorageOutcome:
    mutations: int = 0
    queue_expired: int = 0
    stale_queue: int = 0
    inbox_trimmed: int = 0
    expired_dropped: int = 0
    removed: int = 0
    swept: int = 0
    reclaimed: int = 0
    missing: int = 0
    failed: int = 0
    unreadable: int = 0
    skipped: int = 0
    error: bool = False

    def details(self) -> list[str]:
        parts: list[str] = []
        if self.failed or self.unreadable:
            parts.append(
                f"{self.failed + self.unreadable} file(s) could not be inspected or removed; "
                "their download information was kept"
            )
        if self.missing:
            parts.append(f"{self.missing} file(s) were already unavailable")
        if self.skipped:
            parts.append(f"{self.skipped} changed or protected file(s) were kept")
        if self.error:
            parts.append("housekeeping could not finish; completed changes were kept")
        return parts

    def housekeeping(self) -> str:
        parts: list[str] = []
        if self.queue_expired:
            parts.append(
                f"{self.queue_expired} episode(s) expired from the queue -- "
                "find them under Recently Expired"
            )
        if self.stale_queue:
            parts.append(f"{self.stale_queue} unavailable queue slot(s) cleared")
        if self.expired_dropped:
            parts.append(
                f"{self.expired_dropped} expired episode(s) passed the "
                f"{expiration.RECENTLY_EXPIRED_HOLD_DAYS}-day hold; "
                f"{self.swept} downloaded file(s) removed"
            )
        if self.inbox_trimmed:
            parts.append(
                f"{self.inbox_trimmed} episode(s) left the Inbox at its limit "
                "(still unheard in their podcasts)"
            )
        if self.removed - self.swept:
            parts.append(f"{self.removed - self.swept} old download(s) removed")
        if self.removed:
            parts.append(f"{retention.format_bytes(self.reclaimed)} freed")
        return "; ".join([*parts, *self.details()])

    def freed(self) -> str:
        if not (self.removed or self.missing or self.failed or self.unreadable or self.error):
            text = "Nothing to free up: no download is past its age limit or over the cap"
        else:
            text = (
                f"Freed {retention.format_bytes(self.reclaimed)} from "
                f"{self.removed} downloaded episode file(s)"
            )
        return "; ".join([text, *self.details()]) + "."


def apply_metadata(
    host: Any,
    captured: StorageCapture,
    plan: StoragePlan,
    outcome: StorageOutcome,
    mutated: Callable[[], None],
) -> Generator[None]:
    library = captured.source
    changes = {}
    for change in plan.queue:
        changes[id(captured.queue[change.index])] = change
        yield
    kept = []
    queued = set()
    new_expired: list[ExpiredEntry] = []
    removed = stale = 0
    for item in library.queue:
        change = changes.get(id(item))
        if change is not None and item == change.before:
            if change.after is None:
                if change.expired is not None:
                    new_expired.append(change.expired)
                    removed += 1
                else:
                    stale += 1
                yield
                continue
            if item.added_at != change.after.added_at:
                item.added_at = change.after.added_at
                mutated()
        kept.append(item)
        queued.add((item.show_id, item.episode_guid))
        yield
    if removed or stale:
        library.queue = kept
        outcome.queue_expired += removed
        outcome.stale_queue += stale
        mutated()
    captured.queued = queued
    known = set()
    for entry in library.recently_expired:
        known.add((entry.show_id, entry.episode_guid))
        yield
    for entry in new_expired:
        key = (entry.show_id, entry.episode_guid)
        if key not in known:
            library.recently_expired.append(
                ExpiredEntry(entry.show_id, entry.episode_guid, entry.expired_at)
            )
            known.add(key)
            mutated()
        yield
    for change in plan.inbox:
        pair = captured.episodes.get(change.key)
        key = inbox.inbox_key(*change.key)
        if pair is not None:
            show, episode = pair
            if (
                library.inbox_assignments.get(key) == change.assignment
                and episode.published == change.published
                and not episode.played
                and episode.position_ms == 0
                and change.key not in captured.queued
                and not transfer_protected(host, change.key)
            ):
                library.inbox_assignments[key] = inbox.TRIMMED_MARKER
                outcome.inbox_trimmed += 1
                mutated()
        yield


def permission_checks(
    host: Any,
    captured: StorageCapture,
    plan: StoragePlan,
    targets: tuple[DownloadTarget, ...],
) -> Iterator[bool]:
    for target in targets:
        for key in target.references:
            pair = captured.episodes.get(key)
            if pair is None:
                yield False
                continue
            show, episode = pair
            yield (
                bool(episode.downloaded_path)
                and path_key(episode.downloaded_path) == path_key(target.path)
                and not retention.is_protected(
                    captured.source,
                    show,
                    episode,
                    queued=captured.queued,
                    pinned=plan.pinned[show.id],
                )
                and not transfer_protected(host, key)
            )


def authorize_batch(
    host: Any,
    captured: StorageCapture,
    plan: StoragePlan,
    cursor: int,
    attempted: set[str],
    outcome: StorageOutcome,
) -> Generator[None, None, tuple[tuple[DownloadTarget, ...], int]]:
    approved: list[DownloadTarget] = []
    while cursor < len(plan.downloads) and len(approved) < FILES_PER_BATCH:
        target = plan.downloads[cursor]
        cursor += 1
        if path_key(target.path) in attempted:
            yield
            continue
        safe = True
        for permitted in permission_checks(host, captured, plan, (target,)):
            safe &= permitted
            yield
        if safe:
            approved.append(target)
        else:
            outcome.skipped += 1
            attempted.add(path_key(target.path))
    return tuple(approved), cursor


def apply_deletions(
    host: Any,
    captured: StorageCapture,
    deletions: tuple[Deletion, ...],
    mutated: Callable[[], None],
) -> Generator[None]:
    for deletion in deletions:
        if deletion.status not in ("removed", "missing"):
            yield
            continue
        for key in deletion.target.references:
            pair = captured.episodes.get(key)
            if pair is not None:
                episode = pair[1]
                if (
                    episode.downloaded_path
                    and path_key(episode.downloaded_path) == path_key(deletion.target.path)
                    and not transfer_protected(host, key)
                ):
                    episode.downloaded_path = ""
                    mutated()
            yield


def drop_expired(
    host: Any,
    captured: StorageCapture,
    plan: StoragePlan,
    successful: set[str],
    outcome: StorageOutcome,
    mutated: Callable[[], None],
) -> Generator[None]:
    changes = {}
    for change in plan.expired:
        changes[(change.before.show_id, change.before.episode_guid, change.before.expired_at)] = (
            change
        )
        yield
    kept = []
    dropped = 0
    for entry in captured.source.recently_expired:
        key = (entry.show_id, entry.episode_guid)
        change = changes.get((*key, entry.expired_at))
        pair = captured.episodes.get(key)
        current_path = pair[1].downloaded_path if pair is not None else ""
        compatible_path = not current_path or (
            change is not None and change.path == path_key(current_path)
        )
        if (
            change is not None
            and (not change.path or change.path in successful)
            and compatible_path
            and key not in captured.queued
            and not transfer_protected(host, key)
        ):
            dropped += 1
        else:
            kept.append(entry)
        yield
    if dropped:
        captured.source.recently_expired = kept
        outcome.expired_dropped += dropped
        mutated()
