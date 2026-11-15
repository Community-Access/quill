"""Context-menu rows for WooCommerce's reviews, shipping, taxes, webhooks, attributes, brands,
customers and variations, The Events Calendar's categories and tags, and Yoast SEO's bulk editor.

Split from :mod:`quill.core.wordpress.workbench_plugin_actions` (GATE-11), which
merges these in: :data:`MORE_ROWS` are new row kinds, :data:`MORE_EXTRA` go
into existing kinds' menus before Properties, and :data:`MORE_NEW_HERE`,
:data:`MORE_TRASH` and :data:`MORE_KEYLESS` join their tables. Every command
has a key or a written reason (family rule 8): New is Ctrl+N on its node and
a review's Move to Trash is Delete; a permanent delete (shipping zones, tax
rates and classes, attributes, brands, webhooks, event terms have no Trash)
is never a bare key (rule 4). *requirement* is the site capability each needs,
so the Workbench greys it and says which role would allow it. Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping

from quill.core.workbench.actions import ActionRow, Tier

__all__ = ["MORE_EXTRA", "MORE_KEYLESS", "MORE_NEW_HERE", "MORE_ROWS", "MORE_TRASH"]

_SHOP = "manage_woocommerce"


def _c(verb: str) -> str:
    return f"wordpress.workbench.{verb}"


def _a(
    verb: str,
    label: str,
    help: str,  # noqa: A002 - field name
    *,
    tier: Tier = Tier.READ,
    needs: str = "",
    default: bool = False,
) -> ActionRow:
    return ActionRow(_c(verb), label, tier, needs, help, default)


_READ = _a("read", "Read in Full", "Move to the details pane to read it.", default=True)
_SHEET = _a("sheet", "Properties...", "Everything about it on one sheet. Alt+Enter.")


def _new(verb: str, label: str, what: str, needs: str = _SHOP) -> ActionRow:
    return _a(verb, label, f"{what}, after a preview. Ctrl+N.", tier=Tier.WRITE, needs=needs)


_RENAME = _a(
    "rename_shop_item",
    "Rename...",
    "Change its name, after a preview.",
    tier=Tier.WRITE,
    needs=_SHOP,
)
_DELETE = _a(
    "delete_shop_item",
    "Delete...",
    "Gone for good, after a preview of what goes with it: WooCommerce keeps no Trash for this.",
    tier=Tier.DESTRUCTIVE,
    needs=_SHOP,
)

MORE_ROWS: Mapping[str, tuple[ActionRow, ...]] = {
    "shop_review": (
        _READ,
        _a(
            "approve_review",
            "Approve",
            "Show it on the product's page; several at once.",
            tier=Tier.WRITE,
            needs="moderate_comments",
        ),
        _a(
            "hold_review",
            "Hold",
            "Take it off the page until approved; several at once.",
            tier=Tier.WRITE,
            needs="moderate_comments",
        ),
        _a(
            "spam_review",
            "Mark as Spam",
            "Hide it as spam; several at once.",
            tier=Tier.WRITE,
            needs="moderate_comments",
        ),
        _a(
            "reply_review",
            "Reply...",
            "Answer it under the review, as you, after a preview.",
            tier=Tier.WRITE,
            needs="moderate_comments",
        ),
        _a(
            "edit_review",
            "Edit Review...",
            "Change its words or rating, after a preview.",
            tier=Tier.WRITE,
            needs="moderate_comments",
        ),
        _a(
            "trash_review",
            "Move to Trash...",
            "Into WooCommerce's Trash, after a preview. Delete.",
            tier=Tier.ORGANIZE,
            needs="moderate_comments",
        ),
        _SHEET,
    ),
    "shop_zone": (
        _READ,
        _a(
            "zone_locations",
            "Locations...",
            "The countries, states and postal codes it covers.",
            tier=Tier.WRITE,
            needs=_SHOP,
        ),
        _a(
            "zone_methods",
            "Methods...",
            "Its shipping methods: turn one on or off, change a cost, add or remove one.",
            tier=Tier.WRITE,
            needs=_SHOP,
        ),
        _new("new_zone", "New Shipping Zone...", "A zone"),
        _RENAME,
        _DELETE,
        _SHEET,
    ),
    "shop_tax_rate": (
        _READ,
        _a(
            "edit_tax_rate",
            "Edit Tax Rate...",
            "Its name, percentage and where it applies.",
            tier=Tier.WRITE,
            needs=_SHOP,
        ),
        _new("new_tax_rate", "New Tax Rate...", "A rate"),
        _DELETE,
        _SHEET,
    ),
    "shop_tax_class": (
        _READ,
        _new("new_tax_class", "New Tax Class...", "A class"),
        _DELETE,
        _SHEET,
    ),
    "shop_webhook": (
        _READ,
        _a(
            "toggle_webhook",
            "Pause or Activate...",
            "Stop it sending, or start it again.",
            tier=Tier.WRITE,
            needs=_SHOP,
        ),
        _new("new_webhook", "New Webhook...", "A webhook; WooCommerce makes its secret"),
        _a(
            "delete_webhook",
            "Delete...",
            "Gone for good, after a preview.",
            tier=Tier.DESTRUCTIVE,
            needs=_SHOP,
        ),
        _SHEET,
    ),
    "shop_attribute": (
        _READ,
        _a(
            "attribute_terms",
            "Terms...",
            "Its values, such as Small and Large: add, rename, delete.",
            tier=Tier.WRITE,
            needs=_SHOP,
        ),
        _new("new_attribute", "New Attribute...", "An attribute"),
        _RENAME,
        _DELETE,
        _SHEET,
    ),
    "shop_brand": (
        _READ,
        _new("new_brand", "New Brand...", "A brand"),
        _RENAME,
        _DELETE,
        _SHEET,
    ),
    "tribe_category": (
        _READ,
        _new("new_event_category", "New Event Category...", "A category", "manage_categories"),
        _a(
            "rename_event_term",
            "Rename...",
            "Change its name, after a preview.",
            tier=Tier.WRITE,
            needs="manage_categories",
        ),
        _a(
            "delete_event_term",
            "Delete...",
            "Gone for good; its events keep everything else.",
            tier=Tier.DESTRUCTIVE,
            needs="manage_categories",
        ),
        _SHEET,
    ),
    "tribe_tag": (
        _READ,
        _new("new_event_tag", "New Event Tag...", "A tag", "manage_categories"),
        _a(
            "rename_event_term",
            "Rename...",
            "Change its name, after a preview.",
            tier=Tier.WRITE,
            needs="manage_categories",
        ),
        _a(
            "delete_event_term",
            "Delete...",
            "Gone for good; its events keep everything else.",
            tier=Tier.DESTRUCTIVE,
            needs="manage_categories",
        ),
        _SHEET,
    ),
}
"""The rows for each kind these commands add."""

MORE_EXTRA: Mapping[str, tuple[ActionRow, ...]] = {
    "shop_product": (
        _a(
            "edit_variation",
            "Edit a Variation...",
            "One variation's price, sale price, stock and status, after a preview.",
            tier=Tier.WRITE,
            needs=_SHOP,
        ),
    ),
    "shop_customer": (
        _a(
            "customer_details",
            "Customer Details",
            "Their email and addresses, read now, for a role WooCommerce lets read them.",
            needs="list_users",
        ),
        _a(
            "edit_customer",
            "Edit Customer...",
            "Their name and email, or an address, after a preview of old and new.",
            tier=Tier.WRITE,
            needs="edit_users",
        ),
    ),
    "tribe_event": (
        _a(
            "set_event_terms",
            "Categories and Tags...",
            "Which categories and tags it has, by name, after a preview.",
            tier=Tier.WRITE,
            needs="edit_posts",
        ),
    ),
    "seo_item": (
        _a(
            "bulk_seo",
            "Bulk SEO Editor...",
            "Every post and page's SEO title and description, changed where they stand.",
            tier=Tier.WRITE,
            needs="wpseo_manage_options",
        ),
    ),
}
"""Rows added to existing kinds' menus, before Properties."""

