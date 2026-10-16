"""The allowance, in words: one wording for AI Usage and both About windows.

Every number comes from the server on the way in (:class:`GatewayQuota`), because
an operator can raise or lower any limit at any time; this module only decides
how to say them. Written once so the three places that show usage cannot drift
into three explanations of the same allowance.

The part that needed writing down is the **starter allowance**. A newly
connected computer gets a smaller monthly cap for its first hours -- the
gateway's defence against somebody scripting fresh connections for fresh
allowances -- and "15 of 15 left" with no reason reads as a mistake to somebody
who was told the service gives 100. So when the server says the starter
allowance applies, this says what it is, when it ends, and who can lift it.
"""

from __future__ import annotations

from datetime import datetime

from quill.core.ai.gateway_client import GatewayQuota

__all__ = ["WEB_SEARCH_OFF", "describe_quota", "describe_web_searches", "starter_ends"]

#: Said when the service does not offer web search: switched off there (it
#: ships off), or a server that predates it.
WEB_SEARCH_OFF = (
    "QUILL's free AI is not offering web search right now. Everything else in "
    "the AI menu still works."
)


def starter_ends(quota: GatewayQuota, *, now: datetime | None = None) -> datetime | None:
    """When the starter allowance ends, in local time, or ``None``.

    ``None`` when the server did not say, said something unreadable, or named
    a moment already past (the next fetch will show the full allowance).
    """
    if not quota.starter_until:
        return None
    try:
        ends = datetime.fromisoformat(quota.starter_until)
    except ValueError:
        return None
    if ends.tzinfo is None:
        return None
    current = now or datetime.now(ends.tzinfo)
    if ends <= current:
        return None
    return ends.astimezone()


def _when(moment: datetime) -> str:
    # Built by hand: Windows' strftime has no way to drop a leading zero, and
    # "05 October" is read aloud as "zero five October".
    return f"{moment.day} {moment:%B} at {moment:%H:%M}"


def describe_quota(quota: GatewayQuota, *, now: datetime | None = None) -> str:
    """The allowance as short sections, each a heading line and a sentence."""
    reset = (quota.reset_at or "")[:10] or "the 1st"
    sections = [
        "This month\n"
        f"{quota.monthly_left} of {quota.monthly_cap} requests left. Starts again {reset}."
    ]
    ends = starter_ends(quota, now=now)
    if ends is not None:
        after = (
            f"After that it becomes {quota.standard_monthly_cap} a month on its own"
            if quota.standard_monthly_cap > quota.monthly_cap
            else "After that the full monthly allowance applies on its own"
        )
        sections.append(
            "Why the smaller number\n"
            "This computer was connected recently, so it starts with a smaller "
            f"allowance of {quota.monthly_cap} requests until {_when(ends)}. "
            f"{after}; there is nothing you need to do. If you need more sooner, "
            "Get Help from Support can lift it -- your support ID goes with the "
            "message."
        )
    # No cap beside today's number: it is the smaller of the two the server
    # sent, so "of 20" beside a month with 15 left would contradict itself.
    sections.append(f"Today\n{quota.daily_left} left.")
    if quota.web_search_cap > 0:
        sections.append(f"Web searches\n{describe_web_searches(True, quota)}")
    return "\n\n".join(sections)


def describe_web_searches(enabled: bool, quota: GatewayQuota | None) -> str:
    """How many web searches are left this month, as one sentence.

    *enabled* is the service's answer from ``/v1/config``; *quota* is this
    account's, from ``/v1/quota``. Both numbers are the server's: an operator
    can change the monthly number at any time, so none is written here.
    """
    if not enabled or quota is None or quota.web_search_cap <= 0:
        return WEB_SEARCH_OFF
    left = quota.web_searches_left
    reset = (quota.reset_at or "")[:10] or "the 1st"
    if left <= 0:
        return (
            f"No web searches left this month; all {quota.web_search_cap} are used. "
            f"They start again {reset}."
        )
    plural = "search" if left == 1 else "searches"
    return (
        f"{left} of {quota.web_search_cap} web {plural} left this month. They start again {reset}."
    )
