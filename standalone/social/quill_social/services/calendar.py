"""Accessible calendar views over publication plans (PRD 18.5).

The agenda list is the accessibility baseline (PRD 18.5): every entry exposes
all of its fields as plain text so a screen-reader user never depends on a
visual grid. This module is presentation-neutral -- it returns dataclasses and
grouped mappings, and the wx layer renders them -- so the views are fully
unit-testable.

Provided views:

- ``agenda`` -- one ordered ``AgendaEntry`` per plan, with date/time, time
  zone, account, network, campaign, state, preview, thread/media counts,
  approval state, conflict flag, and failure/retry state.
- ``group_by_day`` / ``group_by_week`` / ``group_by_month`` -- ordered mappings
  of a period key to its plans, in local time.
- ``conflicts`` -- pairs of plans on the same account scheduled closer than the
  minimum spacing.

Timestamps are integer milliseconds since the Unix epoch (UTC). Grouping and
labels are computed in a caller-supplied IANA time zone via :mod:`zoneinfo`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from quill_social.model import Campaign, Draft, PublicationPlan, now_ms

# States that represent an approval phase (PRD 18.8); once a plan is queued or
# later, approval is considered complete.
_APPROVAL_PHASES = frozenset({"idea", "draft", "ready", "changes_requested", "approved"})

_WEEKDAY_NAMES = (
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday",
)

_MS_PER_MIN = 60_000


@dataclass
class AgendaEntry:
    """One accessible agenda row for a publication plan (PRD 18.5).

    Every field is exposed as text via :meth:`describe` so the entry is fully
    legible to a screen reader without a visual calendar grid.
    """

    plan_id: str = ""
    when_ms: int | None = None
    when_text: str = "Unscheduled"
    timezone: str = "UTC"
    account_id: str = ""
    network: str = ""
    campaign: str = ""
    state: str = ""
    approval_state: str = ""
    preview: str = ""
    thread_count: int = 0
    media_count: int = 0
    conflict: bool = False
    failure_state: str = ""
    retry_count: int = 0
    next_retry_ms: int | None = None
    error_message: str = ""

    def describe(self) -> str:
        """A single spoken-friendly line covering every field (PRD 18.5)."""
        parts = [
            self.when_text,
            self.timezone,
            f"account {self.account_id}" if self.account_id else "no account",
            self.network or "unknown network",
            f"campaign {self.campaign}" if self.campaign else "no campaign",
            f"state {self.state}",
            f"approval {self.approval_state}",
        ]
        if self.thread_count > 1:
            parts.append(f"{self.thread_count} posts")
        if self.media_count:
            parts.append(f"{self.media_count} media")
        if self.conflict:
            parts.append("conflict")
        if self.failure_state:
            parts.append(self.failure_state)
        if self.preview:
            parts.append(f"preview: {self.preview}")
        return ", ".join(parts)

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "when_ms": self.when_ms,
            "when_text": self.when_text,
            "timezone": self.timezone,
            "account_id": self.account_id,
            "network": self.network,
            "campaign": self.campaign,
            "state": self.state,
            "approval_state": self.approval_state,
            "preview": self.preview,
            "thread_count": self.thread_count,
            "media_count": self.media_count,
            "conflict": self.conflict,
            "failure_state": self.failure_state,
            "retry_count": self.retry_count,
            "next_retry_ms": self.next_retry_ms,
            "error_message": self.error_message,
        }


@dataclass
class ConflictPair:
    """Two plans on one account scheduled closer than the minimum spacing."""

    first: PublicationPlan
    second: PublicationPlan
    gap_min: float = 0.0

    def to_dict(self) -> dict:
        return {
            "first": self.first.plan_id,
            "second": self.second.plan_id,
            "account_id": self.first.account_id,
            "gap_min": self.gap_min,
        }


# -- helpers ------------------------------------------------------------------


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo("UTC")


def _local(ms: int, zone: ZoneInfo) -> datetime:
    return datetime.fromtimestamp(ms / 1000, tz=zone)


def _when_text(ms: int | None, zone: ZoneInfo) -> str:
    if ms is None:
        return "Unscheduled"
    dt = _local(ms, zone)
    return f"{_WEEKDAY_NAMES[dt.weekday()]} {dt.strftime('%Y-%m-%d %H:%M')}"


def _approval_state(state: str) -> str:
    return state if state in _APPROVAL_PHASES else "approved"


def _failure_state(plan: PublicationPlan) -> str:
    if plan.state == "failed":
        return "failed"
    if plan.state == "partial":
        return "partial"
    if plan.next_retry_at:
        return "retry pending"
    return ""


def _sort_key(plan: PublicationPlan) -> tuple[int, int]:
    # Scheduled plans first in time order; unscheduled sort last by creation.
    if plan.scheduled_for is None:
        return (1, plan.created)
    return (0, plan.scheduled_for)


# -- conflicts ----------------------------------------------------------------


def conflicts(
    plans: list[PublicationPlan], min_spacing_min: int
) -> list[ConflictPair]:
    """Pairs of same-account plans scheduled closer than ``min_spacing_min``.

    Only scheduled plans (a ``scheduled_for`` set) participate. Terminal or
    cancelled plans are ignored. Pairs are returned in ascending time order.
    """
    if min_spacing_min <= 0:
        return []
    spacing_ms = min_spacing_min * _MS_PER_MIN
    by_account: dict[str, list[PublicationPlan]] = {}
    for plan in plans:
        if plan.scheduled_for is None or plan.state in ("cancelled", "archived"):
            continue
        by_account.setdefault(plan.account_id, []).append(plan)

    pairs: list[ConflictPair] = []
    for account_plans in by_account.values():
        ordered = sorted(account_plans, key=lambda p: p.scheduled_for or 0)
        for prev, curr in zip(ordered, ordered[1:], strict=False):
            gap = (curr.scheduled_for or 0) - (prev.scheduled_for or 0)
            if gap < spacing_ms:
                pairs.append(ConflictPair(prev, curr, round(gap / _MS_PER_MIN, 2)))
    pairs.sort(key=lambda c: c.first.scheduled_for or 0)
    return pairs


def _conflicting_ids(plans: list[PublicationPlan], min_spacing_min: int) -> set[str]:
    ids: set[str] = set()
    for pair in conflicts(plans, min_spacing_min):
        ids.add(pair.first.plan_id)
        ids.add(pair.second.plan_id)
    return ids


# -- agenda -------------------------------------------------------------------


def agenda(
    plans: list[PublicationPlan],
    *,
    now: int | None = None,
    tz: str = "UTC",
    drafts: dict[str, Draft] | None = None,
    campaigns: dict[str, Campaign] | None = None,
    min_spacing_min: int = 0,
) -> list[AgendaEntry]:
    """Ordered agenda entries for ``plans`` (PRD 18.5).

    ``drafts`` (draft_id -> Draft) supplies preview text and thread/media
    counts; ``campaigns`` (campaign_id -> Campaign) supplies campaign names.
    When ``min_spacing_min`` is positive, conflicting entries are flagged.
    """
    _ = now if now is not None else now_ms()
    zone = _zone(tz)
    drafts = drafts or {}
    campaigns = campaigns or {}
    conflict_ids = _conflicting_ids(plans, min_spacing_min)

    entries: list[AgendaEntry] = []
    for plan in sorted(plans, key=_sort_key):
        draft = drafts.get(plan.draft_id)
        preview = ""
        thread_count = 0
        media_count = 0
        if draft is not None:
            preview = draft.text.strip().replace("\n", " ")[:120]
            media_count = len(draft.media)
            thread_count = _thread_count(draft)
        campaign = campaigns.get(plan.campaign_id)
        last_error = ""
        for attempt in reversed(plan.attempts):
            if not attempt.ok and attempt.error_message:
                last_error = attempt.error_message
                break
        entries.append(
            AgendaEntry(
                plan_id=plan.plan_id,
                when_ms=plan.scheduled_for,
                when_text=_when_text(plan.scheduled_for, zone),
                timezone=tz,
                account_id=plan.account_id,
                network=plan.network,
                campaign=campaign.name if campaign else plan.campaign_id,
                state=plan.state,
                approval_state=_approval_state(plan.state),
                preview=preview,
                thread_count=thread_count,
                media_count=media_count,
                conflict=plan.plan_id in conflict_ids,
                failure_state=_failure_state(plan),
                retry_count=plan.retry_count,
                next_retry_ms=plan.next_retry_at,
                error_message=last_error,
            )
        )
    return entries


def _thread_count(draft: Draft) -> int:
    if not draft.thread_mode:
        return 1
    # A thread draft splits on blank lines; count non-empty blocks.
    blocks = [b for b in draft.text.split("\n\n") if b.strip()]
    return max(1, len(blocks))


# -- grouping -----------------------------------------------------------------


def _grouped(
    plans: list[PublicationPlan], tz: str, keyer
) -> dict[str, list[PublicationPlan]]:
    zone = _zone(tz)
    out: dict[str, list[PublicationPlan]] = {}
    for plan in sorted(plans, key=_sort_key):
        if plan.scheduled_for is None:
            key = "unscheduled"
        else:
            key = keyer(_local(plan.scheduled_for, zone))
        out.setdefault(key, []).append(plan)
    return out


def group_by_day(
    plans: list[PublicationPlan], tz: str = "UTC"
) -> dict[str, list[PublicationPlan]]:
    """Group plans by local calendar day (key ``YYYY-MM-DD``)."""
    return _grouped(plans, tz, lambda dt: dt.strftime("%Y-%m-%d"))


def group_by_week(
    plans: list[PublicationPlan], tz: str = "UTC"
) -> dict[str, list[PublicationPlan]]:
    """Group plans by local ISO week (key ``YYYY-Www``)."""
    return _grouped(plans, tz, lambda dt: f"{dt.isocalendar().year}-W"
                    f"{dt.isocalendar().week:02d}")


def group_by_month(
    plans: list[PublicationPlan], tz: str = "UTC"
) -> dict[str, list[PublicationPlan]]:
    """Group plans by local calendar month (key ``YYYY-MM``)."""
    return _grouped(plans, tz, lambda dt: dt.strftime("%Y-%m"))
