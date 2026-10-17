"""Quill Converter's Auphonic account view and production list: two read-only calls.

The post-MVP account view (``docs/planning/QUILL-Converter-Auphonic-Integration-PRD.md``,
section 14) shows who the stored token belongs to, the credits left -- split
into one-time and recurring hours when Auphonic says so -- and the plan the
recurring hours come from. Production History's **Refresh from Auphonic**
reads the account's recent productions to bring their status up to date.

Both are explicit, user-initiated reads through the shared client's one
reviewed egress site (:func:`quill.core.publish.auphonic._request`, via
``_json``); neither uploads anything, starts anything, or uses credits.
The field names (``onetime_credits``, ``recurring_credits``,
``recharge_recurring_credits``, ``recharge_date``; a production's
``creation_time`` and ``status_string``) were written against Auphonic's
published API pages and recorded fakes, and are listed in the PRD for a live
check; a field Auphonic leaves out is simply not shown. wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.publish import auphonic
from quill.core.publish.auphonic import API_BASE, AuphonicError

#: How many recent productions Refresh from Auphonic asks for.
RECENT_LIMIT = 50


@dataclass(frozen=True, slots=True)
class AccountDetails:
    """Everything the account view shows; ``None`` means Auphonic did not say."""

    username: str
    email: str = ""
    credits: float = 0.0
    onetime_credits: float | None = None
    recurring_credits: float | None = None
    recharge_hours: float | None = None
    recharge_date: str = ""

    def plan(self) -> str:
        """The plan in plain words, from the recurring hours Auphonic reports."""
        if self.recharge_hours:
            when = f", next added on {self.recharge_date}" if self.recharge_date else ""
            return f"A recurring plan: {self.recharge_hours:g} hours each month{when}."
        if self.recharge_hours is None:
            return "Auphonic did not say which plan this account has."
        return "No recurring plan: one-time credits only."

    def lines(self) -> list[str]:
        """The account, one fact a line, for the read-only account box."""
        lines = [f"Account: {self.username or '(no name)'}"]
        if self.email:
            lines.append(f"Email: {self.email}")
        lines.append(f"Credits left: {self.credits:g} hours of processing.")
        if self.onetime_credits is not None:
            lines.append(f"  One-time credits: {self.onetime_credits:g} hours.")
        if self.recurring_credits is not None:
            lines.append(f"  Recurring credits: {self.recurring_credits:g} hours.")
        lines.append(f"Plan: {self.plan()}")
        return lines


@dataclass(frozen=True, slots=True)
class RemoteProduction:
    """One production as the account's list reports it."""

    uuid: str
    title: str
    status: int
    status_string: str
    created: str = ""


def _number(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def parse_account(data: dict[str, object]) -> AccountDetails:
    """``user.json``'s ``data`` block as :class:`AccountDetails` (pure; unit-tested)."""
    user = data.get("data")
    if not isinstance(user, dict):
        raise AuphonicError("Auphonic returned an unexpected response.")
    return AccountDetails(
        username=str(user.get("username", "") or ""),
        email=str(user.get("email", "") or ""),
        credits=_number(user.get("credits")) or 0.0,
        onetime_credits=_number(user.get("onetime_credits")),
        recurring_credits=_number(user.get("recurring_credits")),
        recharge_hours=_number(user.get("recharge_recurring_credits")),
        recharge_date=str(user.get("recharge_date", "") or "")[:10],
    )


def account_details(token: str) -> AccountDetails:
    """The account behind *token* (``GET /api/user.json``). Uploads nothing."""
    return parse_account(auphonic._json(f"{API_BASE}/user.json", token))


def parse_productions(data: dict[str, object]) -> list[RemoteProduction]:
    """``productions.json``'s list as :class:`RemoteProduction` rows (pure)."""
    rows = data.get("data")
    found: list[RemoteProduction] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict) or not isinstance(row.get("uuid"), str):
            continue
        uuid = str(row["uuid"])
        if not uuid.replace("-", "").isalnum():
            continue  # never a production id QUILL would put in a URL
        metadata = row.get("metadata")
        title = str(metadata.get("title", "") or "") if isinstance(metadata, dict) else ""
        try:
            status = int(row.get("status", -1))  # type: ignore[call-overload]
        except (TypeError, ValueError):
            status = -1
        found.append(
            RemoteProduction(
                uuid=uuid,
                title=title or uuid,
                status=status,
                status_string=str(row.get("status_string", "") or ""),
                created=str(row.get("creation_time", "") or "")[:16].replace("T", " "),
            )
        )
    return found


def list_productions(token: str, *, limit: int = RECENT_LIMIT) -> list[RemoteProduction]:
    """The account's most recent productions (``GET /api/productions.json``)."""
    count = max(1, min(int(limit), 100))
    return parse_productions(auphonic._json(f"{API_BASE}/productions.json?limit={count}", token))
