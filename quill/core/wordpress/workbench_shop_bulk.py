"""Change many products at once (complete.md 2.3, Shop: ``products/batch``).

For a sale across a category, a price rise, or a range going out of stock:
the selected products, one change, one preview of every product's old and
new value, then WooCommerce's batch route (``POST wc/v3/products/batch``),
at most 100 products a request, as WooCommerce allows.

A product the change cannot apply to is named in the preview with the reason
and left alone: a variable product's prices live on its variations, a price
change needs a regular price to start from, and a stock status is
WooCommerce's to set where it counts the stock itself. Every change keeps the
old values, so Undo sends them back the same way. Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from quill.core.wordpress.plugin_shop_seo import SHOP_NAMESPACE, ShopValueError
from quill.core.wordpress.workbench_shop_catalog import PRODUCT_STATUSES

__all__ = [
    "BATCH_LIMIT",
    "BATCH_ROUTE",
    "BULK_CHANGES",
    "STOCK_STATUSES",
    "BulkPlan",
    "batch_bodies",
    "batch_failures",
    "parse_percent",
    "plan_bulk",
]

BATCH_ROUTE = f"{SHOP_NAMESPACE}/products/batch"
BATCH_LIMIT = 100

#: The changes on offer, with how the chooser says them.
BULK_CHANGES: dict[str, str] = {
    "sale": "Put on sale: a percentage off the regular price",
    "end_sale": "End the sale",
    "price": "Change the regular price by a percentage (up or down)",
    "stock": "Set the stock status",
    "status": "Set the status (published, draft, private)",
    "add_category": "Add a category",
    "remove_category": "Remove a category",
}

STOCK_STATUSES: dict[str, str] = {
    "instock": "in stock",
    "outofstock": "out of stock",
    "onbackorder": "on backorder",
}

_CENT = Decimal("0.01")


def parse_percent(text: str, *, allow_negative: bool) -> Decimal:
    """A percentage as typed ("15", "-10", "12.5%"), within sense."""
    words = text.strip().rstrip("%").strip()
    try:
        value = Decimal(words)
    except InvalidOperation:
        raise ShopValueError(f"{text.strip() or 'Nothing'} is not a percentage.") from None
    low = Decimal(-90) if allow_negative else Decimal("0.01")
    if not low <= value <= Decimal(500 if allow_negative else 99):
        raise ShopValueError(
            "A change is from -90 to 500 percent."
            if allow_negative
            else "A sale is 0.01 to 99 percent off."
        )
    return value


def _price(text: str) -> Decimal | None:
    try:
        value = Decimal(str(text).strip())
    except InvalidOperation:
        return None
    return value if value > 0 else None


def _money(value: Decimal) -> str:
    return str(value.quantize(_CENT, rounding=ROUND_HALF_UP))


@dataclass(frozen=True)
class BulkPlan:
    """What a bulk change sends, what it would undo with, and what it leaves alone."""

    updates: list[dict[str, Any]] = field(default_factory=list)
    undo: list[dict[str, Any]] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


def _facts(row: Any) -> tuple[int, str, Mapping[str, Any]]:
    raw = row.raw if isinstance(getattr(row, "raw", None), Mapping) else {}
    return int(getattr(row, "object_id", 0) or 0), str(raw.get("name") or row.title), raw


def plan_bulk(
    rows: Sequence[Any],
    change: str,
    *,
    percent: Decimal | None = None,
    choice: str = "",
    category: tuple[int, str] | None = None,
) -> BulkPlan:
    """The plan for *change* on each product row, previewed before anything is sent."""
    if change not in BULK_CHANGES:
        raise ShopValueError(f"{change} is not a bulk change QUILL offers.")
    plan = BulkPlan()
    for row in rows:
        product_id, name, raw = _facts(row)
        if not product_id:
            continue
        variable = str(raw.get("product_type", "simple")) == "variable"
        regular, sale = str(raw.get("regular_price") or ""), str(raw.get("sale_price") or "")
        if change in ("sale", "end_sale", "price") and variable:
            plan.skipped.append(f"{name}: a variable product's prices are on its variations.")
            continue
        if change == "sale":
            start = _price(regular)
            if start is None or percent is None:
                plan.skipped.append(f"{name}: it has no regular price to take a sale from.")
                continue
            new = _money(start * (Decimal(100) - percent) / Decimal(100))
            plan.updates.append({"id": product_id, "sale_price": new})
            plan.undo.append({"id": product_id, "sale_price": sale})
            plan.lines.append(f"{name}: {regular}, on sale at {new}.")
        elif change == "end_sale":
            if not sale:
                plan.skipped.append(f"{name}: it is not on sale.")
                continue
            plan.updates.append({
                "id": product_id,
                "sale_price": "",
                "date_on_sale_from": "",
                "date_on_sale_to": "",
            })
            plan.undo.append({
                "id": product_id,
                "sale_price": sale,
                "date_on_sale_from": str(raw.get("sale_from") or ""),
                "date_on_sale_to": str(raw.get("sale_to") or ""),
            })
            plan.lines.append(f"{name}: sale at {sale} ends; back to {regular or 'no price'}.")
        elif change == "price":
            start = _price(regular)
            if start is None or percent is None:
                plan.skipped.append(f"{name}: it has no regular price to change.")
                continue
            new = _money(start * (Decimal(100) + percent) / Decimal(100))
            plan.updates.append({"id": product_id, "regular_price": new})
            plan.undo.append({"id": product_id, "regular_price": regular})
            plan.lines.append(f"{name}: {regular} becomes {new}.")
            if sale and _price(sale) is not None and Decimal(new) <= Decimal(sale):
                plan.lines.append(f"  Its sale price, {sale}, is no longer below it.")
        elif change == "stock":
            if choice not in STOCK_STATUSES:
                raise ShopValueError(f"{choice} is not a stock status.")
            if raw.get("manage_stock") == "yes":
                plan.skipped.append(f"{name}: WooCommerce sets its stock status from its count.")
                continue
            plan.updates.append({"id": product_id, "stock_status": choice})
            plan.undo.append({"id": product_id, "stock_status": _stock_slug(raw)})
            plan.lines.append(f"{name}: {STOCK_STATUSES[choice]}.")
        elif change == "status":
            if choice not in PRODUCT_STATUSES:
                raise ShopValueError(f"{choice} is not a product status.")
            old = str(raw.get("status_slug") or "")
            if old == choice:
                plan.skipped.append(f"{name}: it is already {PRODUCT_STATUSES[choice]}.")
                continue
            plan.updates.append({"id": product_id, "status": choice})
            plan.undo.append({"id": product_id, "status": old or "draft"})
            plan.lines.append(
                f"{name}: {PRODUCT_STATUSES.get(old, old)} becomes {PRODUCT_STATUSES[choice]}."
            )
        else:
            _plan_category(plan, product_id, name, raw, change, category)
    if not plan.updates:
        raise ShopValueError(
            "None of the products would change." + (f" {plan.skipped[0]}" if plan.skipped else "")
        )
    return plan


def _stock_slug(raw: Mapping[str, Any]) -> str:
    words = str(raw.get("stock") or "").casefold()
    for slug, said in STOCK_STATUSES.items():
        if said in words:
            return slug
    return "instock"


def _plan_category(
    plan: BulkPlan,
    product_id: int,
    name: str,
    raw: Mapping[str, Any],
    change: str,
    category: tuple[int, str] | None,
) -> None:
    if category is None:
        raise ShopValueError("Choose a category first.")
    number, title = category
    held = [int(c) for c in raw.get("category_ids") or [] if str(c).isdigit()]
    if change == "add_category":
        if number in held:
            plan.skipped.append(f"{name}: it is already in {title}.")
            return
        new = [*held, number]
        plan.lines.append(f"{name}: add {title}.")
    else:
        if number not in held:
            plan.skipped.append(f"{name}: it is not in {title}.")
            return
        new = [c for c in held if c != number]
        if not new:
            plan.skipped.append(f"{name}: {title} is its only category; WooCommerce needs one.")
            return
        plan.lines.append(f"{name}: take out of {title}.")
    plan.updates.append({"id": product_id, "categories": [{"id": c} for c in new]})
    plan.undo.append({"id": product_id, "categories": [{"id": c} for c in held]})


def batch_bodies(updates: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """The updates in WooCommerce's batch shape, at most :data:`BATCH_LIMIT` a request."""
    return [
        {"update": [dict(u) for u in updates[start : start + BATCH_LIMIT]]}
        for start in range(0, len(updates), BATCH_LIMIT)
    ]


def batch_failures(answer: Any) -> list[str]:
    """The products a batch answer says failed, each as "id: message"."""
    found = answer.get("update") if isinstance(answer, Mapping) else None
    failed: list[str] = []
    for item in found if isinstance(found, list) else []:
        error = item.get("error") if isinstance(item, Mapping) else None
        if isinstance(error, Mapping):
            failed.append(f"Product {item.get('id', '?')}: {error.get('message', 'refused')}")
    return failed
