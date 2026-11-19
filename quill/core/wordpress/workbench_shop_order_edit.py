"""Make a shop order, or change its items and addresses (complete.md 2.3, Shop).

For shops that take orders by telephone or fix one by hand. Three requests,
each previewed in words first:

- **New Order:** ``POST wc/v3/orders`` with the customer (or a guest's name
  and email), the products and quantities chosen, and a status. QUILL never
  marks it paid (``set_paid`` false): the shop takes the money its own way.
  WooCommerce works out the prices and totals.
- **Change Items:** ``POST wc/v3/orders/{id}`` with ``line_items``: an item
  already on the order is named by its item id with its new quantity, and a
  quantity of 0 removes it; a new product is added by its product id.
- **Change Address:** the billing or shipping address, sending only the
  fields that changed, and the old values kept for undo.

Removing an item by a quantity of 0 is WooCommerce's documented route in its
version 2 and 3 order controllers; it is marked for a live check on the test
site in complete.md 2.4. Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.wordpress.plugin_shop_seo import SHOP_NAMESPACE, ShopValueError
from quill.core.wordpress.site import raw_text

__all__ = [
    "ADDRESS_FIELDS",
    "NEW_ORDER_STATUSES",
    "ItemChange",
    "NewOrder",
    "OrderItem",
    "address_body",
    "address_preview",
    "items_body",
    "items_preview",
    "new_order_body",
    "new_order_preview",
    "order_items",
    "order_route",
    "parse_quantity",
]

#: Statuses a new order may start in; "Pending payment" is WooCommerce's own default.
NEW_ORDER_STATUSES: dict[str, str] = {
    "pending": "Pending payment",
    "processing": "Processing (paid, to be sent)",
    "on-hold": "On hold (waiting for payment)",
}

#: An address's fields, in the order a form asks them, with their spoken names.
ADDRESS_FIELDS: tuple[tuple[str, str], ...] = (
    ("first_name", "First name"),
    ("last_name", "Last name"),
    ("company", "Company"),
    ("address_1", "Address line 1"),
    ("address_2", "Address line 2"),
    ("city", "Town or city"),
    ("state", "State or county"),
    ("postcode", "Postal code"),
    ("country", "Country code, such as US"),
    ("email", "Email"),
    ("phone", "Telephone"),
)
_SHIPPING_FIELDS = frozenset(key for key, _name in ADDRESS_FIELDS if key not in ("email", "phone"))


def parse_quantity(text: str, *, allow_zero: bool) -> int:
    """A whole quantity from what was typed; 0 only where it removes an item."""
    words = text.strip()
    try:
        number = int(words)
    except ValueError:
        raise ShopValueError(f"{words or 'Nothing'} is not a whole number.") from None
    if number < 0 or (number == 0 and not allow_zero) or number > 100_000:
        lowest = 0 if allow_zero else 1
        raise ShopValueError(f"A quantity is a whole number from {lowest} to 100000.")
    return number


@dataclass(frozen=True)
class OrderItem:
    """One line of an order: its item id, product, name and quantity."""

    item_id: int
    product_id: int
    name: str
    quantity: int

    def words(self) -> str:
        return f"{self.quantity} x {self.name}"


def order_items(order: Mapping[str, Any]) -> list[OrderItem]:
    """The order's lines, as WooCommerce returns them."""
    found: list[OrderItem] = []
    for raw in order.get("line_items") or ():
        if not isinstance(raw, Mapping):
            continue
        try:
            item_id, quantity = int(raw.get("id") or 0), int(raw.get("quantity") or 0)
            product = int(raw.get("variation_id") or 0) or int(raw.get("product_id") or 0)
        except (TypeError, ValueError):
            continue
        if item_id:
            name = raw_text(raw.get("name")) or f"Product {product}"
            found.append(OrderItem(item_id, product, name, quantity))
    return found


# -- a new order ------------------------------------------------------------------------


@dataclass(frozen=True)
class NewOrder:
    """What the person chose for a new order."""

    status: str
    customer_id: int = 0
    customer_name: str = ""
    billing: Mapping[str, str] = field(default_factory=dict)
    lines: Sequence[tuple[int, str, int]] = ()
    """(product id, product name, quantity) for each product chosen."""


