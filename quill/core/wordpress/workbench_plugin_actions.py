"""Context-menu rows for WooCommerce, The Events Calendar, Yoast SEO and QAF (Packages 8-13).

Split from :mod:`quill.core.wordpress.workbench_actions` (GATE-11), which
splices :data:`PLUGIN_ACTION_ROWS` into its table. Every command has a key or
a written reason (family rule 8): New is Ctrl+N on the node (New Here,
:data:`PLUGIN_NEW_HERE`) and Move to Trash is Delete on the row
(:data:`PLUGIN_TRASH`); the rest are once-in-a-while jobs (rule 9) behind a
preview, reached from the context menu, and :data:`KEYLESS` says why each
has no chord of its own. A refund moves money: it is tier 3, never a bare
key, and never part of a batch. Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping

from quill.core.wordpress.workbench_plugin_actions_more import (
    MORE_EXTRA,
    MORE_KEYLESS,
    MORE_NEW_HERE,
    MORE_ROWS,
    MORE_TRASH,
)
from quill.core.workbench.actions import ActionRow, Tier

__all__ = [
    "KEYLESS",
    "PLUGIN_ACTION_ROWS",
    "PLUGIN_NEW_HERE",
    "PLUGIN_TRASH",
    "QAF_FORM_ROWS",
    "command",
]


def command(verb: str) -> str:
    """The same ids as :func:`quill.core.wordpress.workbench_window_menu.command`."""
    return f"wordpress.workbench.{verb}"


def _a(
    verb: str,
    label: str,
    help: str,  # noqa: A002 - field name
    *,
    tier: Tier = Tier.READ,
    default: bool = False,
) -> ActionRow:
    return ActionRow(command(verb), label, tier, "", help, default)


_READ = _a("read", "Read in Full", "Move to the details pane to read it.", default=True)
_SHEET = _a("sheet", "Properties...", "Everything about it on one sheet. Alt+Enter.")


def _open(label: str, help: str) -> ActionRow:  # noqa: A002 - field name
    return _a("open_on_site", label, help, default=True)


def _trash(noun: str) -> ActionRow:
    return _a(
        f"trash_{noun}",
        "Move to Trash...",
        "Into the plugin's Trash, after a preview of what it affects. Delete.",
        tier=Tier.ORGANIZE,
    )


PLUGIN_ACTION_ROWS: Mapping[str, tuple[ActionRow, ...]] = {
    "shop_product": (
        _open("Open on the Site", "The product's page, in your browser. Enter."),
        _a("read", "Read in Full", "Move to the details pane to read it."),
        _a(
            "edit_product",
            "Edit Product...",
            "Change its price, sale price, stock, status and categories, after a preview.",
            tier=Tier.WRITE,
        ),
        _a("show_variations", "Show Its Variations", "Each variation's options, price and stock."),
        _a(
            "duplicate_product",
            "Duplicate...",
            "WooCommerce makes a draft copy, after a preview.",
            tier=Tier.WRITE,
        ),
        _a(
            "new_product",
            "New Product...",
            "A draft product, after a preview. Ctrl+N.",
            tier=Tier.WRITE,
        ),
        _a("copy_link", "Copy Link", "The product's address. Ctrl+Shift+C."),
        _trash("product"),
        _SHEET,
    ),
    "shop_order": (
        _open(
            "Open in the Shop's Dashboard",
            "The order in WooCommerce's own screen. Enter.",
        ),
        _a("read", "Read in Full", "The order as a receipt, in the details pane."),
        _a(
            "change_order_status",
            "Change Status...",
            "Processing, completed, on hold and the rest, after a preview of the email it sends.",
            tier=Tier.WRITE,
        ),
        _a(
            "order_notes",
            "Notes...",
            "Read the order's notes, and add a private one or one emailed to the customer.",
        ),
        _a(
            "refund_order",
            "Refund...",
            "Money moves: a refund of an amount you give, previewed with a money warning, sent "
            "only after you type the amount. One order at a time, never in a batch.",
            tier=Tier.DESTRUCTIVE,
        ),
        _SHEET,
    ),
    "shop_customer": (_READ, _SHEET),
    "shop_coupon": (
        _READ,
        _a("edit_coupon", "Edit Coupon...", "Change it, after a preview.", tier=Tier.WRITE),
        _a("new_coupon", "New Coupon...", "Make one, after a preview. Ctrl+N.", tier=Tier.WRITE),
        _trash("coupon"),
        _SHEET,
    ),
    "shop_report": (_READ, _SHEET),
    "shop_setting": (
        _READ,
        _a(
            "change_shop_setting",
            "Change Setting...",
            "Choose or type its new value; the old and new are previewed first.",
            tier=Tier.WRITE,
        ),
        _SHEET,
    ),
    "tribe_event": (
        _open("Open on the Site", "The event's page, in your browser. Enter."),
        _a("read", "Read in Full", "Move to the details pane to read it."),
        _a(
            "edit_event",
            "Edit Event...",
            "Its title, start, end, time zone, venue and cost, after a preview.",
            tier=Tier.WRITE,
        ),
        _a("new_event", "New Event...", "A draft event, after a preview. Ctrl+N.", tier=Tier.WRITE),
        _a("events_between", "Events Between Dates...", "Every event from one date to another."),
        _a("copy_link", "Copy Link", "The event's address. Ctrl+Shift+C."),
        _trash("event"),
        _SHEET,
    ),
    "tribe_venue": (
        _READ,
        _a("edit_venue", "Edit Venue...", "Its name, address and phone.", tier=Tier.WRITE),
        _a("new_venue", "New Venue...", "A venue, after a preview. Ctrl+N.", tier=Tier.WRITE),
        _trash("venue"),
        _SHEET,
    ),
    "tribe_organizer": (
        _READ,
        _a(
            "edit_organizer",
            "Edit Organizer...",
            "Its name, phone, website and email.",
            tier=Tier.WRITE,
        ),
        _a("new_organizer", "New Organizer...", "An organizer. Ctrl+N.", tier=Tier.WRITE),
        _trash("organizer"),
        _SHEET,
    ),
    "seo_item": (
        _a(
            "search_appearance",
            "Search Appearance",
            "The title, address and description a search engine shows, with where each is "
            "cut off. Enter.",
            default=True,
        ),
        _a(
            "edit_seo",
            "Edit SEO...",
            "The SEO title, meta description, focus keyphrase and indexing, after a preview.",
            tier=Tier.WRITE,
        ),
        _a("open_on_site", "Open on the Site", "In your browser. Shift+Enter."),
        _SHEET,
    ),
    "seo_score": (
        _open("Open in Dashboard", "Yoast's own screen for this, in your browser. Enter."),
        _a("read", "Read in Full", "Move to the details pane to read it."),
        _SHEET,
    ),
}
"""The rows for each kind these packages add; shop_product and shop_order replace the old."""

PLUGIN_ACTION_ROWS = {  # reviews, shipping, taxes, webhooks, brands, event terms, bulk SEO
    **{k: (*v[:-1], *MORE_EXTRA.get(k, ()), v[-1]) for k, v in PLUGIN_ACTION_ROWS.items()},
    **MORE_ROWS,
}

QAF_FORM_ROWS: tuple[ActionRow, ...] = (
    _a(
        "change_form_status",
        "Change Form Status...",
        "Draft, open or closed, after a preview. QUILL Accessible Forms only.",
        tier=Tier.WRITE,
    ),
    _a(
        "form_settings",
        "Form Settings...",
        "Read the form's settings and change one, after a preview.",
        tier=Tier.WRITE,
    ),
    _a("show_views", "Saved Views", "The site's saved views of its responses."),
    _a("search_responses", "Search Responses on the Site...", "Words across every answer."),
    _a(
        "delete_form",
        "Delete Form...",
        "Gone for good with its responses, after a preview and typing its name.",
        tier=Tier.DESTRUCTIVE,
    ),
)
"""Spliced into the ``form`` row type (a QAF form; Gravity Forms has its own rows)."""

PLUGIN_NEW_HERE: dict[str, str] = {
    "shop": "do_new_product",
    "shop_drafts": "do_new_product",
    "shop_on_sale": "do_new_product",
    "shop_out_of_stock": "do_new_product",
    "shop_coupons": "do_new_coupon",
    "events": "do_new_event",
    "events_past": "do_new_event",
    "events_venues": "do_new_venue",
    "events_organizers": "do_new_organizer",
}
"""The node key -> the handler Ctrl+N (New Here) runs there."""
PLUGIN_NEW_HERE.update(MORE_NEW_HERE)

PLUGIN_TRASH: dict[str, str] = {
    "shop_product": "do_trash_product",
    "shop_coupon": "do_trash_coupon",
    "tribe_event": "do_trash_event",
    "tribe_venue": "do_trash_venue",
    "tribe_organizer": "do_trash_organizer",
}
"""The row kind -> the handler Delete (Move to Trash) runs on it."""
PLUGIN_TRASH.update(MORE_TRASH)

_NEW = "Ctrl+N (New Here) on its node runs it; the context menu has it too."
_TRASH = "Delete (Move to Trash) on its row runs it, after a preview."

KEYLESS: dict[str, str] = {
    command("edit_product"): "Prices and stock change now and then, behind a preview (rule 9).",
    command("show_variations"): "Read when a variable product is in question (rule 9).",
    command("duplicate_product"): "A copy is made when a new product is like an old one (rule 9).",
    command("new_product"): _NEW,
    command("trash_product"): _TRASH,
    command("change_order_status"): "Each status change can email a customer: never a bare key.",
    command("order_notes"): "Read when an order is in question, a few times a week (rule 9).",
    command("refund_order"): "A refund moves money: tier 3, never a bare key, never batched.",
    command("edit_coupon"): "Coupons change for a sale or an event, rarely (rule 9).",
    command("new_coupon"): _NEW,
    command("trash_coupon"): _TRASH,
    command("change_shop_setting"): "Store settings change a few times a year (rule 9).",
    command("edit_event"): "An event's details change now and then, behind a preview (rule 9).",
    command("new_event"): _NEW,
    command("events_between"): "Asked when planning, now and then (rule 9).",
    command("trash_event"): _TRASH,
    command("edit_venue"): "A venue's address changes rarely (rule 9).",
    command("new_venue"): _NEW,
    command("trash_venue"): _TRASH,
    command("edit_organizer"): "An organizer's details change rarely (rule 9).",
    command("new_organizer"): _NEW,
    command("trash_organizer"): _TRASH,
    command("search_appearance"): "Enter runs it on an SEO row, its default.",
    command("edit_seo"): "SEO fields are set once per post, behind a preview (rule 9).",
    command("change_form_status"): "A form opens or closes a few times a year (rule 9).",
    command("form_settings"): "A form's settings are set when it is made (rule 9).",
    command("show_views"): "Saved views are read now and then (rule 9).",
    command("search_responses"): "The filter box finds within loaded rows; this asks the site.",
    command("delete_form"): "Deleting a form deletes its responses: never a bare key (rule 4).",
}
"""Why each command here has no chord of its own (family rule 8)."""
KEYLESS.update(MORE_KEYLESS)
