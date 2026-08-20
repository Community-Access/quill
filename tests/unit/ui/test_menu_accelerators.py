"""Every menu item shows a way to reach it from the keyboard.

The house rule (CLAUDE.md; the radio PRD): a screen-reader user should never
have to walk a menu to discover there is no faster way in, and a menu item
that advertises a key must actually be reachable by it. Before this gate,
Quill Radio shipped 115 menu items of which 49 had no accelerator at all,
seven keys were claimed by two items each (so one of the pair silently never
fired), and two labels advertised "Ctrl+Shift+Plus"/"Minus" -- which wx
rejects outright with "Unrecognized accel key, accel string ignored".

Built from the real menu bar rather than by reading source, because that is
the thing the listener actually meets: submenus, dynamic rows and all.

Exempt, deliberately: a *disabled* item (Quill Radio's "Radio: stopped" is a
status readout, not a command -- there is nothing to invoke).
"""

from __future__ import annotations

import collections

import pytest

wx = pytest.importorskip("wx")


@pytest.fixture(scope="module")
def radio_menu_bar():
    app = wx.App()
    from quill.apps.radio import RadioAppFrame
    from quill.ui.dialog_contract import set_transition_announcement_policy

    frame = RadioAppFrame()
    # The gate must walk a menu bar with DATA in it, not the empty-profile
    # default: the Favorites submenu is only appended when favorites exist, so
    # an empty fixture shipped rows with no keyboard route while this gate
    # stayed green (found 2026-08-17 — the blind spot polish.md called P0.2).
    # Twelve favorites (one foldered) exercise the ten quick-play slots AND the
    # disabled overflow readout; the menu bar is then rebuilt so the walk sees
    # what a real user's menu shows.
    from quill.core.radio.models import RadioStation

    favorites = frame._radio_favorites
    for index in range(1, 13):
        station = RadioStation(
            name=f"Gate Station {index}",
            stream_url=f"http://example.invalid/{index}",
        )
        favorites.add(station, folder="Morning" if index == 12 else "")
    frame._build_menu_bar()
    yield frame.frame.GetMenuBar()
    # Building the app installs a process-global dialog-transition policy;
    # leaving it set leaks this app's preference into every later test.
    set_transition_announcement_policy(None)
    del app


def _walk(menu, path, out):
    for item in menu.GetMenuItems():
        if item.IsSeparator():
            continue
        label = item.GetItemLabel()
        submenu = item.GetSubMenu()
        if submenu is not None:
            _walk(submenu, f"{path} > {label.split(chr(9))[0]}", out)
            continue
        out.append((f"{path} > {label.split(chr(9))[0]}", label, item.IsEnabled()))


def _items(menu_bar):
    out: list[tuple[str, str, bool]] = []
    for index in range(menu_bar.GetMenuCount()):
        _walk(menu_bar.GetMenu(index), menu_bar.GetMenuLabel(index), out)
    return out


def test_every_enabled_menu_item_advertises_a_keyboard_route(radio_menu_bar) -> None:
    missing = [
        where for where, label, enabled in _items(radio_menu_bar) if enabled and chr(9) not in label
    ]
    assert missing == [], "menu items with no accelerator: " + "; ".join(missing)


def test_no_two_menu_items_claim_the_same_key(radio_menu_bar) -> None:
    """Two items on one key means one of them never fires -- worse than none,
    because the menu promises something it cannot deliver."""
    claimed = collections.defaultdict(list)
    for where, label, _enabled in _items(radio_menu_bar):
        if chr(9) in label:
            claimed[label.split(chr(9), 1)[1].strip()].append(where)
    duplicated = {key: where for key, where in claimed.items() if len(where) > 1}
    assert duplicated == {}, f"accelerators claimed twice: {duplicated}"


def test_every_advertised_key_is_one_wx_can_actually_bind(radio_menu_bar) -> None:
    """wx parses the text after the tab; anything it cannot parse is dropped
    with a warning and the menu is left advertising a key that does nothing."""
    unparsable = []
    for where, label, _enabled in _items(radio_menu_bar):
        if chr(9) not in label:
            continue
        entry = wx.AcceleratorEntry()
        if not entry.FromString(label):
            unparsable.append(f"{where} ({label.split(chr(9), 1)[1]})")
    assert unparsable == [], "wx cannot bind these: " + "; ".join(unparsable)


def test_no_menu_item_claims_a_table_navigation_key(radio_menu_bar) -> None:
    """Ctrl+Alt+arrow belongs to table navigation and never reaches the app.

    Two claimants, not one: QUILL's own table navigation binds that block
    (keymap.table.next_cell and kin), and JAWS and NVDA bind it for *their*
    table navigation too -- so a menu item advertising one of these keys is
    advertising a key the screen reader eats before the app ever sees it
    (reported 2026-08-18: "ctralt and arrow keys will not work either, more
    table navigation keys for JAWS and NVDA").

    Quill Radio shipped six transport verbs there -- speed, chapters, position
    -- and they now read their keys from quill.core.radio.transport_commands.
    This is the gate that keeps them out.
    """
    forbidden = {"ctrl+alt+up", "ctrl+alt+down", "ctrl+alt+left", "ctrl+alt+right"}
    offenders = []
    for where, label, _enabled in _items(radio_menu_bar):
        _text, _, key = label.partition(chr(9))
        if key and key.replace(" ", "").lower() in forbidden:
            offenders.append(f"{where} -> {key}")

    assert not offenders, "menu items on a table-navigation key: " + "; ".join(offenders)
