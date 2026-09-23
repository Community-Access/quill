"""The numbers the public landing page is allowed to show.

Two rules decide what is in here, and one of them is not obvious.

**Aggregate only, never a person.** Nothing in this module can return anything
about one account. That is easy to hold to, because there is nothing about a
person to return: the schema has no name, no email and no document text (see
``app/models.py``'s module docstring). What is published is a count and a sum.

**Say what was spent, not how much room is left.** This is the non-obvious one,
and it is why there is no ``budget_cap`` or ``percent_used`` field here.
Publishing the headroom -- "92% of this month's budget used" -- tells anybody who
would like the service switched off for everybody else exactly how hard to push
and when. It turns a transparency page into a targeting aid. Spending to date
is the honest half of that number and carries none of the risk: it says what the
service costs without saying what it would take to break it.

The figures are cached in Redis for :data:`_CACHE_SECONDS`, so a page anyone can
load cannot be used to hammer Postgres, and so a burst of traffic costs one
query rather than one per visitor.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import Any

_CACHE_KEY = "public:stats:v1"
_CACHE_SECONDS = 300

#: Roughly how many words a token is, for turning a token count into a number
#: somebody can picture. Display only, and deliberately rounded hard afterwards.
_WORDS_PER_TOKEN = 0.75


@dataclass(frozen=True, slots=True)
class PublicStats:
    """What the landing page shows. Every field is a total or a count."""

    people: int = 0
    requests_this_month: int = 0
    requests_all_time: int = 0
    words_read: int = 0
    spend_this_month_usd: float = 0.0
    spend_all_time_usd: float = 0.0
    available: bool = True
    paused_reason: str = ""

    def money(self, amount: float) -> str:
        """*amount* as a person would say it.

        Two decimal places turn the first weeks of this service into a column of
        "$0.00", which next to "0.003 of a cent per answer" reads as a page that
        is broken rather than one reporting a genuinely tiny number. Under a
        cent it says so in words instead.
        """
        if amount <= 0:
            return "nothing yet"
        if amount < 0.01:
            return "less than a cent"
        return f"${amount:,.2f}"

    @property
    def started(self) -> bool:
        """Whether there is anything to report yet.

        A brand-new deployment showing four zeroes reads as a broken page. The
        template says "just getting started" instead, which is both friendlier
        and true.
        """
        return self.requests_all_time > 0

    @property
    def cost_per_request_cents(self) -> float:
        """What one answer costs, in cents.

        The single most persuasive number on the page, and the reason the
        service can be free at all: a fraction of a cent. Worth showing
        precisely for that reason.
        """
        if not self.requests_all_time:
            return 0.0
        return self.spend_all_time_usd / self.requests_all_time * 100


def _round_words(words: float) -> int:
    """Words rounded to something a person would say out loud.

    Nobody needs "4,318,772 words", and publishing it to the digit invites
    somebody to watch it move and infer what one account is doing. A rounded
    figure carries the same meaning and none of that.
    """
    if words >= 1_000_000:
        return int(round(words / 100_000) * 100_000)
    if words >= 10_000:
        return int(round(words / 1_000) * 1_000)
    return int(round(words / 100) * 100)


def gather(app) -> PublicStats:
    """The current figures, from cache when it is warm."""
    redis = app.extensions["gateway_redis"]
    cached = redis.get(_CACHE_KEY)
    if cached:
        try:
            return PublicStats(**json.loads(cached))
        except (ValueError, TypeError):  # pragma: no cover - a corrupt cache re-reads
            pass

    stats = _compute(app)
    redis.set(_CACHE_KEY, json.dumps(asdict(stats)), ex=_CACHE_SECONDS)
    return stats


def _compute(app) -> PublicStats:
    from sqlalchemy import func

    from app.limits import _month_key
    from app.models import FeatureFlag, MonthlyUsageSummary, UsageEvent, User, db

    month = _month_key()

    people = db.session.query(func.count(User.id)).scalar() or 0
    requests_all, tokens_in, spend_all = db.session.query(
        func.count(UsageEvent.id),
        func.coalesce(func.sum(UsageEvent.tokens_in), 0),
        func.coalesce(func.sum(UsageEvent.estimated_cost_usd), 0),
    ).one()

    month_requests, month_spend = (
        db.session
        .query(
            func.coalesce(func.sum(MonthlyUsageSummary.request_count), 0),
            func.coalesce(func.sum(MonthlyUsageSummary.total_cost_usd), 0),
        )
        .filter(MonthlyUsageSummary.year_month == month)
        .one()
    )

    flag = db.session.get(FeatureFlag, "hosted_ai")
    available = flag.enabled if flag is not None else True
    # The stored reason is shown as-is when the service is off. It is written by
    # an admin for users to read -- or by the budget auto-pause, which writes its
    # own -- so it is already a sentence meant for this audience.
    reason = "" if available else ((flag.disabled_reason if flag else "") or "")

    return PublicStats(
        people=int(people),
        requests_this_month=int(month_requests or 0),
        requests_all_time=int(requests_all or 0),
        words_read=_round_words(float(tokens_in or 0) * _WORDS_PER_TOKEN),
        spend_this_month_usd=float(month_spend or 0),
        spend_all_time_usd=float(spend_all or 0),
        available=bool(available),
        paused_reason=reason,
    )


def invalidate(app: Any) -> None:
    """Drop the cache, so an admin change shows up without waiting it out."""
    app.extensions["gateway_redis"].delete(_CACHE_KEY)
