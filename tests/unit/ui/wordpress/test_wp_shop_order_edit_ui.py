"""New Order, Change Items and Change Address in the Workbench (complete.md 2.3)."""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("wx")

from quill.core.wordpress.workbench_plugin_actions import PLUGIN_NEW_HERE  # noqa: E402
from quill.core.wordpress.workbench_rows import WbRow  # noqa: E402
from tests.unit.ui.wordpress.test_wp_workbench_plugins_ui import (  # noqa: E402
    SITE,
    _ref,
)
from tests.unit.ui.wordpress.test_wp_workbench_plugins_ui import bench as _bench  # noqa: E402

bench = _bench

_ANN = {"first_name": "Ann", "city": "Tucson", "email": "ann@example.com"}
_CUSTOMERS = [
    {"id": 4, "first_name": "Ann", "last_name": "Lee", "email": "ann@example.com", "billing": _ANN}
]
_PRODUCTS = [{"id": 9, "name": "Mug"}, {"id": 20, "name": "Cap"}]
_ORDER = {
    "id": 77,
    "number": "1077",
    "line_items": [{"id": 5, "product_id": 9, "name": "Mug", "quantity": 2}],
    "billing": {"first_name": "Ann", "city": "Tucson"},
    "shipping": {"first_name": "Ann", "city": "Tucson"},
}


@pytest.fixture
def shop(bench, monkeypatch):
    plain = bench.api.get

    def get(route: str, **params: Any) -> Any:
        if route == "wc/v3/customers":
            return _CUSTOMERS
        if route == "wc/v3/products":
            return _PRODUCTS
        if route == "wc/v3/orders/77":
            return _ORDER
        return plain(route, **params)

    monkeypatch.setattr(bench.api, "get", get)
    monkeypatch.setattr(bench.api, "post", lambda route, body=None, **_p: (
        bench.api.sent.append(("POST", route, body)) or {"id": 90, "number": "1090"}))  # fmt: skip
    return bench


def _order() -> WbRow:
    return WbRow("shop_order", SITE, "77", {"what": "Shop order 1077"}, "", raw={"order": "1077"})


def test_ctrl_n_on_shop_orders_makes_a_new_order() -> None:
    assert PLUGIN_NEW_HERE["shop_orders"] == "do_new_order"


def test_a_new_order_for_a_customer_previews_sends_and_undoes_to_the_trash(shop) -> None:
    a = shop.answers
    a.choices += [1, 1, 0, 0]  # Ann; Mug; Done choosing; Pending payment
    a.texts += ["2"]
    shop.provider.do_new_order(_ref("shop_orders"), None)
    assert a.previews[-1]["lines"][:2] == [
        f"A new shop order on {SITE}, for Ann Lee, ann@example.com.",
        "2 x Mug.",
    ]
    method, route, body = shop.api.sent[-1]
    assert (method, route) == ("POST", "wc/v3/orders")
    assert body["customer_id"] == 4 and body["set_paid"] is False
    assert body["line_items"] == [{"product_id": 9, "quantity": 2}]
    assert shop.said[-1] == f"Made shop order 1090 on {SITE}."
    step = shop.provider.history.entries[-1]
    assert step.undo is not None
    assert step.undo() == f"Shop order 1090 on {SITE} is in the Trash."
    assert shop.api.sent[-1] == ("DELETE", "wc/v3/orders/90", None)


def test_a_guest_order_asks_the_address_and_needs_an_email(shop) -> None:
    a = shop.answers
    a.choices += [0, 2, 0, 0]  # a guest; Cap; Done; Pending payment
    a.texts += ["Sam", "Ray", "", "1 Main St", "", "Mesa", "AZ", "85201", "US", "", "555", "1"]
    shop.provider.do_new_order(_ref("shop_orders"), None)
    assert shop.api.sent == []
    assert shop.said[-1].endswith(
        "A guest's order needs their email, for the receipt. Nothing was made."
    )


def test_cancelling_the_quantity_adds_nothing(shop) -> None:
    a = shop.answers
    a.choices += [1, 1, 0]  # Ann; Mug, then cancel its quantity; Done
    a.texts += [None]
    shop.provider.do_new_order(_ref("shop_orders"), None)
    assert shop.said[-1] == "No products were chosen. Nothing was made."


def test_change_items_removes_one_and_adds_another_and_says_it_cannot_be_undone(shop) -> None:
    a = shop.answers
    a.choices += [2, 1, 2, 0, 0]  # 2 x Mug; Add a product; Cap; Done choosing; Done
    a.texts += ["0", "1"]
    shop.provider.do_change_order_items(_ref("shop_orders"), _order())
    lines = a.previews[-1]["lines"]
    assert "Remove Mug (was 2)." in lines and "Add 1 x Cap." in lines
    assert "cannot be undone here" in lines[-1]
    assert shop.api.sent[-1] == (
        "POST",
        "wc/v3/orders/77",
        {
            "line_items": [
                {"id": 5, "product_id": 9, "quantity": 0},
                {"product_id": 20, "quantity": 1},
            ]
        },
    )


def test_change_address_sends_only_the_change_and_undo_sends_the_old(shop) -> None:
    a = shop.answers
    a.choices += [1]  # Shipping
    a.texts += ["Ann", "", "", "", "", "Phoenix", "", "", ""]
    shop.provider.do_change_order_address(_ref("shop_orders"), _order())
    assert a.previews[-1]["lines"][-1] == "Town or city: Tucson becomes Phoenix."
    assert shop.api.sent[-1] == ("POST", "wc/v3/orders/77", {"shipping": {"city": "Phoenix"}})
    shop.provider.history.entries[-1].undo()
    assert shop.api.sent[-1] == ("POST", "wc/v3/orders/77", {"shipping": {"city": "Tucson"}})
