"""Read-only Paid Memberships Pro lists through its documented abilities API.

Levels, orders, subscriptions and renewals are requested only when their node
is opened. The site still checks the caller's PMPro capability for each read;
the returned order shape omits billing and card details.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import TYPE_CHECKING, Any

from quill.core.wordpress.abilities import list_abilities, run_ability
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.site import plain_text
from quill.core.wordpress.workbench_listing import pages_for
from quill.core.wordpress.workbench_rows import WbRow

if TYPE_CHECKING:
    from quill.core.wordpress.workbench_load import SiteContext

__all__ = ["load_pmpro"]

_ABILITY_FOR = {
    "levels": "pmpro/levels-query",
    "orders": "pmpro/orders-query",
    "subscriptions": "pmpro/subscriptions-query",
    "renewals": "pmpro/subscriptions-query",
}
_PAGE_SIZE = 50
_RENEWAL_WINDOW = timedelta(days=30)


def _unavailable(site: str) -> list[WbRow]:
    row = WbRow(
        "fact",
        site,
        "pmpro-not-available",
        {"fact": "Paid Memberships Pro", "value": "Not exposed"},
        "Paid Memberships Pro abilities are not exposed on this site. They require "
        "WordPress 6.9 or later and Paid Memberships Pro 3.9 or later.",
    )
    return [row]


def _text(value: Any) -> str:
    if isinstance(value, dict):
        value = value.get("rendered") or value.get("raw") or ""
    return plain_text(str(value or ""))


def _date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
        except ValueError:
            return None


def _billing(item: dict[str, Any]) -> str:
    amount = str(item.get("billing_amount") or "")
    number = str(item.get("cycle_number") or "")
    period = str(item.get("cycle_period") or "")
    frequency = f"every {number} {period}" if number and period else period
    return " ".join(part for part in (amount, frequency) if part) or "none"


def _rows(site: str, kind: str, items: list[dict[str, Any]]) -> list[WbRow]:
    rows: list[WbRow] = []
    for item in items:
        ident = str(item.get("id") or item.get("code") or "")
        if kind == "level":
            title = _text(item.get("name")) or f"Level {ident}"
            billing = _billing(item)
            expiration = (
                " ".join(
                    str(part)
                    for part in (item.get("expiration_number"), item.get("expiration_period"))
                    if part
                )
                or "none"
            )
            cells = {
                "name": title,
                "signups": "Yes" if item.get("allow_signups") else "No",
                "initial": str(item.get("initial_payment") or "0"),
                "billing": billing,
                "expires": expiration,
            }
            detail = (
                f"{title}. Signups: {cells['signups']}. Initial payment: {cells['initial']}. "
                f"Recurring billing: {billing}. Expires after: {expiration}."
            )
        elif kind == "order":
            title = str(item.get("code") or f"Order {ident}")
            status = str(item.get("status") or "unknown")
            total = str(item.get("total") or "0")
            gateway = str(item.get("gateway") or "")
            when = str(item.get("timestamp") or "")
            cells = {
                "code": title,
                "status": status.replace("_", " ").title(),
                "total": total,
                "gateway": gateway,
                "date": when,
                "member": str(item.get("user_id") or ""),
                "level": str(item.get("membership_level_id") or ""),
            }
            detail = (
                f"Order {title}. {cells['status']}, total {total}, gateway "
                f"{gateway or 'not named'}, "
                f"member {cells['member'] or 'not named'}, level {cells['level'] or 'not named'}, "
                f"{when or 'date not given'}."
            )
        else:
            title = f"Subscription {ident}"
            status = str(item.get("status") or "unknown")
            next_payment = str(item.get("next_payment_date") or "")
            billing = _billing(item)
            gateway = str(item.get("gateway") or "")
            cells = {
                "subscription": title,
                "status": status.replace("_", " ").title(),
                "next_payment": next_payment,
                "billing": billing,
                "gateway": gateway,
                "member": str(item.get("user_id") or ""),
                "level": str(item.get("membership_level_id") or ""),
            }
            detail = (
                f"{title}. {cells['status']}, level {cells['level'] or 'not named'}, "
                f"member {cells['member'] or 'not named'}, next payment "
                f"{next_payment or 'not scheduled'}, billing {billing}, "
                f"gateway {gateway or 'not named'}."
            )
        rows.append(
            WbRow(
                "pmpro",
                site,
                ident or title,
                cells,
                detail,
                status=str(item.get("status") or ""),
                subkind=kind,
                modified_gmt=str(item.get("timestamp") or item.get("next_payment_date") or ""),
                raw=dict(item),
            )
        )
    return rows


def load_pmpro(ctx: SiteContext, view: str) -> list[WbRow]:
    """Load one PMPro list through a read-only documented ability."""
    ability_name = _ABILITY_FOR.get(view)
    if ability_name is None:
        raise WordPressApiError(f"The Workbench does not know the PMPro view {view}.")
    abilities = {ability.name: ability for ability in list_abilities(ctx.api)}
    ability = abilities.get(ability_name)
    if ability is None:
        return _unavailable(ctx.name)
    if not ability.readonly:
        raise WordPressApiError(f"{ability_name} is not marked read-only by {ctx.name}.")
    result_items: list[dict[str, Any]] = []
    max_pages = pages_for(3) * 2  # PMPro allows 50 per page; the Workbench counts 100.
    for page in range(1, max_pages + 1):
        result = run_ability(ctx.api, ability, {"limit": _PAGE_SIZE, "page": page})
        values = result.get("items", []) if isinstance(result, dict) else []
        page_items = (
            [item for item in values if isinstance(item, dict)] if isinstance(values, list) else []
        )
        result_items.extend(page_items)
        try:
            total = int(result.get("total", 0)) if isinstance(result, dict) else 0
        except (TypeError, ValueError):
            total = 0
        if len(page_items) < _PAGE_SIZE or (total and page * _PAGE_SIZE >= total):
            break
    items = result_items
    if view == "renewals":
        today = datetime.now(UTC).date()
        end = today + _RENEWAL_WINDOW
        items = [
            item
            for item in items
            if (next_payment := _date(item.get("next_payment_date"))) is not None
            and next_payment <= end
        ]
        items.sort(key=lambda item: _date(item.get("next_payment_date")) or date.max)
    kind = {"levels": "level", "orders": "order"}.get(view, "subscription")
    return _rows(ctx.name, kind, items)
