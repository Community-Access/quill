"""WooCommerce and SEO plugins, recognised (wordpress.md 9.15).

**WooCommerce** (``wc/v3``), read and light edit only: a product's price and
stock in Properties, with the regular price, sale price and stock quantity
changeable; and orders as a list QUILL reads aloud. Orders are never edited,
and never leave QUILL without asking first, because they hold customers'
names and addresses.

**SEO plugins** that register their meta for the REST API (Yoast SEO, Rank
Math): the SEO title and description, each with its length against what
search engines show.

Wx-free; every request goes through
:class:`~quill.core.wordpress.api.WordPressApi`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.wordpress.api import WordPressApi
from quill.core.wordpress.site import friendly_date, kind_route, rendered

SHOP_NAMESPACE = "wc/v3"
PRODUCT_KINDS = frozenset({"product"})


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


class ShopValueError(CodedError, ValueError):
    """A price or a stock count QUILL cannot read."""

    code = "QUILL-WP-SHOP-VALUE"


# --------------------------------------------------------------------------- #
# Products


@dataclass(frozen=True)
class Product:
    id: int
    name: str
    price: str
    regular_price: str
    sale_price: str
    stock_status: str
    manage_stock: bool
    stock_quantity: int | None
    currency: str = ""

    def stock_words(self) -> str:
        status = {
            "instock": "in stock",
            "outofstock": "out of stock",
            "onbackorder": "on backorder",
        }.get(self.stock_status, self.stock_status or "stock not given")
        if self.manage_stock and self.stock_quantity is not None:
            return f"{status}, {self.stock_quantity} left"
        return status

    def facts(self) -> str:
        sale = f" (on sale from {self.regular_price})" if self.sale_price else ""
        return f"Price: {self.price or 'not set'}{sale}\nStock: {self.stock_words()}\n"


def product_from(raw: Any) -> Product:
    data = raw if isinstance(raw, dict) else {}
    quantity = data.get("stock_quantity")
    return Product(
        id=int(data.get("id", 0) or 0),
        name=rendered(data.get("name")) or "Untitled product",
        price=str(data.get("price", "") or ""),
        regular_price=str(data.get("regular_price", "") or ""),
        sale_price=str(data.get("sale_price", "") or ""),
        stock_status=str(data.get("stock_status", "") or ""),
        manage_stock=bool(data.get("manage_stock", False)),
        stock_quantity=int(quantity) if isinstance(quantity, (int, float)) else None,
    )


def load_product(api: WordPressApi, product_id: int) -> Product:
    return product_from(api.get(f"{SHOP_NAMESPACE}/products/{product_id}"))


_PRICE = re.compile(r"^\d+(\.\d{1,2})?$")


def check_price(text: str, *, label: str) -> str:
    clean = text.strip()
    if clean and not _PRICE.match(clean):
        raise ShopValueError(f"{label} needs a number such as 12.50, with no currency sign.")
    return clean


def check_quantity(text: str) -> int:
    try:
        value = int(text.strip())
    except ValueError as exc:
        raise ShopValueError("Stock needs a whole number, such as 12.") from exc
    if value < 0:
        raise ShopValueError("Stock cannot be below nought.")
    return value


def update_product(
    api: WordPressApi,
    product_id: int,
    *,
    regular_price: str,
    sale_price: str,
    stock_quantity: int | None = None,
) -> Product:
    body: dict[str, Any] = {"regular_price": regular_price, "sale_price": sale_price}
    if stock_quantity is not None:
        body["stock_quantity"] = stock_quantity
    return product_from(api.post(f"{SHOP_NAMESPACE}/products/{product_id}", body))


# --------------------------------------------------------------------------- #
# Orders, to read


@dataclass(frozen=True)
class Order:
    id: int
    number: str
    status: str
    total: str
    currency: str
    customer: str
    created: str
    items: tuple[tuple[str, int, str], ...] = field(default_factory=tuple)
    address: str = ""

    def spoken(self) -> str:
        count = sum(q for _n, q, _t in self.items)
        things = f"{count} {'item' if count == 1 else 'items'}"
        return (
            f"Order {self.number}, {self.status.replace('-', ' ')}, {things}, "
            f"{self.total} {self.currency}, from {self.customer or 'a guest'}, "
            f"{friendly_date(self.created)}"
        )

    def details(self) -> str:
        lines = [f"{q} x {name}, {total}" for name, q, total in self.items]
        if self.address:
            lines.append(f"Ship to: {self.address}")
        return "\n".join(lines) or "No items."


def order_from(raw: Any) -> Order:
    data = raw if isinstance(raw, dict) else {}
    billing = _as_dict(data.get("billing"))
    shipping = _as_dict(data.get("shipping"))
    who = " ".join(str(billing.get(k, "") or "") for k in ("first_name", "last_name")).strip()
    address = ", ".join(
        str(shipping.get(k, "") or "")
        for k in ("address_1", "address_2", "city", "postcode", "country")
        if shipping.get(k)
    )
    items = tuple(
        (rendered(i.get("name")), int(i.get("quantity", 0) or 0), str(i.get("total", "") or ""))
        for i in data.get("line_items", []) or []
        if isinstance(i, dict)
    )
    return Order(
        id=int(data.get("id", 0) or 0),
        number=str(data.get("number", "") or data.get("id", "")),
        status=str(data.get("status", "") or ""),
        total=str(data.get("total", "") or ""),
        currency=str(data.get("currency", "") or ""),
        customer=who,
        created=str(data.get("date_created_gmt", "") or data.get("date_created", "") or ""),
        items=items,
        address=address,
    )


def recent_orders(api: WordPressApi, *, per_page: int = 50) -> list[Order]:
    """The newest orders, read only."""
    raw = api.get(f"{SHOP_NAMESPACE}/orders", per_page=per_page, orderby="date", order="desc")
    return [order_from(r) for r in raw if isinstance(r, dict)] if isinstance(raw, list) else []


# --------------------------------------------------------------------------- #
# SEO title and description

#: meta key -> (plugin, which field, how long search engines show).
SEO_FIELDS: dict[str, tuple[str, str, int]] = {
    "_yoast_wpseo_title": ("Yoast SEO", "title", 60),
    "_yoast_wpseo_metadesc": ("Yoast SEO", "description", 160),
    "rank_math_title": ("Rank Math", "title", 60),
    "rank_math_description": ("Rank Math", "description", 160),
}

SEO_NAMESPACES = ("yoast/v1", "rankmath/v1")


def seo_fields(meta: Any) -> list[tuple[str, str, int, str]]:
    """``(key, label, limit, value)`` for each SEO field the item's meta carries."""
    if not isinstance(meta, dict):
        return []
    found = []
    for key, (_plugin, which, limit) in SEO_FIELDS.items():
        if key in meta:
            label = "SEO title" if which == "title" else "SEO description"
            found.append((key, label, limit, str(meta.get(key) or "")))
    return found


def length_note(label: str, value: str, limit: int) -> str:
    """ "SEO title: 54 characters of about 60" or "... 72 characters, 12 over about 60"."""
    count = len(value)
    if count > limit:
        return f"{label}: {count} characters, {count - limit} over about {limit}"
    return f"{label}: {count} characters of about {limit}"


def load_meta(api: WordPressApi, kind: str, item_id: int) -> dict[str, Any]:
    raw = api.get(f"{kind_route(kind)}/{item_id}", context="edit", _fields="meta")
    meta = raw.get("meta") if isinstance(raw, dict) else None
    return meta if isinstance(meta, dict) else {}


def save_meta(api: WordPressApi, kind: str, item_id: int, values: dict[str, str]) -> None:
    api.post(f"{kind_route(kind)}/{item_id}", {"meta": values})


def seo_facts(meta: Any) -> str:
    return "".join(
        f"{label}: {value or '(empty)'}\n{length_note(label, value, limit)}\n"
        for _k, label, limit, value in seo_fields(meta)
    )
