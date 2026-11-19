"""Shop Analytics in the Workbench window (complete.md 2.3, Shop): range, interval, the sentence.

The real provider and frame over a fake site answering in ``wc-analytics``'s shapes;
the dialogs answer from queues and background work runs inline. No site is reached and
nothing is sent: live testing is deferred.
"""

from __future__ import annotations

import csv
from datetime import date
from typing import Any

import pytest

pytest.importorskip("wx")

from quill.core.wordpress import workbench_shop_analytics as wsa  # noqa: E402
from quill.core.wordpress.workbench_shop_analytics_period import Period  # noqa: E402
from quill.core.workbench.tree import NodeSpec  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_plugins_ui import SITE, _ref  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_plugins_ui import bench as _bench  # noqa: E402

bench = _bench

REVENUE = {
    "totals": {"orders_count": 31, "total_sales": 1240, "net_revenue": 1150},
    "intervals": [
        {
            "interval": "2026-11-18",
            "date_start": "2026-11-18 00:00:00",
            "subtotals": {"orders_count": 3, "total_sales": 120},
        }
    ],
}
BEFORE = {"totals": {"orders_count": 28, "total_sales": 1107.14}, "intervals": []}
STOCK = [{"id": 2, "name": "Mug", "stock_status": "outofstock", "stock_quantity": 0}]


@pytest.fixture
def shop(bench, monkeypatch):
    monkeypatch.setattr(wsa, "today", lambda: date(2026, 11, 19))
    plain = bench.api.get
    asked: list[tuple[str, dict[str, Any]]] = []

    def get(route: str, **params: Any) -> Any:
        if route == "":
            return {"name": SITE, "namespaces": ["wp/v2", "wc/v3", "wc-analytics"]}
        if route.startswith("wc-analytics/"):
            asked.append((route, params))
            if route.endswith("revenue/stats") or route.endswith("orders/stats"):
                return BEFORE if params.get("after") == "2026-11-06T00:00:00" else REVENUE
            if route.endswith("stock/stats"):
                return {"totals": {"products": 1, "outofstock": 1}}
            return {"totals": {}}
        if route == "wc/v3/data/currencies/current":
            return {"code": "USD", "symbol": "$"}
        return plain(route, **params)

    def iter_collection(route: str, params: Any = None, **_k: Any):
        asked.append((route, dict(params or {})))
        yield from STOCK if route.endswith("/stock") else []

    monkeypatch.setattr(bench.api, "get", get)
    monkeypatch.setattr(bench.api, "iter_collection", iter_collection)
    bench.asked = asked  # type: ignore[attr-defined]
    return bench


def _summaries(said: list[str]) -> list[str]:
    return [s for s in said if s.startswith(("Revenue on", "Orders on", "Stock on"))]


def _open(shop, key: str) -> None:
    shop.provider.ctx(SITE)  # the site is known before its node is opened
    assert shop.select(_ref(key))


def test_arriving_on_a_report_says_its_sentence_once(shop) -> None:
    _open(shop, "shop_analytics_revenue")
    assert _summaries(shop.said) == [
        f"Revenue on {SITE}, last 7 days: $1,240 from 31 orders, up 12% on the 7 days before."
    ]
    assert [r.cell("when") for r in shop.rows] == [
        "Total, last 7 days",
        "Wednesday 18 November 2026",
    ]
    shop.reload(report=True)  # F5: the count is said, the sentence is not said again
    shop.apply_filter()
    assert len(_summaries(shop.said)) == 1


def test_date_range_is_kept_for_the_site_and_says_the_new_sentence(shop) -> None:
    _open(shop, "shop_analytics_revenue")
    shop.answers.choices += [5]  # Last Month
    shop.provider.do_analytics_range(_ref("shop_analytics_revenue"), shop.rows[0])
    assert shop.provider.analytics_period(SITE) == Period("last_month")
    revenue = [p for r, p in shop.asked if r.endswith("revenue/stats")]
    assert revenue[-2]["after"] == "2026-10-01T00:00:00"  # this period, then the one before
    assert _summaries(shop.said)[-1].startswith(f"Revenue on {SITE}, last month: $1,240")
    orders = NodeSpec("x", "Orders", loader="shop:analytics_orders")
    assert shop.provider.analytics_params(_ref("shop_analytics_orders"), orders) == {
        "range": "last_month",
        "interval": "day",
    }
    assert shop.provider.analytics_params(_ref("shop"), NodeSpec("shop", "Shop")) == {}


