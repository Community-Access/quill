"""A rule: what kind of thing, where to look, which ones, in what order, how many,
and -- the half most smart lists forget -- how long they stay.

Tests decide what **comes in**; :class:`Keep` decides when it **goes**. The two
are separate on purpose: a news station should never leave, a new video should
stay a few days even after the channel's feed rolls it off, and an episode
should stay until it is heard even once it is no longer "published this week".

Evaluation follows Cast's smart playlists (``quill.core.podcasts.playlists``):
scope is always ANDed, one predicate per test that is set (an empty rule never
makes "any" match everything), then sort, then the limits.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace

from quill.core.lineups.conditions import Condition, matches
from quill.core.lineups.fields import GROUP_FIELDS, ItemFacts, field_for
from quill.core.lineups.refs import FINISHABLE_KINDS, KINDS

# -- Keep ------------------------------------------------------------------------

KEEP_FOLLOW = "follow"
KEEP_UNTIL_DONE = "until_done"
KEEP_FOR_DAYS = "for_days"
KEEP_UNTIL_DONE_OR_DAYS = "until_done_or_days"
KEEP_ALWAYS = "always"

KEEP_MODES: tuple[str, ...] = (
    KEEP_FOLLOW,
    KEEP_UNTIL_DONE,
    KEEP_FOR_DAYS,
    KEEP_UNTIL_DONE_OR_DAYS,
    KEEP_ALWAYS,
)

#: The choice as the rule editor offers it.
KEEP_LABELS: dict[str, str] = {
    KEEP_FOLLOW: "While it matches",
    KEEP_UNTIL_DONE: "Until finished",
    KEEP_FOR_DAYS: "For a number of days",
    KEEP_UNTIL_DONE_OR_DAYS: "Until finished, or a number of days",
    KEEP_ALWAYS: "Always",
}

#: Which reason "Why Is This Here" gives first when several rules hold an item:
#: the one that will keep it longest. (An item stays while *any* claim holds it;
#: this order only chooses the sentence.)
KEEP_STRENGTH: dict[str, int] = {
    KEEP_FOLLOW: 0,
    KEEP_FOR_DAYS: 1,
    KEEP_UNTIL_DONE_OR_DAYS: 2,
    KEEP_UNTIL_DONE: 3,
    KEEP_ALWAYS: 4,
}

DEFAULT_DAYS = 7
DEFAULT_PERCENT = 95


@dataclass(frozen=True, slots=True)
class Keep:
    """When a rule lets its items go."""

    mode: str = KEEP_FOLLOW
    days: int = DEFAULT_DAYS
    #: "Finished" means heard past this percentage (Cast's own "played" also counts).
    percent: int = DEFAULT_PERCENT
    #: Keep at most this many from the rule, oldest arrivals leaving first; 0 = no cap.
    max_kept: int = 0

    def effective(self, kind: str) -> Keep:
        """The policy as it can actually apply to *kind*.

        A station is never "finished", so "Until finished" on a station rule would
        mean "forever" by accident; it reads as "While it matches" instead, and a
        "finished or N days" choice keeps only its days.
        """
        if kind in FINISHABLE_KINDS:
            return self
        if self.mode == KEEP_UNTIL_DONE:
            return replace(self, mode=KEEP_FOLLOW)
        if self.mode == KEEP_UNTIL_DONE_OR_DAYS:
            return replace(self, mode=KEEP_FOR_DAYS)
        return self

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {"mode": self.mode}
        if self.mode in (KEEP_FOR_DAYS, KEEP_UNTIL_DONE_OR_DAYS):
            data["days"] = self.days
        if self.mode in (KEEP_UNTIL_DONE, KEEP_UNTIL_DONE_OR_DAYS):
            data["percent"] = self.percent
        if self.max_kept:
            data["max_kept"] = self.max_kept
        return data

    @classmethod
    def from_dict(cls, data: object) -> Keep:
        if not isinstance(data, dict):
            return cls()
        mode = str(data.get("mode", KEEP_FOLLOW) or KEEP_FOLLOW)
        if mode not in KEEP_MODES:
            # A choice from a newer build: the cautious reading keeps things
            # rather than letting them go.
            mode = KEEP_ALWAYS
        return cls(
            mode=mode,
            days=_clamp(data.get("days"), 1, 365, DEFAULT_DAYS),
            percent=_clamp(data.get("percent"), 1, 100, DEFAULT_PERCENT),
            max_kept=_clamp(data.get("max_kept"), 0, 10_000, 0),
        )


def default_keep(kind: str) -> Keep:
    """What a new rule over *kind* keeps by default."""
    if kind in FINISHABLE_KINDS:
        return Keep(KEEP_UNTIL_DONE_OR_DAYS, days=DEFAULT_DAYS)
    return Keep(KEEP_FOLLOW)


def _clamp(value: object, low: int, high: int, default: int) -> int:
    try:
        number = int(str(value))
    except (TypeError, ValueError):
        return default
    return max(low, min(high, number))


# -- order -------------------------------------------------------------------------

SORT_SOURCE = "source"
SORT_NEWEST = "newest"
SORT_OLDEST = "oldest"
SORT_SHORTEST = "shortest"
SORT_LONGEST = "longest"
SORT_NAME = "name"
SORT_MOST_LISTENED = "most_listened"

SORTS: tuple[str, ...] = (
    SORT_SOURCE,
    SORT_NEWEST,
    SORT_OLDEST,
    SORT_SHORTEST,
    SORT_LONGEST,
    SORT_NAME,
    SORT_MOST_LISTENED,
)

SORT_LABELS: dict[str, str] = {
    SORT_SOURCE: "as the source orders them",
    SORT_NEWEST: "newest first",
    SORT_OLDEST: "oldest first",
    SORT_SHORTEST: "shortest first",
    SORT_LONGEST: "longest first",
    SORT_NAME: "by name",
    SORT_MOST_LISTENED: "most listened first",
}

MATCH_ALL = "all"
MATCH_ANY = "any"


@dataclass(frozen=True, slots=True)
class Rule:
    """One rule of a Lineup.

    ``scope`` is "where to look": each field's values are ORed ("folder is News
    or Tech"), and the fields are ANDed with each other and with the tests, as
    Cast scopes a smart playlist.
    """

    id: str
    kind: str
    scope: tuple[tuple[str, tuple[str, ...]], ...] = ()
    tests: tuple[Condition, ...] = ()
    match: str = MATCH_ALL
    sort: str = SORT_SOURCE
    #: At most this many matches; 0 = no limit.
    limit: int = 0
    #: At most this many per podcast / channel / album / folder; 0 = no limit.
    per_group: int = 0
    #: Matches up to this many minutes in total, in sort order; 0 = no budget.
    budget_minutes: int = 0
    keep: Keep = field(default_factory=Keep)
    enabled: bool = True

    @property
    def usable(self) -> bool:
        """A rule whose kind or any test this build cannot use matches nothing."""
        if self.kind not in KINDS:
            return False
        if any(field_for(self.kind, name) is None for name, _values in self.scope):
            return False
        return all(test.is_usable(self.kind) for test in self.tests)

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {"id": self.id, "kind": self.kind}
        if self.scope:
            data["scope"] = [{"field": name, "values": list(values)} for name, values in self.scope]
        if self.tests:
            data["tests"] = [test.to_dict() for test in self.tests]
        if self.match != MATCH_ALL:
            data["match"] = self.match
        if self.sort != SORT_SOURCE:
            data["sort"] = self.sort
        for key in ("limit", "per_group", "budget_minutes"):
            value = getattr(self, key)
            if value:
                data[key] = value
        data["keep"] = self.keep.to_dict()
        if not self.enabled:
            data["enabled"] = False
        return data

    @classmethod
    def from_dict(cls, data: object) -> Rule | None:
        if not isinstance(data, dict):
            return None
        rule_id = str(data.get("id", "") or "").strip()
        kind = str(data.get("kind", "") or "").strip()
        if not rule_id or not kind:
            return None
        scope: list[tuple[str, tuple[str, ...]]] = []
        for entry in data.get("scope") or []:
            if isinstance(entry, dict):
                values = entry.get("values")
                if isinstance(values, list):
                    scope.append((
                        str(entry.get("field", "")),
                        tuple(str(v) for v in values if str(v)),
                    ))
        tests = tuple(
            condition
            for condition in (Condition.from_dict(raw) for raw in data.get("tests") or [])
            if condition is not None
        )
        match = str(data.get("match", MATCH_ALL))
        sort = str(data.get("sort", SORT_SOURCE))
        return cls(
            id=rule_id,
            kind=kind,
            scope=tuple(scope),
            tests=tests,
            match=match if match in (MATCH_ALL, MATCH_ANY) else MATCH_ALL,
            sort=sort if sort in SORTS else SORT_SOURCE,
            limit=_clamp(data.get("limit"), 0, 10_000, 0),
            per_group=_clamp(data.get("per_group"), 0, 1_000, 0),
            budget_minutes=_clamp(data.get("budget_minutes"), 0, 100_000, 0),
            keep=Keep.from_dict(data.get("keep")),
            enabled=bool(data.get("enabled", True)),
        )


def new_rule_id() -> str:
    """A rule id: stable across renames and reorders, which is why claims use it."""
    return f"r{uuid.uuid4().hex[:10]}"


def new_rule(kind: str) -> Rule:
    """A fresh rule over *kind* with that kind's default Keep."""
    return Rule(id=new_rule_id(), kind=kind, keep=default_keep(kind))


