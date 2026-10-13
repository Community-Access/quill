"""Every change to a Lineup, as a pure function named by keys, never by positions.

Radio and Cast can both have Lineups open. A change is therefore never "save
the copy I am holding": the store re-reads the file under a short lock and
applies the operation to what it just read (:mod:`quill.core.lineups.store`).
That only works if an operation means the same thing on a slightly newer list,
which is why every one here names items by their reference: "move *this* item
to just after *that* one" still makes sense after the other app added a row;
"move row 3 to row 1" does not.

An operation that no longer makes sense -- the item it names has already left
-- changes nothing and says so (:attr:`Outcome.stale`), rather than guessing.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace

from quill.core.lineups.fields import ItemFacts
from quill.core.lineups.merge import Catalogue, RefreshResult, refresh
from quill.core.lineups.model import (
    HELD_ADDED,
    HELD_KEPT,
    RECENTLY_LEFT_LIMIT,
    Departure,
    Lineup,
    LineupBook,
    Removed,
    Row,
    new_lineup_id,
)
from quill.core.lineups.refs import ItemRef
from quill.core.lineups.rules import Rule, new_rule_id


@dataclass(frozen=True, slots=True)
class Outcome:
    """What an operation did, for the window to say and to select."""

    #: Nothing the operation named was still there; nothing changed.
    stale: bool = False
    #: The rows to select afterwards, by reference.
    select: tuple[ItemRef, ...] = ()
    #: For a refresh: what it did.
    refresh: RefreshResult | None = None
    #: For a delete: what was deleted, so undo can put it back.
    deleted: Lineup | None = None
    deleted_index: int = -1
    lineup_id: str = ""


Operation = Callable[[LineupBook], tuple[LineupBook, Outcome]]

MAX_NAME = 80


def clean_name(name: str) -> str:
    return " ".join(str(name or "").split())[:MAX_NAME]


def unique_name(book: LineupBook, wanted: str, *, ignore_id: str = "") -> str:
    """*wanted*, or "*wanted* (2)" and so on: names are unique, ignoring case."""
    base = clean_name(wanted) or "New lineup"
    taken = {lineup.name.casefold() for lineup in book.lineups if lineup.id != ignore_id}
    if base.casefold() not in taken:
        return base
    number = 2
    while f"{base} ({number})".casefold() in taken:
        number += 1
    return f"{base} ({number})"


def _bump(book: LineupBook, lineup: Lineup) -> LineupBook:
    changed = replace(lineup, revision=lineup.revision + 1)
    return replace(book.replace_lineup(changed), revision=book.revision + 1)


def _with_lineup(
    lineup_id: str, edit: Callable[[Lineup], tuple[Lineup, Outcome] | None]
) -> Operation:
    """Apply *edit* to one Lineup; a Lineup the other app deleted is stale."""

    def operation(book: LineupBook) -> tuple[LineupBook, Outcome]:
        lineup = book.find(lineup_id)
        if lineup is None:
            return book, Outcome(stale=True, lineup_id=lineup_id)
        result = edit(lineup)
        if result is None:
            return book, Outcome(stale=True, lineup_id=lineup_id)
        changed, outcome = result
        return _bump(book, changed), replace(outcome, lineup_id=lineup_id)

    return operation


# -- the Lineups themselves ---------------------------------------------------------


def create_lineup(name: str, *, rules: Sequence[Rule] = (), lineup_id: str = "") -> Operation:
    def operation(book: LineupBook) -> tuple[LineupBook, Outcome]:
        lineup = Lineup(
            id=lineup_id or new_lineup_id(), name=unique_name(book, name), rules=tuple(rules)
        )
        return replace(book, lineups=(*book.lineups, lineup), revision=book.revision + 1), Outcome(
            lineup_id=lineup.id
        )

    return operation


def rename_lineup(lineup_id: str, name: str) -> Operation:
    def operation(book: LineupBook) -> tuple[LineupBook, Outcome]:
        lineup = book.find(lineup_id)
        if lineup is None:
            return book, Outcome(stale=True, lineup_id=lineup_id)
        renamed = replace(lineup, name=unique_name(book, name, ignore_id=lineup_id))
        return _bump(book, renamed), Outcome(lineup_id=lineup_id)

    return operation


def delete_lineup(lineup_id: str) -> Operation:
    def operation(book: LineupBook) -> tuple[LineupBook, Outcome]:
        for index, lineup in enumerate(book.lineups):
            if lineup.id == lineup_id:
                rest = book.lineups[:index] + book.lineups[index + 1 :]
                return replace(book, lineups=rest, revision=book.revision + 1), Outcome(
                    deleted=lineup, deleted_index=index, lineup_id=lineup_id
                )
        return book, Outcome(stale=True, lineup_id=lineup_id)

    return operation


def restore_lineup(lineup: Lineup, index: int) -> Operation:
    """Undo a delete: the Lineup back where it was (its name made unique again)."""

    def operation(book: LineupBook) -> tuple[LineupBook, Outcome]:
        if book.find(lineup.id) is not None:
            return book, Outcome(stale=True, lineup_id=lineup.id)
        back = replace(lineup, name=unique_name(book, lineup.name))
        at = max(0, min(index, len(book.lineups)))
        lineups = (*book.lineups[:at], back, *book.lineups[at:])
        return replace(book, lineups=lineups, revision=book.revision + 1), Outcome(
            lineup_id=lineup.id
        )

    return operation


def duplicate_lineup(lineup_id: str) -> Operation:
    """A copy with the rules, settings and current order; empty Removed and Left.

    The copy's rules get new ids, so the two Lineups never share a claim.
    """

    def operation(book: LineupBook) -> tuple[LineupBook, Outcome]:
        source = book.find(lineup_id)
        if source is None:
            return book, Outcome(stale=True, lineup_id=lineup_id)
        mapping = {rule.id: new_rule_id() for rule in source.rules}
        rules = tuple(replace(rule, id=mapping[rule.id]) for rule in source.rules)
        rows = tuple(
            replace(
                row,
                claims={mapping[rid]: since for rid, since in row.claims.items() if rid in mapping},
            )
            for row in source.rows
        )
        copy = replace(
            source,
            id=new_lineup_id(),
            name=unique_name(book, f"{source.name} (copy)"),
            rules=rules,
            rows=rows,
            removed=(),
            recently_left=(),
            released={},
            revision=0,
        )
        index = book.lineups.index(source)
        lineups = (*book.lineups[: index + 1], copy, *book.lineups[index + 1 :])
        return replace(book, lineups=lineups, revision=book.revision + 1), Outcome(
            lineup_id=copy.id
        )

    return operation


def move_lineup(lineup_id: str, *, delta: int = 0, to: int | None = None) -> Operation:
    """Move a Lineup by *delta* places, or to index *to* (clamped)."""

    def operation(book: LineupBook) -> tuple[LineupBook, Outcome]:
        ids = [lineup.id for lineup in book.lineups]
        if lineup_id not in ids:
            return book, Outcome(stale=True, lineup_id=lineup_id)
        index = ids.index(lineup_id)
        target = to if to is not None else index + delta
        target = max(0, min(target, len(ids) - 1))
        if target == index:
            return book, Outcome(lineup_id=lineup_id)
        lineups = list(book.lineups)
        lineups.insert(target, lineups.pop(index))
        return replace(book, lineups=tuple(lineups), revision=book.revision + 1), Outcome(
            lineup_id=lineup_id
        )

    return operation


def set_settings(lineup_id: str, **changes: object) -> Operation:
    """Change Lineup settings: ``new_items``, ``skip_live``, ``budget_minutes``."""
    allowed = {"new_items", "skip_live", "budget_minutes"}

    def edit(lineup: Lineup) -> tuple[Lineup, Outcome]:
        values = {key: value for key, value in changes.items() if key in allowed}
        return replace(lineup, **values), Outcome()  # type: ignore[arg-type]

    return _with_lineup(lineup_id, edit)


# -- rows ------------------------------------------------------------------------


def add_items(
    lineup_id: str,
    items: Sequence[ItemFacts],
    *,
    after: ItemRef | None = None,
    payloads: Mapping[ItemRef, Mapping[str, object]] | None = None,
    now: float | None = None,
) -> Operation:
    """Add items by hand: they stay until removed. One already there is held."""
    moment = time.time() if now is None else now

    def edit(lineup: Lineup) -> tuple[Lineup, Outcome] | None:
        rows = list(lineup.rows)
        removed = [entry for entry in lineup.removed if entry.ref not in {i.ref for i in items}]
        fresh: list[Row] = []
        for item in items:
            existing = lineup.row_for(item.ref)
            if existing is not None:
                index = rows.index(existing)
                rows[index] = replace(existing, held=existing.held or HELD_ADDED)
                continue
            if any(row.ref == item.ref for row in fresh):
                continue
            payload = (payloads or {}).get(item.ref)
            fresh.append(
                Row(ref=item.ref, name=item.name, held=HELD_ADDED, arrived=moment, payload=payload)
            )
        at = len(rows)
        if after is not None:
            anchor = next((i for i, row in enumerate(rows) if row.ref == after), None)
            if anchor is not None:
                at = anchor + 1
        rows[at:at] = fresh
        selection = tuple(item.ref for item in items)
        return replace(lineup, rows=tuple(rows), removed=tuple(removed)), Outcome(select=selection)

    return _with_lineup(lineup_id, edit)


def move_rows(
    lineup_id: str,
    refs: Sequence[ItemRef],
    *,
    after: ItemRef | None = None,
    to_top: bool = False,
) -> Operation:
    """Place *refs* (as a block, in list order) just after *after*, or at the top.

    ``after=None`` and ``to_top=False`` means the bottom. The moved rows are
    marked ``moved``: a budget never leaves out a row somebody placed.
    """

    def edit(lineup: Lineup) -> tuple[Lineup, Outcome] | None:
        wanted = set(refs)
        block = [row for row in lineup.rows if row.ref in wanted]
        if not block:
            return None
        rest = [row for row in lineup.rows if row.ref not in wanted]
        if to_top:
            at = 0
        elif after is None:
            at = len(rest)
        else:
            anchor = next((i for i, row in enumerate(rest) if row.ref == after), None)
            if anchor is None:
                return None  # the item to move next to has left: do not guess
            at = anchor + 1
        moved = [replace(row, moved=True) for row in block]
        rows = (*rest[:at], *moved, *rest[at:])
        return replace(lineup, rows=rows), Outcome(select=tuple(row.ref for row in moved))

    return _with_lineup(lineup_id, edit)


def restore_order(lineup_id: str, order: Sequence[ItemRef]) -> Operation:
    """Undo of a move: rows back in *order* (by reference).

    Rows *order* does not name -- arrivals since -- keep their place after the
    row they followed, so undoing an old move never loses a newer arrival.
    """

    def edit(lineup: Lineup) -> tuple[Lineup, Outcome] | None:
        rank = {ref: index for index, ref in enumerate(order)}
        known = sorted(
            (row for row in lineup.rows if row.ref in rank), key=lambda row: rank[row.ref]
        )
        if not known:
            return None
        rows: list[Row] = []
        pending = iter(known)
        for row in lineup.rows:
            rows.append(next(pending) if row.ref in rank else row)
        return replace(lineup, rows=tuple(rows)), Outcome()

    return _with_lineup(lineup_id, edit)


def set_kept(lineup_id: str, refs: Iterable[ItemRef], kept: bool) -> Operation:
    """Keep This Item (on), or give the item back to its rules (off).

    Turning Keep off on an item no rule claims would make it leave at the next
    refresh, so a hand-added item stays "added"; only Keep itself is cleared.
    """
    wanted = set(refs)

    def edit(lineup: Lineup) -> tuple[Lineup, Outcome] | None:
        if not any(row.ref in wanted for row in lineup.rows):
            return None
        rows = []
        for row in lineup.rows:
            if row.ref in wanted:
                if kept:
                    row = replace(row, held=HELD_KEPT)
                elif row.held == HELD_KEPT:
                    row = replace(row, held=None if row.claims else HELD_ADDED)
            rows.append(row)
        return replace(lineup, rows=tuple(rows)), Outcome(
            select=tuple(r for r in refs if r in wanted)
        )

    return _with_lineup(lineup_id, edit)


def remove_rows(lineup_id: str, refs: Iterable[ItemRef], *, now: float | None = None) -> Operation:
    """Delete: the rows go to Removed Items, and no rule brings them back."""
    wanted = set(refs)
    moment = time.time() if now is None else now

    def edit(lineup: Lineup) -> tuple[Lineup, Outcome] | None:
        gone = [row for row in lineup.rows if row.ref in wanted]
        if not gone:
            return None
        index = min(lineup.rows.index(row) for row in gone)
        rows = tuple(row for row in lineup.rows if row.ref not in wanted)
        already = lineup.removed_tokens
        removed = (
            *(Removed(row.ref, row.name, moment) for row in gone if row.ref.token not in already),
            *lineup.removed,
        )
        # The cursor goes to the row that took the first removed row's place.
        follow = (rows[min(index, len(rows) - 1)].ref,) if rows else ()
        return replace(lineup, rows=rows, removed=removed), Outcome(select=follow)

    return _with_lineup(lineup_id, edit)


def restore_rows(
    lineup_id: str,
    entries: Sequence[Row],
    *,
    at: Mapping[ItemRef, ItemRef | None] | None = None,
) -> Operation:
    """Undo of a remove or a move-out: put rows back, after their old neighbours.

    *at* maps a row to the item it followed (``None`` = the top). A neighbour
    that has left since puts the row at the end rather than guessing.
    """

    def edit(lineup: Lineup) -> tuple[Lineup, Outcome] | None:
        rows = [row for row in lineup.rows if row.ref not in {e.ref for e in entries}]
        for entry in entries:
            anchor = (at or {}).get(entry.ref, ...)
            if anchor is None:
                position = 0
            elif anchor is ...:
                position = len(rows)
            else:
                found = next((i for i, row in enumerate(rows) if row.ref == anchor), None)
                position = len(rows) if found is None else found + 1
            rows.insert(position, entry)
        restored = {entry.ref for entry in entries}
        removed = tuple(item for item in lineup.removed if item.ref not in restored)
        left = tuple(item for item in lineup.recently_left if item.ref not in restored)
        return replace(lineup, rows=tuple(rows), removed=removed, recently_left=left), Outcome(
            select=tuple(entry.ref for entry in entries)
        )

    return _with_lineup(lineup_id, edit)


def restore_removed(
    lineup_id: str, refs: Iterable[ItemRef], *, now: float | None = None
) -> Operation:
    """Bring Removed Items back, as Kept rows at the end."""
    return _restore_from(lineup_id, refs, "removed", now)


def restore_left(lineup_id: str, refs: Iterable[ItemRef], *, now: float | None = None) -> Operation:
    """Bring Recently Left items back, as Kept rows at the end."""
    return _restore_from(lineup_id, refs, "left", now)


def _restore_from(
    lineup_id: str, refs: Iterable[ItemRef], which: str, now: float | None
) -> Operation:
    wanted = set(refs)
    moment = time.time() if now is None else now

    def edit(lineup: Lineup) -> tuple[Lineup, Outcome] | None:
        source: Sequence[Removed | Departure] = (
            lineup.removed if which == "removed" else lineup.recently_left
        )
        found = [entry for entry in source if entry.ref in wanted]
        if not found:
            return None
        present = {row.ref for row in lineup.rows}
        new_rows = tuple(
            Row(ref=entry.ref, name=entry.name, held=HELD_KEPT, arrived=moment)
            for entry in found
            if entry.ref not in present
        )
        rows = (
            tuple(replace(row, held=HELD_KEPT) if row.ref in wanted else row for row in lineup.rows)
            + new_rows
        )
        released = {
            rid: tuple(t for t in tokens if t not in {r.token for r in wanted})
            for rid, tokens in lineup.released.items()
        }
        changed = replace(
            lineup,
            rows=rows,
            removed=tuple(e for e in lineup.removed if e.ref not in wanted),
            recently_left=tuple(e for e in lineup.recently_left if e.ref not in wanted),
            released={rid: tokens for rid, tokens in released.items() if tokens},
        )
        return changed, Outcome(select=tuple(entry.ref for entry in found))

    return _with_lineup(lineup_id, edit)


def clear_list(lineup_id: str, which: str) -> Operation:
    """Empty Removed Items (``"removed"``) or Recently Left (``"left"``)."""

    def edit(lineup: Lineup) -> tuple[Lineup, Outcome]:
        if which == "removed":
            return replace(lineup, removed=()), Outcome()
        return replace(lineup, recently_left=()), Outcome()

    return _with_lineup(lineup_id, edit)


# -- rules -------------------------------------------------------------------------


def set_rules(
    lineup_id: str,
    rules: Sequence[Rule],
    *,
    keep_items_of_deleted: bool = True,
    now: float | None = None,
) -> Operation:
    """Replace the rules. A deleted rule's items become Kept, or are let go.

    The choice is the listener's, asked by the rule editor ("Rule 2 brought in 6
    items. Keep them, or let them go?"); either way nothing vanishes without
    trace -- let-go items go to Recently Left.
    """
    moment = time.time() if now is None else now

    def edit(lineup: Lineup) -> tuple[Lineup, Outcome]:
        keep_ids = {rule.id for rule in rules}
        numbers = {rule.id: index + 1 for index, rule in enumerate(lineup.rules)}
        rows: list[Row] = []
        departures: list[Departure] = []
        for row in lineup.rows:
            gone = [rid for rid in row.claims if rid not in keep_ids]
            if not gone:
                rows.append(row)
                continue
            claims = {rid: since for rid, since in row.claims.items() if rid in keep_ids}
            if claims or row.is_held:
                rows.append(replace(row, claims=claims))
            elif keep_items_of_deleted:
                rows.append(replace(row, claims={}, held=HELD_KEPT))
            else:
                departures.append(
                    Departure(
                        row.ref, row.name, f"rule {numbers.get(gone[0], '?')} was deleted", moment
                    )
                )
        released = {rid: tokens for rid, tokens in lineup.released.items() if rid in keep_ids}
        left = (*reversed(departures), *lineup.recently_left)[:RECENTLY_LEFT_LIMIT]
        changed = replace(
            lineup,
            rules=tuple(rules),
            rows=tuple(rows),
            released=released,
            recently_left=tuple(left),
        )
        return changed, Outcome()

    return _with_lineup(lineup_id, edit)


def items_of_rule(lineup: Lineup, rule_id: str) -> tuple[Row, ...]:
    """Rows only *rule_id* holds: what deleting that rule would affect."""
    return tuple(
        row
        for row in lineup.rows
        if row.claims and set(row.claims) == {rule_id} and not row.is_held
    )


# -- refresh ---------------------------------------------------------------------------


def apply_refresh(lineup_id: str, catalogue: Catalogue, *, now: float | None = None) -> Operation:
    """Run the rules on the Lineup *as it is in the file now*, under the lock.

    The catalogue is gathered outside the lock (it reads Radio's and Cast's
    files); only the fold is done inside it, on fresh state, so a move the other
    app made a moment ago is not undone by this refresh.
    """
    moment = time.time() if now is None else now

    def operation(book: LineupBook) -> tuple[LineupBook, Outcome]:
        lineup = book.find(lineup_id)
        if lineup is None:
            return book, Outcome(stale=True, lineup_id=lineup_id)
        result = refresh(lineup, catalogue, moment)
        if (
            result.lineup.rows == lineup.rows
            and result.lineup.released == lineup.released
            and not result.left
        ):
            # Nothing changed but the time: record it without churning revisions.
            touched = replace(lineup, refreshed_at=moment)
            return book.replace_lineup(touched), Outcome(refresh=result, lineup_id=lineup_id)
        return replace(book.replace_lineup(result.lineup), revision=book.revision + 1), Outcome(
            refresh=result, lineup_id=lineup_id
        )

    return operation


__all__ = [
    "MAX_NAME",
    "Operation",
    "Outcome",
    "add_items",
    "apply_refresh",
    "clean_name",
    "clear_list",
    "create_lineup",
    "delete_lineup",
    "duplicate_lineup",
    "items_of_rule",
    "move_lineup",
    "move_rows",
    "remove_rows",
    "rename_lineup",
    "restore_left",
    "restore_lineup",
    "restore_order",
    "restore_removed",
    "restore_rows",
    "set_kept",
    "set_rules",
    "set_settings",
    "unique_name",
]
