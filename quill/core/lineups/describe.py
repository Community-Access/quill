"""Every sentence Lineups speak or show, in one place, so wording is never retyped.

The rules of the house apply (CLAUDE.md, GATE-12 and GATE-13): say only what the
screen reader does not already say. Row text is read by the reader, so it is
built here once, in a fixed column order -- **name, kind, length, source,
state** -- with the name first so first-letter navigation lands on the thing
itself. Moves say the new position, never the row (the reader reads the row).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence

from quill.core.lineups.conditions import describe as describe_condition
from quill.core.lineups.fields import GROUP_FIELDS, ItemFacts, field_for
from quill.core.lineups.merge import RefreshResult
from quill.core.lineups.model import HELD_ADDED, HELD_KEPT, Lineup, Row
from quill.core.lineups.refs import KIND_LABELS, KIND_PLURALS, Presence
from quill.core.lineups.rules import (
    KEEP_ALWAYS,
    KEEP_FOLLOW,
    KEEP_FOR_DAYS,
    KEEP_STRENGTH,
    KEEP_UNTIL_DONE,
    KEEP_UNTIL_DONE_OR_DAYS,
    MATCH_ANY,
    SORT_LABELS,
    SORT_SOURCE,
    Keep,
    Rule,
)


def minutes_text(seconds: int) -> str:
    """ "32 minutes", "1 hour 5 minutes"; ``""`` for unknown."""
    if seconds <= 0:
        return ""
    minutes = max(1, round(seconds / 60))
    hours, rest = divmod(minutes, 60)
    parts = []
    if hours:
        parts.append("1 hour" if hours == 1 else f"{hours} hours")
    if rest or not hours:
        parts.append("1 minute" if rest == 1 else f"{rest} minutes")
    return " ".join(parts)


def count_text(count: int, noun: str) -> str:
    """ "1 item", "3 items": every count said the same way."""
    return f"1 {noun}" if count == 1 else f"{count} {noun}s"


def _days(days: int) -> str:
    return "1 day" if days == 1 else f"{days} days"


def keep_phrase(keep: Keep, kind: str) -> str:
    """How long a rule's items stay, as the end of its sentence."""
    effective = keep.effective(kind)
    mode = effective.mode
    if mode == KEEP_ALWAYS:
        text = "They always stay."
    elif mode == KEEP_UNTIL_DONE:
        text = "They go once finished."
    elif mode == KEEP_FOR_DAYS:
        text = f"They stay {_days(effective.days)}."
    elif mode == KEEP_UNTIL_DONE_OR_DAYS:
        text = f"They go once finished, or after {_days(effective.days)}."
    else:
        text = "They go when they stop matching."
    if effective.max_kept:
        text += f" At most {effective.max_kept} are kept."
    return text


def _scope_text(rule: Rule, known: Mapping[str, frozenset[str]] | None) -> str:
    parts = []
    for field_id, values in rule.scope:
        if not values:
            continue
        found = field_for(rule.kind, field_id)
        label = (found.label if found is not None else field_id).lower()
        names = []
        for value in values:
            text = f'"{value}"'
            if known is not None and field_id in known and value.casefold() not in known[field_id]:
                text += ", which does not exist"
            names.append(text)
        parts.append(f"{label} {' or '.join(names)}")
    return " and ".join(parts)