# -- evaluation ----------------------------------------------------------------------


def _in_scope(rule: Rule, item: ItemFacts) -> bool:
    for name, values in rule.scope:
        if not values:
            continue
        actual = item.fact(name)
        wanted = {value.casefold() for value in values}
        if isinstance(actual, tuple):
            if not any(str(v).casefold() in wanted for v in actual):
                return False
        elif actual is None or str(actual).casefold() not in wanted:
            return False
    return True


def _passes(rule: Rule, item: ItemFacts) -> bool:
    if not rule.tests:
        return True
    results = (matches(test, item) for test in rule.tests)
    return any(results) if rule.match == MATCH_ANY else all(results)


def _sort(rule: Rule, items: list[ItemFacts]) -> list[ItemFacts]:
    if rule.sort == SORT_NEWEST:
        # Unknown dates sort last however the list is ordered.
        return sorted(items, key=lambda i: (i.published_at <= 0, -i.published_at))
    if rule.sort == SORT_OLDEST:
        return sorted(items, key=lambda i: (i.published_at <= 0, i.published_at))
    if rule.sort == SORT_SHORTEST:
        return sorted(items, key=lambda i: (i.length_seconds <= 0, i.length_seconds))
    if rule.sort == SORT_LONGEST:
        return sorted(items, key=lambda i: (i.length_seconds <= 0, -i.length_seconds))
    if rule.sort == SORT_NAME:
        return sorted(items, key=lambda i: i.name.casefold())
    if rule.sort == SORT_MOST_LISTENED:

        def listened(item: ItemFacts) -> int:
            value = item.fact("listened")
            return value if isinstance(value, int) and not isinstance(value, bool) else 0

        return sorted(items, key=lambda i: -listened(i))
    return items


