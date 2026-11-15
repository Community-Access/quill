"""Change a member's level, or cancel it, in Paid Memberships Pro (complete.md WP-C).

Two of PMPro's own REST routes, the ones its wp-admin Edit User screen
stands for:

- ``POST pmpro/v1/change_membership_level`` with ``user_id`` and ``level_id``;
- ``POST pmpro/v1/cancel_membership_level`` with ``user_id`` and ``level_id``.

PMPro's own permission callback decides who may call them; QUILL asks for
Full Workbench access on top and never assumes the site agreed. Neither
change can be taken back from here: cancelling also cancels the member's
recurring subscription at the payment gateway, so the preview names each
subscription, its gateway and its next payment, read just before (from the
``pmpro/subscriptions-query`` ability where the site has it), and says
plainly when QUILL could not read them. Every run is previewed; nothing is
remembered between runs.

Card and billing details never reach a row: :func:`without_payment_details`
strips them from whatever the site returns. Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError

__all__ = [
    "CANCEL_ROUTE",
    "CHANGE_ROUTE",
    "PAYMENT_DETAIL_KEYS",
    "cancel_membership",
    "cancel_preview",
    "change_membership",
    "change_preview",
    "member_subscriptions",
    "without_payment_details",
]

CHANGE_ROUTE = "pmpro/v1/change_membership_level"
CANCEL_ROUTE = "pmpro/v1/cancel_membership_level"
_SUBSCRIPTIONS = "pmpro/subscriptions-query"

#: Fields of a PMPro order, member or subscription that are card or billing details.
PAYMENT_DETAIL_KEYS = frozenset({
    "accountnumber",
    "account_number",
    "cardtype",
    "card_type",
    "expirationmonth",
    "expirationyear",
    "expiration_month",
    "expiration_year",
    "billing",
    "billing_name",
    "billing_street",
    "billing_street2",
    "billing_city",
    "billing_state",
    "billing_zip",
    "billing_country",
    "billing_phone",
    "cvv",
    "card_number",
})


def without_payment_details(item: Mapping[str, Any]) -> dict[str, Any]:
    """*item* with every card and billing field removed, however the site nests them."""
    clean: dict[str, Any] = {}
    for key, value in item.items():
        if str(key).lower() in PAYMENT_DETAIL_KEYS:
            continue
        clean[key] = without_payment_details(value) if isinstance(value, Mapping) else value
    return clean


def member_subscriptions(api: WordPressApi, user_id: int) -> list[dict[str, Any]] | None:
    """The person's active subscriptions, or None when the site cannot say.

    Read through the read-only ``pmpro/subscriptions-query`` ability; the person
    is asked for by ``user_id`` when the ability takes it, and filtered here
    either way, so another member's subscription is never named.
    """
    from quill.core.wordpress.abilities import list_abilities, run_ability

    try:
        ability = next((a for a in list_abilities(api) if a.name == _SUBSCRIPTIONS), None)
    except WordPressApiError:
        return None
    if ability is None or not ability.readonly:
        return None
    takes_user = "user_id" in (ability.input_schema.get("properties") or {})
    found: list[dict[str, Any]] = []
    for page in range(1, 7):
        given: dict[str, Any] = {"limit": 50, "page": page}
        if takes_user:
            given["user_id"] = user_id
        try:
            answer = run_ability(api, ability, given)
        except WordPressApiError:
            return None
        items = answer.get("items", []) if isinstance(answer, Mapping) else []
        items = [i for i in items if isinstance(i, Mapping)] if isinstance(items, list) else []
        found += [
            without_payment_details(i)
            for i in items
            if str(i.get("user_id", "")) == str(user_id)
            and str(i.get("status", "active")).lower() == "active"
        ]
        if len(items) < 50:
            break
    return found


def _subscription_sentence(item: Mapping[str, Any]) -> str:
    ident = item.get("id") or item.get("subscription_transaction_id") or ""
    gateway = str(item.get("gateway") or "its payment gateway")
    amount = str(item.get("billing_amount") or "")
    number = str(item.get("cycle_number") or "")
    period = str(item.get("cycle_period") or "")
    every = f" every {number} {period}" if number and period else (f" {period}" if period else "")
    paying = f", {amount}{every}" if amount else ""
    when = str(item.get("next_payment_date") or "")
    next_payment = f", next payment {when}" if when else ""
    return (
        f"Paid Memberships Pro also cancels subscription {ident} at {gateway}{paying}"
        f"{next_payment}: no further payments are taken."
    )


def _gateway_lines(
    subscriptions: Sequence[Mapping[str, Any]] | None, level_id: str | None
) -> list[str]:
    if subscriptions is None:
        return [
            "QUILL could not read this person's subscriptions. If they pay by a recurring "
            "subscription, Paid Memberships Pro cancels it at the payment gateway too, and "
            "no further payments are taken."
        ]
    mine = [
        s
        for s in subscriptions
        if level_id is None or str(s.get("membership_level_id", level_id)) == str(level_id)
    ]
    if not mine:
        return ["QUILL found no active recurring subscription for it, so no gateway is asked."]
    return [_subscription_sentence(s) for s in mine]


_FINAL = (
    "Nothing is refunded: refunds are made in the gateway or in Memberships > Orders.",
    "This cannot be undone from QUILL. A cancelled subscription is not restarted; the "
    "person would check out again.",
)


def cancel_preview(
    person: str,
    site: str,
    level: Mapping[str, Any],
    subscriptions: Sequence[Mapping[str, Any]] | None,
) -> list[str]:
    """What cancelling *level* for *person* does, one line each, before anything is sent."""
    name = str(level.get("name") or f"Level {level.get('id', '')}")
    level_id = str(level.get("id", "")) or None
    return [
        f"{person} loses {name} on {site} now.",
        *_gateway_lines(subscriptions, level_id),
        *_FINAL,
    ]


def change_preview(
    person: str,
    site: str,
    current: Sequence[Mapping[str, Any]],
    new_level: Mapping[str, Any],
    subscriptions: Sequence[Mapping[str, Any]] | None,
) -> list[str]:
    """What giving *person* *new_level* does, one line each, before anything is sent."""
    new_name = str(new_level.get("name") or f"Level {new_level.get('id', '')}")
    lines = [f"{person} gets {new_name} on {site} now, with no checkout and no payment taken."]
    if not current:
        lines.append("They have no current membership, so nothing they have ends.")
        return [*lines, "Cancel Membership takes it away again, after its own preview."]
    for level in current:
        old = str(level.get("name") or f"Level {level.get('id', '')}")
        lines.append(f"{old} ends.")
        lines += _gateway_lines(subscriptions, str(level.get("id", "")) or None)
    return [*lines, *_FINAL]


def _accepted(answer: Any, what: str, site: str) -> Any:
    if answer is False or (isinstance(answer, Mapping) and answer.get("success") is False):
        raise WordPressApiError(f"Paid Memberships Pro on {site} did not {what}.")
    return answer


def change_membership(api: WordPressApi, user_id: int, level_id: int) -> Any:
    """Give *user_id* *level_id* through PMPro's own route."""
    answer = api.post(CHANGE_ROUTE, {"user_id": user_id, "level_id": level_id})
    return _accepted(answer, "change the membership level", api.site_name)


def cancel_membership(api: WordPressApi, user_id: int, level_id: int) -> Any:
    """Cancel *user_id*'s *level_id* through PMPro's own route."""
    answer = api.post(CANCEL_ROUTE, {"user_id": user_id, "level_id": level_id})
    return _accepted(answer, "cancel the membership", api.site_name)