def new_order_body(order: NewOrder) -> dict[str, Any]:
    if order.status not in NEW_ORDER_STATUSES:
        raise ShopValueError(f"{order.status} is not a status a new order can start in.")
    if not order.lines:
        raise ShopValueError("An order needs at least one product.")
    if not order.customer_id and not str(order.billing.get("email", "")).strip():
        raise ShopValueError("A guest's order needs their email, for the receipt.")
    body: dict[str, Any] = {
        "status": order.status,
        "set_paid": False,
        "line_items": [
            {"product_id": product, "quantity": quantity}
            for product, _name, quantity in order.lines
        ],
    }
    if order.customer_id:
        body["customer_id"] = order.customer_id
    billing = {k: v.strip() for k, v in order.billing.items() if v and v.strip()}
    if billing:
        body["billing"] = billing
        body["shipping"] = {k: v for k, v in billing.items() if k in _SHIPPING_FIELDS}
    return body


def new_order_preview(order: NewOrder, site: str) -> list[str]:
    who = order.customer_name or order.billing.get("email", "") or "a guest"
    lines = [f"A new shop order on {site}, for {who}."]
    lines += [f"{quantity} x {name}." for _product, name, quantity in order.lines]
    lines.append(f"It starts as {NEW_ORDER_STATUSES.get(order.status, order.status)}.")
    lines.append(
        "WooCommerce works out the prices and the total. QUILL does not mark it paid, and "
        "WooCommerce may email the customer as it does for any new order."
    )
    return lines


# -- changing the items -----------------------------------------------------------------


@dataclass(frozen=True)
class ItemChange:
    """One line's new quantity (0 removes it), or a product to add (item_id 0)."""

    item_id: int
    product_id: int
    name: str
    quantity: int


def items_body(changes: Sequence[ItemChange]) -> dict[str, Any]:
    lines: list[dict[str, Any]] = []
    for change in changes:
        if change.item_id:
            lines.append({
                "id": change.item_id,
                "product_id": change.product_id,
                "quantity": change.quantity,
            })
        elif change.quantity > 0:
            lines.append({"product_id": change.product_id, "quantity": change.quantity})
    if not lines:
        raise ShopValueError("Nothing about the items would change.")
    return {"line_items": lines}


def items_preview(
    number: str, items: Sequence[OrderItem], changes: Sequence[ItemChange], site: str
) -> list[str]:
    before = {item.item_id: item for item in items}
    lines = [f"Shop order {number} on {site}:"]
    for change in changes:
        old = before.get(change.item_id)
        if old is None:
            lines.append(f"Add {change.quantity} x {change.name}.")
        elif change.quantity == 0:
            lines.append(f"Remove {old.name} (was {old.quantity}).")
        else:
            lines.append(f"{old.name}: {old.quantity} becomes {change.quantity}.")
    lines.append(
        "WooCommerce works out the total again. A refund or a payment for the difference is "
        "yours to make; QUILL does not move money here."
    )
    return lines


# -- changing an address ----------------------------------------------------------------


def address_body(
    which: str, old: Mapping[str, Any], new: Mapping[str, str]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """``(body, undo body)`` sending only the fields that changed."""
    if which not in ("billing", "shipping"):
        raise ShopValueError(f"{which} is not an address an order has.")
    allowed = {key for key, _name in ADDRESS_FIELDS}
    if which == "shipping":
        allowed &= _SHIPPING_FIELDS
    changed = {
        key: value.strip()
        for key, value in new.items()
        if key in allowed and value.strip() != str(old.get(key) or "").strip()
    }
    if not changed:
        raise ShopValueError(f"Nothing about the {which} address would change.")
    return {which: changed}, {which: {key: str(old.get(key) or "") for key in changed}}


def address_preview(
    number: str, which: str, old: Mapping[str, Any], body: Mapping[str, Any], site: str
) -> list[str]:
    names = dict(ADDRESS_FIELDS)
    lines = [f"Shop order {number} on {site}, {which} address:"]
    for key, value in body.get(which, {}).items():
        before = str(old.get(key) or "") or "(empty)"
        lines.append(f"{names.get(key, key)}: {before} becomes {value or '(empty)'}.")
    return lines


def order_route(order_id: int) -> str:
    return f"{SHOP_NAMESPACE}/orders/{int(order_id)}"
