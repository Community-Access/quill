"""WooCommerce Analytics in the Workbench, read only (complete.md 2.3, Shop).

Each report under Sites > site > Shop Analytics is read from WooCommerce's
own ``wc-analytics/reports`` routes, the ones WooCommerce > Analytics draws
its charts from. Its list is the whole range's total first, then one row per
day, week or month (Revenue, Orders and Downloads, from ``/stats``) or one
row per thing (a product, a category, a coupon, a tax rate, a customer). The
total row carries the report's sentence (``raw["summary"]``), which the
window says once when you arrive: "Revenue on Radio, last 7 days: $1,240
from 31 orders, up 12% on the 7 days before." The comparison is the same
route asked again for the same number of days just before.

Money is said the way the store writes it
(:func:`~quill.core.wordpress.workbench_shop_analytics_period.read_money`).
A customer's email and address stay out of the rows, as they do for shop
orders. Analytics reads its own copy of the orders, which WooCommerce imports,
at once or on a schedule; while some are not imported yet
(``import/totals?skip_existing=true``) the total row's sentence says so,
because the figures would otherwise read as complete. Nothing here writes to
the site. Wx-free.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date
from typing import Any

from quill.core.counted import plural
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_listing import column_title, pages_for
from quill.core.wordpress.workbench_rows import WbRow
from quill.core.wordpress.workbench_shop_analytics_period import (
    Money,
    Period,
    compared,
    number,
    parse_day,
    previous,
    read_money,
)
from quill.core.wordpress.workbench_shop_analytics_places import (
    ANALYTICS_NAMESPACE,
    ROW_KIND,
    Report,
    report_for,
)

__all__ = [
    "BASE",
    "IMPORT_TOTALS",
    "has_analytics",
    "load_analytics",
    "no_analytics_words",
    "summary_of",
    "today",
    "unimported_words",
]

BASE = f"{ANALYTICS_NAMESPACE}/reports"
_PER_PAGE = 100
_INTERVAL_PAGES = 8
"""Up to 800 intervals: a custom range of two years, by day."""

_STOCK_ORDER = {"outofstock": 0, "onbackorder": 1, "instock": 2}
_STOCK_WORDS = {
    "outofstock": "out of stock",
    "onbackorder": "on backorder",
    "instock": "in stock",
}


def today() -> date:
    """Today on this computer; the tests replace it."""
    return date.today()


def has_analytics(ctx: Any) -> bool:
    info = getattr(ctx, "info", None)
    return ANALYTICS_NAMESPACE in tuple(getattr(info, "namespaces", ()) or ())


def no_analytics_words(site: str) -> str:
    return (
        f"{site} does not list WooCommerce Analytics' {ANALYTICS_NAMESPACE} routes in its REST "
        "index, so it has no analytics QUILL can read. WooCommerce turns Analytics on in "
        "WooCommerce > Settings > Advanced > Features. Shop > Shop Reports reads the older "
        "reports."
    )


@dataclass(frozen=True)
class _Ask:
    """One report's reading: the site, its money, the chosen period and the days it covers."""

    api: Any
    site: str
    money: Money
    period: Period
    start: date
    end: date

    @property
    def words(self) -> str:
        return self.period.words(today())

    def dates(self, start: date, end: date) -> dict[str, object]:
        return {"after": f"{start.isoformat()}T00:00:00", "before": f"{end.isoformat()}T23:59:59"}

    def get(self, route: str, **params: object) -> Any:
        try:
            return self.api.get(f"{BASE}/{route}", **params)
        except WordPressApiError as exc:
            raise _refusal(exc, self.site, route) from exc

    def stats(self, name: str, *, before: bool = False) -> tuple[Mapping[str, Any], list[Any]]:
        """``name/stats``'s totals and, for this period, every interval (paged)."""
        start, end = previous(self.start, self.end) if before else (self.start, self.end)
        params = {**self.dates(start, end), "interval": self.period.interval}
        totals: Mapping[str, Any] = {}
        intervals: list[Any] = []
        for page in range(1, (1 if before else _INTERVAL_PAGES) + 1):
            per_page = 1 if before else _PER_PAGE
            found = self.get(f"{name}/stats", **params, page=page, per_page=per_page)
            if not isinstance(found, Mapping):
                break
            got = found.get("totals")
            totals = got if isinstance(got, Mapping) else totals
            these = [i for i in found.get("intervals") or [] if isinstance(i, Mapping)]
            intervals += these
            if len(these) < per_page:
                break
        return totals, intervals

    def now_totals(self, name: str) -> Mapping[str, Any]:
        """``name/stats``'s totals with no dates: Stock and Customers say how things are now."""
        found = self.get(f"{name}/stats")
        totals = found.get("totals") if isinstance(found, Mapping) else None
        return totals if isinstance(totals, Mapping) else {}

    def items(
        self,
        name: str,
        params: Mapping[str, object],
        *,
        before: bool = False,
        dated: bool = True,
    ) -> list[dict[str, Any]]:
        """The ``name`` list for this period (or the one before), every page up to the cap."""
        start, end = previous(self.start, self.end) if before else (self.start, self.end)
        wanted = {**(self.dates(start, end) if dated else {}), **params}
        try:
            found = self.api.iter_collection(
                f"{BASE}/{name}", wanted, per_page=_PER_PAGE, max_pages=pages_for(3)
            )
            return [r for r in found if isinstance(r, dict)]
        except WordPressApiError as exc:
            raise _refusal(exc, self.site, name) from exc


