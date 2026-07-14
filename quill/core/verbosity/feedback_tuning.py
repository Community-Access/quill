"""Local "Too Much / Too Little / Just Right" feedback tuning (verbosity §26).

The user can tell QUILL, per announcement, that it said too much, too little, or
got it just right. :class:`FeedbackStore` keeps those signals per verb, entirely
locally (no telemetry, no cloud), and offers a gentle, reversible suggestion
once a consistent pattern emerges. A declined suggestion is never repeated.

Pure and wx-free.
"""

from __future__ import annotations

from typing import Any

__all__ = ["FeedbackSignal", "FeedbackStore"]

#: Signals lead to a suggestion after this many consistent same-direction votes.
SUGGESTION_THRESHOLD = 3


class FeedbackSignal:
    """The three feedback values."""

    TOO_MUCH = "too_much"
    TOO_LITTLE = "too_little"
    JUST_RIGHT = "just_right"


class FeedbackStore:
    """Per-verb feedback tallies with a gentle, one-shot suggestion."""

    def __init__(self, *, threshold: int = SUGGESTION_THRESHOLD) -> None:
        self._threshold = max(1, threshold)
        self._too_much: dict[str, int] = {}
        self._too_little: dict[str, int] = {}
        self._declined: set[str] = set()

    def record(self, verb_id: str, signal: str) -> None:
        """Record one feedback signal for ``verb_id``.

        "Just right" clears the running tallies — the user is satisfied, so any
        building suggestion is reset.
        """
        if signal == FeedbackSignal.TOO_MUCH:
            self._too_much[verb_id] = self._too_much.get(verb_id, 0) + 1
            self._too_little[verb_id] = 0
        elif signal == FeedbackSignal.TOO_LITTLE:
            self._too_little[verb_id] = self._too_little.get(verb_id, 0) + 1
            self._too_much[verb_id] = 0
        elif signal == FeedbackSignal.JUST_RIGHT:
            self._too_much[verb_id] = 0
            self._too_little[verb_id] = 0

    def suggestion_for(self, verb_id: str) -> str | None:
        """Return a suggestion direction once a consistent pattern is reached.

        ``"reduce"`` when the user repeatedly says too much, ``"increase"`` when
        repeatedly too little, else ``None``. A declined verb never suggests.
        """
        if verb_id in self._declined:
            return None
        if self._too_much.get(verb_id, 0) >= self._threshold:
            return "reduce"
        if self._too_little.get(verb_id, 0) >= self._threshold:
            return "increase"
        return None

    def decline(self, verb_id: str) -> None:
        """Stop suggesting for ``verb_id`` and clear its tallies."""
        self._declined.add(verb_id)
        self._too_much[verb_id] = 0
        self._too_little[verb_id] = 0

    def reset(self) -> None:
        """Clear every signal and decline."""
        self._too_much.clear()
        self._too_little.clear()
        self._declined.clear()

    def to_dict(self) -> dict[str, Any]:
        return {
            "too_much": {k: v for k, v in self._too_much.items() if v},
            "too_little": {k: v for k, v in self._too_little.items() if v},
            "declined": sorted(self._declined),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FeedbackStore:
        store = cls()
        store._too_much = {str(k): int(v) for k, v in data.get("too_much", {}).items()}
        store._too_little = {str(k): int(v) for k, v in data.get("too_little", {}).items()}
        store._declined = {str(v) for v in data.get("declined", [])}
        return store
