"""One refresh: what the rules find now, plus what the listener's hands did, gives
the list. Pure, deterministic, and the most-tested module in the package.

The guarantees, each a property test in ``tests/unit/core/lineups/``:

1. **Nothing leaves because something could not be checked.** A row whose owner
   is unavailable, or whose rule's kind could not be read, is left exactly as
   it was: no exit is evaluated for it.
2. **Nothing leaves without trace.** Every departure is recorded, with its
   reason, in Recently Left.
3. **A removed item never returns** from any rule.
4. **A kept or hand-added item never leaves** except by the listener's hand.
5. **Refresh never reorders.** Surviving rows keep their relative order; only
   arrivals and departures change the list.
6. **Refresh is idempotent.** Running it twice on the same facts at the same
   moment gives the same list as running it once.
7. **Time is measured, not counted.** "3 days" is 72 hours from the claim,
   however often refresh runs.
8. **An item stays while any claim holds it.** One rule letting go never drops
   an item another rule still wants.

A rule that lets an item go *while still matching it* (its days ran out, it was
finished, a cap pushed it out) remembers that in ``Lineup.released``, so the
very next refresh does not bring it straight back; the memory clears once the
rule stops matching the item, after which a fresh match is a fresh arrival.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, replace

from quill.core.lineups.fields import ItemFacts
from quill.core.lineups.model import (
    NEW_ITEMS_BOTTOM,
    NEW_ITEMS_TOP,
    RECENTLY_LEFT_LIMIT,
    Departure,
    Lineup,
    Row,
)
from quill.core.lineups.refs import ItemRef, Presence
from quill.core.lineups.rules import (
    KEEP_ALWAYS,
    KEEP_FOLLOW,
    KEEP_FOR_DAYS,
    KEEP_UNTIL_DONE,
    KEEP_UNTIL_DONE_OR_DAYS,
    Keep,
    Rule,
    evaluate,
)

DAY_SECONDS = 86_400

#: A refresh that would remove more than half the Lineup, and more than this
#: many items, is still applied -- but reported plainly (a clock change, a long
#: absence), so a Lineup can never empty silently.
BIG_LOSS_MINIMUM = 10


@dataclass(frozen=True, slots=True)
class Catalogue:
    """What the sources could see this time, per kind.

    ``items[kind]`` is ``None`` when that kind's owner could not be read. A kind
    in ``complete`` is listed in full, so a reference not found in it is
    missing; any other kind is only partly listed (a directory, a search), and
    a reference not found is unlisted, not missing.
    """

    items: Mapping[str, tuple[ItemFacts, ...] | None] = field(default_factory=dict)
    complete: frozenset[str] = frozenset()

    def available(self, kind: str) -> bool:
        return self.items.get(kind) is not None

    def all_items(self) -> Iterable[ItemFacts]:
        for entries in self.items.values():
            if entries:
                yield from entries

    def lookup(self, ref: ItemRef) -> tuple[Presence, ItemFacts | None]:
        entries = self.items.get(ref.kind)
        if entries is None:
            return Presence.UNAVAILABLE, None
        for item in entries:
            if item.ref == ref:
                return Presence.PRESENT, item
        if ref.kind in self.complete:
            return Presence.MISSING, None
        return Presence.UNLISTED, None


@dataclass(frozen=True, slots=True)
class RefreshResult:
    lineup: Lineup
    added: tuple[ItemRef, ...] = ()
    left: tuple[Departure, ...] = ()
    #: More than half the Lineup (and more than ten items) left in one refresh.
    big_loss: bool = False


def is_finished(item: ItemFacts | None, percent: int) -> bool:
    """Whether the owner says *item* has been heard to the end (or past *percent*)."""
    if item is None:
        return False
    return item.finished or item.position_fraction * 100 >= percent


def _plural_days(days: int) -> str:
    return "1 day passed" if days == 1 else f"{days} days passed"


def exit_reason(
    keep: Keep,
    *,
    still_matches: bool,
    since: float,
    item: ItemFacts | None,
    presence: Presence,
    now: float,
    rule_number: int,
) -> str | None:
    """Why a claim lets its item go now, or ``None`` when it holds (pure)."""
    if presence is Presence.MISSING:
        return None if keep.mode == KEEP_ALWAYS else "it no longer exists"
    if keep.mode == KEEP_ALWAYS:
        return None
    if keep.mode == KEEP_FOLLOW:
        return None if still_matches else f"it no longer matches rule {rule_number}"
    finished = keep.mode in (KEEP_UNTIL_DONE, KEEP_UNTIL_DONE_OR_DAYS) and is_finished(
        item, keep.percent
    )
    if finished:
        return "finished"
    timed = keep.mode in (KEEP_FOR_DAYS, KEEP_UNTIL_DONE_OR_DAYS)
    if timed and now - since >= keep.days * DAY_SECONDS:
        return _plural_days(keep.days)
    return None


def _active_rules(lineup: Lineup, catalogue: Catalogue) -> dict[str, Rule]:
    """Rules that can be evaluated now. Any other rule's claims are frozen."""
    return {
        rule.id: rule
        for rule in lineup.rules
        if rule.enabled and rule.usable and catalogue.available(rule.kind)
    }