def _refusal(exc: WordPressApiError, site: str, route: str) -> WordPressApiError:
    if exc.status in (401, 403):
        return WordPressApiError(
            f"{site} lets only people who can view WooCommerce's reports read Analytics, and "
            "your role there cannot. WooCommerce asks for the view_woocommerce_reports "
            "capability.",
            status=exc.status,
        )
    if exc.status == 404:
        return WordPressApiError(
            f"{site} does not answer WooCommerce Analytics' {route} report. WooCommerce "
            "turns Analytics on in WooCommerce > Settings > Advanced > Features.",
            status=exc.status,
        )
    return exc


# -- rows ----------------------------------------------------------------------------


def _row(ask: _Ask, report: Report, key: str, cells: dict[str, str], summary: str = "") -> WbRow:
    said = [f"{column_title(c).lower()} {cells[c]}" for c in report.columns[1:] if cells.get(c)]
    first = cells.get(report.columns[0], "")
    detail = f"{first}: {', '.join(said)}." if said else f"{first}."
    raw: dict[str, Any] = {"report": report.label, **cells}
    if summary:
        raw["summary"] = summary
        detail = f"{summary}\n{detail}"
    return WbRow(
        kind=ROW_KIND,
        site=ask.site,
        key=key,
        cells=cells,
        detail=detail,
        status="total" if summary else "",
        subkind=report.key,
        raw=raw,
    )


def _total_label(ask: _Ask, report: Report) -> str:
    return f"Total, {ask.words}" if report.dated else "Total, now"


def _count(values: Mapping[str, Any], key: str) -> str:
    return f"{int(number(values.get(key))):,}"


def _when(raw: Mapping[str, Any], interval: str) -> str:
    day = parse_day(str(raw.get("date_start") or "")[:10])
    if day is None:
        return str(raw.get("interval", "") or "")
    if interval == "month":
        return day.strftime("%B %Y")
    named = f"{day.day} {day.strftime('%B %Y')}"
    return f"Week of {named}" if interval == "week" else f"{day.strftime('%A')} {named}"


def _by_interval(
    ask: _Ask,
    report: Report,
    cells_of: Callable[[Mapping[str, Any]], dict[str, str]],
    say: Callable[[Mapping[str, Any], Mapping[str, Any]], str],
) -> list[WbRow]:
    totals, intervals = ask.stats(report.key)
    before, _none = ask.stats(report.key, before=True)
    first = report.columns[0]
    rows = [_row(ask, report, "total", {first: _total_label(ask, report), **cells_of(totals)},
                 say(totals, before))]  # fmt: skip
    for raw in intervals:
        sub = raw.get("subtotals")
        cells = {
            first: _when(raw, ask.period.interval),
            **cells_of(sub if isinstance(sub, Mapping) else {}),
        }
        rows.append(_row(ask, report, str(raw.get("interval", len(rows))), cells))
    return rows


def _revenue(ask: _Ask, report: Report) -> list[WbRow]:
    m = ask.money

    def cells(t: Mapping[str, Any]) -> dict[str, str]:
        return {
            "orders": _count(t, "orders_count"),
            "gross": m.say(t.get("gross_sales")),
            "returns": m.say(t.get("refunds")),
            "coupons": m.say(t.get("coupons")),
            "net": m.say(t.get("net_revenue")),
            "taxes": m.say(t.get("taxes")),
            "shipping": m.say(t.get("shipping")),
            "total": m.say(t.get("total_sales")),
        }

    def say(t: Mapping[str, Any], b: Mapping[str, Any]) -> str:
        now = number(t.get("total_sales"))
        orders = int(number(t.get("orders_count")))
        return (
            f"Revenue on {ask.site}, {ask.words}: {m.say(now, short=True)} from "
            f"{plural(orders, 'order')}"
            f"{compared(now, number(b.get('total_sales')), ask.start, ask.end)}."
        )

    return _by_interval(ask, report, cells, say)


