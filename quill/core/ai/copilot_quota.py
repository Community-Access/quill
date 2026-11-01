"""GitHub Copilot's own count: the quota snapshot, and the sentence the Usage view reads.

The Copilot SDK reports the account's quota through ``account.getQuota``
(``await client.rpc.account.get_quota(copilot.rpc.AccountGetQuotaRequest())``):
``quota_snapshots`` keyed ``premium_interactions``, ``chat`` and
``completions``, each with ``entitlement_requests`` (-1 is unlimited),
``used_requests``, ``remaining_percentage`` and ``reset_date`` (codex.md
10A.11). This module turns that into plain data and one sentence, always
named as **GitHub's** count (a service's number is never called ours), and
never computes money from it.

No SDK import and no network call here: :mod:`quill.core.ai.copilot_chat`
reads the snapshot; this only words it. wx-free and strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

__all__ = [
    "CHAT",
    "COMPLETIONS",
    "PREMIUM",
    "CopilotQuota",
    "QuotaBucket",
    "quota_from_result",
    "reset_words",
    "usage_clause",
]

PREMIUM = "premium_interactions"
CHAT = "chat"
COMPLETIONS = "completions"

_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


@dataclass(frozen=True, slots=True)
class QuotaBucket:
    """One of GitHub's quota counters, as GitHub reported it."""

    entitlement: int
    used: int
    remaining_percent: float = 0.0
    reset_date: str = ""

    @property
    def unlimited(self) -> bool:
        return self.entitlement < 0

    @property
    def exhausted(self) -> bool:
        """True when a limited counter has nothing left."""
        return not self.unlimited and self.entitlement > 0 and self.used >= self.entitlement


@dataclass(frozen=True, slots=True)
class CopilotQuota:
    """The account's quota snapshot: each bucket GitHub sent, keyed by its name."""

    buckets: Mapping[str, QuotaBucket]

    def bucket(self, name: str) -> QuotaBucket | None:
        return self.buckets.get(name)

    @property
    def headline(self) -> tuple[str, QuotaBucket] | None:
        """The bucket a person cares about: premium requests, else chat requests.

        Copilot Free has no premium allowance (an entitlement of 0) and counts
        chat requests instead, so a zero premium bucket gives way to chat.
        """
        premium = self.buckets.get(PREMIUM)
        if premium is not None and premium.entitlement != 0:
            return PREMIUM, premium
        chat = self.buckets.get(CHAT)
        if chat is not None and chat.entitlement != 0:
            return CHAT, chat
        if premium is not None:
            return PREMIUM, premium
        return None


def _field(holder: Any, *names: str) -> Any:
    for name in names:
        if isinstance(holder, Mapping) and name in holder:
            return holder[name]
        value = getattr(holder, name, None)
        if value is not None:
            return value
    return None


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def quota_from_result(result: Any) -> CopilotQuota:
    """A :class:`CopilotQuota` from the SDK's ``AccountGetQuotaResult`` (or its dict).

    Accepts the typed result (``quota_snapshots`` of ``AccountQuotaSnapshot``)
    and the wire shape (``quotaSnapshots`` with camelCase fields), so a minor
    SDK change degrades to fewer numbers rather than an exception.
    """
    snapshots = _field(result, "quota_snapshots", "quotaSnapshots") or {}
    buckets: dict[str, QuotaBucket] = {}
    if isinstance(snapshots, Mapping):
        for name, snap in snapshots.items():
            unlimited = bool(_field(snap, "is_unlimited_entitlement", "isUnlimitedEntitlement"))
            entitlement = _int(_field(snap, "entitlement_requests", "entitlementRequests"))
            buckets[str(name)] = QuotaBucket(
                entitlement=-1 if unlimited else entitlement,
                used=_int(_field(snap, "used_requests", "usedRequests")),
                remaining_percent=_float(
                    _field(snap, "remaining_percentage", "remainingPercentage")
                ),
                reset_date=str(_field(snap, "reset_date", "resetDate") or ""),
            )
    return CopilotQuota(buckets)


def reset_words(reset_date: str) -> str:
    """``2026-11-01T00:00:00Z`` -> ``November 1`` (GitHub resets on the 1st, UTC).

    Read as the calendar date GitHub wrote, with no time-zone shift; an
    unreadable value gives "" and the sentence simply leaves the reset out.
    """
    text = (reset_date or "").strip()
    if not text:
        return ""
    try:
        day = datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            day = date.fromisoformat(text[:10])
        except ValueError:
            return ""
    return f"{_MONTHS[day.month - 1]} {day.day}"


_NOUNS = {PREMIUM: "premium request", CHAT: "chat request", COMPLETIONS: "completion"}


def _counted(count: int, noun: str) -> str:
    return f"{count:,} {noun}" if count == 1 else f"{count:,} {noun}s"


def usage_clause(quota: CopilotQuota | None) -> str:
    """The clause after "My GitHub Copilot: " in the Usage view (10A.11).

    "41 of 300 premium requests this month, by GitHub's count. Resets
    November 1." Unlimited plans say so instead of a ceiling.
    """
    if quota is None:
        return "GitHub's count is not read yet."
    headline = quota.headline
    if headline is None:
        return "GitHub reported no count."
    name, bucket = headline
    noun = _NOUNS.get(name, "request")
    if bucket.unlimited:
        clause = f"{_counted(bucket.used, noun)} this month, no monthly limit, by GitHub's count."
    else:
        ceiling = _counted(bucket.entitlement, noun)
        clause = f"{bucket.used:,} of {ceiling} this month, by GitHub's count."
    reset = reset_words(bucket.reset_date)
    return f"{clause} Resets {reset}." if reset else clause
