"""WooCommerce orders and coupons in the Workbench: status, notes, refunds, coupons (Package 9).

**Orders.** Change Status sends ``POST wc/v3/orders/{id}`` with the new
status; its preview says which email WooCommerce sends because of it, since
the customer may get one. Notes are ``orders/{id}/notes``: private ones for
the shop, or a note to the customer, which WooCommerce emails.

**Refunds move money.** A refund is planned (:func:`plan_refund`), checked
against what is left to refund, previewed with a plain money warning
(:func:`refund_preview`), and sent only after the person types the amount
(:func:`refund_confirmed`). It is one order at a time and never part of a
batch (:data:`NEVER_BATCHED`); whether the payment gateway is asked to return
the money, or only the shop's record changes, is the person's choice and is
said both in the preview and afterwards. Nothing about a refund is remembered
between runs.

**Coupons** are listed, made, changed and moved to the Trash through
``wc/v3/coupons``, each after a preview. Wx-free.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from quill.core.wordpress.plugin_shop_seo import SHOP_NAMESPACE, ShopValueError
from quill.core.wordpress.site import friendly_date, raw_text
from quill.core.wordpress.workbench_rows import WbRow

__all__ = [
    "COUPON_TYPES",
    "NEVER_BATCHED",
    "ORDER_STATUSES",
    "CouponSpec",
    "RefundPlan",
    "coupon_body",
    "coupon_preview",
    "coupon_row",
    "note_lines",
    "note_preview",
    "plan_refund",
    "refund_body",
    "refund_confirmed",
    "refund_preview",
    "refunded_so_far",
    "status_preview",
]

ORDER_STATUSES: dict[str, str] = {
    "pending": "pending payment",
    "processing": "processing",
    "on-hold": "on hold",
    "completed": "completed",
    "cancelled": "cancelled",
    "refunded": "refunded",
    "failed": "failed",
}
"""WooCommerce's order statuses (``orders/{id}`` enum on the live index), as said."""

_STATUS_EMAIL: dict[str, str] = {
    "processing": "WooCommerce emails the customer that the order is being processed.",
    "completed": "WooCommerce emails the customer that the order is complete.",
    "on-hold": "WooCommerce emails the customer that the order is on hold.",
    "refunded": (
        "WooCommerce emails the customer that the order was refunded, but no money moves: "
        "a status is only a word. Use Refund to return money."
    ),
    "cancelled": "WooCommerce emails the shop, not the customer, that it was cancelled.",
    "failed": "WooCommerce emails the shop, not the customer, that the order failed.",
    "pending": "No email is sent for pending payment.",
}

NEVER_BATCHED = frozenset({"wordpress.workbench.refund_order"})
"""Commands that move money: one order at a time, never in a batch or a plain-language run."""


def status_preview(number: str, old: str, new: str, site: str) -> list[str]:
    if new not in ORDER_STATUSES:
        raise ShopValueError(f"WooCommerce has no order status called {new}.")
    return [
        f"Shop order {number} on {site}: {ORDER_STATUSES.get(old, old)} becomes "
        f"{ORDER_STATUSES[new]}.",
        _STATUS_EMAIL[new] + " Each email is sent only if it is turned on in WooCommerce > "
        "Settings > Emails.",
        "Stock and payments are not changed by QUILL.",
    ]


# -- notes ----------------------------------------------------------------------------


def note_lines(notes: Sequence[Mapping[str, Any]]) -> list[str]:
    """Each note, newest first: when, who it was for, and what it says."""
    lines = []
    for raw in notes:
        if not isinstance(raw, Mapping):
            continue
        when = friendly_date(str(raw.get("date_created_gmt") or raw.get("date_created") or ""))
        whom = "to the customer" if raw.get("customer_note") else "private"
        author = str(raw.get("author", "") or "")
        by = f", by {author}" if author else ""
        text = " ".join(raw_text(raw.get("note")).split())
        lines.append(f"{when}, {whom}{by}: {text}")
    return lines


def note_preview(number: str, text: str, to_customer: bool, site: str) -> list[str]:
    if not text.strip():
        raise ShopValueError("A note needs some words.")
    if to_customer:
        return [
            f"A note on shop order {number}, {site}, sent to the customer.",
            "WooCommerce emails it to them now, and it shows on their order page.",
            f"It says: {text.strip()}",
        ]
    return [
        f"A private note on shop order {number}, {site}. The customer does not see it.",
        f"It says: {text.strip()}",
    ]


