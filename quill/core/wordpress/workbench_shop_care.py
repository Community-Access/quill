"""WooCommerce's reviews, webhooks, customers' details and variations in the Workbench.

All through ``wc/v3``, shaped from the test site's public index:

- **Product Reviews** (``products/reviews``): each review with its product,
  rating and status. Approve, Hold, Spam (several at once, an outcome each),
  Edit Review (its words and rating), Reply (a reply is a WordPress comment
  under the review, ``wp/v2/comments`` with the product as its post and the
  review as its parent, because WooCommerce's route has no reply), and Move
  to Trash. The reviewer's email is never kept in a row.
- **Webhooks** (``webhooks``): name, topic, status and delivery address.
  New Webhook leaves the secret to WooCommerce, which makes one; QUILL never
  reads, keeps or says a secret. Pause and Activate are a status change;
  Delete is for good (``force``).
- **Customers' details** (``customers/{id}``): the name, email, and billing
  and shipping addresses are read only when Edit Customer or Customer Details
  asks, never into a list, and only for a role WooCommerce lets read
  customers (``list_users``); changing them needs ``edit_users``.
- **Variations** (``products/{id}/variations/{id}``): price, sale price,
  stock and status, one variation at a time.

Wx-free; every write goes through :func:`quill.core.wordpress.workbench_plugin_write.checked_write`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from quill.core.wordpress.plugin_shop_seo import (
    SHOP_NAMESPACE,
    ShopValueError,
    check_price,
    check_quantity,
)
from quill.core.wordpress.site import friendly_date, rendered
from quill.core.wordpress.workbench_rows import WbRow

__all__ = [
    "ADDRESS_FIELDS",
    "REVIEW_STATUSES",
    "VARIATION_STATUSES",
    "WEBHOOK_TOPICS",
    "CustomerEdit",
    "customer_body",
    "customer_lines",
    "customer_preview",
    "reply_body",
    "review_edit_body",
    "review_row",
    "review_status_preview",
    "variation_body",
    "variation_name",
    "variation_preview",
    "webhook_body",
    "webhook_preview",
    "webhook_row",
]

REVIEWS = f"{SHOP_NAMESPACE}/products/reviews"
WEBHOOKS = f"{SHOP_NAMESPACE}/webhooks"
CUSTOMERS = f"{SHOP_NAMESPACE}/customers"

REVIEW_STATUSES: dict[str, str] = {
    "approved": "approved",
    "hold": "waiting for approval",
    "spam": "spam",
    "trash": "in the Trash",
}
"""WooCommerce's review statuses, as said."""


# -- reviews ------------------------------------------------------------------------------


def review_row(raw: Mapping[str, Any], site: str) -> WbRow:
    """One review: product, rating, reviewer's name and status; never the reviewer's email."""
    status = str(raw.get("status", "") or "")
    product = rendered(raw.get("product_name")) or f"product {raw.get('product_id', '')}"
    rating = int(raw.get("rating", 0) or 0)
    reviewer = rendered(raw.get("reviewer")) or "someone"
    words = rendered(raw.get("review"))
    when = str(raw.get("date_created", "") or "")
    stars = f"{rating} of 5" if rating else "no rating"
    return WbRow(
        kind="shop_review",
        site=site,
        key=str(raw.get("id", "") or ""),
        cells={
            "product": product,
            "rating": stars,
            "reviewer": reviewer,
            "status": REVIEW_STATUSES.get(status, status),
            "date": friendly_date(when) if when else "",
        },
        detail=f"{reviewer} on {product}, {stars}, {REVIEW_STATUSES.get(status, status)}: {words}",
        status=status,
        subkind="woocommerce",
        raw={
            "product": product,
            "product_id": int(raw.get("product_id", 0) or 0),
            "reviewer": reviewer,
            "rating": stars,
            "status": REVIEW_STATUSES.get(status, status),
            "review": words,
            "verified": "yes" if raw.get("verified") else "no",
            "_loaded": {"status": status, "review": words, "rating": rating},
        },
    )


def review_status_preview(rows: Sequence[WbRow], status: str, site: str) -> list[str]:
    said = REVIEW_STATUSES[status]
    lines = [f"{len(rows)} review{'s' if len(rows) != 1 else ''} on {site} become {said}:"]
    lines += [f"{r.cells.get('reviewer', '')} on {r.cells.get('product', '')}" for r in rows]
    if status == "approved":
        lines.append("Approved reviews show on the product's page.")
    elif status == "spam":
        lines.append("Spam is hidden from the page; Ctrl+Z puts each back as it was.")
    return lines