def rule_sentence(
    rule: Rule,
    *,
    finds: int | None = None,
    known: Mapping[str, frozenset[str]] | None = None,
) -> str:
    """The whole rule as one sentence, including how long its items stay.

    "Podcast episodes in folder "News", where Played is no and Age is at most 1
    days, newest first, at most 10. They go once finished. Finds 7 now."

    *known* maps a scope field to the values that exist (case-folded), so a
    rule naming a folder the listener does not have says so rather than
    quietly finding nothing.
    """
    head = KIND_PLURALS.get(rule.kind, f"Items of an unknown kind ({rule.kind})")
    text = head
    scope = _scope_text(rule, known)
    if scope:
        text += f" in {scope}"
    if rule.tests:
        joiner = " or " if rule.match == MATCH_ANY else " and "
        text += ", where " + joiner.join(describe_condition(test, rule.kind) for test in rule.tests)
    extras = []
    if rule.sort != SORT_SOURCE:
        extras.append(SORT_LABELS.get(rule.sort, rule.sort))
    if rule.per_group:
        group = GROUP_FIELDS.get(rule.kind, ("", "group"))[1]
        extras.append(f"at most {rule.per_group} per {group}")
    if rule.budget_minutes:
        extras.append(f"up to {minutes_text(rule.budget_minutes * 60)} in all")
    if rule.limit:
        extras.append(f"no more than {count_text(rule.limit, 'item')}")
    if extras:
        text += ", " + ", ".join(extras)
    text += ". " + keep_phrase(rule.keep, rule.kind)
    if not rule.enabled:
        text += " This rule is switched off."
    elif not rule.usable:
        text += " It finds nothing until it is fixed."
    elif finds is not None:
        text += " Finds nothing now." if finds == 0 else f" Finds {finds} now."
    return text


def known_scope_values(items: Iterable[ItemFacts], kind: str) -> dict[str, frozenset[str]]:
    """For *kind*: each scope field's values that exist, case-folded."""
    values: dict[str, set[str]] = {}
    for item in items:
        if item.ref.kind != kind:
            continue
        for field_id, fact in item.facts.items():
            if isinstance(fact, str) and fact:
                values.setdefault(field_id, set()).add(fact.casefold())
            elif isinstance(fact, tuple):
                values.setdefault(field_id, set()).update(str(v).casefold() for v in fact)
        if item.source:
            values.setdefault("source", set()).add(item.source.casefold())
    return {field_id: frozenset(found) for field_id, found in values.items()}


def state_word(row: Row, presence: Presence, *, finished: bool = False, live: bool = False) -> str:
    """The rare last column: kept, added, missing, unavailable, played, live."""
    words = []
    if presence is Presence.MISSING:
        words.append("missing")
    elif presence is Presence.UNAVAILABLE:
        words.append("unavailable")
    if live:
        words.append("live")
    if finished:
        words.append("played")
    if row.held == HELD_KEPT:
        words.append("kept")
    return ", ".join(words)


def row_text(
    row: Row,
    item: ItemFacts | None,
    presence: Presence,
) -> str:
    """One row as the reader hears it: name, kind, length, source, state."""
    name = (item.name if item is not None and item.name else row.name) or "Unnamed item"
    parts = [name, KIND_LABELS.get(row.ref.kind, row.ref.kind)]
    if item is not None:
        length = "" if item.live else minutes_text(item.length_seconds)
        if length:
            parts.append(length)
        if item.source and item.source.casefold() != name.casefold():
            parts.append(item.source)
    state = state_word(
        row,
        presence,
        finished=bool(item is not None and item.finished),
        live=bool(item is not None and item.live),
    )
    if state:
        parts.append(state)
    return ", ".join(parts)


def lineup_row_text(
    lineup: Lineup, *, total_seconds: int = 0, new: int = 0, is_start: bool = False
) -> str:
    """A Lineup in the Lineups list: "Morning, 14 items, 1 hour 50 minutes, 2 new"."""
    count = len(lineup.rows)
    parts = [lineup.name or "Untitled lineup", "1 item" if count == 1 else f"{count} items"]
    length = minutes_text(total_seconds)
    if length:
        parts.append(length)
    if new:
        parts.append(f"{new} new")
    if is_start:
        parts.append("start lineup")
    return ", ".join(parts)


def _rule_number(lineup: Lineup, rule_id: str) -> int:
    for index, rule in enumerate(lineup.rules):
        if rule.id == rule_id:
            return index + 1
    return 0


