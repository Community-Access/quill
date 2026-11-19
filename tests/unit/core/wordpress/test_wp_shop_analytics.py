"""complete.md 2.3 (Shop): WooCommerce Analytics, read only, wx-free, over recorded answers.

The answers are in the shapes ``wc-analytics/reports/*`` gives (``totals`` and
``intervals`` from a ``/stats`` route, a list of rows with ``extended_info`` from the
others). The previous period is told apart by the ``after`` it is asked with. No site
is reached: live testing is deferred.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.wordpress import workbench_shop_analytics as wsa
from quill.core.wordpress.api import WordPressApiError
from quill.core.wordpress.workbench_coverage import classify
from quill.core.wordpress.workbench_node_help import node_help, row_help
from quill.core.wordpress.workbench_plugin_actions import KEYLESS, PLUGIN_ACTION_ROWS
from quill.core.wordpress.workbench_plugin_branches import shows
from quill.core.wordpress.workbench_shop import SHOP_NODES, load_shop
from quill.core.wordpress.workbench_shop_analytics_period import (
    Money,
    Period,
    compared,
    previous,
    read_money,
)
from quill.core.wordpress.workbench_shop_analytics_places import REPORTS
from quill.core.wordpress.workbench_tree import WORDPRESS_TREE

SITE = "Radio"
TODAY = date(2026, 11, 19)
NOW = "2026-11-13T00:00:00"  # Last 7 Days from 19 November 2026
BEFORE = "2026-11-06T00:00:00"  # the 7 days before
SETTINGS = [
    {"id": "woocommerce_currency", "value": "USD"},
    {"id": "woocommerce_currency_pos", "value": "left"},
    {"id": "woocommerce_price_thousand_sep", "value": ","},
    {"id": "woocommerce_price_decimal_sep", "value": "."},
    {"id": "woocommerce_price_num_decimals", "value": "2"},
]
CURRENCY = {"code": "USD", "name": "United States (US) dollar", "symbol": "&#36;"}


def _day(day: str, **subtotals: Any) -> dict[str, Any]:
    return {
        "interval": day,
        "date_start": f"{day} 00:00:00",
        "date_end": f"{day} 23:59:59",
        "subtotals": subtotals,
    }


REVENUE_NOW = {
    "totals": {
        "orders_count": 31,
        "gross_sales": 1300,
        "total_sales": 1240,
        "refunds": 20,
        "coupons": 40,
        "taxes": 60,
        "shipping": 30,
        "net_revenue": 1150,
    },
    "intervals": [
        _day("2026-11-18", orders_count=3, total_sales=120, net_revenue=100),
        _day("2026-11-19", orders_count=0, total_sales=0, net_revenue=0),
    ],
}
REVENUE_BEFORE = {"totals": {"orders_count": 28, "total_sales": 1107.14}, "intervals": []}


class Api:
    """Answers by route, and by the period asked for (``after``)."""

    def __init__(self, answers: dict[str, Any]) -> None:
        self.answers = answers
        self.asked: list[tuple[str, dict[str, Any]]] = []

    def get(self, route: str, **params: Any) -> Any:
        self.asked.append((route, params))
        when = "before" if params.get("after") == BEFORE else "now"
        found = self.answers.get(f"{route} {when}", self.answers.get(route, []))
        if isinstance(found, Exception):
            raise found
        return found

    def iter_collection(self, route: str, params: Any = None, **_k: Any):
        found = self.get(route, **dict(params or {}))
        yield from found if isinstance(found, list) else []


def _ctx(api: Api, *namespaces: str) -> Any:
    info = SimpleNamespace(namespaces=namespaces or ("wc/v3", "wc-analytics"), routes=())
    return SimpleNamespace(api=api, name=SITE, info=info, url="https://radio.example")


def _api(**reports: Any) -> Api:
    answers = {
        "wc/v3/settings/general": SETTINGS,
        "wc/v3/data/currencies/current": CURRENCY,
        **{f"wc-analytics/reports/{k.replace('__', '/')}": v for k, v in reports.items()},
    }
    return Api(answers)


@pytest.fixture(autouse=True)
def _today(monkeypatch) -> None:
    monkeypatch.setattr(wsa, "today", lambda: TODAY)


def _load(api: Api, key: str, **query: str) -> list[Any]:
    return load_shop(_ctx(api), "shop", f"analytics_{key}", query)


# -- where it lives ---------------------------------------------------------------------


def test_shop_analytics_is_a_site_node_beside_shop_with_a_node_per_report() -> None:
    keys = [n.key for n in SHOP_NODES]
    assert keys.index("shop_analytics") == keys.index("shop_orders") + 1
    parent = next(n for n in SHOP_NODES if n.key == "shop_analytics")
    assert (parent.label, parent.parent, parent.loader) == ("Shop Analytics", "site", "")
    children = [n for n in SHOP_NODES if n.parent == "shop_analytics"]
    assert [n.label for n in children] == [
        "Revenue", "Orders", "Products", "Categories", "Coupons", "Taxes", "Downloads",
        "Stock", "Customers",
    ]  # fmt: skip
    assert {n.loader for n in children} == {f"shop:analytics_{r.key}" for r in REPORTS}
    assert {n.row_type for n in children} == {"shop_analytics"}
    for node in (parent, *children):
        assert node_help(node.key), node.key
    assert WORDPRESS_TREE.depth("sites") == 4  # Sites > site > Shop Analytics > Revenue
    assert row_help("shop_analytics").startswith("One row of a WooCommerce Analytics report")


def test_it_shows_only_where_the_index_lists_wc_analytics() -> None:
    assert shows("shop_analytics", ["wp/v2", "wc/v3", "wc-analytics"])
    assert not shows("shop_analytics", ["wp/v2", "wc/v3"])
    assert shows("shop_analytics", None)  # not read yet: nothing hidden on a guess


def test_the_rows_only_read_and_their_commands_say_why_they_have_no_key() -> None:
    rows = PLUGIN_ACTION_ROWS["shop_analytics"]
    assert [r.label for r in rows] == ["Read in Full", "Date Range...", "Interval...",
                                       "Properties..."]  # fmt: skip
    assert all(r.tier == 0 for r in rows)
    for verb in ("analytics_range", "analytics_interval"):
        assert KEYLESS[f"wordpress.workbench.{verb}"]


def test_the_routes_used_are_covered_and_the_rest_stay_planned() -> None:
    for route in (
        "/wc-analytics/reports/revenue/stats",
        "/wc-analytics/reports/orders/stats",
        "/wc-analytics/reports/products",
        "/wc-analytics/reports/products/stats",
        "/wc-analytics/reports/categories",
        "/wc-analytics/reports/coupons/stats",
        "/wc-analytics/reports/taxes",
        "/wc-analytics/reports/downloads/stats",
        "/wc-analytics/reports/stock/stats",
        "/wc-analytics/reports/customers",
    ):
        assert classify(route).status == "covered", route
    assert classify("/wc-analytics/reports/orders").status == "planned"
    assert classify("/wc-analytics/admin/notes").status == "planned"


# -- the period --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("chosen", "first", "last", "words"),
    [
        ("today", date(2026, 11, 19), date(2026, 11, 19), "today"),
        ("yesterday", date(2026, 11, 18), date(2026, 11, 18), "yesterday"),
        ("last_7_days", date(2026, 11, 13), date(2026, 11, 19), "last 7 days"),
        ("last_30_days", date(2026, 10, 21), date(2026, 11, 19), "last 30 days"),
        ("month_to_date", date(2026, 11, 1), date(2026, 11, 19), "month to date"),
        ("last_month", date(2026, 10, 1), date(2026, 10, 31), "last month"),
        ("this_year", date(2026, 1, 1), date(2026, 11, 19), "this year"),
        ("last_year", date(2025, 1, 1), date(2025, 12, 31), "last year"),
    ],
)
def test_each_range_covers_its_days(chosen: str, first: date, last: date, words: str) -> None:
    period = Period(chosen)
    assert period.dates(TODAY) == (first, last)
    assert period.words(TODAY) == words


def test_a_custom_range_travels_as_strings_and_comes_back_whole() -> None:
    period = Period("custom", "week", date(2026, 11, 1), date(2026, 11, 15))
    params = period.as_params()
    assert params == {"range": "custom", "interval": "week", "start": "2026-11-01",
                      "end": "2026-11-15"}  # fmt: skip
    assert Period.from_params(params) == period
    assert period.words(TODAY) == "1 November 2026 to 15 November 2026"
    assert Period.from_params({"range": "custom", "start": "nonsense"}) == Period()
    assert Period.from_params({"range": "fortnight", "interval": "hour"}) == Period()


def test_the_previous_period_is_the_same_number_of_days_just_before() -> None:
    assert previous(date(2026, 11, 13), date(2026, 11, 19)) == (
        date(2026, 11, 6),
        date(2026, 11, 12),
    )
    week = (date(2026, 11, 13), date(2026, 11, 19))
    assert compared(1240, 1107.14, *week) == ", up 12% on the 7 days before"
    assert compared(90, 100, *week) == ", down 10% on the 7 days before"
    assert compared(5, 5, *week) == ", the same as the 7 days before"
    assert compared(5, 0, *week) == ", against none in the 7 days before"
    assert compared(0, 0, *week) == ", and none in the 7 days before either"
    one = (date(2026, 11, 19), date(2026, 11, 19))
    assert compared(2, 1, *one) == ", up 100% on the day before"


def test_money_is_said_the_way_the_store_writes_it() -> None:
    dollars = read_money(_api())
    assert dollars == Money("$", "USD", "left", ",", ".", 2)
    assert dollars.say(1240) == "$1,240.00"
    assert dollars.say(1240, short=True) == "$1,240"
    assert dollars.say("12.5", short=True) == "$12.50"
    assert dollars.say(-20) == "-$20.00"
    euros = Money("€", "EUR", "right_space", ".", ",", 2)
    assert euros.say(1234.5) == "1.234,50 €"
    plain = Money(code="USD")
    assert plain.say(3) == "3.00 USD"


def test_money_falls_back_when_the_settings_cannot_be_read() -> None:
    api = Api({"wc/v3/settings/general": WordPressApiError("no", status=403)})
    api.answers["wc/v3/data/currencies/current"] = WordPressApiError("no", status=403)
    assert read_money(api).say(5) == "5.00"


# -- the reports -------------------------------------------------------------------------


def test_revenue_lists_the_total_then_each_day_and_says_its_sentence() -> None:
    api = _api(revenue__stats=REVENUE_NOW)
    api.answers["wc-analytics/reports/revenue/stats before"] = REVENUE_BEFORE
    rows = _load(api, "revenue")
    total = rows[0]
    assert total.kind == "shop_analytics" and total.status == "total"
    assert total.raw["summary"] == (
        "Revenue on Radio, last 7 days: $1,240 from 31 orders, up 12% on the 7 days before."
    )
    assert wsa.summary_of(rows) == total.raw["summary"]
    assert total.cells == {
        "when": "Total, last 7 days",
        "orders": "31",
        "gross": "$1,300.00",
        "returns": "$20.00",
        "coupons": "$40.00",
        "net": "$1,150.00",
        "taxes": "$60.00",
        "shipping": "$30.00",
        "total": "$1,240.00",
    }
    assert [r.cell("when") for r in rows[1:]] == [
        "Wednesday 18 November 2026",
        "Thursday 19 November 2026",
    ]
    assert rows[1].detail.startswith("Wednesday 18 November 2026: orders 3, gross $0.00")
    route, params = api.asked[2]
    assert route == "wc-analytics/reports/revenue/stats"
    assert params["after"] == NOW and params["before"] == "2026-11-19T23:59:59"
    assert params["interval"] == "day" and params["per_page"] == 100


def test_the_interval_and_range_reach_the_route_and_label_the_rows() -> None:
    month = {"totals": {"orders_count": 4}, "intervals": [_day("2026-10-01", orders_count=4)]}
    api = _api(orders__stats=month)
    rows = _load(api, "orders", range="last_month", interval="month")
    asked = [p for r, p in api.asked if r.endswith("orders/stats")]
    assert asked[0]["after"] == "2026-10-01T00:00:00"
    assert asked[0]["before"] == "2026-10-31T23:59:59"
    assert asked[0]["interval"] == "month"
    assert asked[1]["after"] == "2026-08-31T00:00:00"  # the 31 days before
    assert rows[1].cell("when") == "October 2026"
    assert rows[0].raw["summary"].startswith("Orders on Radio, last month: 4 orders, $0 net")
    two = {"totals": {"download_count": 2}, "intervals": [_day("2026-11-16", download_count=2)]}
    weeks = _api(downloads__stats=two)
    weeks.answers["wc-analytics/reports/downloads/stats before"] = {"totals": {}}
    rows = _load(weeks, "downloads", interval="week")
    assert rows[1].cell("when") == "Week of 16 November 2026"
    assert rows[0].raw["summary"] == (
        "Downloads on Radio, last 7 days: 2 downloads, against none in the 7 days before."
    )


def test_intervals_are_read_page_after_page() -> None:
    page = {"totals": {"orders_count": 1}, "intervals": [_day("2026-01-01")] * 100}
    api = _api(orders__stats=page)
    api.answers["wc-analytics/reports/orders/stats before"] = {"totals": {}, "intervals": []}
    rows = _load(api, "orders", range="this_year")
    pages = [p["page"] for r, p in api.asked if r.endswith("orders/stats") and p["per_page"] == 100]
    assert pages == list(range(1, 9)) and len(rows) == 801


def test_products_lists_best_sellers_with_the_total_from_stats() -> None:
    api = _api(
        products=[
            {"product_id": 9, "items_sold": 12, "net_revenue": 144, "orders_count": 10,
             "extended_info": {"name": "Mug"}},
            {"product_id": 11, "items_sold": 2, "net_revenue": 30, "orders_count": 2},
        ],
        products__stats={"totals": {"items_sold": 14, "net_revenue": 174, "orders_count": 11,
                                    "products_count": 2}},
    )  # fmt: skip
    api.answers["wc-analytics/reports/products/stats before"] = {"totals": {"net_revenue": 200}}
    rows = _load(api, "products")
    assert [r.cell("product") for r in rows] == ["Total, last 7 days", "Mug", "Product 11"]
    assert rows[1].cells == {"product": "Mug", "sold": "12", "net": "$144.00", "orders": "10"}
    assert rows[0].raw["summary"] == (
        "Products on Radio, last 7 days: 14 items sold across 2 products, $174 net, down 13% "
        "on the 7 days before."
    )
    listed = next(p for r, p in api.asked if r == "wc-analytics/reports/products")
    assert listed["extended_info"] == "true" and listed["orderby"] == "items_sold"


def test_categories_add_their_rows_up_for_the_total_and_the_comparison() -> None:
    gifts = {"category_id": 3, "items_sold": 4, "net_revenue": 40, "products_count": 2,
             "orders_count": 3, "extended_info": {"name": "Gifts"}}  # fmt: skip
    api = _api(categories=[gifts, {**gifts, "category_id": 4, "extended_info": {"name": "Mugs"}}])
    api.answers["wc-analytics/reports/categories before"] = [gifts]
    rows = _load(api, "categories")
    assert rows[0].cells == {"category": "Total, last 7 days", "sold": "8", "net": "$80.00"}
    assert rows[0].raw["summary"] == (
        "Categories on Radio, last 7 days: $80 net from 8 items in 2 categories, up 100% on "
        "the 7 days before."
    )


def test_coupons_and_taxes_say_their_totals() -> None:
    api = _api(
        coupons=[{"coupon_id": 5, "amount": 12.5, "orders_count": 3,
                  "extended_info": {"code": "radio10"}}],
        coupons__stats={"totals": {"amount": 12.5, "orders_count": 3, "coupons_count": 1}},
        taxes=[{"tax_rate_id": 1, "name": "State", "tax_code": "US-AZ-STATE-1", "tax_rate": 5.6,
                "country": "US", "state": "AZ", "total_tax": 6, "order_tax": 5,
                "shipping_tax": 1, "orders_count": 4}],
        taxes__stats={"totals": {"total_tax": 6, "order_tax": 5, "shipping_tax": 1,
                                 "orders_count": 4}},
    )  # fmt: skip
    api.answers["wc-analytics/reports/coupons/stats before"] = {"totals": {"amount": 0}}
    coupons = _load(api, "coupons")
    assert coupons[1].cells == {"coupon": "radio10", "orders": "3", "discount": "$12.50"}
    assert coupons[0].raw["summary"] == (
        "Coupons on Radio, last 7 days: $12.50 off across 3 orders, using 1 coupon, against "
        "none in the 7 days before."
    )
    taxes = _load(api, "taxes")
    assert taxes[1].cell("tax") == "State (US AZ)" and taxes[1].cell("rate") == "5.6%"
    said = taxes[0].raw["summary"]
    assert said.startswith("Taxes on Radio, last 7 days: $6 collected, $5 on orders and $1 on ")
    assert "shipping, from 4 orders" in said


def test_stock_is_as_it_is_now_out_of_stock_first() -> None:
    api = _api(
        stock=[
            {"id": 1, "name": "Cap", "sku": "CAP", "stock_status": "instock", "stock_quantity": 9},
            {"id": 2, "name": "Mug", "sku": "", "stock_status": "outofstock",
             "stock_quantity": 0},
            {"id": 3, "name": "Pin", "stock_status": "onbackorder", "stock_quantity": None},
        ],
        stock__stats={"totals": {"products": 3, "lowstock": 1, "instock": 1, "outofstock": 1,
                                 "onbackorder": 1}},
    )  # fmt: skip
    rows = _load(api, "stock", range="last_year")
    assert [r.cell("product") for r in rows] == ["Total, now", "Mug", "Pin", "Cap"]
    assert rows[2].cells["status"] == "on backorder" and rows[2].cells["stock"] == "not counted"
    assert rows[0].raw["summary"] == (
        "Stock on Radio, now: 3 products, 1 out of stock, 1 on backorder, 1 low in stock and "
        "1 in stock."
    )
    assert all("after" not in p for _r, p in api.asked)


def test_customers_keep_their_email_and_address_out_of_the_rows() -> None:
    api = _api(
        customers=[{"id": 4, "name": "Ann Lee", "username": "ann", "email": "ann@example.com",
                    "city": "Tucson", "orders_count": 3, "total_spend": 90,
                    "avg_order_value": 30, "date_last_active": "2026-11-02 10:00:00"}],
        customers__stats={"totals": {"customers_count": 1, "avg_orders_count": 3,
                                     "avg_total_spend": 90, "avg_avg_order_value": 30}},
    )  # fmt: skip
    rows = _load(api, "customers")
    ann = rows[1]
    assert ann.cells == {"name": "Ann Lee", "username": "ann", "orders": "3", "spent": "$90.00",
                         "average": "$30.00", "last_active": "2 November 2026"}  # fmt: skip
    assert "ann@example.com" not in str(ann.raw) and "Tucson" not in ann.detail
    assert rows[0].raw["summary"] == (
        "Customers on Radio: 1 customer, averaging 3.0 orders and $90 spent each."
    )


def test_an_empty_range_still_says_its_total() -> None:
    rows = _load(_api(revenue__stats={"totals": {}, "intervals": []}), "revenue", range="today")
    assert len(rows) == 1
    assert rows[0].raw["summary"] == (
        "Revenue on Radio, today: $0 from 0 orders, and none in the day before either."
    )


# -- refusals ------------------------------------------------------------------------------


def test_a_site_without_wc_analytics_is_told_how_to_turn_it_on() -> None:
    with pytest.raises(WordPressApiError, match="Advanced > Features"):
        load_shop(_ctx(_api(), "wc/v3"), "shop", "analytics_revenue", {})


def test_a_role_that_cannot_view_reports_is_told_which_capability() -> None:
    api = _api(revenue__stats=WordPressApiError("Sorry", status=403))
    with pytest.raises(WordPressApiError, match="view_woocommerce_reports"):
        _load(api, "revenue")
    gone = _api(products=WordPressApiError("No route", status=404))
    with pytest.raises(WordPressApiError, match="does not answer WooCommerce Analytics"):
        _load(gone, "products")


def test_nothing_is_ever_sent_to_the_site() -> None:
    api = _api(revenue__stats=REVENUE_NOW)
    _load(api, "revenue")
    assert not hasattr(api, "post") and not hasattr(api, "delete")
