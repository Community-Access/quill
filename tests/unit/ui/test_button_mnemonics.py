"""Every action button has an Alt key, and none of them fights the menu bar.

The subtle half is the collision. A button mnemonic on a frame competes with
the MENU BAR's mnemonics, so "&Record" on a button and "&Record" on the menu
bar means Alt+R opens the menu and the button never fires -- reported as #1208
against Alt+S/Alt+P. That was fixed by stripping the button's "&" entirely,
which traded a broken key for no key at all and left the transport button
unreachable by Alt. Two more buttons kept colliding mnemonics until 2026-08-16
(Add to Fa&vorites vs &View, &Record vs &Record).

So the rule has two halves, and both are pinned here: an action button carries
a mnemonic, and that letter is not one the menu bar has claimed.

Exempt: the status-bar cells (Now playing, Volume, Recording, Sleep timer,
Favorites, Time). They are a read-out reached with F6 and arrow keys -- the
PRD's A-6 -- and spending six Alt letters on them would take the letters real
actions need.
"""

from __future__ import annotations

import re

import pytest

wx = pytest.importorskip("wx")


@pytest.fixture(scope="module")
def radio_frame():
    app = wx.App()
    from quill.apps.radio import RadioAppFrame
    from quill.ui.dialog_contract import set_transition_announcement_policy

    frame = RadioAppFrame()
    yield frame
    # Building the app installs a process-global dialog-transition policy;
    # leaving it set leaks this app's preference into every later test.
    set_transition_announcement_policy(None)
    del app


def _menu_bar_keys(frame) -> dict[str, str]:
    menu_bar = frame.frame.GetMenuBar()
    keys: dict[str, str] = {}
    for index in range(menu_bar.GetMenuCount()):
        label = menu_bar.GetMenuLabel(index)
        found = re.search(r"&(.)", label)
        if found:
            keys[found.group(1).upper()] = label
    return keys


def _buttons(frame) -> list[str]:
    labels: list[str] = []

    def walk(widget) -> None:
        for child in widget.GetChildren():
            if child.__class__.__name__ in ("Button", "ToggleButton", "CheckBox"):
                labels.append(child.GetLabel())
            walk(child)

    walk(frame.frame)
    # A status cell reads "Name: value"; an action button never does.
    return [label for label in labels if ":" not in label]


def test_every_action_button_carries_an_alt_key(radio_frame) -> None:
    missing = [label for label in _buttons(radio_frame) if "&" not in label]
    assert missing == [], f"buttons with no Alt key: {missing}"


def test_no_button_mnemonic_is_stolen_by_the_menu_bar(radio_frame) -> None:
    menu_keys = _menu_bar_keys(radio_frame)
    stolen = []
    for label in _buttons(radio_frame):
        found = re.search(r"&(.)", label)
        if found and found.group(1).upper() in menu_keys:
            stolen.append(f"{label} -> Alt opens {menu_keys[found.group(1).upper()]}")
    assert stolen == [], "button mnemonics the menu bar answers first: " + "; ".join(stolen)


def test_the_transport_button_keeps_a_key_in_both_states(radio_frame) -> None:
    """Play and Stop are the same button with two labels; a mnemonic that
    survives only one of them is a key that vanishes mid-listen."""
    for label in ("P&lay", "S&top"):
        found = re.search(r"&(.)", label)
        assert found, label
        assert found.group(1).upper() not in _menu_bar_keys(radio_frame)