def _orders(ask: _Ask, report: Report) -> list[WbRow]:
    m = ask.money

    def cells(t: Mapping[str, Any]) -> dict[str, str]:
        return {
            "orders": _count(t, "orders_count"),
            "net": m.say(t.get("net_revenue")),
            "average": m.say(t.get("avg_order_value")),
            "items": f"{number(t.get('avg_items_per_order')):.1f}",
        }

    def say(t: Mapping[str, Any], b: Mapping[str, Any]) -> str:
        now = number(t.get("orders_count"))
        return (
            f"Orders on {ask.site}, {ask.words}: {plural(int(now), 'order')}, "
            f"{m.say(t.get('net_revenue'), short=True)} net, "
            f"{m.say(t.get('avg_order_value'), short=True)} on average"
            f"{compared(now, number(b.get('orders_count')), ask.start, ask.end)}."
        )

    return _by_interval(ask, report, cells, say)


def _downloads(ask: _Ask, report: Report) -> list[WbRow]:
    def cells(t: Mapping[str, Any]) -> dict[str, str]:
        return {"downloads": _count(t, "download_count")}

    def say(t: Mapping[str, Any], b: Mapping[str, Any]) -> str:
        now = number(t.get("download_count"))
        return (
            f"Downloads on {ask.site}, {ask.words}: {plural(int(now), 'download')}"
            f"{compared(now, number(b.get('download_count')), ask.start, ask.end)}."
        )

    return _by_interval(ask, report, cells, say)


def _name(raw: Mapping[str, Any], key: str, fallback: str) -> str:
    info = raw.get("extended_info")
    found = info.get(key) if isinstance(info, Mapping) else None
    return str(found or fallback)


def _products(ask: _Ask, report: Report) -> list[WbRow]:
    m = ask.money
    found = ask.items(
        "products", {"extended_info": "true", "orderby": "items_sold", "order": "desc"}
    )
    totals, _i = ask.stats("products")
    before, _n = ask.stats("products", before=True)
    net = number(totals.get("net_revenue"))
    sold = int(number(totals.get("items_sold")))
    count = int(number(totals.get("products_count"))) or len(found)
    summary = (
        f"Products on {ask.site}, {ask.words}: {plural(sold, 'item')} sold across "
        f"{plural(count, 'product')}, {m.say(net, short=True)} net"
        f"{compared(net, number(before.get('net_revenue')), ask.start, ask.end)}."
    )

    def cells(r: Mapping[str, Any], label: str) -> dict[str, str]:
        return {
            "product": label,
            "sold": _count(r, "items_sold"),
            "net": m.say(r.get("net_revenue")),
            "orders": _count(r, "orders_count"),
        }

    rows = [_row(ask, report, "total", cells(totals, _total_label(ask, report)), summary)]
    for r in found:
        label = _name(r, "name", f"Product {r.get('product_id', '')}")
        rows.append(_row(ask, report, str(r.get("product_id", "")), cells(r, label)))
    return rows


def _categories(ask: _Ask, report: Report) -> list[WbRow]:
    """No ``categories/stats`` route: the totals are the rows added up."""
    m = ask.money
    params: dict[str, object] = {"extended_info": "true", "orderby": "items_sold", "order": "desc"}
    found = ask.items("categories", params)
    before = ask.items("categories", params, before=True)
    net = sum(number(r.get("net_revenue")) for r in found)
    sold = sum(int(number(r.get("items_sold"))) for r in found)
    summary = (
        f"Categories on {ask.site}, {ask.words}: {m.say(net, short=True)} net from "
        f"{plural(sold, 'item')} in {plural(len(found), 'category', 'categories')}"
        f"{compared(net, sum(number(r.get('net_revenue')) for r in before), ask.start, ask.end)}."
    )
    total = {"category": _total_label(ask, report), "sold": f"{sold:,}", "net": m.say(net)}
    rows = [_row(ask, report, "total", total, summary)]
    for r in found:
        cells = {
            "category": _name(r, "name", f"Category {r.get('category_id', '')}"),
            "sold": _count(r, "items_sold"),
            "net": m.say(r.get("net_revenue")),
            "products": _count(r, "products_count"),
            "orders": _count(r, "orders_count"),
        }
        rows.append(_row(ask, report, str(r.get("category_id", "")), cells))
    return rows


