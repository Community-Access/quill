"""What a refresh did, in words a person can hold (pure).

Counts first, sources by name only when something is wrong, ages as phrases
rather than timestamps - the same speech rules as everything else in the
radio. Automatic refreshes that changed nothing say nothing; a manual refresh
always answers, because the listener asked.
"""

from __future__ import annotations

from dataclasses import dataclass, field


def spoken_age(seconds: float | None) -> str:
    """An age as a phrase: "just now", "2 hours ago", "3 days ago"."""
    if seconds is None:
        return "never"
    if seconds < 90:
        return "just now"
    minutes = int(seconds // 60)
    if minutes < 90:
        return f"{minutes} minute{'' if minutes == 1 else 's'} ago"
    hours = int(seconds // 3600)
    if hours < 36:
        return f"{hours} hour{'' if hours == 1 else 's'} ago"
    days = int(seconds // 86400)
    return f"{days} day{'' if days == 1 else 's'} ago"


@dataclass(slots=True)
class SourceOutcome:
    """One source's part of a refresh."""

    source_id: str
    label: str
    status: str  # 'ok' | 'unchanged' | 'stale' | 'skipped'
    added: int = 0
    updated: int = 0
    vanished: int = 0
    error: str = ""


@dataclass(slots=True)
class RefreshSummary:
    """Everything one refresh run did."""

    outcomes: list[SourceOutcome] = field(default_factory=list)

    @property
    def added(self) -> int:
        return sum(o.added for o in self.outcomes)

    @property
    def updated(self) -> int:
        return sum(o.updated for o in self.outcomes)

    @property
    def vanished(self) -> int:
        return sum(o.vanished for o in self.outcomes)

    @property
    def unreachable(self) -> list[SourceOutcome]:
        return [o for o in self.outcomes if o.status == "stale"]

    @property
    def changed_anything(self) -> bool:
        return bool(self.added or self.updated or self.vanished or self.unreachable)

    def spoken(self) -> str:
        """The one-sentence announcement. Counts first; failures last."""
        if not self.outcomes:
            return "Nothing needed updating."
        parts: list[str] = []
        if self.added:
            parts.append(f"{self.added} new station{'' if self.added == 1 else 's'}")
        if self.updated:
            parts.append(f"{self.updated} updated")
        if self.vanished:
            parts.append(f"{self.vanished} no longer listed")
        body = ", ".join(parts) if parts else "no changes"
        bad = self.unreachable
        tail = ""
        if bad:
            names = ", ".join(o.label for o in bad[:3])
            tail = f" {names} could not be reached; keeping what you have."
        return f"Station catalog updated: {body}.{tail}".rstrip()

    def review_rows(self) -> list[str]:
        """One spoken sentence per source, for the review dialog."""
        rows: list[str] = []
        for o in self.outcomes:
            if o.status == "ok":
                rows.append(
                    f"{o.label}: {o.added} new, {o.updated} updated, {o.vanished} no longer listed."
                )
            elif o.status == "unchanged":
                rows.append(f"{o.label}: no changes.")
            elif o.status == "skipped":
                rows.append(f"{o.label}: not due yet.")
            else:
                reason = o.error or "could not be reached"
                rows.append(f"{o.label}: {reason}; keeping what you have.")
        return rows
