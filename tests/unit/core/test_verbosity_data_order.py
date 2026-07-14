"""Tests for the verbosity data-ordering model (§14)."""

from __future__ import annotations

from quill.core.verbosity.data_order import DataOrder


def _order() -> DataOrder:
    return DataOrder("nav.next_line", ("line", "text", "column"))


def test_data_order_is_frozen_and_hashable() -> None:
    order = _order()
    # frozen: hashable, usable as a dict key
    assert hash(order) == hash(_order())
    assert {order: 1}[order] == 1


def test_move_up_reorders() -> None:
    moved = _order().move_up("text")
    assert moved.fields == ("text", "line", "column")


def test_move_down_reorders() -> None:
    moved = _order().move_down("line")
    assert moved.fields == ("text", "line", "column")


def test_move_up_first_is_noop() -> None:
    order = _order()
    assert order.move_up("line") == order


def test_move_down_last_is_noop() -> None:
    order = _order()
    assert order.move_down("column") == order


def test_move_missing_field_is_noop() -> None:
    order = _order()
    assert order.move_up("absent") == order


def test_reorder_returns_new_instance() -> None:
    order = _order()
    moved = order.move_up("text")
    assert moved is not order
    assert order.fields == ("line", "text", "column")  # original untouched


def test_reset_restores_defaults() -> None:
    order = _order().move_up("text")
    reset = order.reset(("line", "text", "column"))
    assert reset.fields == ("line", "text", "column")


def test_render_joins_present_fields_in_order() -> None:
    order = _order()
    rendered = order.render({"line": 12, "text": "hello", "column": 3})
    assert rendered == "12, hello, 3"


def test_render_skips_missing_and_empty() -> None:
    order = _order()
    rendered = order.render({"line": 12, "text": "", "column": None})
    assert rendered == "12"


def test_render_custom_separator() -> None:
    order = DataOrder("v", ("a", "b"), separator=" | ")
    assert order.render({"a": "x", "b": "y"}) == "x | y"


def test_dict_round_trip() -> None:
    order = _order()
    assert DataOrder.from_dict(order.to_dict()) == order
