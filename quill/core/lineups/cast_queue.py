"""Cast's Play Queue and Lineups: one meaning of "lineup" in the family.

Before QUILL Lineups, Cast's Play Queue had "Save Lineup..." and "Apply
Lineup..." (``quill.core.podcasts.queue_lineups``), where a lineup was a manual
playlist holding a snapshot of the queue order. That idea is now a QUILL Lineup:

* **Save Lineup...** saves the queue as a Lineup of hand-added episodes, in
  order. Saving over a Lineup of the same name replaces its rows (re-saving
  "Tuesday" means *this* is Tuesday now), and keeps its rules if it has any.
* **Apply Lineup...** puts a Lineup's episodes at the front of the queue through
  the very same ``apply_lineup`` it always used -- available, unplayed episodes
  to the front in order, the rest of the queue left as it was, and what was
  skipped counted -- so the verb behaves exactly as before.
* **Queue snapshots saved before** (manual playlists whose id starts with
  ``lineup-``, the ids ``save_lineup`` made) are copied into Lineups once. The
  playlists themselves are left exactly where they were.

wx-free. The caller saves Cast's library (for Apply) and announces.
"""

from __future__ import annotations

import time
from dataclasses import replace

from quill.core.counted import Counted
from quill.core.lineups.model import HELD_ADDED, Lineup, LineupBook, Row
from quill.core.lineups.ops import Operation, Outcome, create_lineup, unique_name
from quill.core.lineups.refs import KIND_EPISODE, episode_ref, split_key
from quill.core.podcasts.models import QueueItem
from quill.core.podcasts.models_playlists import Playlist
from quill.core.podcasts.queue_lineups import apply_lineup
from quill.core.podcasts.subscriptions import PodcastLibrary

#: The id prefix ``queue_lineups.save_lineup`` gave the queue snapshots it made.
LEGACY_PREFIX = "lineup-"


def _episode_rows(library: PodcastLibrary, items: list[QueueItem], now: float) -> tuple[Row, ...]:
    rows: list[Row] = []
    seen: set[str] = set()
    for item in items:
        ref = episode_ref(item.show_id, item.episode_guid)
        if ref.token in seen:
            continue
        seen.add(ref.token)
        show = library.find_show(item.show_id)
        episode = show.find_episode(item.episode_guid) if show is not None else None
        name = episode.title if episode is not None else ""
        rows.append(Row(ref=ref, name=name, held=HELD_ADDED, arrived=now))
    return tuple(rows)


def save_queue(library: PodcastLibrary, name: str, *, now: float | None = None) -> Operation:
    """Save the Play Queue as a Lineup named *name* (replacing one of that name)."""
    moment = time.time() if now is None else now
    rows = _episode_rows(library, list(library.queue), moment)

    def operation(book: LineupBook) -> tuple[LineupBook, Outcome]:
        if not rows:
            return book, Outcome(stale=True)
        existing = book.find_by_name(name)
        if existing is not None:
            changed = replace(existing, rows=rows, revision=existing.revision + 1)
            return replace(book.replace_lineup(changed), revision=book.revision + 1), Outcome(
                lineup_id=existing.id
            )
        book, outcome = create_lineup(name)(book)
        created = book.find(outcome.lineup_id)
        assert created is not None
        return book.replace_lineup(replace(created, rows=rows)), outcome

    return operation


def queue_items_of(lineup: Lineup) -> list[QueueItem]:
    """The Lineup's episodes, in order, as queue references."""
    items: list[QueueItem] = []
    for row in lineup.rows:
        if row.ref.kind == KIND_EPISODE:
            show_id, guid = split_key(row.ref)
            if show_id and guid:
                items.append(QueueItem(show_id, guid))
    return items


def apply_to_queue(library: PodcastLibrary, lineup: Lineup) -> Counted:
    """Put the Lineup's available, unplayed episodes at the front of the queue.

    The same rules as before (``queue_lineups.apply_lineup``), so nothing about
    the verb changed but where its list comes from. Stations, videos and other
    kinds are not episodes and are not counted.
    """
    playlist = Playlist(id=lineup.id, name=lineup.name, kind="manual", items=queue_items_of(lineup))
    return apply_lineup(library, playlist)


def import_queue_snapshots(library: PodcastLibrary, *, now: float | None = None) -> Operation:
    """Copy queue snapshots saved by the old Save Lineup into Lineups, once.

    Each copied snapshot is remembered in ``LineupBook.imported``, so deleting
    the Lineup later does not bring it back, and running this again is a no-op.
    """
    moment = time.time() if now is None else now
    snapshots = [
        playlist
        for playlist in library.playlists
        if playlist.kind == "manual" and str(playlist.id).startswith(LEGACY_PREFIX)
    ]

    def operation(book: LineupBook) -> tuple[LineupBook, Outcome]:
        pending = [p for p in snapshots if p.id not in book.imported]
        if not pending:
            return book, Outcome()
        for playlist in pending:
            rows = _episode_rows(library, list(playlist.items), moment)
            book, outcome = create_lineup(unique_name(book, playlist.name))(book)
            created = book.find(outcome.lineup_id)
            if created is not None:
                book = book.replace_lineup(replace(created, rows=rows))
        imported = (*book.imported, *(p.id for p in pending))
        return replace(book, imported=imported, revision=book.revision + 1), Outcome()

    return operation


__all__ = [
    "LEGACY_PREFIX",
    "apply_to_queue",
    "import_queue_snapshots",
    "queue_items_of",
    "save_queue",
]
