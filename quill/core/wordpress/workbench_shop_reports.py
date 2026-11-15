"""WooCommerce's customers and reports in the Workbench, read only (Package 9).

**Customers** come from ``wc/v3/customers`` and keep what a list needs: name,
username, when they joined and whether they have paid. Email, telephone and
addresses stay out of the rows, as they do for shop orders.

**Reports** are WooCommerce's own ``wc/v3/reports`` routes, each turned into a
sentence with a small table under it (wordpress.md 9.18: "sentences and a
small table, never a chart only"): sales for the month, top sellers, and the
totals of orders, products, customers, coupons and reviews by kind. Money is
said with the shop's currency code. Wx-free.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.plugin_shop_seo import SHOP_NAMESPACE
from quill.core.wordpress.site import friendly_date
from quill.core.wordpress.workbench_rows import WbRow

__all__ = [
    "REPORT_TOTALS",
    "customer_row",
    "report_rows",
    "sales_row",
    "top_sellers_row",
    "totals_row",
]

REPORT_TOTALS: tuple[tuple[str, str], ...] = (
    ("orders/totals", "Orders by status"),
    ("products/totals", "Products by type"),
    ("customers/totals", "Customers"),
    ("coupons/totals", "Coupons by type"),
    ("reviews/totals", "Reviews by rating"),
)
"""The totals reports the live index lists, in the order they are read."""


def customer_row(raw: Mapping[str, Any], site: str) -> WbRow:
    """One customer, with no email, telephone or address."""
    name = " ".join(str(raw.get(k, "") or "") for k in ("first_name", "last_name")).strip() or str(
        raw.get("username", "") or "A customer"
    )
    username = str(raw.get("username", "") or "")
    joined = str(raw.get("date_created_gmt") or raw.get("date_created") or "")
    paying = "yes" if raw.get("is_paying_customer") else "no"
    since = friendly_date(joined) if joined else "an unknown date"
    paid = "has paid for an order" if paying == "yes" else "has not paid yet"
    return WbRow(
        kind="shop_customer",
        site=site,
        key=str(raw.get("id", "") or ""),
        cells={
            "name": name,
            "username": username,
            "registered": friendly_date(joined) if joined else "",
            "paying": paying,
        },
        detail=(
            f"{name}, a WooCommerce customer since {since}; {paid}. Their email and addresses "
            "are in WooCommerce > Customers."
        ),
        subkind="woocommerce",
        raw={"name": name, "username": username, "joined": joined, "paying": paying},
    )


def _report(key: str, title: str, says: str, table: Sequence[str], site: str) -> WbRow:
    return WbRow(
        kind="shop_report",
        site=site,
        key=key,
        cells={"report": title, "says": says},
        detail=f"{title}: {says}" + ("\n" + "\n".join(table) if table else ""),
        subkind="woocommerce",
        raw={"report": title, "says": says, "table": "\n".join(table)},
    )


def sales_row(answer: Any, currency: str, site: str) -> WbRow:
    """``reports/sales?period=month`` as one sentence and a line per day with orders."""
    data = answer[0] if isinstance(answer, list) and answer else {}
    data = data if isinstance(data, Mapping) else {}

    def money(key: str) -> str:
        return f"{data.get(key, '0') or '0'} {currency}".strip()

    orders = int(data.get("total_orders", 0) or 0)
    items = int(data.get("total_items", 0) or 0)
    says = (
        f"This month, {orders} order{'s' if orders != 1 else ''} and {items} "
        f"item{'s' if items != 1 else ''}: {money('total_sales')} in sales, "
        f"{money('net_sales')} net, {money('total_refunds')} refunded, "
        f"{money('total_discount')} in discounts."
    )
    table = []
    totals = data.get("totals")
    for day, row in totals.items() if isinstance(totals, Mapping) else []:
        if isinstance(row, Mapping) and int(row.get("orders", 0) or 0):
            table.append(
                f"{day}: {row.get('orders')} orders, {row.get('sales', '0')} {currency}".strip()
            )
    return _report("sales", "Sales", says, table, site)


def top_sellers_row(answer: Any, site: str) -> WbRow:
    found = [r for r in answer or [] if isinstance(r, Mapping)] if isinstance(answer, list) else []
    table = [f"{r.get('name', 'A product')}: {r.get('quantity', 0)} sold" for r in found]
    says = "; ".join(table[:3]) if table else "Nothing sold this month."
    return _report("top_sellers", "Top sellers this month", says, table, site)


def totals_row(route: str, title: str, answer: Any, site: str) -> WbRow:
    found = [r for r in answer or [] if isinstance(r, Mapping)] if isinstance(answer, list) else []
    table = [f"{r.get('name') or r.get('slug')}: {r.get('total', 0)}" for r in found]
    nonzero = [line for line, r in zip(table, found, strict=True) if str(r.get("total", 0)) != "0"]
    says = ", ".join(nonzero) if nonzero else "none yet"
    return _report(route.replace("/", "_"), title, says, table, site)


def report_rows(api: Any, site: str) -> list[WbRow]:
    """Every report the shop offers, read now; one that fails says why in its own row."""
    base = f"{SHOP_NAMESPACE}/reports"
    currency = ""
    try:
        current = api.get(f"{SHOP_NAMESPACE}/data/currencies/current")
        currency = str(current.get("code", "") if isinstance(current, Mapping) else "")
    except WordPressApiError:
        pass
    rows: list[WbRow] = []
    readers: list[tuple[str, str, Any]] = [
        (
            "sales",
            "Sales",
            lambda: sales_row(api.get(f"{base}/sales", period="month"), currency, site),
        ),
        (
            "top_sellers",
            "Top sellers this month",
            lambda: top_sellers_row(api.get(f"{base}/top_sellers", period="month"), site),
        ),
        *(
            (route, title, lambda r=route, t=title: totals_row(r, t, api.get(f"{base}/{r}"), site))
            for route, title in REPORT_TOTALS
        ),
    ]
    for key, title, read in readers:
        try:
            rows.append(read())
        except WordPressApiError as exc:
            rows.append(_report(key.replace("/", "_"), title, f"not read: {exc.plain}", (), site))
    return rows
