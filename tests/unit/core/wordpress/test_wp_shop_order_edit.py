"""New Order, Change Items and Change Address, the wx-free half (complete.md 2.3)."""

from __future__ import annotations

import pytest

from quill.core.wordpress import workbench_shop_order_edit as edit
from quill.core.wordpress.plugin_shop_seo import ShopValueError

ORDER = {
    "id": 77,
    "line_items": [
        {"id": 5, "product_id": 9, "name": "Mug", "quantity": 2},
        {"id": 6, "product_id": 12, "variation_id": 13, "name": "Shirt - Large", "quantity": 1},
        {"id": 0, "name": "broken"},
    ],
    "billing": {"first_name": "Ann", "city": "Tucson", "email": "ann@example.com"},
}


def test_quantities_are_whole_numbers_and_zero_only_removes() -> None:
    assert edit.parse_quantity(" 3 ", allow_zero=False) == 3
    assert edit.parse_quantity("0", allow_zero=True) == 0
    with pytest.raises(ShopValueError, match="from 1 to 100000"):
        edit.parse_quantity("0", allow_zero=False)
    with pytest.raises(ShopValueError, match="not a whole number"):
        edit.parse_quantity("two", allow_zero=True)


def test_an_orders_items_name_the_variation_when_there_is_one() -> None:
    items = edit.order_items(ORDER)
    assert [(i.item_id, i.product_id, i.quantity) for i in items] == [(5, 9, 2), (6, 13, 1)]
    assert items[0].words() == "2 x Mug"


def test_a_guest_order_is_never_marked_paid_and_ships_to_the_billing_address() -> None:
    order = edit.NewOrder(
        "pending",
        billing={"first_name": "Sam", "email": "sam@example.com", "phone": "555", "city": " "},
        lines=[(9, "Mug", 2)],
    )
    body = edit.new_order_body(order)
    assert body["set_paid"] is False
    assert body["line_items"] == [{"product_id": 9, "quantity": 2}]
    assert body["billing"] == {"first_name": "Sam", "email": "sam@example.com", "phone": "555"}
    assert body["shipping"] == {"first_name": "Sam"}  # no email or telephone on a parcel
    assert "customer_id" not in body


def test_a_customers_order_names_them_and_the_preview_says_who_works_out_the_total() -> None:
    order = edit.NewOrder("processing", 4, "Ann Lee", {}, [(9, "Mug", 1), (12, "Cap", 3)])
    assert edit.new_order_body(order)["customer_id"] == 4
    lines = edit.new_order_preview(order, "Shop")
    assert lines[:3] == ["A new shop order on Shop, for Ann Lee.", "1 x Mug.", "3 x Cap."]
    assert "does not mark it paid" in lines[-1]


@pytest.mark.parametrize(
    ("order", "words"),
    [
        (edit.NewOrder("pending", 4, "Ann", {}, []), "at least one product"),
        (edit.NewOrder("pending", 0, "", {"first_name": "Sam"}, [(9, "Mug", 1)]), "email"),
        (edit.NewOrder("completed", 4, "Ann", {}, [(9, "Mug", 1)]), "not a status"),
    ],
)
def test_an_order_that_cannot_be_made_says_why(order: edit.NewOrder, words: str) -> None:
    with pytest.raises(ShopValueError, match=words):
        edit.new_order_body(order)


def test_changing_items_sends_ids_for_old_lines_and_product_ids_for_new() -> None:
    changes = [
        edit.ItemChange(5, 9, "Mug", 0),
        edit.ItemChange(6, 13, "Shirt - Large", 2),
        edit.ItemChange(0, 20, "Cap", 1),
    ]
    assert edit.items_body(changes) == {
        "line_items": [
            {"id": 5, "product_id": 9, "quantity": 0},
            {"id": 6, "product_id": 13, "quantity": 2},
            {"product_id": 20, "quantity": 1},
        ]
    }
    lines = edit.items_preview("1077", edit.order_items(ORDER), changes, "Shop")
    assert lines[1:4] == ["Remove Mug (was 2).", "Shirt - Large: 1 becomes 2.", "Add 1 x Cap."]
    assert "QUILL does not move money here" in lines[-1]


#: Two lines of a real order on the test site (WooCommerce 11.3.1, 2026-11-19), as
#: ``wc/v3/orders/{id}`` answers them, trimmed to the keys QUILL reads.
LIVE_ORDER = {
    "id": 589,
    "line_items": [
        {"id": 4, "name": "Braille Mug", "product_id": 562, "variation_id": 0, "quantity": 1,
         "subtotal": "12.00", "total": "12.00", "price": 12},
        {"id": 5, "name": "QUILL T-shirt - Small", "product_id": 564, "variation_id": 565,
         "quantity": 2, "subtotal": "36.00", "total": "32.40", "price": 18},
    ],
}  # fmt: skip


def test_a_new_quantity_carries_the_lines_price_because_woocommerce_keeps_the_old_one() -> None:
    # Live, a POST with only {"id", "quantity": 3} left the mug at 12.00 and the
    # order's total wrong; sent with subtotal and total it came back right.
    items = edit.order_items(LIVE_ORDER)
    assert (items[1].subtotal, items[1].total) == ("36.00", "32.40")
    changes = [
        edit.ItemChange(4, 562, "Braille Mug", 3),
        edit.ItemChange(5, 565, "QUILL T-shirt - Small", 1),
    ]
    assert edit.items_body(changes, items)["line_items"] == [
        {"id": 4, "product_id": 562, "quantity": 3, "subtotal": "36.00", "total": "36.00"},
        {"id": 5, "product_id": 565, "quantity": 1, "subtotal": "18.00", "total": "16.20"},
    ]
    lines = edit.items_preview("589", items, changes, "Shop")
    assert "keeps its price per item" in lines[-1]


def test_a_removed_line_or_an_unreadable_price_sends_the_quantity_alone() -> None:
    items = [edit.OrderItem(4, 562, "Mug", 2, "12.00", "12.00"), edit.OrderItem(6, 9, "Cap", 1)]
    body = edit.items_body(
        [edit.ItemChange(4, 562, "Mug", 0), edit.ItemChange(6, 9, "Cap", 2)], items
    )
    assert body["line_items"] == [
        {"id": 4, "product_id": 562, "quantity": 0},
        {"id": 6, "product_id": 9, "quantity": 2},
    ]


def test_no_item_changes_is_said() -> None:
    with pytest.raises(ShopValueError, match="Nothing about the items"):
        edit.items_body([])


def test_an_address_change_sends_only_what_changed_and_keeps_the_old_for_undo() -> None:
    old = ORDER["billing"]
    body, back = edit.address_body("billing", old, {"first_name": "Ann", "city": "Phoenix"})
    assert body == {"billing": {"city": "Phoenix"}}
    assert back == {"billing": {"city": "Tucson"}}
    lines = edit.address_preview("1077", "billing", old, body, "Shop")
    assert lines == [
        "Shop order 1077 on Shop, billing address:",
        "Town or city: Tucson becomes Phoenix.",
    ]


def test_a_shipping_address_has_no_email_and_an_unchanged_one_is_refused() -> None:
    body, _back = edit.address_body("shipping", {}, {"email": "x@example.com", "city": "Mesa"})
    assert body == {"shipping": {"city": "Mesa"}}
    with pytest.raises(ShopValueError, match="Nothing about the shipping"):
        edit.address_body("shipping", {"city": "Mesa"}, {"city": "Mesa"})