# -- refunds ----------------------------------------------------------------------------

_AMOUNT = re.compile(r"^\d+(\.\d{1,2})?$")


def _money(text: Any) -> Decimal:
    try:
        return Decimal(str(text or "0").strip() or "0")
    except InvalidOperation:
        return Decimal("0")


def refunded_so_far(order: Mapping[str, Any]) -> Decimal:
    """What the order's refunds already add up to (WooCommerce lists them as negatives)."""
    return sum(
        (abs(_money(r.get("total"))) for r in order.get("refunds") or [] if isinstance(r, Mapping)),
        Decimal("0"),
    )


@dataclass(frozen=True)
class RefundPlan:
    order_id: int
    number: str
    amount: str
    currency: str
    reason: str
    through_gateway: bool
    gateway: str
    left_after: str


def plan_refund(
    order: Mapping[str, Any], amount_text: str, reason: str, *, through_gateway: bool
) -> RefundPlan:
    """A refund of *amount_text*, checked against what is left; nothing is sent."""
    text = amount_text.strip()
    if not _AMOUNT.match(text):
        raise ShopValueError("A refund needs an amount such as 12.50, with no currency sign.")
    amount = Decimal(text)
    left = _money(order.get("total")) - refunded_so_far(order)
    if amount <= 0:
        raise ShopValueError("A refund must be more than nought.")
    if amount > left:
        raise ShopValueError(
            f"Only {left:.2f} is left to refund on this order, so {amount:.2f} cannot be."
        )
    gateway = str(order.get("payment_method_title") or order.get("payment_method") or "")
    return RefundPlan(
        order_id=int(order.get("id", 0) or 0),
        number=str(order.get("number") or order.get("id") or ""),
        amount=f"{amount:.2f}",
        currency=str(order.get("currency", "") or ""),
        reason=reason.strip(),
        through_gateway=through_gateway,
        gateway=gateway or "the payment method",
        left_after=f"{left - amount:.2f}",
    )


def refund_preview(plan: RefundPlan, site: str) -> list[str]:
    """The money warning first, then exactly what happens; read before typing the amount."""
    money = f"{plan.amount} {plan.currency}".strip()
    if plan.through_gateway:
        how = (
            f"WooCommerce asks {plan.gateway} to return {money} to the customer. This moves "
            "real money and cannot be taken back from QUILL or from WooCommerce."
        )
    else:
        how = (
            f"Only the shop's record changes: no money is returned by {plan.gateway}. Return "
            f"the {money} yourself, outside WooCommerce."
        )
    return [
        f"Money warning: this refunds {money} on shop order {plan.number}, {site}.",
        how,
        f"Reason recorded: {plan.reason or 'none given'}.",
        f"Left to refund afterwards: {plan.left_after} {plan.currency}.".strip(),
        "Stock is not put back, and WooCommerce may email the customer about the refund.",
        f"To go ahead, you will type the amount, {plan.amount}, exactly.",
    ]


def refund_confirmed(plan: RefundPlan, typed: str | None) -> bool:
    """True only when *typed* is the amount, exactly (a currency sign or spaces aside)."""
    if typed is None:
        return False
    return typed.strip().lstrip("$£€").strip() == plan.amount


def refund_body(plan: RefundPlan) -> dict[str, Any]:
    return {
        "amount": plan.amount,
        "reason": plan.reason,
        "api_refund": plan.through_gateway,
        "api_restock": False,
    }


def refund_route(order_id: int) -> str:
    return f"{SHOP_NAMESPACE}/orders/{order_id}/refunds"


# -- coupons --------------------------------------------------------------------------

COUPON_TYPES: dict[str, str] = {
    "percent": "a percentage off",
    "fixed_cart": "a fixed amount off the whole cart",
    "fixed_product": "a fixed amount off each product",
}
"""WooCommerce's discount types (``coupons`` enum on the live index), as said."""


def _discount_words(kind: str, amount: str) -> str:
    if kind == "percent":
        return f"{amount} percent off"
    if kind == "fixed_product":
        return f"{amount} off each product"
    return f"{amount} off the cart"


