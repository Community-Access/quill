"""Every command in menu, name or key order (EdSharp's command list)."""

from __future__ import annotations

from quill.core.command_list import LABELS, ORDERS, command_list_text, menu_of

COMMANDS = [
    ("edit.find", "Find..."),
    ("file.open", "Open..."),
    ("help.about", "About"),
    ("edit.undo", "Undo"),
    ("quill_radio.play", "Play Radio"),
]
KEYS = {"edit.find": "Ctrl+F", "file.open": "Ctrl+O", "edit.undo": "Ctrl+Z"}


def _text(order: str, query: str = "") -> list[str]:
    return command_list_text(COMMANDS, lambda c: KEYS.get(c, ""), order=order, query=query).split(
        "\n"
    )


def test_three_orders_with_labels() -> None:
    assert ORDERS == ("menu", "name", "key")
    assert LABELS["key"] == "Key order"


def test_name_order() -> None:
    assert _text("name") == [
        "About: (no key)",
        "Find...: Ctrl+F",
        "Open...: Ctrl+O",
        "Play Radio: (no key)",
        "Undo: Ctrl+Z",
    ]


def test_menu_order_follows_the_menu_bar_with_a_heading_per_menu() -> None:
    assert _text("menu") == [
        "File menu:",
        "Open...: Ctrl+O",
        "",
        "Edit menu:",
        "Find...: Ctrl+F",
        "Undo: Ctrl+Z",
        "",
        "Help menu:",
        "About: (no key)",
        "",
        "Quill Radio menu:",
        "Play Radio: (no key)",
    ]


def test_key_order_puts_the_key_first_and_unbound_last() -> None:
    assert _text("key") == [
        "Ctrl+F: Find...",
        "Ctrl+O: Open...",
        "Ctrl+Z: Undo",
        "(no key): About",
        "(no key): Play Radio",
    ]


def test_the_filter_matches_name_or_key_in_any_order() -> None:
    assert _text("key", "ctrl+z") == ["Ctrl+Z: Undo"]
    assert _text("name", "OPEN") == ["Open...: Ctrl+O"]
    assert _text("menu", "nothing like this") == ["No matching commands."]
    assert menu_of("navigate.next_heading") == "Navigate"
