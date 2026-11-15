"""WooCommerce's catalogue in the Workbench: products, filters, edits, variations (Package 8).

Everything goes through ``wc/v3`` on the site's own client:

- the list takes WooCommerce's own filters (:data:`PRODUCT_FILTERS`), so a
  filter node or a query narrows on the site, not in QUILL;
- a product's row carries what Properties reads: type, SKU, prices and sale
  dates, stock, categories and tags, visibility, tax, weight and shipping;
- **Edit Product** changes the regular and sale price, the stock count, the
  status and the categories, previewed as "old becomes new", and sends only
  what changed (:func:`edit_body`);
- **New Product** makes a draft, **Duplicate** asks WooCommerce's own
  ``products/{id}/duplicate`` (its copy is a draft too), and **Move to
  Trash** is ``DELETE products/{id}`` without ``force``, so WooCommerce keeps
  it in its Trash;
- a variable product's **variations** are read as one line each.

Wx-free; the windows ask, preview and run these off the UI thread.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from quill.core.wordpress.plugin_shop_seo import (
    SHOP_NAMESPACE,
    ShopValueError,
    check_price,
    check_quantity,
    product_from,
)
from quill.core.wordpress.site import rendered
from quill.core.wordpress.workbench_rows import WbRow

__all__ = [
    "PRODUCT_FILTERS",
    "PRODUCT_STATUSES",
    "ProductEdit",
    "category_ids",
    "duplicate_preview",
    "edit_body",
    "edit_preview",
    "new_product_body",
    "new_product_preview",
    "product_params",
    "product_row",
    "trash_preview",
    "variation_lines",
]

PRODUCT_FILTERS = frozenset({
    "status",
    "type",
    "stock_status",
    "category",
    "tag",
    "on_sale",
    "featured",
    "sku",
    "search",
    "min_price",
    "max_price",
    "orderby",
    "order",
})
"""The ``wc/v3/products`` arguments a filter node or query may set (from the live index)."""

PRODUCT_STATUSES: dict[str, str] = {
    "publish": "published",
    "draft": "draft",
    "pending": "pending review",
    "private": "private",
}
"""The statuses Edit Product offers, with how each is said."""

_TYPES = {
    "simple": "a simple product",
    "variable": "a variable product, with variations",
    "grouped": "a grouped product",
    "external": "an external or affiliate product",
}
_VISIBILITY = {
    "visible": "shop and search results",
    "catalog": "shop only",
    "search": "search results only",
    "hidden": "hidden",
}


def product_params(query: Mapping[str, object]) -> dict[str, object]:
    """The parts of *query* WooCommerce's products route takes; the rest are QUILL's own."""
    params: dict[str, object] = {"orderby": "date", "order": "desc"}
    for key, value in query.items():
        if key in PRODUCT_FILTERS and str(value).strip():
            params[key] = value
    return params


def _names(items: Any) -> str:
    found = [rendered(i.get("name")) for i in items or [] if isinstance(i, Mapping)]
    return ", ".join(n for n in found if n) or "none"


def product_row(raw: Mapping[str, Any], site: str) -> WbRow:
    """One product, with everything Properties reads; read through, changed by command."""
    product = product_from(dict(raw))
    status = str(raw.get("status", "") or "")
    price = product.price or "not set"
    stock = product.stock_words()
    kind = str(raw.get("type", "") or "simple")
    sale = ""
    if product.sale_price:
        sale = f", on sale from {product.regular_price or 'its regular price'}"
    variations = raw.get("variations") or []
    facts = {
        "name": product.name,
        "type": _TYPES.get(kind, kind),
        "status": PRODUCT_STATUSES.get(status, status),
        "status_slug": status,
        "sku": str(raw.get("sku", "") or "none"),
        "price": price,
        "regular_price": product.regular_price,
        "sale_price": product.sale_price,
        "sale_from": str(raw.get("date_on_sale_from", "") or ""),
        "sale_to": str(raw.get("date_on_sale_to", "") or ""),
        "stock": stock,
        "manage_stock": "yes" if product.manage_stock else "no",
        "stock_quantity": "" if product.stock_quantity is None else str(product.stock_quantity),
        "backorders": str(raw.get("backorders", "") or "no"),
        "categories": _names(raw.get("categories")),
        "category_ids": [int(c.get("id", 0) or 0) for c in raw.get("categories") or []],
        "tags": _names(raw.get("tags")),
        "featured": "yes" if raw.get("featured") else "no",
        "visibility": _VISIBILITY.get(str(raw.get("catalog_visibility", "")), "shop and search"),
        "tax_status": str(raw.get("tax_status", "") or ""),
        "weight": str(raw.get("weight", "") or ""),
        "shipping_class": str(raw.get("shipping_class", "") or "none"),
        "variations": str(len(variations)) if isinstance(variations, list) else "0",
        "description": rendered(raw.get("short_description")),
        "product_type": kind,
    }
    return WbRow(
        kind="shop_product",
        site=site,
        key=str(product.id),
        cells={"name": product.name, "price": price, "stock": stock, "status": status},
        detail=(
            f"{product.name}, {_TYPES.get(kind, kind)}. Price {price}{sale}, {stock}, "
            f"{PRODUCT_STATUSES.get(status, status or 'no status')}. Categories: "
            f"{facts['categories']}. Enter opens it on the site."
        ),
        link=str(raw.get("permalink", "") or ""),
        status=status,
        subkind="woocommerce",
        raw=facts,
    )


# -- Edit Product ---------------------------------------------------------------------


@dataclass(frozen=True)
class ProductEdit:
    """What Edit Product was given; ``None`` leaves that part as it is."""

    regular_price: str | None = None
    sale_price: str | None = None
    stock_quantity: str | None = None
    status: str | None = None
    category_ids: tuple[int, ...] | None = None
    category_names: str = ""


def category_ids(text: str, known: Iterable[Mapping[str, Any]]) -> tuple[tuple[int, ...], str]:
    """``"Mugs, Gifts"`` -> the shop's category ids and their names, matched without case.

    A name the shop does not have is refused, naming it, rather than made:
    new categories are made in Products > Categories.
    """
    by_name = {rendered(c.get("name")).casefold(): c for c in known if isinstance(c, Mapping)}
    wanted = [part.strip() for part in text.split(",") if part.strip()]
    missing = [w for w in wanted if w.casefold() not in by_name]
    if missing:
        raise ShopValueError(
            f"The shop has no category called {', '.join(missing)}. Categories are made in "
            "Products > Categories, in wp-admin."
        )
    found = [by_name[w.casefold()] for w in wanted]
    ids = tuple(int(c.get("id", 0) or 0) for c in found)
    return ids, ", ".join(rendered(c.get("name")) for c in found)


def edit_body(old: Mapping[str, Any], edit: ProductEdit) -> dict[str, Any]:
    """Only what changed, in WooCommerce's own field names; checked first."""
    body: dict[str, Any] = {}
    if edit.regular_price is not None:
        value = check_price(edit.regular_price, label="The regular price")
        if value != str(old.get("regular_price", "")):
            body["regular_price"] = value
    if edit.sale_price is not None:
        value = check_price(edit.sale_price, label="The sale price")
        if value != str(old.get("sale_price", "")):
            body["sale_price"] = value
    if edit.stock_quantity is not None and edit.stock_quantity.strip():
        count = check_quantity(edit.stock_quantity)
        if str(count) != str(old.get("stock_quantity", "")):
            body["manage_stock"] = True
            body["stock_quantity"] = count
    if edit.status is not None and edit.status != old.get("status_slug", old.get("status")):
        if edit.status not in PRODUCT_STATUSES:
            raise ShopValueError(f"WooCommerce has no product status called {edit.status}.")
        body["status"] = edit.status
    if edit.category_ids is not None and list(edit.category_ids) != list(
        old.get("category_ids") or []
    ):
        body["categories"] = [{"id": i} for i in edit.category_ids]
    return body


