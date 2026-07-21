"""Recurring content plans with safeguards (PRD 18.9).

A ``RecurringPlan`` describes content that repeats on a cadence. Supported kinds
(PRD 18.9): ``fixed`` (same content each time), ``template`` (a template body),
``rotating`` (cycle through variants), ``rss`` (driven by an external feed),
``event_relative`` (a single post at an offset from an event), and
``anniversary`` (yearly). Two pure functions drive it, both clock-injectable so
they are unit-testable without a database:

- ``next_occurrence`` -- the next fire time strictly after a reference instant,
  or ``None`` if the plan has expired, is paused, or has no further occurrences.
- ``materialize`` -- up to ``count`` upcoming Draft-like payloads, each carrying
  the resolved text and the safeguard flags.

Safeguards (PRD 18.9): an expiration date stops occurrences; repeated content is
flagged as a duplicate; a plan can request review after N cycles; a plan pauses
after too many failures; and AI-generated content that has not been verified is
flagged (``ai_unverified``) rather than silently trusted -- QUILL never lets AI
change facts without current verification.

Timestamps are integer milliseconds since the Unix epoch (UTC); yearly and
interval math is done with :mod:`zoneinfo` so it stays timezone-correct.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

from quill_social.model import new_id, now_ms

DOC_KIND = "recurring_plan"

KINDS = ("fixed", "template", "rotating", "rss", "event_relative", "anniversary")

_MS_PER_DAY = 86_400_000


@dataclass
class RecurringPlan:
    """A repeating content plan (PRD 18.9).

    ``anchor_ms`` is the first occurrence for periodic kinds; ``interval_days``
    is the spacing between occurrences. ``event_ms`` + ``offset_ms`` define a
    single ``event_relative`` post. ``expiration_ms`` stops all occurrences.
    ``review_after_cycles`` and ``pause_after_failures`` are 0 to disable.
    """

    plan_id: str = field(default_factory=lambda: new_id("recur"))
    name: str = ""
    kind: str = "fixed"
    content: str = ""
    variants: list[str] = field(default_factory=list)
    targets: list[str] = field(default_factory=list)
    timezone: str = "UTC"
    anchor_ms: int = 0
    interval_days: int = 7
    event_ms: int = 0
    offset_ms: int = 0
    expiration_ms: int | None = None
    review_after_cycles: int = 0
    pause_after_failures: int = 0
    failure_count: int = 0
    paused: bool = False
    ai_generated: bool = False
    ai_verified: bool = False

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "name": self.name,
            "kind": self.kind,
            "content": self.content,
            "variants": list(self.variants),
            "targets": list(self.targets),
            "timezone": self.timezone,
            "anchor_ms": self.anchor_ms,
            "interval_days": self.interval_days,
            "event_ms": self.event_ms,
            "offset_ms": self.offset_ms,
            "expiration_ms": self.expiration_ms,
            "review_after_cycles": self.review_after_cycles,
            "pause_after_failures": self.pause_after_failures,
            "failure_count": self.failure_count,
            "paused": self.paused,
            "ai_generated": self.ai_generated,
            "ai_verified": self.ai_verified,
        }

    @classmethod
    def from_dict(cls, d: dict) -> RecurringPlan:
        return cls(
            plan_id=d.get("plan_id") or new_id("recur"),
            name=d.get("name", ""),
            kind=d.get("kind", "fixed"),
            content=d.get("content", ""),
            variants=list(d.get("variants", [])),
            targets=list(d.get("targets", [])),
            timezone=d.get("timezone", "UTC"),
            anchor_ms=int(d.get("anchor_ms", 0) or 0),
            interval_days=int(d.get("interval_days", 7) or 0),
            event_ms=int(d.get("event_ms", 0) or 0),
            offset_ms=int(d.get("offset_ms", 0) or 0),
            expiration_ms=d.get("expiration_ms"),
            review_after_cycles=int(d.get("review_after_cycles", 0) or 0),
            pause_after_failures=int(d.get("pause_after_failures", 0) or 0),
            failure_count=int(d.get("failure_count", 0) or 0),
            paused=bool(d.get("paused", False)),
            ai_generated=bool(d.get("ai_generated", False)),
            ai_verified=bool(d.get("ai_verified", False)),
        )


@dataclass
class Occurrence:
    """One materialized Draft-like payload from a recurring plan (PRD 18.9)."""

    plan_id: str
    cycle_index: int  # 0-based
    scheduled_for: int
    text: str
    targets: list[str] = field(default_factory=list)
    review_due: bool = False
    duplicate: bool = False
    ai_unverified: bool = False
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "cycle_index": self.cycle_index,
            "scheduled_for": self.scheduled_for,
            "text": self.text,
            "targets": list(self.targets),
            "review_due": self.review_due,
            "duplicate": self.duplicate,
            "ai_unverified": self.ai_unverified,
            "warnings": list(self.warnings),
        }


# -- helpers ------------------------------------------------------------------


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("UTC")


def should_pause(plan: RecurringPlan) -> bool:
    """True if the plan is paused or has hit its failure threshold (PRD 18.9)."""
    if plan.paused:
        return True
    return plan.pause_after_failures > 0 and plan.failure_count >= plan.pause_after_failures


def _expired(plan: RecurringPlan, ms: int) -> bool:
    return plan.expiration_ms is not None and ms > plan.expiration_ms


def _add_years(ms: int, years: int, zone: ZoneInfo) -> int:
    dt = datetime.fromtimestamp(ms / 1000, tz=zone)
    try:
        moved = dt.replace(year=dt.year + years)
    except ValueError:
        # Feb 29 -> Feb 28 on non-leap years.
        moved = dt.replace(year=dt.year + years, day=28)
    return int(moved.timestamp() * 1000)


def _cycle_of(plan: RecurringPlan, ms: int) -> int:
    """0-based cycle index of the occurrence at ``ms`` for periodic kinds."""
    if plan.interval_days <= 0:
        return 0
    return max(0, round((ms - plan.anchor_ms) / (plan.interval_days * _MS_PER_DAY)))


# -- occurrences --------------------------------------------------------------


def next_occurrence(
    plan: RecurringPlan, after_ms: int, *, now: int | None = None
) -> int | None:
    """Next fire time strictly after ``after_ms``, or ``None`` (PRD 18.9).

    Returns ``None`` when the plan is paused / past its failure threshold, when
    the computed time is past the expiration date, or when a one-shot
    (``event_relative``) occurrence is already behind ``after_ms``.
    """
    _ = now if now is not None else now_ms()
    if should_pause(plan):
        return None
    zone = _zone(plan.timezone)

    if plan.kind == "event_relative":
        occ = plan.event_ms + plan.offset_ms
        if occ <= after_ms or _expired(plan, occ):
            return None
        return occ

    if plan.kind == "anniversary":
        occ = plan.anchor_ms
        guard = 0
        while occ <= after_ms and guard < 1000:
            occ = _add_years(occ, 1, zone)
            guard += 1
        if occ <= after_ms or _expired(plan, occ):
            return None
        return occ

    # Periodic kinds: fixed, template, rotating, rss.
    if plan.interval_days <= 0:
        occ = plan.anchor_ms
        if occ <= after_ms or _expired(plan, occ):
            return None
        return occ
    step = plan.interval_days * _MS_PER_DAY
    if after_ms < plan.anchor_ms:
        occ = plan.anchor_ms
    else:
        elapsed = after_ms - plan.anchor_ms
        occ = plan.anchor_ms + (elapsed // step + 1) * step
    if _expired(plan, occ):
        return None
    return occ


def resolve_text(plan: RecurringPlan, cycle_index: int) -> str:
    """The content for a given cycle; ``rotating`` cycles through variants."""
    if plan.kind == "rotating" and plan.variants:
        return plan.variants[cycle_index % len(plan.variants)]
    return plan.content


def materialize(
    plan: RecurringPlan, count: int, *, now: int | None = None
) -> list[Occurrence]:
    """Up to ``count`` upcoming occurrences with safeguard flags (PRD 18.9).

    Stops early at the expiration date or when the plan is paused. Duplicate
    content across the produced set is flagged; ``review_after_cycles`` marks
    review-due occurrences; unverified AI content is flagged ``ai_unverified``.
    """
    if count <= 0 or should_pause(plan):
        return []
    ai_unverified = plan.ai_generated and not plan.ai_verified

    out: list[Occurrence] = []
    seen_text: set[str] = set()
    cursor = plan.anchor_ms - 1
    while len(out) < count:
        occ_ms = next_occurrence(plan, cursor, now=now)
        if occ_ms is None:
            break
        cursor = occ_ms
        cycle = _cycle_of(plan, occ_ms)
        text = resolve_text(plan, cycle)
        norm = " ".join(text.lower().split())
        duplicate = norm in seen_text and bool(norm)
        seen_text.add(norm)
        review_due = (
            plan.review_after_cycles > 0
            and (cycle + 1) % plan.review_after_cycles == 0
        )
        warnings: list[str] = []
        if duplicate:
            warnings.append("duplicate content: identical to an earlier occurrence")
        if review_due:
            warnings.append(
                f"review due after {plan.review_after_cycles} cycles"
            )
        if ai_unverified:
            warnings.append(
                "AI-generated content is not verified; check any facts before posting"
            )
        out.append(
            Occurrence(
                plan_id=plan.plan_id,
                cycle_index=cycle,
                scheduled_for=occ_ms,
                text=text,
                targets=list(plan.targets),
                review_due=review_due,
                duplicate=duplicate,
                ai_unverified=ai_unverified,
                warnings=warnings,
            )
        )
    return out


# -- persistence --------------------------------------------------------------


def save(store, plan: RecurringPlan) -> RecurringPlan:
    """Persist a recurring plan (kind ``recurring_plan``)."""
    store.put_document(DOC_KIND, plan.plan_id, plan.to_dict())
    return plan


def load(store, plan_id: str) -> RecurringPlan | None:
    data = store.get_document(DOC_KIND, plan_id)
    return RecurringPlan.from_dict(data) if data else None


def load_all(store) -> list[RecurringPlan]:
    return [RecurringPlan.from_dict(d) for d in store.list_documents(DOC_KIND)]