def review_edit_body(old: Mapping[str, Any], review: str, rating: str) -> dict[str, Any]:
    """The changed words and rating; a rating is 1 to 5."""
    body: dict[str, Any] = {}
    if review.strip() and review.strip() != str(old.get("review", "")).strip():
        body["review"] = review.strip()
    if rating.strip():
        try:
            stars = int(rating.strip())
        except ValueError as exc:
            raise ShopValueError("A rating is a whole number from 1 to 5.") from exc
        if not 1 <= stars <= 5:
            raise ShopValueError("A rating is a whole number from 1 to 5.")
        if stars != int(old.get("rating", 0) or 0):
            body["rating"] = stars
    return body


def reply_body(row: WbRow, text: str) -> dict[str, Any]:
    """A reply as WordPress makes one in wp-admin: a comment on the product, under the review."""
    if not text.strip():
        raise ShopValueError("A reply needs some words.")
    return {
        "post": int(row.raw.get("product_id", 0) or 0),
        "parent": row.object_id,
        "content": text.strip(),
    }


# -- webhooks -----------------------------------------------------------------------------

WEBHOOK_TOPICS: dict[str, str] = {
    "order.created": "an order is placed",
    "order.updated": "an order changes",
    "order.deleted": "an order is deleted",
    "product.created": "a product is made",
    "product.updated": "a product changes",
    "product.deleted": "a product is deleted",
    "customer.created": "a customer signs up",
    "customer.updated": "a customer changes",
    "coupon.created": "a coupon is made",
    "coupon.updated": "a coupon changes",
}
"""The topics New Webhook offers, with what each means."""

WEBHOOK_STATUSES = {"active": "active", "paused": "paused", "disabled": "turned off"}


def webhook_row(raw: Mapping[str, Any], site: str) -> WbRow:
    """One webhook, without its secret."""
    name = rendered(raw.get("name")) or "Unnamed webhook"
    topic = str(raw.get("topic", "") or "")
    status = str(raw.get("status", "") or "")
    url = str(raw.get("delivery_url", "") or "")
    when = WEBHOOK_TOPICS.get(topic, topic)
    return WbRow(
        kind="shop_webhook",
        site=site,
        key=str(raw.get("id", "") or ""),
        cells={
            "name": name,
            "topic": when,
            "status": WEBHOOK_STATUSES.get(status, status),
            "delivery": url,
        },
        detail=(
            f"{name}: when {when}, WooCommerce sends it to {url or 'no address'}. "
            f"{WEBHOOK_STATUSES.get(status, status).capitalize()}. Its secret is never shown."
        ),
        status=status,
        subkind="woocommerce",
        raw={
            "name": name,
            "topic": topic,
            "status": status,
            "delivery": url,
            "_loaded": {"status": status, "name": name},
        },
    )


def webhook_body(name: str, topic: str, url: str) -> dict[str, Any]:
    """A new webhook, active; no secret, so WooCommerce makes one."""
    if not name.strip():
        raise ShopValueError("A webhook needs a name.")
    if topic not in WEBHOOK_TOPICS:
        raise ShopValueError(f"WooCommerce has no webhook topic called {topic}.")
    if not url.strip().startswith("https://"):
        raise ShopValueError("The delivery address must start with https://.")
    return {"name": name.strip(), "topic": topic, "delivery_url": url.strip(), "status": "active"}


def webhook_preview(body: Mapping[str, Any], site: str) -> list[str]:
    return [
        f"A new webhook on {site}: {body['name']}.",
        f"When {WEBHOOK_TOPICS[str(body['topic'])]}, WooCommerce sends the details to "
        f"{body['delivery_url']}.",
        "That address receives your shop's data, customers' names and addresses included, "
        "so send only to a service you trust.",
        "WooCommerce makes its secret; QUILL never reads or says it.",
    ]


# -- customers' details ---------------------------------------------------------------------

ADDRESS_FIELDS: tuple[tuple[str, str], ...] = (
    ("first_name", "First name"),
    ("last_name", "Last name"),
    ("company", "Company"),
    ("address_1", "Address line 1"),
    ("address_2", "Address line 2"),
    ("city", "City"),
    ("state", "State or county"),
    ("postcode", "Postal code"),
    ("country", "Country code"),
    ("phone", "Telephone"),
)
"""An address's fields, as WooCommerce names them and as they are said."""


@dataclass(frozen=True)
class CustomerEdit:
    """What Edit Customer changes: one part (``account``, ``billing`` or ``shipping``)."""

    part: str
    values: Mapping[str, str]