def edit_preview(
    name: str, site: str, old: Mapping[str, Any], body: Mapping[str, Any], edit: ProductEdit
) -> list[str]:
    """What Edit Product changes, one line each, in words."""
    lines: list[str] = []

    def was(key: str) -> str:
        return str(old.get(key, "") or "") or "not set"

    if "regular_price" in body:
        new_price = body["regular_price"] or "not set"
        lines.append(f"Regular price: {was('regular_price')} becomes {new_price}.")
    if "sale_price" in body:
        new = body["sale_price"] or "no sale price, so the sale ends"
        lines.append(f"Sale price: {was('sale_price')} becomes {new}.")
    if "stock_quantity" in body:
        lines.append(
            f"Stock: {was('stock_quantity')} becomes {body['stock_quantity']}; WooCommerce "
            "manages this product's stock from now on."
        )
    if "status" in body:
        lines.append(
            f"Status: {was('status')} becomes {PRODUCT_STATUSES[body['status']]}."
            + (" Shoppers can buy it." if body["status"] == "publish" else "")
        )
    if "categories" in body:
        lines.append(f"Categories: {was('categories')} become {edit.category_names or 'none'}.")
    return [
        f"{name} on {site}:",
        *lines,
        "Nothing else about the product changes, and no order is touched.",
    ]


