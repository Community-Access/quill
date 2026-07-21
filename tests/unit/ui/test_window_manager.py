"""Tests for the pure family window registry (numbered, cyclic traversal)."""

from __future__ import annotations

from quill.ui.window_manager import WindowItem, WindowRegistry


def test_register_preserves_open_order_and_numbers() -> None:
    reg = WindowRegistry()
    reg.register("a", "Main")
    reg.register("b", "Browse")
    reg.register("c", "Weather")
    assert reg.items() == [
        WindowItem(1, "a", "Main"),
        WindowItem(2, "b", "Browse"),
        WindowItem(3, "c", "Weather"),
    ]
    assert len(reg) == 3
    assert "b" in reg


def test_register_existing_key_updates_title_without_reordering() -> None:
    reg = WindowRegistry()
    reg.register("a", "Main")
    reg.register("b", "Browse")
    reg.register("a", "Main - playing KEXP")  # title refresh, same slot
    assert reg.title("a") == "Main - playing KEXP"
    assert [i.key for i in reg.items()] == ["a", "b"]


def test_unregister_renumbers_and_closes_the_gap() -> None:
    reg = WindowRegistry()
    for k, t in (("a", "Main"), ("b", "Browse"), ("c", "Weather")):
        reg.register(k, t)
    reg.unregister("b")
    assert [(i.number, i.key) for i in reg.items()] == [(1, "a"), (2, "c")]
    assert "b" not in reg
    reg.unregister("b")  # idempotent


def test_by_number_is_one_based_and_bounds_checked() -> None:
    reg = WindowRegistry()
    reg.register("a", "Main")
    reg.register("b", "Browse")
    assert reg.by_number(1) == "a"
    assert reg.by_number(2) == "b"
    assert reg.by_number(0) is None
    assert reg.by_number(3) is None


def test_next_and_previous_cycle() -> None:
    reg = WindowRegistry()
    for k in ("a", "b", "c"):
        reg.register(k, k)
    assert reg.next("a") == "b"
    assert reg.next("c") == "a"  # wraps
    assert reg.previous("a") == "c"  # wraps
    assert reg.previous("b") == "a"


def test_navigation_on_unknown_current_lands_on_first() -> None:
    reg = WindowRegistry()
    reg.register("a", "Main")
    reg.register("b", "Browse")
    assert reg.next("gone") == "a"
    assert reg.previous("gone") == "a"


def test_empty_registry_navigation_is_none() -> None:
    reg = WindowRegistry()
    assert reg.next("x") is None
    assert reg.previous("x") is None
    assert reg.by_number(1) is None
    assert reg.items() == []
    assert reg.title("x") == ""
