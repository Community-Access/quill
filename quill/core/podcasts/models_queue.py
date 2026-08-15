"""One queued episode, and the coercion every settings loader needs.

Extracted from ``models.py`` under GATE-11. Small, and here because two model
modules need it: a :class:`QueueItem` is what the Play Queue holds *and* what a
manual playlist holds, and putting it in either of those would make the other
import it -- which is a cycle waiting for the next change.

``coerce_int`` is the shared "a stored value is somebody else's input" helper.
Its one non-obvious rule is that a ``bool`` is **not** an int here: Python says
``True == 1``, and a settings file that stored ``true`` where a count belongs
means a mistake, not the number one.

wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass


def coerce_int(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value)) if value.strip() else default
        except ValueError:
            return default
    return default


@dataclass(slots=True)
class QueueItem:
    """One Play Queue slot: a cross-show episode reference (Phase 4 §Queue).

    Stored by ids, not object references, so the queue survives restarts and
    tolerates an episode disappearing (its slot resolves to nothing and is
    skipped at play time rather than crashing).
    """

    show_id: str
    episode_guid: str
    #: When this slot entered the queue (ISO 8601 UTC) -- the age Queue
    #: Expiration measures against ``PodcastSettings.queue_age_limit_days``.
    #: Additive: a queue written before 1.1.0 has no timestamp at all, and an
    #: empty value must read as "age unknown", which
    #: ``expiration.stamp_missing_added_at`` turns into "added just now" on
    #: first load. Reading it as "infinitely old" would silently empty
    #: everybody's queue on the first launch after updating.
    added_at: str = ""

    def to_dict(self) -> dict:
        return {
            "show_id": self.show_id,
            "episode_guid": self.episode_guid,
            "added_at": self.added_at,
        }

    @classmethod
    def from_dict(cls, data: object) -> QueueItem | None:
        if not isinstance(data, dict):
            return None
        show_id = str(data.get("show_id", "")).strip()
        episode_guid = str(data.get("episode_guid", "")).strip()
        if not show_id or not episode_guid:
            return None
        return cls(
            show_id=show_id,
            episode_guid=episode_guid,
            added_at=str(data.get("added_at", "")).strip(),
        )