def _coupons(ask: _Ask, report: Report) -> list[WbRow]:
    m = ask.money
    found = ask.items(
        "coupons", {"extended_info": "true", "orderby": "orders_count", "order": "desc"}
    )
    totals, _i = ask.stats("coupons")
    before, _n = ask.stats("coupons", before=True)
    off = number(totals.get("amount"))
    orders = int(number(totals.get("orders_count")))
    used = int(number(totals.get("coupons_count"))) or len(found)
    summary = (
        f"Coupons on {ask.site}, {ask.words}: {m.say(off, short=True)} off across "
        f"{plural(orders, 'order')}, using {plural(used, 'coupon')}"
        f"{compared(off, number(before.get('amount')), ask.start, ask.end)}."
    )
    total = {"coupon": _total_label(ask, report), "orders": f"{orders:,}", "discount": m.say(off)}
    rows = [_row(ask, report, "total", total, summary)]
    for r in found:
        cells = {
            "coupon": _name(r, "code", f"Coupon {r.get('coupon_id', '')}"),
            "orders": _count(r, "orders_count"),
            "discount": m.say(r.get("amount")),
        }
        rows.append(_row(ask, report, str(r.get("coupon_id", "")), cells))
    return rows


def _taxes(ask: _Ask, report: Report) -> list[WbRow]:
    m = ask.money
    found = ask.items("taxes", {"orderby": "total_tax", "order": "desc"})
    totals, _i = ask.stats("taxes")
    before, _n = ask.stats("taxes", before=True)
    tax = number(totals.get("total_tax"))
    summary = (
        f"Taxes on {ask.site}, {ask.words}: {m.say(tax, short=True)} collected, "
        f"{m.say(totals.get('order_tax'), short=True)} on orders and "
        f"{m.say(totals.get('shipping_tax'), short=True)} on shipping, from "
        f"{plural(int(number(totals.get('orders_count'))), 'order')}"
        f"{compared(tax, number(before.get('total_tax')), ask.start, ask.end)}."
    )

    def cells(r: Mapping[str, Any], label: str, rate: str) -> dict[str, str]:
        return {
            "tax": label,
            "rate": rate,
            "total": m.say(r.get("total_tax")),
            "order_tax": m.say(r.get("order_tax")),
            "shipping_tax": m.say(r.get("shipping_tax")),
            "orders": _count(r, "orders_count"),
        }

    rows = [_row(ask, report, "total", cells(totals, _total_label(ask, report), ""), summary)]
    for r in found:
        where = " ".join(str(r.get(k) or "") for k in ("country", "state")).strip()
        label = str(r.get("name") or r.get("tax_code") or "A tax rate")
        label = f"{label} ({where})" if where else label
        rate = f"{number(r.get('tax_rate')):g}%"
        rows.append(_row(ask, report, str(r.get("tax_rate_id", "")), cells(r, label, rate)))
    return rows


def _stock(ask: _Ask, report: Report) -> list[WbRow]:
    found = ask.items("stock", {"type": "all"}, dated=False)
    totals = ask.now_totals("stock")
    products = int(number(totals.get("products"))) or len(found)
    summary = (
        f"Stock on {ask.site}, now: {plural(products, 'product')}, "
        f"{_count(totals, 'outofstock')} out of stock, {_count(totals, 'onbackorder')} on "
        f"backorder, {_count(totals, 'lowstock')} low in stock and "
        f"{_count(totals, 'instock')} in stock."
    )
    total = {
        "product": _total_label(ask, report),
        "status": f"{_count(totals, 'outofstock')} out of stock",
        "stock": f"{_count(totals, 'lowstock')} low",
    }
    rows = [_row(ask, report, "total", total, summary)]
    ordered = sorted(
        found,
        key=lambda r: (_STOCK_ORDER.get(str(r.get("stock_status")), 3), str(r.get("name", ""))),
    )
    for r in ordered:
        status = str(r.get("stock_status") or "")
        quantity = r.get("stock_quantity")
        cells = {
            "product": str(r.get("name") or f"Product {r.get('id', '')}"),
            "sku": str(r.get("sku") or ""),
            "status": _STOCK_WORDS.get(status, status.replace("_", " ")),
            "stock": "not counted" if quantity is None else f"{int(number(quantity)):,}",
        }
        rows.append(_row(ask, report, str(r.get("id", "")), cells))
    return rows


