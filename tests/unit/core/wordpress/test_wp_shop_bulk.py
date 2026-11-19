"""Change Many Products, the wx-free half (complete.md 2.3, Shop: products/batch)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from quill.core.wordpress import workbench_shop_bulk as bulk
from quill.core.wordpress.plugin_shop_seo import ShopValueError
from quill.core.wordpress.workbench_shop_catalog import product_row

SITE = "Shop"


def _product(pid: int, name: str, **extra: object):
    raw = {"id": pid, "name": name, "status": "publish", "regular_price": "20.00"}
    raw.update(extra)
    return product_row(raw, SITE)


MUG = _product(9, "Mug", categories=[{"id": 3, "name": "Gifts"}])
CAP = _product(10, "Cap", sale_price="15.00", date_on_sale_to="2026-12-01")
SHIRT = _product(11, "Shirt", type="variable", regular_price="")
COUNTED = _product(12, "Pen", manage_stock=True, stock_quantity=4)


def test_a_sale_is_a_percentage_off_the_regular_price_rounded_to_the_cent() -> None:
    plan = bulk.plan_bulk([MUG, SHIRT], "sale", percent=Decimal("12.5"))
    assert plan.updates == [{"id": 9, "sale_price": "17.50"}]
    assert plan.undo == [{"id": 9, "sale_price": ""}]
    assert plan.lines == ["Mug: 20.00, on sale at 17.50."]
    assert plan.skipped == ["Shirt: a variable product's prices are on its variations."]


def test_ending_a_sale_clears_its_dates_and_undo_puts_them_back() -> None:
    plan = bulk.plan_bulk([MUG, CAP], "end_sale")
    assert plan.updates == [
        {"id": 10, "sale_price": "", "date_on_sale_from": "", "date_on_sale_to": ""}
    ]
    assert plan.undo[0]["sale_price"] == "15.00"
    assert plan.undo[0]["date_on_sale_to"] == "2026-12-01"
    assert plan.skipped == ["Mug: it is not on sale."]


def test_a_price_change_says_when_a_sale_price_is_no_longer_below_it() -> None:
    plan = bulk.plan_bulk([CAP], "price", percent=Decimal(-30))
    assert plan.updates == [{"id": 10, "regular_price": "14.00"}]
    assert plan.lines[1] == "  Its sale price, 15.00, is no longer below it."


def test_stock_status_leaves_counted_stock_to_woocommerce() -> None:
    plan = bulk.plan_bulk([MUG, COUNTED], "stock", choice="outofstock")
    assert plan.updates == [{"id": 9, "stock_status": "outofstock"}]
    assert plan.undo == [{"id": 9, "stock_status": "instock"}]
    assert plan.skipped == ["Pen: WooCommerce sets its stock status from its count."]


def test_status_skips_what_is_already_so() -> None:
    plan = bulk.plan_bulk([MUG], "status", choice="draft")
    assert plan.updates == [{"id": 9, "status": "draft"}]
    with pytest.raises(ShopValueError, match="already published"):
        bulk.plan_bulk([MUG], "status", choice="publish")


def test_categories_are_added_and_removed_but_never_to_none() -> None:
    added = bulk.plan_bulk([MUG, CAP], "add_category", category=(4, "Mugs"))
    assert added.updates[0] == {"id": 9, "categories": [{"id": 3}, {"id": 4}]}
    assert added.undo[0] == {"id": 9, "categories": [{"id": 3}]}
    with pytest.raises(ShopValueError, match="its only category"):
        bulk.plan_bulk([MUG], "remove_category", category=(3, "Gifts"))


def test_percentages_are_checked() -> None:
    assert bulk.parse_percent("15%", allow_negative=False) == Decimal(15)
    assert bulk.parse_percent("-10", allow_negative=True) == Decimal(-10)
    with pytest.raises(ShopValueError, match="0.01 to 99"):
        bulk.parse_percent("100", allow_negative=False)
    with pytest.raises(ShopValueError, match="not a percentage"):
        bulk.parse_percent("lots", allow_negative=True)


def test_batches_hold_at_most_one_hundred_and_failures_are_named() -> None:
    bodies = bulk.batch_bodies([{"id": n} for n in range(250)])
    assert [len(b["update"]) for b in bodies] == [100, 100, 50]
    answer = {"update": [{"id": 9}, {"id": 10, "error": {"message": "Invalid price."}}]}
    assert bulk.batch_failures(answer) == ["Product 10: Invalid price."]
