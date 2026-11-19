"""Where Shop Analytics lives in the Workbench: its nodes, F1 words and commands (complete.md 2.3).

WooCommerce Analytics is its own menu in wp-admin, beside WooCommerce, and so
is **Shop Analytics** here: a site node with one child per report (Revenue,
Orders, Products, Categories, Coupons, Taxes, Downloads, Stock, Customers).
It sits beside Shop rather than under it because the tree is never more than
four levels deep (GitHub PRD 3.3), and Sites > site > Shop > Analytics >
Revenue would be five. Each report's rows are read by
:mod:`quill.core.wordpress.workbench_shop_analytics`; every row is the one
kind :data:`ROW_KIND`, whose context menu is Read in Full, Date Range...,
Interval... and Properties. Nothing here writes to the site.

Spliced in by :mod:`quill.core.wordpress.workbench_shop` (nodes),
:mod:`quill.core.wordpress.workbench_node_help` (F1) and
:mod:`quill.core.wordpress.workbench_plugin_actions` (menus and the written
reason each command has no key, family rule 8). Wx-free and network-free.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from quill.core.workbench.actions import ActionRow, Tier
from quill.core.workbench.tree import NodeSpec

__all__ = [
    "ANALYTICS_ACTION_ROWS",
    "ANALYTICS_KEYLESS",
    "ANALYTICS_NAMESPACE",
    "ANALYTICS_NODES",
    "ANALYTICS_NODE_HELP",
    "ANALYTICS_ROW_HELP",
    "LOADER_PREFIX",
    "REPORTS",
    "ROW_KIND",
    "Report",
    "report_for",
]

ANALYTICS_NAMESPACE = "wc-analytics"
ROW_KIND = "shop_analytics"
LOADER_PREFIX = "shop:analytics_"
"""A report node's loader is this and the report's key (``shop:analytics_revenue``)."""


@dataclass(frozen=True)
class Report:
    """One WooCommerce Analytics report: its rows' columns and how its range applies.

    *by_interval* lists one row per day, week or month from the report's
    ``/stats`` route; otherwise one row per thing (a product, a coupon).
    *dated* is False for Stock and Customers, which say how things are now.
    """

    key: str
    label: str
    columns: tuple[str, ...]
    by_interval: bool = False
    dated: bool = True


REPORTS: tuple[Report, ...] = (
    Report(
        "revenue",
        "Revenue",
        ("when", "orders", "gross", "returns", "coupons", "net", "taxes", "shipping", "total"),
        by_interval=True,
    ),
    Report("orders", "Orders", ("when", "orders", "net", "average", "items"), by_interval=True),
    Report("products", "Products", ("product", "sold", "net", "orders")),
    Report("categories", "Categories", ("category", "sold", "net", "products", "orders")),
    Report("coupons", "Coupons", ("coupon", "orders", "discount")),
    Report("taxes", "Taxes", ("tax", "rate", "total", "order_tax", "shipping_tax", "orders")),
    Report("downloads", "Downloads", ("when", "downloads"), by_interval=True),
    Report("stock", "Stock", ("product", "sku", "status", "stock"), dated=False),
    Report(
        "customers",
        "Customers",
        ("name", "username", "orders", "spent", "average", "last_active"),
        dated=False,
    ),
)
"""The reports, in the order WooCommerce > Analytics lists them."""


def report_for(what: str) -> Report | None:
    """The report a loader's ``what`` (``analytics_revenue``) names, if any."""
    key = what.removeprefix("analytics_")
    return next((r for r in REPORTS if r.key == key), None)


ANALYTICS_NODES: tuple[NodeSpec, ...] = (
    NodeSpec("shop_analytics", "Shop Analytics", "site"),
    *(
        NodeSpec(
            f"shop_analytics_{r.key}",
            r.label,
            "shop_analytics",
            loader=f"{LOADER_PREFIX}{r.key}",
            columns=r.columns,
            row_type=ROW_KIND,
        )
        for r in REPORTS
    ),
)
"""Sites > site > Shop Analytics and its reports; hidden on a site without wc-analytics."""

_RANGE = (
    "Date Range on a report's row chooses the days, from Today to This Year or two dates "
    "of your own, and Interval chooses rows by day, week or month; both are kept for every "
    "report on the site until you change them."
)

ANALYTICS_NODE_HELP: Mapping[str, str] = {
    "shop_analytics": (
        "WooCommerce Analytics, read only: revenue, orders, products, categories, coupons, "
        "taxes, downloads, stock and customers. Each report says its totals once when you "
        "arrive, compared with the same number of days before. " + _RANGE
    ),
    "shop_analytics_revenue": (
        "Revenue by day, week or month: orders, gross sales, returns, coupons, net sales, "
        "taxes, shipping and total sales, with the whole range's total first. " + _RANGE
    ),
    "shop_analytics_orders": (
        "Orders by day, week or month: how many, their net sales, the average order and the "
        "items in each, with the total first. " + _RANGE
    ),
    "shop_analytics_products": (
        "Each product that sold in the range, best seller first: items sold, net sales and "
        "orders, with the total first. Export List (Ctrl+Shift+X) writes it as Excel or CSV."
    ),
    "shop_analytics_categories": (
        "Each product category that sold in the range: items sold, net sales, products and "
        "orders, best first, with the total first."
    ),
    "shop_analytics_coupons": (
        "Each coupon used in the range: how many orders used it and how much it took off, "
        "with the total first."
    ),
    "shop_analytics_taxes": (
        "Each tax rate charged in the range: the rate, the tax on orders and on shipping, and "
        "the orders it was on, with the total first."
    ),
    "shop_analytics_downloads": (
        "Downloads of downloadable products by day, week or month, with the total first."
    ),
    "shop_analytics_stock": (
        "Every product's stock as it is now, out of stock first, then on backorder, then in "
        "stock. The date range does not apply here."
    ),
    "shop_analytics_customers": (
        "Customers, biggest spenders first: orders, total spent, the average order and when "
        "they were last active. Emails and addresses stay out of the list. The date range "
        "does not apply here."
    ),
}
"""One F1 sentence per node above."""

ANALYTICS_ROW_HELP: Mapping[str, str] = {
    ROW_KIND: (
        "One row of a WooCommerce Analytics report, read only; the first row is the total. "
        "Date Range... and Interval... on its context menu change what every report on the "
        "site shows."
    ),
}


def _a(verb: str, label: str, help: str, *, default: bool = False) -> ActionRow:  # noqa: A002
    return ActionRow(f"wordpress.workbench.{verb}", label, Tier.READ, "", help, default)


ANALYTICS_ACTION_ROWS: Mapping[str, tuple[ActionRow, ...]] = {
    ROW_KIND: (
        _a("read", "Read in Full", "Move to the details pane to read it.", default=True),
        _a(
            "analytics_range",
            "Date Range...",
            "Today, Last 7 Days, Month to Date, Last Month, This Year and more, or two dates "
            "of your own. Kept for every report on the site.",
        ),
        _a(
            "analytics_interval",
            "Interval...",
            "One row per day, week or month in Revenue, Orders and Downloads.",
        ),
        _a("sheet", "Properties...", "Everything about it on one sheet. Alt+Enter."),
    ),
}
"""The context menu of every Shop Analytics row: it only reads."""

_ONCE = "Chosen once for a sitting and kept for every report on the site (rule 9)."

ANALYTICS_KEYLESS: dict[str, str] = {
    "wordpress.workbench.analytics_range": _ONCE,
    "wordpress.workbench.analytics_interval": _ONCE,
}
"""Why each command here has no chord of its own (family rule 8)."""
