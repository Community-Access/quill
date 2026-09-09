"""QuillLite's command table keeps the house keyboard rules, mechanically.

``CLAUDE.md`` states the rule this file enforces: **every enabled menu item
shows a keyboard route in its label, and no two items in one menu bar may claim
the same key.** Walking a menu to discover there is no shortcut is a cost a
screen-reader user pays on every visit, and a key claimed twice means one of the
pair silently never fires.

Four checks, each for a failure that is invisible until somebody pays for it:

1. **Every item carries a key.** A keyless item is a menu-only command.
2. **No key twice.** Windows fires one of a duplicated pair and the other is
   dead, with nothing announcing the loss.
3. **No ``&`` mnemonic twice inside one menu.** Windows *cycles* focus between
   duplicate mnemonics instead of pressing, so one of the pair cannot be
   reached at all (GATE-14's rule, applied to menu items, which the source-level
   access-key gate does not see).
4. **Every key is one wx can parse.** ``wx.AcceleratorEntry`` silently drops
   what it cannot parse -- ``Ctrl+Shift+Plus`` is the known example -- leaving
   the menu advertising a key that does nothing.

The last one needs wx, so it is skipped where wx is absent; the first three are
pure data and run anywhere.
"""

from __future__ import annotations

import collections

import pytest

from quill.core.lite.commands import COMMANDS, menu_titles, shortcut_text


def _items() -> list[tuple[str, str, str, str]]:
    """``(menu, label, key, handler)`` for every real item -- separators out."""
    return [
        (menu, label, key, handler) for menu, label, key, handler, kind in COMMANDS if kind != "sep"
    ]


def _mnemonic(label: str) -> str:
    """The Alt letter *label* claims, or "" (``&&`` escapes a literal &)."""
    index = label.find("&")
    while label[index : index + 2] == "&&":
        index = label.find("&", index + 2)
    if index == -1 or index + 1 >= len(label):
        return ""
    char = label[index + 1]
    return char.upper() if char.isalnum() else ""


def test_the_table_is_not_empty_and_every_row_is_well_formed() -> None:
    """A gate that inspects nothing passes everything."""
    assert len(_items()) > 40
    for menu, label, key, handler, kind in COMMANDS:
        assert kind in {"", "check", "sep"}, (menu, label, kind)
        if kind == "sep":
            continue
        assert menu.startswith("&") or "&" in menu, menu
        assert label and key and handler, (menu, label)


def test_every_enabled_item_advertises_a_key() -> None:
    keyless = [f"{menu} > {label}" for menu, label, key, _h in _items() if not key.strip()]
    assert keyless == [], f"menu items with no keyboard route: {keyless}"


def test_no_key_is_claimed_twice() -> None:
    counts = collections.Counter(key for _m, _l, key, _h in _items())
    duplicates = {key: count for key, count in counts.items() if count > 1}
    assert duplicates == {}, (
        f"these keys are claimed more than once, so one of each pair never fires: {duplicates}"
    )


def test_no_access_key_is_claimed_twice_within_one_menu() -> None:
    """Windows cycles focus between duplicate mnemonics instead of pressing."""
    per_menu: dict[str, dict[str, str]] = collections.defaultdict(dict)
    collisions: list[str] = []
    for menu, label, _key, _handler in _items():
        letter = _mnemonic(label)
        if not letter:
            continue
        claimed = per_menu[menu]
        if letter in claimed:
            collisions.append(f"{menu}: {claimed[letter]!r} and {label!r} both claim Alt+{letter}")
        else:
            claimed[letter] = label
    assert collisions == [], "\n".join(collisions)


def test_no_two_menus_on_the_bar_claim_the_same_alt_letter() -> None:
    letters = [_mnemonic(title) for title in menu_titles()]
    assert all(letters), f"a menu with no mnemonic: {menu_titles()}"
    assert len(set(letters)) == len(letters), f"duplicate menu-bar mnemonics: {letters}"


def test_every_handler_name_is_unique_and_looks_like_a_command() -> None:
    handlers = [handler for _m, _l, _k, handler in _items()]
    assert all(handler.startswith("cmd_") for handler in handlers), handlers
    duplicates = [h for h, n in collections.Counter(handlers).items() if n > 1]
    assert duplicates == [], f"one handler on two items: {duplicates}"


def test_every_key_is_one_wx_can_actually_parse() -> None:
    """wx drops what it cannot parse, leaving a menu advertising a dead key."""
    wx = pytest.importorskip("wx", reason="wx is not installed")
    app = wx.App()  # AcceleratorEntry needs an app object on some platforms
    try:
        unparsed = []
        for menu, label, key, _handler in _items():
            entry = wx.AcceleratorEntry()
            if not entry.FromString(f"item\t{key}"):
                unparsed.append(f"{menu} > {label}: {key!r}")
        assert unparsed == [], "wx cannot parse these accelerators:\n  " + "\n  ".join(unparsed)
    finally:
        del app


def test_the_shortcut_window_lists_what_is_actually_bound() -> None:
    """The key list is generated from the table, so it cannot drift from it."""
    text = shortcut_text()
    for _menu, label, key, _handler in _items():
        assert key in text, f"{key} ({label}) is bound but not listed"
        assert label.replace("&", "") in text, f"{label} is bound but not listed"
    # The two things the table cannot carry, because they are built per window.
    assert "Alt+1 to Alt+9" in text
    assert "Alt+Shift+1 to Alt+Shift+9" in text
    # And the one fact about rich mode that saves a support email.
    assert "20, 16, 14 and 12" in text


def test_f1_is_the_context_help_key_and_the_key_list_moved_off_it() -> None:
    """Every app in the family answers F1 with what this window is for."""
    by_key = {key: handler for _m, _l, key, handler in _items()}
    assert by_key["F1"] == "cmd_context_help"
    assert by_key["Ctrl+F1"] == "cmd_shortcuts"