def coupon_row(raw: Mapping[str, Any], site: str) -> WbRow:
    code = str(raw.get("code", "") or "")
    kind = str(raw.get("discount_type", "") or "fixed_cart")
    amount = str(raw.get("amount", "") or "0")
    used = int(raw.get("usage_count", 0) or 0)
    limit = raw.get("usage_limit")
    used_words = f"{used} of {limit}" if limit else f"{used}, no limit"
    expires = str(raw.get("date_expires", "") or "")[:10]
    discount = _discount_words(kind, amount)
    return WbRow(
        kind="shop_coupon",
        site=site,
        key=str(raw.get("id", "") or ""),
        cells={
            "code": code,
            "discount": discount,
            "used": used_words,
            "expires": expires or "never",
        },
        detail=(
            f"Coupon {code}: {discount}, used {used_words}, "
            f"{'expires ' + expires if expires else 'never expires'}."
        ),
        status=str(raw.get("status", "") or ""),
        subkind="woocommerce",
        raw={
            "code": code,
            "discount_type": kind,
            "amount": amount,
            "usage_limit": "" if limit is None else str(limit),
            "expires": expires,
            "description": str(raw.get("description", "") or ""),
            "free_shipping": "yes" if raw.get("free_shipping") else "no",
            "minimum_amount": str(raw.get("minimum_amount", "") or ""),
        },
    )


_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


@dataclass(frozen=True)
class CouponSpec:
    code: str
    discount_type: str
    amount: str
    expires: str = ""
    usage_limit: str = ""
    description: str = ""


def coupon_body(spec: CouponSpec, old: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The coupon in WooCommerce's names, checked; with *old*, only what changed."""
    if not spec.code.strip():
        raise ShopValueError("A coupon needs a code, such as SPRING10.")
    if spec.discount_type not in COUPON_TYPES:
        raise ShopValueError(f"WooCommerce has no discount type called {spec.discount_type}.")
    if not _AMOUNT.match(spec.amount.strip()):
        raise ShopValueError("The discount needs an amount such as 10 or 5.50.")
    if spec.discount_type == "percent" and Decimal(spec.amount) > 100:
        raise ShopValueError("A percentage discount cannot be more than 100.")
    if spec.expires.strip() and not _DATE.match(spec.expires.strip()):
        raise ShopValueError("The expiry date needs the form 2026-12-31, or nothing for never.")
    if spec.usage_limit.strip() and not spec.usage_limit.strip().isdigit():
        raise ShopValueError("The usage limit is a whole number, or nothing for no limit.")
    body: dict[str, Any] = {
        "code": spec.code.strip(),
        "discount_type": spec.discount_type,
        "amount": spec.amount.strip(),
        "date_expires": spec.expires.strip() or None,
        "usage_limit": int(spec.usage_limit) if spec.usage_limit.strip() else None,
        "description": spec.description.strip(),
    }
    if old is None:
        return body
    was = {
        "code": old.get("code", ""),
        "discount_type": old.get("discount_type", ""),
        "amount": old.get("amount", ""),
        "date_expires": old.get("expires") or None,
        "usage_limit": int(old["usage_limit"])
        if str(old.get("usage_limit", "")).isdigit()
        else None,
        "description": old.get("description", ""),
    }
    return {k: v for k, v in body.items() if v != was.get(k)}


def coupon_preview(spec: CouponSpec, site: str, body: Mapping[str, Any], *, new: bool) -> list[str]:
    discount = _discount_words(spec.discount_type, spec.amount.strip())
    limit = spec.usage_limit.strip() or "no limit"
    changed = ", ".join(sorted(body)) or "nothing"
    expires = spec.expires.strip() or "never"
    head = (
        f"A new coupon on {site}: {spec.code.strip()}."
        if new
        else f"Coupon {spec.code.strip()} on {site} changes: {changed}."
    )
    return [
        head,
        f"Shoppers who type it get {discount}; uses: {limit}; expires: {expires}.",
        "It works at checkout as soon as it is saved. Orders already placed are not changed.",
    ]


def coupon_trash_preview(code: str, site: str) -> list[str]:
    return [
        f"Coupon {code} moves to WooCommerce's Trash on {site} and stops working at checkout.",
        "Orders that used it keep their discount. Restore it from Marketing > Coupons in wp-admin.",
    ]
