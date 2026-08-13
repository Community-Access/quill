"""Queue Expiration and Recently Expired (1.1.0).

A queued episode you never got to is clutter, and clutter in a queue is
worse than clutter in a list: the queue is what plays next, so a stale item
does not merely sit there, it takes a turn. This module ages the Play Queue
out on a per-podcast limit -- "daily news show? two days. Weekly long-form?
two weeks. Or leave it off entirely" -- and gives what it removed a seven-day
safety net before anything on disk is touched.

Three rules the rest of the feature depends on:

1. **Nothing is deleted at expiry time.** An expired episode leaves the
   *queue*; it keeps its downloaded file, its position, and its place in its
   show's episode list. Only the seven-day sweep deletes the file, and only
   for an entry the listener chose not to restore.
2. **An unknown age is "now", never "ancient".** A queue written before
   1.1.0 has no ``added_at`` at all. Reading that as "added at the epoch"
   would empty everybody's queue on the first launch after updating, so
   :func:`stamp_missing_added_at` runs at load and treats an unstamped slot
   as having been added the moment it was first seen.
3. **Expiry is announced.** Silently removing something the listener queued
   is exactly the unannounced state change Cast PRD A-4 forbids; the callers
   speak the count, and Recently Expired is a real, browsable tree node
   rather than a place things quietly go.

wx-free, strict-typed.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from quill.core.podcasts.models import ExpiredEntry, PodcastShow, QueueItem, now_iso
from quill.core.podcasts.subscriptions import PodcastLibrary

#: How long an expired episode stays restorable before its file is deleted.
#: Earshot's number, and a good one: long enough to notice on a weekly
#: rhythm, short enough that "recently" still means something.
RECENTLY_EXPIRED_HOLD_DAYS = 7


def _parse(timestamp: str) -> datetime | None:
    """An ISO 8601 timestamp as an aware datetime, or None if unreadable.

    A naive timestamp (no offset) is read as UTC rather than rejected: every
    timestamp this feature writes is UTC, and a hand-edited or synced file
    that dropped the offset should still age correctly.
    """
    text = (timestamp or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def _age_days(timestamp: str, now: datetime) -> float | None:
    stamped = _parse(timestamp)
    if stamped is None:
        return None
    return (now - stamped).total_seconds() / 86400.0


def _delete_file(path_str: str) -> bool:
    if not path_str:
        return False
    try:
        Path(path_str).unlink(missing_ok=True)
    except OSError:
        return False
    return True


def stamp_missing_added_at(library: PodcastLibrary, *, now: str | None = None) -> int:
    """Give every unstamped queue slot a timestamp of *now*; returns how many.

    The whole migration. Call it once, right after the library loads and
    before anything asks how old the queue is. See this module's rule 2.
    """
    stamp = now or now_iso()
    stamped = 0
    for item in library.queue:
        if not item.added_at:
            item.added_at = stamp
            stamped += 1
    return stamped


def queue_age_limit_days(library: PodcastLibrary, show: PodcastShow) -> int:
    """This show's queue age limit in days (0 = never expire)."""
    return max(0, int(library.effective_settings(show).queue_age_limit_days))


def expire_stale_queue_items(
    library: PodcastLibrary, *, now: datetime | None = None
) -> list[ExpiredEntry]:
    """Move every over-age queue slot into Recently Expired; returns them.

    Runs on library load and after every refresh. A slot whose show or
    episode has gone (an unsubscribe, a pruned episode) is dropped outright
    rather than recorded -- there is nothing left to restore it to.
    """
    moment = now or datetime.now(UTC)
    stamp = moment.isoformat()
    kept: list[QueueItem] = []
    expired: list[ExpiredEntry] = []
    for item in library.queue:
        show = library.find_show(item.show_id)
        if show is None or show.find_episode(item.episode_guid) is None:
            continue  # stale slot: self-heal, exactly as pop_next_playable does
        limit = queue_age_limit_days(library, show)
        age = _age_days(item.added_at, moment)
        if limit <= 0 or age is None or age < limit:
            kept.append(item)
            continue
        entry = ExpiredEntry(show_id=item.show_id, episode_guid=item.episode_guid, expired_at=stamp)
        expired.append(entry)
    # Always write the kept list back, even when nothing expired: the loop
    # also drops slots whose show or episode has gone, and leaving those in
    # place would mean the queue only self-heals on the days something
    # happens to expire.
    library.queue = kept
    if not expired:
        return []
    known = {(e.show_id, e.episode_guid) for e in library.recently_expired}
    for entry in expired:
        if (entry.show_id, entry.episode_guid) not in known:
            library.recently_expired.append(entry)
    return expired


