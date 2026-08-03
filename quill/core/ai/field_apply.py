"""Field-by-field review of structured AI output (assessment finding 5e.38).

The generic shape for applying structured LLM output to a user's data: one
reviewable suggestion at a time — a guessed target field, the current value,
the proposed value — with the user accepting, skipping, or copying each. Never
a bulk overwrite: for prose edits the word-level diff review plays this role;
this module plays it for *fields* (metadata, front matter, forms).

wx-free, strict-typed. The dialog lives in ``quill/ui/field_apply_dialog.py``.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field

__all__ = ["ApplySession", "FieldSuggestion", "guess_target_field"]


def _normalize(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (name or "").casefold())


def guess_target_field(available: Sequence[str], suggested_name: str) -> str:
    """The best matching field in *available* for *suggested_name*, or "".

    Normalized (case/punctuation-insensitive) scoring: exact beats prefix
    beats substring. A guess is only a preselection — the reviewer confirms
    every application, so a wrong guess costs one arrow press, never data.
    """
    wanted = _normalize(suggested_name)
    if not wanted:
        return ""
    best = ""
    best_score = 0
    for name in available:
        candidate = _normalize(name)
        if not candidate:
            continue
        if candidate == wanted:
            score = 300
        elif candidate.startswith(wanted) or wanted.startswith(candidate):
            score = 200
        elif wanted in candidate or candidate in wanted:
            score = 100
        else:
            continue
        if score > best_score:
            best_score = score
            best = name
    return best


@dataclass(frozen=True, slots=True)
class FieldSuggestion:
    """One proposed value for one named field."""

    field: str
    value: str

    def summary(self) -> str:
        """A short spoken row label: field name and a preview of the value."""
        flat = " ".join(self.value.split())
        preview = flat[:60] + ("..." if len(flat) > 60 else "")
        return f"{self.field}: {preview}" if preview else f"{self.field}: (empty)"


@dataclass(slots=True)
class ApplySession:
    """Review state over a list of suggestions.

    ``statuses[i]`` is "pending", "accepted", or "skipped". The session never
    writes anywhere — the caller applies ``accepted_values()`` when the review
    ends, as one operation (one undo step).
    """

    suggestions: list[FieldSuggestion]
    statuses: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.statuses:
            self.statuses = ["pending"] * len(self.suggestions)

    def accept(self, index: int) -> None:
        self.statuses[index] = "accepted"

    def skip(self, index: int) -> None:
        self.statuses[index] = "skipped"

    def accepted_values(self) -> dict[str, str]:
        """Field -> value for every accepted suggestion, in review order."""
        return {
            suggestion.field: suggestion.value
            for suggestion, status in zip(self.suggestions, self.statuses, strict=True)
            if status == "accepted"
        }

    def next_pending(self, after: int) -> int:
        """Index of the next pending suggestion after *after*, or -1."""
        total = len(self.suggestions)
        for offset in range(1, total + 1):
            index = (after + offset) % total
            if self.statuses[index] == "pending":
                return index
        return -1

    def summary(self) -> str:
        accepted = sum(1 for status in self.statuses if status == "accepted")
        skipped = sum(1 for status in self.statuses if status == "skipped")
        pending = len(self.statuses) - accepted - skipped
        return f"{accepted} accepted, {skipped} skipped, {pending} to review."