def evaluate(rule: Rule, items: Iterable[ItemFacts]) -> list[ItemFacts]:
    """What *rule* finds among *items*, in its order, after its limits (pure)."""
    if not rule.enabled or not rule.usable:
        return []
    found = [
        item
        for item in items
        if item.ref.kind == rule.kind and _in_scope(rule, item) and _passes(rule, item)
    ]
    found = _sort(rule, found)
    if rule.per_group:
        group_field = GROUP_FIELDS.get(rule.kind, ("", ""))[0]
        if group_field:
            counts: dict[str, int] = {}
            kept: list[ItemFacts] = []
            for item in found:
                group = str(item.fact(group_field) or "").casefold()
                if counts.get(group, 0) < rule.per_group:
                    counts[group] = counts.get(group, 0) + 1
                    kept.append(item)
            found = kept
    if rule.budget_minutes:
        budget = rule.budget_minutes * 60
        total = 0
        within: list[ItemFacts] = []
        for item in found:
            if total + max(item.length_seconds, 0) > budget and within:
                break
            total += max(item.length_seconds, 0)
            within.append(item)
        found = within
    if rule.limit:
        found = found[: rule.limit]
    return found


def scope_values(rule: Rule, field_id: str) -> tuple[str, ...]:
    """The values *rule* scopes *field_id* to, or ``()``."""
    for name, values in rule.scope:
        if name == field_id:
            return values
    return ()


def with_scope(rule: Rule, field_id: str, values: Sequence[str]) -> Rule:
    """*rule* with *field_id*'s scope replaced (``()`` removes it)."""
    rest = tuple((name, vals) for name, vals in rule.scope if name != field_id)
    cleaned = tuple(v for v in (str(x).strip() for x in values) if v)
    return replace(rule, scope=(*rest, (field_id, cleaned)) if cleaned else rest)


__all__ = [
    "DEFAULT_DAYS",
    "DEFAULT_PERCENT",
    "KEEP_ALWAYS",
    "KEEP_FOLLOW",
    "KEEP_FOR_DAYS",
    "KEEP_LABELS",
    "KEEP_MODES",
    "KEEP_STRENGTH",
    "KEEP_UNTIL_DONE",
    "KEEP_UNTIL_DONE_OR_DAYS",
    "MATCH_ALL",
    "MATCH_ANY",
    "SORTS",
    "SORT_LABELS",
    "SORT_LONGEST",
    "SORT_MOST_LISTENED",
    "SORT_NAME",
    "SORT_NEWEST",
    "SORT_OLDEST",
    "SORT_SHORTEST",
    "SORT_SOURCE",
    "Keep",
    "Rule",
    "default_keep",
    "evaluate",
    "new_rule",
    "new_rule_id",
    "scope_values",
    "with_scope",
]