def customer_lines(raw: Mapping[str, Any]) -> list[str]:
    """Customer Details: everything WooCommerce keeps about them, for a role that may read it."""
    name = " ".join(str(raw.get(k, "") or "") for k in ("first_name", "last_name")).strip()
    lines = [f"Name: {name or 'not given'}", f"Email: {raw.get('email') or 'not given'}"]
    for part in ("billing", "shipping"):
        found = raw.get(part)
        address: Mapping[str, Any] = found if isinstance(found, Mapping) else {}
        filled = [
            f"{label}: {address.get(key)}" for key, label in ADDRESS_FIELDS if address.get(key)
        ]
        if part == "billing" and address.get("email"):
            filled.append(f"Email: {address.get('email')}")
        lines.append(f"{part.capitalize()} address: " + ("; ".join(filled) or "none"))
    return lines


def customer_body(old: Mapping[str, Any], edit: CustomerEdit) -> dict[str, Any]:
    """Only what changed: top-level name and email, or one address's changed keys."""
    if edit.part == "account":
        body = {
            k: v.strip()
            for k, v in edit.values.items()
            if k in ("first_name", "last_name", "email") and v.strip() != str(old.get(k) or "")
        }
        if "email" in body and "@" not in body["email"]:
            raise ShopValueError("An email address needs an @.")
        return body
    if edit.part not in ("billing", "shipping"):
        raise ShopValueError(f"A customer has no {edit.part} details.")
    was = old.get(edit.part) if isinstance(old.get(edit.part), Mapping) else {}
    changed = {
        k: v.strip() for k, v in edit.values.items() if v.strip() != str((was or {}).get(k) or "")
    }
    return {edit.part: changed} if changed else {}


def customer_preview(name: str, old: Mapping[str, Any], body: Mapping[str, Any]) -> list[str]:
    lines = [f"{name}'s details change:"]
    labels = dict(ADDRESS_FIELDS) | {"email": "Email"}
    for key, value in body.items():
        if isinstance(value, Mapping):
            was = old.get(key) if isinstance(old.get(key), Mapping) else {}
            for sub, new in value.items():
                old_value = (was or {}).get(sub) or "not given"
                label = labels.get(sub, sub)
                lines.append(f"{key.capitalize()} {label}: {old_value} becomes {new or 'blank'}.")
            continue
        lines.append(f"{labels.get(key, key)}: {old.get(key) or 'not given'} becomes {value}.")
    lines.append("WooCommerce uses these on the customer's next order; past orders keep theirs.")
    return lines


# -- variations -----------------------------------------------------------------------------

VARIATION_STATUSES: dict[str, str] = {
    "publish": "for sale",
    "private": "hidden",
    "draft": "draft",
    "pending": "pending review",
}


def variation_name(raw: Mapping[str, Any]) -> str:
    options = [
        str(a.get("option", "") or "")
        for a in raw.get("attributes") or []
        if isinstance(a, Mapping) and a.get("option")
    ]
    return ", ".join(options) or f"Variation {raw.get('id', '')}"


def variation_body(
    old: Mapping[str, Any], price: str, sale: str, stock: str, status: str
) -> dict[str, Any]:
    """Only what changed, checked: prices, a stock count (WooCommerce then manages it), status."""
    body: dict[str, Any] = {}
    regular = check_price(price, label="The regular price")
    if regular != str(old.get("regular_price", "") or ""):
        body["regular_price"] = regular
    on_sale = check_price(sale, label="The sale price")
    if on_sale != str(old.get("sale_price", "") or ""):
        body["sale_price"] = on_sale
    if stock.strip():
        count = check_quantity(stock)
        if str(count) != str(old.get("stock_quantity", "") or ""):
            body["manage_stock"] = True
            body["stock_quantity"] = count
    if status not in VARIATION_STATUSES:
        raise ShopValueError(f"A variation has no status called {status}.")
    if status != str(old.get("status", "") or ""):
        body["status"] = status
    return body


def variation_preview(product: str, raw: Mapping[str, Any], body: Mapping[str, Any]) -> list[str]:
    lines = [f"{product}, the {variation_name(raw)} variation:"]
    for key, label in (("regular_price", "Regular price"), ("sale_price", "Sale price")):
        if key in body:
            lines.append(f"{label}: {raw.get(key) or 'not set'} becomes {body[key] or 'not set'}.")
    if "stock_quantity" in body:
        lines.append(
            f"Stock: {raw.get('stock_quantity') or 'not counted'} becomes {body['stock_quantity']}."
        )
    if "status" in body:
        lines.append(
            f"Status: {VARIATION_STATUSES.get(str(raw.get('status')), 'unknown')} "
            f"becomes {VARIATION_STATUSES[body['status']]}."
        )
    lines.append("The other variations and past orders are not touched.")
    return lines
