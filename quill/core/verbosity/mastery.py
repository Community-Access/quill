"""Mastery-based step-down detection (verbosity §27).

When a user has driven a verb successfully many times, QUILL can offer to step
that verb down to a quieter profile. :class:`MasteryTracker` counts successful
uses per verb and signals exactly once when the threshold is crossed, so the
offer never nags. The 10-second offer dialog and its spoken countdown live in
the UI; this is the pure counting and policy layer.

Pure and wx-free.
"""

from __future__ import annotations

from typing import Any

__all__ = ["MasteryTracker"]

DEFAULT_THRESHOLD = 25


class MasteryTracker:
    """Counts per-verb successful uses and offers a step-down at threshold."""

    def __init__(self, *, threshold: int = DEFAULT_THRESHOLD, enabled: bool = True) -> None:
        self._threshold = max(1, threshold)
        self._enabled = enabled
        self._counts: dict[str, int] = {}
        self._disabled: set[str] = set()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def count_for(self, verb_id: str) -> int:
        return self._counts.get(verb_id, 0)

    def record_use(self, verb_id: str) -> bool:
        """Record one successful use; return True exactly when an offer is due.

        Returns False when mastery is disabled globally or for this verb. On the
        use that crosses the threshold, the counter resets so the same verb does
        not re-offer on every subsequent use.
        """
        if not self._enabled or verb_id in self._disabled:
            return False
        self._counts[verb_id] = self._counts.get(verb_id, 0) + 1
        if self._counts[verb_id] >= self._threshold:
            self._counts[verb_id] = 0
            return True
        return False

    def disable_verb(self, verb_id: str) -> None:
        """Stop offering step-downs for ``verb_id`` (e.g. the user declined)."""
        self._disabled.add(verb_id)

    def is_disabled(self, verb_id: str) -> bool:
        return verb_id in self._disabled

    def reset(self) -> None:
        """Clear all counters and per-verb disables."""
        self._counts.clear()
        self._disabled.clear()

    def to_dict(self) -> dict[str, Any]:
        return {
            "threshold": self._threshold,
            "enabled": self._enabled,
            "counts": dict(self._counts),
            "disabled": sorted(self._disabled),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MasteryTracker:
        tracker = cls(
            threshold=int(data.get("threshold", DEFAULT_THRESHOLD)),
            enabled=bool(data.get("enabled", True)),
        )
        tracker._counts = {str(k): int(v) for k, v in data.get("counts", {}).items()}
        tracker._disabled = {str(v) for v in data.get("disabled", [])}
        return tracker