def _customers(ask: _Ask, report: Report) -> list[WbRow]:
    m = ask.money
    found = ask.items("customers", {"orderby": "total_spend", "order": "desc"}, dated=False)
    totals = ask.now_totals("customers")
    count = int(number(totals.get("customers_count"))) or len(found)
    each = number(totals.get("avg_orders_count"))
    summary = (
        f"Customers on {ask.site}: {plural(count, 'customer')}, averaging {each:.1f} orders "
        f"and {m.say(totals.get('avg_total_spend'), short=True)} spent each."
    )
    total = {
        "name": f"Total, {plural(count, 'customer')}",
        "orders": f"{each:.1f} each",
        "spent": f"{m.say(totals.get('avg_total_spend'))} each",
        "average": m.say(totals.get("avg_avg_order_value")),
    }
    rows = [_row(ask, report, "total", total, summary)]
    for r in found:
        last = parse_day(str(r.get("date_last_active") or "")[:10])
        cells = {
            "name": str(r.get("name") or r.get("username") or "A customer").strip(),
            "username": str(r.get("username") or ""),
            "orders": _count(r, "orders_count"),
            "spent": m.say(r.get("total_spend")),
            "average": m.say(r.get("avg_order_value")),
            "last_active": f"{last.day} {last.strftime('%B %Y')}" if last else "",
        }
        rows.append(_row(ask, report, str(r.get("id", "")), cells))
    return rows


_READERS: Mapping[str, Callable[[_Ask, Report], list[WbRow]]] = {
    "revenue": _revenue,
    "orders": _orders,
    "products": _products,
    "categories": _categories,
    "coupons": _coupons,
    "taxes": _taxes,
    "downloads": _downloads,
    "stock": _stock,
    "customers": _customers,
}


def load_analytics(ctx: Any, what: str, query: Mapping[str, object]) -> list[WbRow]:
    """The rows of the report *what* names (``analytics_revenue``) for the chosen period."""
    report = report_for(what)
    if report is None:
        raise WordPressApiError(f"WooCommerce Analytics has no report called {what}.")
    if not has_analytics(ctx):
        raise WordPressApiError(no_analytics_words(ctx.name))
    period = Period.from_params(query)
    start, end = period.dates(today())
    ask = _Ask(ctx.api, ctx.name, read_money(ctx.api), period, start, end)
    rows = _READERS[report.key](ask, report)
    if report.key not in _NOT_FROM_ORDERS and rows:
        rows[0] = _with_unimported(rows[0], _unimported(ctx.api), ctx.name)
    return rows


_NOT_FROM_ORDERS = frozenset({"stock", "downloads"})
"""Reports that are not built from the order history Analytics imports."""

IMPORT_TOTALS = f"{BASE}/import/totals"


def _unimported(api: Any) -> int:
    """How many orders WooCommerce has not brought into Analytics yet; 0 when it will not say.

    ``import/totals`` with ``skip_existing`` counts only the orders still to import
    (without it, every order). On the test site an order made while Analytics
    imported on a schedule was left out of every report until it was imported.
    """
    try:
        found = api.get(IMPORT_TOTALS, skip_existing="true")
    except WordPressApiError:
        return 0
    try:
        return int(number(found.get("orders"))) if isinstance(found, Mapping) else 0
    except (TypeError, ValueError):
        return 0


def unimported_words(count: int) -> str:
    """The sentence a report's total row gains while orders are waiting to be imported."""
    return (
        f"{plural(count, 'order')} {'is' if count == 1 else 'are'} not in WooCommerce Analytics "
        "yet, so these figures leave "
        f"{'it' if count == 1 else 'them'} out; Import historical data, under WooCommerce > "
        "Settings > Advanced > Analytics, brings them in."
    )


def _with_unimported(row: WbRow, count: int, site: str) -> WbRow:
    if count <= 0 or not row.raw.get("summary"):
        return row
    said = f"{row.raw['summary']} {unimported_words(count)}"
    raw = {**row.raw, "summary": said, "unimported": count}
    detail = row.detail.replace(str(row.raw["summary"]), said, 1)
    return replace(row, detail=detail, raw=raw)


def summary_of(rows: Sequence[object]) -> str:
    """The sentence a report's total row carries, or ""."""
    for row in rows[:1]:
        if isinstance(row, WbRow) and row.kind == ROW_KIND:
            return str(row.raw.get("summary", "") or "")
    return ""