def sweep_recently_expired(
    library: PodcastLibrary, *, now: datetime | None = None
) -> tuple[list[ExpiredEntry], int]:
    """Drop entries held past the hold window, deleting their files.

    Returns ``(dropped entries, files deleted)``. This is the only place
    expiration deletes anything, and it only ever deletes the *downloaded
    file* -- the episode itself stays in its show, unplayed, exactly where it
    would be if it had never been queued.
    """
    moment = now or datetime.now(UTC)
    kept: list[ExpiredEntry] = []
    dropped: list[ExpiredEntry] = []
    deleted = 0
    for entry in library.recently_expired:
        age = _age_days(entry.expired_at, moment)
        if age is None or age < RECENTLY_EXPIRED_HOLD_DAYS:
            kept.append(entry)
            continue
        dropped.append(entry)
        show = library.find_show(entry.show_id)
        episode = show.find_episode(entry.episode_guid) if show is not None else None
        if episode is not None and episode.downloaded_path:
            if _delete_file(episode.downloaded_path):
                deleted += 1
            episode.downloaded_path = ""
    library.recently_expired = kept
    return dropped, deleted


def expired_pairs(library: PodcastLibrary) -> list[tuple[PodcastShow, object]]:
    """``(show, episode)`` for every restorable entry, newest expiry first.

    Entries whose show or episode has since disappeared resolve to nothing
    and are skipped, the same way a stale queue slot is.
    """
    pairs: list[tuple[PodcastShow, object]] = []
    for entry in sorted(library.recently_expired, key=lambda e: e.expired_at, reverse=True):
        show = library.find_show(entry.show_id)
        episode = show.find_episode(entry.episode_guid) if show is not None else None
        if show is not None and episode is not None:
            pairs.append((show, episode))
    return pairs


def restore_expired(library: PodcastLibrary, show_id: str, episode_guid: str) -> bool:
    """Put one expired episode back at the end of the queue, freshly stamped.

    Freshly stamped on purpose: restoring means "I do want this", and the
    limit should start counting again from that decision rather than expiring
    it a second time on the next refresh.
    """
    before = len(library.recently_expired)
    library.recently_expired = [
        e
        for e in library.recently_expired
        if not (e.show_id == show_id and e.episode_guid == episode_guid)
    ]
    if len(library.recently_expired) == before:
        return False
    already = any(
        item.show_id == show_id and item.episode_guid == episode_guid for item in library.queue
    )
    if not already:
        library.queue.append(
            QueueItem(show_id=show_id, episode_guid=episode_guid, added_at=now_iso())
        )
    return True


def restore_all_expired(library: PodcastLibrary) -> int:
    """Restore every entry; returns how many went back into the queue."""
    entries = list(library.recently_expired)
    restored = 0
    for entry in entries:
        if restore_expired(library, entry.show_id, entry.episode_guid):
            restored += 1
    return restored


def forget_expired(library: PodcastLibrary, show_id: str, episode_guid: str) -> bool:
    """Drop one entry from Recently Expired without restoring it.

    The file is left alone: this is "stop offering it back to me", not
    "delete it". Removing a downloaded copy stays the Remove Download
    action's job, where the wording says so.
    """
    before = len(library.recently_expired)
    library.recently_expired = [
        e
        for e in library.recently_expired
        if not (e.show_id == show_id and e.episode_guid == episode_guid)
    ]
    return len(library.recently_expired) != before


__all__ = [
    "RECENTLY_EXPIRED_HOLD_DAYS",
    "expire_stale_queue_items",
    "expired_pairs",
    "forget_expired",
    "queue_age_limit_days",
    "restore_all_expired",
    "restore_expired",
    "stamp_missing_added_at",
    "sweep_recently_expired",
]
