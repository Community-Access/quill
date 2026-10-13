"""Add to Lineup: the one verb every row in Radio and Cast offers.

Whatever the row is -- a station, a saved place, a podcast or one of its
episodes, a YouTube video, playlist or channel, a Local Media file, a recording
-- it becomes :class:`~quill.core.lineups.fields.ItemFacts` at the call site
(``quill.core.lineups.sources.station_facts`` and friends) and arrives here.
The listener picks a Lineup (or makes one) and the items are added by hand: they
stay until removed, whatever the rules say.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from quill.core.lineups import ops
from quill.core.lineups.describe import list_sentence
from quill.core.lineups.fields import ItemFacts
from quill.core.lineups.refs import ItemRef
from quill.core.lineups.store import LineupStore, LineupStoreError
from quill.ui.lineups import dialogs
from quill.ui.lineups.host import LineupsHost

TITLE = "Add to Lineup"
NEW_CHOICE = "New Lineup..."


def offer(host: LineupsHost, items: Sequence[ItemFacts], *, parent: Any = None) -> bool:
    """Ask which Lineup, add *items* to it, and say so. ``False`` when nothing was added."""
    if not items:
        host.announce("There is nothing here to add to a lineup.")
        return False
    store = LineupStore(host.data_dir)
    try:
        book = store.load()
    except Exception as exc:  # noqa: BLE001 - say it, never raise into a menu handler
        host.announce(f"Your lineups could not be read: {exc}.")
        return False
    names = [lineup.name for lineup in book.lineups]
    what = list_sentence([item.name for item in items])
    index = dialogs.choose(
        host,
        parent if parent is not None else host.frame,
        f"Add {what} to which lineup?",
        TITLE,
        [*names, NEW_CHOICE],
    )
    if index is None:
        return False
    try:
        if index == len(names):
            name = dialogs.ask_text(
                host, parent or host.frame, "Name for the new lineup:", "New Lineup"
            )
            if not name:
                return False
            _book, created = store.update(ops.create_lineup(name))
            lineup_id = created.lineup_id
        else:
            lineup_id = book.lineups[index].id
        payloads = {item.ref: item.payload for item in items if item.payload}
        changed, outcome = store.update(ops.add_items(lineup_id, list(items), payloads=payloads))
    except LineupStoreError as exc:
        host.announce(str(exc))
        return False
    if outcome.stale:
        host.announce("That lineup was deleted a moment ago.")
        return False
    lineup = changed.find(lineup_id)
    target = lineup.name if lineup is not None else "the lineup"
    before = book.find(lineup_id)  # the lineup as it was, before these were added
    fresh = [item.ref for item in items if before is None or before.row_for(item.ref) is None]
    if fresh:

        def undo() -> None:
            # Only what this Add brought: an item already there stays (R4).
            LineupStore(host.data_dir).update(_take_back(lineup_id, fresh))
            _reload_open_window(host)

        host.remember_undo("Add", what, "the lineup as it was", undo)
    _reload_open_window(host, select_lineup=lineup_id)
    if not fresh:  # nothing new: say what did change (review N2)
        host.say_outcome(f"Already in {target}; it now stays until you remove it.")
    else:
        host.say_outcome(host.offer_undo(f"Added to {target}."))
    return True


def _take_back(lineup_id: str, refs: Sequence[ItemRef]) -> ops.Operation:
    """Undo of Add: rows that are only there by hand go; a rule's own row stays."""
    from dataclasses import replace

    wanted = set(refs)

    def operation(book: Any) -> tuple[Any, ops.Outcome]:
        lineup = book.find(lineup_id)
        if lineup is None:
            return book, ops.Outcome(stale=True)
        rows = tuple(
            row
            for row in lineup.rows
            if not (row.ref in wanted and row.held == "added" and not row.claims)
        )
        changed = replace(lineup, rows=rows, revision=lineup.revision + 1)
        return replace(book.replace_lineup(changed), revision=book.revision + 1), ops.Outcome()

    return operation


def _reload_open_window(host: LineupsHost, *, select_lineup: str = "") -> None:
    from quill.ui.lineups.window import open_window_of

    window = open_window_of(host.app_key)
    if window is None:
        return
    window._book = window._load_book()
    window._stamp = window._store.stamp()
    window.reload(select_lineup=select_lineup)


__all__ = ["NEW_CHOICE", "TITLE", "offer"]