def refresh(lineup: Lineup, catalogue: Catalogue, now: float) -> RefreshResult:
    """Run every rule against *catalogue* and fold the result into *lineup* (pure)."""
    active = _active_rules(lineup, catalogue)
    numbers = {rule.id: index + 1 for index, rule in enumerate(lineup.rules)}
    known_rules = set(numbers)
    matched: dict[str, list[ItemFacts]] = {
        rid: evaluate(rule, catalogue.items.get(rule.kind) or ()) for rid, rule in active.items()
    }
    matched_tokens = {
        rid: {item.ref.token: rank for rank, item in enumerate(items)}
        for rid, items in matched.items()
    }
    removed = lineup.removed_tokens
    released: dict[str, set[str]] = {
        rid: set(tokens) for rid, tokens in lineup.released.items() if rid in known_rules
    }

    def admits(rid: str, item: ItemFacts) -> bool:
        """Whether rule *rid* may claim *item* now (and remember it if not).

        A new claim passes the same exit test as an old one: an episode already
        heard does not arrive in an "Until finished" rule only to leave on the
        next refresh (guarantee 6). A refused claim is remembered as released.
        """
        token = item.ref.token
        if token in removed or token in released.get(rid, set()):
            return False
        rule = active[rid]
        refused = exit_reason(
            rule.keep.effective(rule.kind),
            still_matches=True,
            since=now,
            item=item,
            presence=Presence.PRESENT,
            now=now,
            rule_number=numbers[rid],
        )
        if refused is not None:
            released.setdefault(rid, set()).add(token)
            return False
        return True

    order = [rule.id for rule in lineup.rules if rule.id in active]
    survivors: list[Row] = []
    departures: list[Departure] = []
    departed: set[str] = set()
    for row in lineup.rows:
        presence, item = catalogue.lookup(row.ref)
        if presence is Presence.UNAVAILABLE:
            survivors.append(row)  # guarantee 1: never judged on what could not be read
            continue
        name = item.name if item is not None and item.name else row.name
        claims = dict(row.claims)
        # New claims first, so a row one rule lets go while another now wants it
        # simply stays where it is -- it never "leaves and comes back" at a new
        # position in the same refresh (guarantees 2 and 5).
        if item is not None:
            for rid in order:
                if rid not in claims and row.ref.token in matched_tokens[rid] and admits(rid, item):
                    claims[rid] = now
        reasons: list[str] = []
        for rid, since in list(claims.items()):
            if rid not in known_rules:
                del claims[rid]
                reasons.append("its rule was deleted")
                continue
            rule = active.get(rid)
            if rule is None:
                continue  # frozen: disabled, unusable or its kind unreadable
            reason = exit_reason(
                rule.keep.effective(rule.kind),
                still_matches=row.ref.token in matched_tokens[rid],
                since=since,
                item=item,
                presence=presence,
                now=now,
                rule_number=numbers[rid],
            )
            if reason is not None:
                del claims[rid]
                reasons.append(reason)
                if row.ref.token in matched_tokens[rid]:
                    released.setdefault(rid, set()).add(row.ref.token)
        updated = replace(row, name=name, claims=claims)
        if updated.is_held or claims:
            survivors.append(updated)
        elif row.claims:
            departed.add(row.ref.token)
            departures.append(Departure(row.ref, name, reasons[0] if reasons else "it left", now))

    # Arrivals: items no row holds yet, in each rule's own order. An item two
    # rules find arrives once, with both claims, in the same refresh --
    # otherwise a second refresh would add the second claim (guarantee 6).
    present = {row.ref.token for row in survivors} | departed
    pending: dict[str, tuple[ItemFacts, list[str]]] = {}
    for rid in order:
        for item in matched[rid]:
            token = item.ref.token
            if token in present or not admits(rid, item):
                continue
            if token in pending:
                pending[token][1].append(rid)
            else:
                pending[token] = (item, [rid])
    arrivals: dict[str, list[ItemFacts]] = {}
    for item, rids in pending.values():
        for rid in rids:
            arrivals.setdefault(rid, []).append(item)

    # Caps: a rule keeps at most N. The newest claims stay; among claims made
    # at the same moment, the rule's own order decides. Everything else is let
    # go (and remembered, so it does not come straight back).
    for rid, rule in active.items():
        cap = rule.keep.max_kept
        if not cap:
            continue
        ranks = matched_tokens[rid]
        unranked = len(ranks)
        entries: list[tuple[float, int, ItemRef, bool]] = [
            (row.claims[rid], ranks.get(row.ref.token, unranked), row.ref, False)
            for row in survivors
            if rid in row.claims
        ]
        entries += [
            (now, ranks.get(item.ref.token, unranked), item.ref, True)
            for item in arrivals.get(rid, [])
        ]
        if len(entries) <= cap:
            continue
        entries.sort(key=lambda entry: (-entry[0], entry[1]))
        dropped = entries[cap:]
        dropped_refs = {ref for _since, _rank, ref, _arriving in dropped}
        reason = f"rule {numbers[rid]} keeps at most {cap}"
        for _since, _rank, ref, arriving in dropped:
            released.setdefault(rid, set()).add(ref.token)
            if arriving:
                continue
            index = next(i for i, r in enumerate(survivors) if r.ref == ref)
            claims = {k: v for k, v in survivors[index].claims.items() if k != rid}
            if not claims and not survivors[index].is_held:
                departures.append(Departure(ref, survivors[index].name, reason, now))
            survivors[index] = replace(survivors[index], claims=claims)
        arrivals[rid] = [item for item in arrivals.get(rid, []) if item.ref not in dropped_refs]
    survivors = [row for row in survivors if row.is_held or row.claims]

    # Releases are forgotten once the rule stops matching the item.
    for rid in list(released):
        if rid in active:
            released[rid] &= set(matched_tokens[rid])

    # Who still claims each arrival after the caps; an arrival every claim
    # dropped does not arrive. Each is placed by its first remaining rule.
    claimants: dict[str, list[str]] = {}
    for rid in (rule.id for rule in lineup.rules):
        for item in arrivals.get(rid, []):
            claimants.setdefault(item.ref.token, []).append(rid)
    placed: dict[str, list[tuple[ItemFacts, list[str]]]] = {}
    for token, (item, _rids) in pending.items():
        still = claimants.get(token)
        if still:
            placed.setdefault(still[0], []).append((item, still))
    rows = _place_arrivals(lineup, survivors, placed, now)
    added = tuple(
        item.ref for rid in (r.id for r in lineup.rules) for item, _rids in placed.get(rid, [])
    )
    recently_left = (*reversed(departures), *lineup.recently_left)[:RECENTLY_LEFT_LIMIT]
    big_loss = len(departures) > BIG_LOSS_MINIMUM and len(departures) * 2 > len(lineup.rows)
    result = replace(
        lineup,
        rows=tuple(rows),
        recently_left=tuple(recently_left),
        released={rid: tuple(sorted(tokens)) for rid, tokens in released.items() if tokens},
        refreshed_at=now,
        revision=lineup.revision + 1,
    )
    return RefreshResult(result, added, tuple(departures), big_loss)