MORE_NEW_HERE: dict[str, str] = {
    "shop_shipping": "do_new_zone",
    "shop_taxes": "do_new_tax_rate",
    "shop_tax_classes": "do_new_tax_class",
    "shop_webhooks": "do_new_webhook",
    "shop_attributes": "do_new_attribute",
    "shop_brands": "do_new_brand",
    "events_categories": "do_new_event_category",
    "events_tags": "do_new_event_tag",
}
"""The node key -> the handler Ctrl+N (New Here) runs there."""

MORE_TRASH: dict[str, str] = {"shop_review": "do_trash_review"}
"""The row kind -> the handler Delete runs (only reviews here have a Trash)."""

_NEW = "Ctrl+N (New Here) on its node runs it; the context menu has it too."
_GONE = "A delete for good, with no Trash: never a bare key (rule 4)."
_RARE = "Set up once and changed a few times a year, behind a preview (rule 9)."

MORE_KEYLESS: dict[str, str] = {
    _c("approve_review"): "Reviews are moderated a few times a week, on a selection (rule 9).",
    _c("hold_review"): "Reviews are moderated a few times a week, on a selection (rule 9).",
    _c("spam_review"): "Reviews are moderated a few times a week, on a selection (rule 9).",
    _c("reply_review"): "A reply is written now and then, behind a preview (rule 9).",
    _c("edit_review"): "A review is corrected rarely (rule 9).",
    _c("trash_review"): "Delete (Move to Trash) on its row runs it, after a preview.",
    _c("zone_locations"): _RARE,
    _c("zone_methods"): _RARE,
    _c("new_zone"): _NEW,
    _c("rename_shop_item"): _RARE,
    _c("delete_shop_item"): _GONE,
    _c("edit_tax_rate"): _RARE,
    _c("new_tax_rate"): _NEW,
    _c("new_tax_class"): _NEW,
    _c("toggle_webhook"): _RARE,
    _c("new_webhook"): _NEW,
    _c("delete_webhook"): _GONE,
    _c("attribute_terms"): _RARE,
    _c("new_attribute"): _NEW,
    _c("new_brand"): _NEW,
    _c("new_event_category"): _NEW,
    _c("new_event_tag"): _NEW,
    _c("rename_event_term"): _RARE,
    _c("delete_event_term"): _GONE,
    _c("edit_variation"): "Prices and stock change now and then, behind a preview (rule 9).",
    _c("customer_details"): "Read when an order or a customer is in question (rule 9).",
    _c("edit_customer"): "A customer's details change rarely, behind a preview (rule 9).",
    _c("set_event_terms"): "An event's terms are set when it is made (rule 9).",
    _c("bulk_seo"): "A window opened for an SEO pass now and then (rule 9).",
}
"""Why each command here has no chord of its own (family rule 8)."""