# -- New, Duplicate, Trash --------------------------------------------------------------


def new_product_body(name: str, price: str, kind: str = "simple") -> dict[str, Any]:
    """A new product, always a draft: nothing is on sale until it is published."""
    if not name.strip():
        raise ShopValueError("A product needs a name.")
    if kind not in _TYPES:
        raise ShopValueError(f"WooCommerce has no product type called {kind}.")
    return {
        "name": name.strip(),
        "type": kind,
        "regular_price": check_price(price, label="The price"),
        "status": "draft",
    }


def new_product_preview(body: Mapping[str, Any], site: str) -> list[str]:
    price = body.get("regular_price") or "no price yet"
    return [
        f"A new product on {site}: {body['name']}, {_TYPES[str(body['type'])]}, {price}.",
        "It is made as a draft, so shoppers cannot see or buy it until you publish it "
        "(Edit Product, status published).",
    ]


def duplicate_preview(name: str, site: str) -> list[str]:
    return [
        f"WooCommerce copies {name} on {site}, with its prices, stock settings, categories "
        "and variations.",
        "The copy is a draft named with (Copy) after it; the original is not changed.",
    ]


def trash_preview(name: str, site: str) -> list[str]:
    return [
        f"{name} moves to WooCommerce's Trash on {site}; shoppers can no longer buy it.",
        "Past orders keep their lines. Restore it from Products > Trash in wp-admin.",
    ]


def product_route(product_id: int) -> str:
    return f"{SHOP_NAMESPACE}/products/{product_id}"


# -- variations ------------------------------------------------------------------------


def variation_lines(variations: Sequence[Mapping[str, Any]]) -> list[str]:
    """``"Large, Blue: 14.00, in stock, 3 left, SKU MUG-L"`` for each variation."""
    lines = []
    for raw in variations:
        if not isinstance(raw, Mapping):
            continue
        attributes = [
            str(a.get("option", "") or "")
            for a in raw.get("attributes") or []
            if isinstance(a, Mapping) and a.get("option")
        ]
        product = product_from(dict(raw))
        which = ", ".join(attributes) or f"Variation {product.id}"
        sku = str(raw.get("sku", "") or "")
        sale = f" (on sale from {product.regular_price})" if product.sale_price else ""
        line = f"{which}: {product.price or 'no price'}{sale}, {product.stock_words()}"
        lines.append(line + (f", SKU {sku}" if sku else ""))
    return lines