def _new_row(item: ItemFacts, rids: list[str], now: float) -> Row:
    return Row(ref=item.ref, name=item.name, claims=dict.fromkeys(rids, now), arrived=now)


def _place_arrivals(
    lineup: Lineup,
    survivors: list[Row],
    arrivals: Mapping[str, list[tuple[ItemFacts, list[str]]]],
    now: float,
) -> list[Row]:
    order = [rule.id for rule in lineup.rules]
    if not arrivals:
        return survivors
    if lineup.new_items in (NEW_ITEMS_TOP, NEW_ITEMS_BOTTOM):
        new_rows = [
            _new_row(item, rids, now) for rid in order for item, rids in arrivals.get(rid, [])
        ]
        return (
            [*new_rows, *survivors]
            if lineup.new_items == NEW_ITEMS_TOP
            else [*survivors, *new_rows]
        )
    rows = list(survivors)
    for position, rid in enumerate(order):
        items = arrivals.get(rid)
        if not items:
            continue
        new_rows = [_new_row(item, rids, now) for item, rids in items]
        last_own = max((i for i, row in enumerate(rows) if rid in row.claims), default=-1)
        if last_own >= 0:
            insert_at = last_own + 1
        else:
            later = set(order[position + 1 :])
            insert_at = next(
                (i for i, row in enumerate(rows) if later & set(row.claims) and not row.is_held),
                len(rows),
            )
        rows[insert_at:insert_at] = new_rows
    return rows


def budget_cut(lineup: Lineup, lengths: Mapping[ItemRef, int]) -> frozenset[ItemRef]:
    """Rows a play-through leaves out to keep within the Lineup's minutes.

    Rule rows are left out from the end; a kept, hand-added or moved row never
    is. *lengths* gives each row's seconds (unknown counts as 0).
    """
    if not lineup.budget_minutes:
        return frozenset()
    budget = lineup.budget_minutes * 60
    protected = [row for row in lineup.rows if row.is_held or row.moved]
    used = sum(max(lengths.get(row.ref, 0), 0) for row in protected)
    out: set[ItemRef] = set()
    for row in lineup.rows:
        if row.is_held or row.moved:
            continue
        seconds = max(lengths.get(row.ref, 0), 0)
        if used + seconds > budget:
            out.add(row.ref)
        else:
            used += seconds
    return frozenset(out)


__all__ = [
    "BIG_LOSS_MINIMUM",
    "DAY_SECONDS",
    "Catalogue",
    "RefreshResult",
    "budget_cut",
    "exit_reason",
    "is_finished",
    "refresh",
]
