"""A Lineup, its rows, and the two lists that make it trustworthy.

Each row remembers *why* it is there (:class:`Row`): which rules claim it and
since when, whether the listener's hand holds it, when it arrived. That small
record is what lets a refresh be predictable and lets "Why Is This Here" answer
honestly. Two lists stand beside the rows:

* **Removed Items** -- what the listener deleted. No rule ever brings these back.
* **Recently Left** -- what the rules let go, each with its reason, so nothing
  leaves without trace and anything can be restored.

Everything is immutable; edits return new objects (:mod:`quill.core.lineups.ops`).
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field, replace

from quill.core.lineups.refs import ItemRef
from quill.core.lineups.rules import Rule

HELD_KEPT = "kept"
HELD_ADDED = "added"
HELD_STATES = (HELD_KEPT, HELD_ADDED)

NEW_ITEMS_RULE_ORDER = "rule"
NEW_ITEMS_TOP = "top"
NEW_ITEMS_BOTTOM = "bottom"
NEW_ITEMS_PLACES = (NEW_ITEMS_RULE_ORDER, NEW_ITEMS_TOP, NEW_ITEMS_BOTTOM)
NEW_ITEMS_LABELS: dict[str, str] = {
    NEW_ITEMS_RULE_ORDER: "With the other items from the same rule",
    NEW_ITEMS_TOP: "At the top",
    NEW_ITEMS_BOTTOM: "At the bottom",
}

#: How many departures Recently Left remembers per Lineup.
RECENTLY_LEFT_LIMIT = 100


@dataclass(frozen=True, slots=True)
class Row:
    """One item in a Lineup, and why it is there."""

    ref: ItemRef
    #: The name last seen, so a row whose owner is unavailable or which has gone
    #: missing can still say what it was.
    name: str = ""
    #: rule id -> when that rule first claimed it (seconds since the epoch).
    claims: Mapping[str, float] = field(default_factory=dict)
    #: ``None``, ``"kept"`` (Keep This Item) or ``"added"`` (added by hand).
    held: str | None = None
    arrived: float = 0.0
    #: The listener moved it: a budget never leaves out a row somebody placed.
    moved: bool = False
    #: What the owner needs to play it, for kinds with no complete list (a
    #: station from a search, a video from a search result): the owner's own
    #: serialised form, opaque here. ``None`` when the owner can look it up.
    payload: Mapping[str, object] | None = None

    @property
    def is_held(self) -> bool:
        return self.held in HELD_STATES

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {"ref": self.ref.to_dict(), "arrived": self.arrived}
        if self.name:
            data["name"] = self.name
        if self.claims:
            data["claims"] = dict(sorted(self.claims.items()))
        if self.held:
            data["held"] = self.held
        if self.moved:
            data["moved"] = True
        if self.payload:
            data["payload"] = dict(self.payload)
        return data

    @classmethod
    def from_dict(cls, data: object) -> Row | None:
        if not isinstance(data, dict):
            return None
        ref = ItemRef.from_dict(data.get("ref"))
        if ref is None:
            return None
        claims_raw = data.get("claims")
        claims: dict[str, float] = {}
        if isinstance(claims_raw, dict):
            for rule_id, since in claims_raw.items():
                try:
                    claims[str(rule_id)] = float(since)
                except (TypeError, ValueError):
                    continue
        held = data.get("held")
        payload = data.get("payload")
        return cls(
            ref=ref,
            name=str(data.get("name", "") or ""),
            claims=claims,
            held=str(held) if held in HELD_STATES else None,
            arrived=_float(data.get("arrived")),
            moved=bool(data.get("moved", False)),
            payload=dict(payload) if isinstance(payload, dict) else None,
        )


@dataclass(frozen=True, slots=True)
class Departure:
    """An item a rule let go, and why. Shown in Recently Left."""

    ref: ItemRef
    name: str
    reason: str
    when: float

    def to_dict(self) -> dict[str, object]:
        return {
            "ref": self.ref.to_dict(),
            "name": self.name,
            "reason": self.reason,
            "when": self.when,
        }

    @classmethod
    def from_dict(cls, data: object) -> Departure | None:
        if not isinstance(data, dict):
            return None
        ref = ItemRef.from_dict(data.get("ref"))
        if ref is None:
            return None
        return cls(
            ref,
            str(data.get("name", "") or ""),
            str(data.get("reason", "") or ""),
            _float(data.get("when")),
        )


@dataclass(frozen=True, slots=True)
class Removed:
    """An item the listener deleted. No rule brings it back until it is restored."""

    ref: ItemRef
    name: str
    when: float

    def to_dict(self) -> dict[str, object]:
        return {"ref": self.ref.to_dict(), "name": self.name, "when": self.when}

    @classmethod
    def from_dict(cls, data: object) -> Removed | None:
        if not isinstance(data, dict):
            return None
        ref = ItemRef.from_dict(data.get("ref"))
        if ref is None:
            return None
        return cls(ref, str(data.get("name", "") or ""), _float(data.get("when")))


@dataclass(frozen=True, slots=True)
class Lineup:
    """A named, ordered list built by rules and arranged by hand."""

    id: str
    name: str
    rules: tuple[Rule, ...] = ()
    rows: tuple[Row, ...] = ()
    removed: tuple[Removed, ...] = ()
    recently_left: tuple[Departure, ...] = ()
    #: rule id -> item tokens that rule let go and must not bring straight back
    #: while it still matches them (a "for 3 days" video still in the feed).
    released: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    new_items: str = NEW_ITEMS_RULE_ORDER
    skip_live: bool = False
    #: The whole Lineup up to this many minutes when played through; 0 = none.
    budget_minutes: int = 0
    #: When rules last ran, for "Updated 6:02" (seconds since the epoch, 0 = never).
    refreshed_at: float = 0.0
    revision: int = 0

    def row_for(self, ref: ItemRef) -> Row | None:
        for row in self.rows:
            if row.ref == ref:
                return row
        return None

    def rule_for(self, rule_id: str) -> Rule | None:
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None

    @property
    def removed_tokens(self) -> frozenset[str]:
        return frozenset(entry.ref.token for entry in self.removed)

    def to_dict(self) -> dict[str, object]:
        data: dict[str, object] = {
            "id": self.id,
            "name": self.name,
            "rules": [rule.to_dict() for rule in self.rules],
            "rows": [row.to_dict() for row in self.rows],
            "revision": self.revision,
        }
        if self.removed:
            data["removed"] = [entry.to_dict() for entry in self.removed]
        if self.recently_left:
            data["recently_left"] = [entry.to_dict() for entry in self.recently_left]
        if self.released:
            data["released"] = {
                rid: list(tokens) for rid, tokens in sorted(self.released.items()) if tokens
            }
        if self.new_items != NEW_ITEMS_RULE_ORDER:
            data["new_items"] = self.new_items
        if self.skip_live:
            data["skip_live"] = True
        if self.budget_minutes:
            data["budget_minutes"] = self.budget_minutes
        if self.refreshed_at:
            data["refreshed_at"] = self.refreshed_at
        return data

    @classmethod
    def from_dict(cls, data: object) -> Lineup | None:
        if not isinstance(data, dict):
            return None
        lineup_id = str(data.get("id", "") or "").strip()
        if not lineup_id:
            return None
        rules = tuple(
            r for r in (Rule.from_dict(x) for x in _list(data.get("rules"))) if r is not None
        )
        rows: list[Row] = []
        seen: set[ItemRef] = set()
        for raw in _list(data.get("rows")):
            row = Row.from_dict(raw)
            if row is not None and row.ref not in seen:  # one row per item, always
                seen.add(row.ref)
                rows.append(row)
        released_raw = data.get("released")
        released: dict[str, tuple[str, ...]] = {}
        if isinstance(released_raw, dict):
            for rid, tokens in released_raw.items():
                if isinstance(tokens, list):
                    released[str(rid)] = tuple(str(t) for t in tokens)
        new_items = str(data.get("new_items", NEW_ITEMS_RULE_ORDER))
        return cls(
            id=lineup_id,
            name=str(data.get("name", "") or "Untitled lineup"),
            rules=rules,
            rows=tuple(rows),
            removed=tuple(
                r for r in (Removed.from_dict(x) for x in _list(data.get("removed"))) if r
            ),
            recently_left=tuple(
                d for d in (Departure.from_dict(x) for x in _list(data.get("recently_left"))) if d
            )[:RECENTLY_LEFT_LIMIT],
            released=released,
            new_items=new_items if new_items in NEW_ITEMS_PLACES else NEW_ITEMS_RULE_ORDER,
            skip_live=bool(data.get("skip_live", False)),
            budget_minutes=max(0, int(_float(data.get("budget_minutes")))),
            refreshed_at=_float(data.get("refreshed_at")),
            revision=max(0, int(_float(data.get("revision")))),
        )


@dataclass(frozen=True, slots=True)
class LineupBook:
    """Every Lineup, in the listener's order: the whole of ``lineups.json``."""

    lineups: tuple[Lineup, ...] = ()
    revision: int = 0
    #: Cast queue snapshots (playlist ids) already copied in, so the copy runs once.
    imported: tuple[str, ...] = ()

    def find(self, lineup_id: str) -> Lineup | None:
        for lineup in self.lineups:
            if lineup.id == lineup_id:
                return lineup
        return None

    def find_by_name(self, name: str) -> Lineup | None:
        wanted = name.strip().casefold()
        for lineup in self.lineups:
            if lineup.name.strip().casefold() == wanted:
                return lineup
        return None

    def replace_lineup(self, lineup: Lineup) -> LineupBook:
        lineups = tuple(lineup if item.id == lineup.id else item for item in self.lineups)
        return replace(self, lineups=lineups)


def new_lineup_id() -> str:
    return f"l{uuid.uuid4().hex[:10]}"


def _float(value: object) -> float:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return 0.0


def _list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


__all__ = [
    "HELD_ADDED",
    "HELD_KEPT",
    "HELD_STATES",
    "NEW_ITEMS_BOTTOM",
    "NEW_ITEMS_LABELS",
    "NEW_ITEMS_PLACES",
    "NEW_ITEMS_RULE_ORDER",
    "NEW_ITEMS_TOP",
    "RECENTLY_LEFT_LIMIT",
    "Departure",
    "Lineup",
    "LineupBook",
    "Removed",
    "Row",
    "new_lineup_id",
]