def test_a_custom_range_asks_for_two_dates_and_refuses_one_it_cannot_read(shop) -> None:
    _open(shop, "shop_analytics_revenue")
    shop.answers.choices += [8, 8]
    shop.answers.texts += ["2026-11-10", "2026-11-01"]  # given backwards: put in order
    shop.provider.do_analytics_range(_ref("shop_analytics_revenue"), shop.rows[0])
    held = shop.provider.analytics_period(SITE)
    assert (held.range, held.start, held.end) == ("custom", date(2026, 11, 1), date(2026, 11, 10))
    assert _summaries(shop.said)[-1].startswith(
        f"Revenue on {SITE}, 1 November 2026 to 10 November 2026:"
    )
    shop.answers.texts += ["the first", "2026-11-02"]
    shop.provider.do_analytics_range(_ref("shop_analytics_revenue"), shop.rows[0])
    assert shop.said[-1].startswith("the first is not a date QUILL can read.")
    assert shop.provider.analytics_period(SITE) == held


def test_a_custom_range_into_the_future_stops_today(shop) -> None:
    _open(shop, "shop_analytics_revenue")
    shop.answers.choices += [8]
    shop.answers.texts += ["2026-11-15", "2026-12-31"]
    shop.provider.do_analytics_range(_ref("shop_analytics_revenue"), shop.rows[0])
    assert shop.provider.analytics_period(SITE).end == date(2026, 11, 19)
    assert any(s.startswith("The range ends after today, so it ends today: 2026-11-15 to 2026")
               for s in shop.said)  # fmt: skip


def test_a_cancelled_choice_changes_nothing(shop) -> None:
    _open(shop, "shop_analytics_revenue")
    asked = len(shop.asked)
    shop.answers.choices += [None, None]
    shop.provider.do_analytics_range(_ref("shop_analytics_revenue"), shop.rows[0])
    shop.provider.do_analytics_interval(_ref("shop_analytics_revenue"), shop.rows[0])
    assert shop.provider.analytics_period(SITE) == Period() and len(shop.asked) == asked


def test_interval_reaches_the_route(shop) -> None:
    _open(shop, "shop_analytics_orders")
    shop.answers.choices += [2]  # Month
    shop.provider.do_analytics_interval(_ref("shop_analytics_orders"), shop.rows[0])
    assert shop.provider.analytics_period(SITE).interval == "month"
    assert [p for r, p in shop.asked if r.endswith("orders/stats")][-1]["interval"] == "month"


def test_stock_says_the_range_does_not_change_it(shop) -> None:
    _open(shop, "shop_analytics_stock")
    assert _summaries(shop.said)[-1].startswith(f"Stock on {SITE}, now: 1 product")
    asked = len(shop.asked)
    shop.answers.choices += [2]  # Last 7 Days, as before
    shop.provider.do_analytics_range(_ref("shop_analytics_stock"), shop.rows[1])
    assert shop.said[-1].startswith("Stock is as things are now, so its list stays the same")
    shop.answers.choices += [1]
    shop.provider.do_analytics_interval(_ref("shop_analytics_stock"), shop.rows[1])
    assert shop.said[-1].startswith("Stock lists one row per product, so it stays the same")
    assert len(shop.asked) == asked


def test_export_list_writes_the_report_as_shown(shop, tmp_path, monkeypatch) -> None:
    _open(shop, "shop_analytics_revenue")
    path = tmp_path / "revenue.csv"
    monkeypatch.setattr(shop.provider, "_file", lambda *_a, **_k: path)
    shop.provider.do_export_list(_ref("shop_analytics_revenue"), None)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        table = list(csv.reader(handle))
    assert table[0][:3] == ["When", "Orders", "Gross"]
    assert table[1][0] == "Total, last 7 days" and table[1][-1] == "$1,240.00"
    assert shop.said[-1].startswith("Exported 2 rows to revenue.csv.")