def why_text(lineup: Lineup, row: Row, item: ItemFacts | None, *, now: float) -> str:
    """Why Is This Here: the reason first, then how long it will stay."""
    where = f"In {lineup.name}"
    if row.held == HELD_ADDED and not row.claims:
        return f"{where} because you added it. It stays until you remove it."
    if row.held == HELD_KEPT:
        return f"{where} because you kept it. It stays whatever the rules say, until you remove it."
    claims = sorted(
        ((lineup.rule_for(rid), since) for rid, since in row.claims.items()),
        key=lambda pair: -KEEP_STRENGTH.get(pair[0].keep.mode, 0) if pair[0] else 0,
    )
    rules = [(rule, since) for rule, since in claims if rule is not None]
    if not rules:
        return f"{where}, though no rule claims it now."
    numbers = [str(_rule_number(lineup, rule.id)) for rule, _since in rules]
    if len(rules) == 1:
        lead = f"{where} because rule {numbers[0]} found it: {rule_sentence(rules[0][0])}"
    else:
        listed = ", ".join(numbers[:-1]) + f" and {numbers[-1]}"
        lead = f"{where} because rules {listed} found it."
    strongest, since = rules[0]
    keep = strongest.keep.effective(strongest.kind)
    tail = ""
    if keep.mode in (KEEP_FOR_DAYS, KEEP_UNTIL_DONE_OR_DAYS):
        remaining = keep.days * 86_400 - (now - since)
        days_left = max(0, int(remaining // 86_400))
        left = "less than a day" if days_left == 0 else _days(days_left)
        tail = f" {left} left."
    if len(rules) > 1:
        tail = f" Rule {numbers[0]} keeps it longest: {keep_phrase(keep, strongest.kind)}" + tail
    elif keep.mode == KEEP_FOLLOW:
        tail = ""
    elif keep.mode == KEEP_UNTIL_DONE and item is not None and item.position_fraction > 0:
        tail = f" You have heard {round(item.position_fraction * 100)} percent."
    return lead + tail


def refresh_sentence(result: RefreshResult, *, selected_left: str = "") -> str:
    """What a refresh did, said once: "2 added, 1 left." or ``""`` for no change.

    *selected_left* is the reason the item under the cursor left, said first in
    the sentence; the window says the sentence once the cursor has moved.
    """
    parts = []
    if selected_left:
        parts.append(f"Your item left: {selected_left}.")
    added, left = len(result.added), len(result.left)
    if added or left:
        bits = []
        if added:
            bits.append(f"{added} added")
        if left:
            bits.append(f"{left} left")
        parts.append(", ".join(bits) + ".")
    if result.big_loss:
        reasons = sorted({departure.reason for departure in result.left})
        why = reasons[0] if len(reasons) == 1 else "several reasons"
        # The count was said a moment ago; this says why, and where they went (N3).
        parts.append(f"The reason: {why}. Recently Left can bring them back.")
    return " ".join(parts)


def summary_text(lineup: Lineup, lengths: Mapping[object, int], *, refreshed: str = "") -> str:
    """Lineup Summary (Ctrl+T) and the status bar: count, time, last update."""
    total = sum(max(0, lengths.get(row.ref, 0)) for row in lineup.rows)
    count = len(lineup.rows)
    text = f"{lineup.name}: " + ("1 item" if count == 1 else f"{count} items")
    length = minutes_text(total)
    if length:
        text += f", {length}"
    text += "."
    if refreshed:
        text += f" Updated {refreshed}."
    if not count:
        text = f"{lineup.name} is empty." + (
            " Its rules find nothing now." if lineup.rules else " Add items, or give it rules."
        )
    return text


def list_sentence(names: Sequence[str], *, limit: int = 3) -> str:
    """ "A, B and 4 more" for short confirmations."""
    names = [n for n in names if n]
    if not names:
        return ""
    if len(names) <= limit:
        return names[0] if len(names) == 1 else ", ".join(names[:-1]) + f" and {names[-1]}"
    return ", ".join(names[:limit]) + f" and {len(names) - limit} more"


__all__ = [
    "keep_phrase",
    "lineup_row_text",
    "list_sentence",
    "minutes_text",
    "refresh_sentence",
    "row_text",
    "rule_sentence",
    "state_word",
    "summary_text",
    "why_text",
]
