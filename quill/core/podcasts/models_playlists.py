"""Playlists: a saved, named list of episodes, and the rules that fill one.

Extracted from ``models.py`` under GATE-11 (extract, never rebaseline). A
coherent pair rather than a slice: a **Playlist** is what a listener saved, and
**PlaylistRules** is how a *smart* one keeps itself current.

The distinction the two types exist to hold, and the reason Cast has both:

* a **manual** playlist is a curated, ordered, self-healing list -- what you put
  in it stays in it, in the order you put it;
* a **smart** playlist is a question re-asked every time it is opened (which
  shows, which episode states, how recent, how long, sorted how), so it is never
  stale and never needs tending.

Both are distinct from the transient Play Queue and from the fixed pinned views,
which are the two things people most often confuse them with.

wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill.core.podcasts.models_queue import QueueItem, coerce_int

#: The episode states a smart playlist can filter on. Here rather than in
#: models.py because it exists only to constrain PlaylistRules.
PLAYLIST_STATUS_MODES = ("any", "unplayed", "in_progress", "played")


@dataclass(slots=True)
class PlaylistRules:
    """A Smart Playlist's matching criteria (Phase 5 §Playlists). Every
    field is a filter; its "no restriction" value (an empty list, 0, or
    "any") means that field doesn't narrow the result at all -- an
    all-defaults record matches every episode of every subscribed show."""

    #: Empty = every subscribed show.
    show_ids: list[str] = field(default_factory=list)
    episode_status: str = "any"  # one of PLAYLIST_STATUS_MODES
    published_within_days: int = 0  # 0 = no limit
    min_duration_minutes: int = 0  # 0 = no limit
    max_duration_minutes: int = 0  # 0 = no limit
    sort_mode: str = "date_newest"  # one of podcasts.sorting.EPISODE_SORT_MODES

    def to_dict(self) -> dict[str, object]:
        return {
            "show_ids": list(self.show_ids),
            "episode_status": self.episode_status,
            "published_within_days": self.published_within_days,
            "min_duration_minutes": self.min_duration_minutes,
            "max_duration_minutes": self.max_duration_minutes,
            "sort_mode": self.sort_mode,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> PlaylistRules:
        raw_show_ids = data.get("show_ids")
        status = str(data.get("episode_status", "any"))
        return cls(
            show_ids=[str(s) for s in raw_show_ids] if isinstance(raw_show_ids, list) else [],
            episode_status=status if status in PLAYLIST_STATUS_MODES else "any",
            published_within_days=max(0, coerce_int(data.get("published_within_days"), 0)),
            min_duration_minutes=max(0, coerce_int(data.get("min_duration_minutes"), 0)),
            max_duration_minutes=max(0, coerce_int(data.get("max_duration_minutes"), 0)),
            sort_mode=str(data.get("sort_mode", "date_newest")),
        )


@dataclass(slots=True)
class Playlist:
    """A saved, named collection of episodes (Phase 5 §Playlists) -- either
    a rule-based "Smart Playlist" (``kind="smart"``, auto-updating, resolved
    live from ``rules`` every time it's opened, the user-configurable
    counterpart to the built-in pinned views) or a manually curated
    "Playlist" (``kind="manual"``, an ordered list of specific episode
    references, the saved counterpart to the transient Play Queue)."""

    id: str
    name: str
    kind: str = "manual"  # "smart" | "manual"
    rules: PlaylistRules = field(default_factory=PlaylistRules)  # smart only
    items: list[QueueItem] = field(default_factory=list)  # manual only

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "rules": self.rules.to_dict(),
            "items": [item.to_dict() for item in self.items],
        }

    @classmethod
    def from_dict(cls, data: object) -> Playlist | None:
        if not isinstance(data, dict):
            return None
        playlist_id = str(data.get("id", "")).strip()
        name = str(data.get("name", "")).strip()
        if not playlist_id or not name:
            return None
        kind = str(data.get("kind", "manual"))
        rules_data = data.get("rules")
        items_raw = data.get("items")
        items: list[QueueItem] = []
        for entry in items_raw if isinstance(items_raw, list) else []:
            item = QueueItem.from_dict(entry)
            if item is not None:
                items.append(item)
        rules = (
            PlaylistRules.from_dict(rules_data) if isinstance(rules_data, dict) else PlaylistRules()
        )
        return cls(
            id=playlist_id,
            name=name,
            kind=kind if kind in ("smart", "manual") else "manual",
            rules=rules,
            items=items,
        )
