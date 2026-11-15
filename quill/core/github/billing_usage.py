"""Billing and Usage: this month's metered GitHub use for the signed-in account.

Read only. One ``GET /user`` for the login, then GitHub's enhanced billing
report, ``GET /users/{login}/settings/billing/usage?year=&month=``, which
lists usage items (product, SKU, quantity, unit, net amount). Rows are grouped
by product and SKU and read as sentences: "Actions, Linux minutes: 1,204
minutes, $0.00 after discounts." A last row gives the month's net total.

GitHub shares this only with a token allowed to read the account's plan (a
classic token's ``user`` scope, or a fine-grained token's Plan read
permission); without it GitHub answers 403 or 404, and the one row says so
and where the same figures are on the website, rather than showing an empty
list that would read as "no usage".

No ``wx`` imports; strict-typed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from quill.core.github.explore_models import ExploreRow
from quill.core.github.rest_transport import GitHubRestError, request_json

__all__ = ["BILLING_URL", "UsageLine", "fetch_billing_usage", "summarize_usage", "usage_rows"]

BILLING_URL = "https://github.com/settings/billing"


@dataclass(frozen=True, slots=True)
class UsageLine:
    product: str
    sku: str
    quantity: float
    unit: str
    net: float
    gross: float


def _number(value: object) -> float:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0


def summarize_usage(items: Sequence[Mapping[str, Any]]) -> list[UsageLine]:
    """Usage items grouped by product and SKU, largest net amount first."""
    totals: dict[tuple[str, str, str], list[float]] = {}
    for item in items:
        key = (
            str(item.get("product") or "other"),
            str(item.get("sku") or ""),
            str(item.get("unitType") or ""),
        )
        row = totals.setdefault(key, [0.0, 0.0, 0.0])
        row[0] += _number(item.get("quantity"))
        row[1] += _number(item.get("netAmount"))
        row[2] += _number(item.get("grossAmount"))
    lines = [
        UsageLine(product, sku, values[0], unit, values[1], values[2])
        for (product, sku, unit), values in totals.items()
    ]
    return sorted(lines, key=lambda line: (-line.net, line.product, line.sku))


def _words(name: str) -> str:
    return name.replace("_", " ").replace("-", " ").strip().capitalize()


def _quantity(value: float, unit: str) -> str:
    shown = f"{value:,.0f}" if value == int(value) else f"{value:,.2f}"
    return f"{shown} {unit.lower()}".strip()


def usage_rows(lines: Sequence[UsageLine], *, month: str) -> list[ExploreRow]:
    """The Workbench rows: one per product and SKU, then the month's total."""
    rows = [
        ExploreRow(
            label=(
                f"{_words(line.product)}, {_words(line.sku) or 'all'}: "
                f"{_quantity(line.quantity, line.unit)}, ${line.net:,.2f} after discounts"
            ),
            detail=(
                f"Product: {_words(line.product)}\nSKU: {line.sku or 'not given'}\n"
                f"Used this month: {_quantity(line.quantity, line.unit)}\n"
                f"Before discounts: ${line.gross:,.2f}\nAfter discounts: ${line.net:,.2f}\n"
                f"Month: {month}. GitHub's own figures; QUILL adds them up and nothing else."
            ),
            url=BILLING_URL,
            kind="billing",
            key=f"{line.product}/{line.sku}",
        )
        for line in lines
    ]
    total = sum(line.net for line in lines)
    rows.append(
        ExploreRow(
            label=f"Total for {month}: ${total:,.2f} after discounts",
            detail=(
                f"The sum of every row above for {month}, as GitHub reported them. "
                "Included minutes and storage count at their discounted price, often $0.00."
            ),
            url=BILLING_URL,
            kind="billing",
            key="total",
        )
    )
    return rows


def fetch_billing_usage(token: str | None, *, now: datetime | None = None) -> list[ExploreRow]:
    """This month's usage rows, or one row saying why GitHub did not share them."""
    when = now or datetime.now(UTC)
    month = when.strftime("%B %Y")
    try:
        login = str(request_json(token, "GET", "/user").data.get("login", ""))  # type: ignore[union-attr]
        if not login:
            raise GitHubRestError("GitHub did not say who is signed in.")
        answer = request_json(
            token,
            "GET",
            f"/users/{login}/settings/billing/usage",
            query={"year": str(when.year), "month": str(when.month)},
        )
    except GitHubRestError as exc:
        if exc.status in (401, 403, 404):
            return [
                ExploreRow(
                    label="GitHub did not share billing usage with this sign-in",
                    detail=(
                        "Reading usage needs a token allowed to read your plan: a classic "
                        "token with the user scope, or a fine-grained token with Plan read "
                        f"access. The same figures are at {BILLING_URL}; Enter opens it."
                    ),
                    url=BILLING_URL,
                    kind="billing",
                    key="unavailable",
                )
            ]
        raise
    data = answer.data if isinstance(answer.data, Mapping) else {}
    items = [i for i in data.get("usageItems") or () if isinstance(i, Mapping)]
    if not items:
        return [
            ExploreRow(
                label=f"No metered usage reported for {month}",
                detail="GitHub reported no billable use this month for this account.",
                url=BILLING_URL,
                kind="billing",
                key="none",
            )
        ]
    return usage_rows(summarize_usage(items), month=month)
