"""Save Lineup... and Apply Lineup... on Cast's Play Queue, now QUILL Lineups.

The Play Queue dialog, the queue place's context menu and the host commands all
call these two, so the verb behaves the same wherever it is reached -- the
sentences included, which are unchanged from before: Save says how many
episodes went in and whether it replaced one; Apply counts what it applied and
what it skipped, because a silent half-applied lineup looks like one that worked.
"""

from __future__ import annotations

from typing import Any

from quill.core.lineups import cast_queue
from quill.core.lineups.store import LineupStore, LineupStoreError


def _data_dir() -> Any:
    from quill.core.paths import app_data_dir

    return app_data_dir()


def _host(app: Any) -> Any:
    from quill.ui.podcasts.lineups_host import CastLineupsHost

    return CastLineupsHost(app)


def save_queue_lineup(app: Any, library: Any, parent: Any, *, announce: Any) -> bool:
    """Keep the queue's order as a Lineup under a name. ``True`` when saved."""
    from quill.ui.lineups import dialogs

    if not library.queue:
        announce("The queue is empty, so there is no order to save.")
        return False
    name = dialogs.ask_text(_host(app), parent, "Lineup name:", "Save Lineup")
    if not name:
        return False
    store = LineupStore(_data_dir())
    try:
        replacing = store.load().find_by_name(name) is not None
        book, outcome = store.update(cast_queue.save_queue(library, name))
    except LineupStoreError as exc:
        announce(str(exc))
        return False
    lineup = book.find(outcome.lineup_id) if outcome.lineup_id else None
    if outcome.stale or lineup is None:
        announce("That lineup could not be saved.")
        return False
    verb = "Replaced" if replacing else "Saved"
    from quill.core.lineups.describe import count_text

    announce(
        f"{verb} lineup {lineup.name}: {count_text(len(lineup.rows), 'episode')}, in this order."
    )
    return True


def apply_queue_lineup(app: Any, library: Any, parent: Any, *, announce: Any) -> bool:
    """Put a Lineup's episodes at the front of the queue. ``True`` when applied."""
    from quill.ui.lineups import dialogs

    try:
        book = LineupStore(_data_dir()).load()
    except Exception as exc:  # noqa: BLE001 - said, never raised into a button
        announce(f"Your lineups could not be read: {exc}.")
        return False
    lineups = [lineup for lineup in book.lineups if cast_queue.queue_items_of(lineup)]
    if not lineups:
        announce(
            "No lineup has episodes yet. Use Save Lineup first, or Add to Lineup on an episode."
        )
        return False
    index = dialogs.choose(
        _host(app),
        parent,
        "Apply which lineup?",
        "Apply Lineup",
        [lineup.name for lineup in lineups],
    )
    if index is None:
        return False
    chosen = lineups[index]
    counted = cast_queue.apply_to_queue(library, chosen)
    announce(counted.sentence("Applied", chosen.name, noun="episode"))
    return True


def import_snapshots_once(library: Any) -> None:
    """Copy queue snapshots the old Save Lineup made into Lineups (once, quietly)."""
    try:
        LineupStore(_data_dir()).update(cast_queue.import_queue_snapshots(library))
    except Exception:  # noqa: BLE001 - tried again next launch; nothing is lost
        pass


__all__ = ["apply_queue_lineup", "import_snapshots_once", "save_queue_lineup"]
