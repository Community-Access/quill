"""Quill Radio's main window can pause, and its Playback menu says so.

The gap: the Playback menu had one transport row, Play/Stop on Ctrl+P, wired to
``_on_play_stop_button`` -- which *stops*. So in the main window Ctrl+P ended a
recording, a downloaded file or a finished video, where the very same key in
every other window of the app paused it (``transport.play_pause`` is Ctrl+P
too, installed everywhere by the shared transport keyboard). One key, two
meanings, decided by which window had focus.

Play/Stop keeps Ctrl+P and keeps its behaviour -- a fix that rewrites muscle
memory is not a fix -- and Pause/Resume is a second, adjacent row.
"""

from __future__ import annotations

from pathlib import Path

from quill.core.app_keymaps import APP_KEYMAPS

_ROOT = Path(__file__).resolve().parents[3]
_MENU = (_ROOT / "quill" / "apps" / "radio_transport_menu.py").read_text(encoding="utf-8")
_RADIO = (_ROOT / "quill" / "apps" / "radio.py").read_text(encoding="utf-8")


def test_pause_has_a_key_and_it_is_one_wx_can_actually_parse() -> None:
    """CLAUDE.md's rule: wx silently drops what it cannot parse, leaving the
    menu advertising a key that does nothing (``Ctrl+Shift+Plus`` is the
    cautionary tale)."""
    import pytest

    pytest.importorskip("wx")
    import wx

    key = APP_KEYMAPS["radio"]["radio.pause"]
    assert key == "Ctrl+Space"

    app = wx.App()  # noqa: F841 - an AcceleratorEntry needs one
    entry = wx.AcceleratorEntry()
    assert entry.FromString(key), key


def test_pause_does_not_take_a_key_something_else_already_claims() -> None:
    """The accelerator gate checks the built bar; this checks the table it is
    built from, so a clash is caught before a window exists."""
    from quill.core.radio import transport_commands as tc

    radio = APP_KEYMAPS["radio"]
    others = [k for cid, k in radio.items() if cid != "radio.pause"]
    others += list(tc.keymap_defaults().values())

    assert radio["radio.pause"] not in others


def test_play_stop_keeps_ctrl_p_and_keeps_its_handler() -> None:
    assert 'playback_menu.Append(play_id, "&Play' in _MENU
    assert "Ctrl+P" in _MENU
    assert "app._on_play_stop_button()" in _MENU


def test_the_two_rows_are_adjacent() -> None:
    """They are the two halves of one question; pause eleven rows further down
    is pause somebody arrowing the menu never finds."""
    play = _MENU.index("playback_menu.Append(play_id")
    pause = _MENU.index("playback_menu.Append(pause_id")
    between = _MENU[play:pause]

    assert "Append" not in between.replace("playback_menu.Append(play_id", "", 1)


def test_the_pause_row_refuses_out_loud_on_live_radio() -> None:
    """A key that does nothing is indistinguishable from a key nobody bound --
    which is how the missing row went unreported for so long."""
    assert "if not pause.enabled:" in _MENU
    assert 'app._announce(f"{pause.plain}: {pause.reason}.")' in _MENU


def test_both_labels_come_from_the_one_shared_face() -> None:
    """The menu, the player panel's buttons and the tray all read the same
    call, so they cannot disagree about what is playing."""
    assert "transport_face.faces(app)" in _MENU
    assert "def refresh_labels(" in _MENU
    assert "radio_transport_menu.refresh_labels(self)" in _RADIO


def test_radio_py_got_smaller_rather_than_larger() -> None:
    """GATE-11 says extract, not rebaseline -- and this is what that looks
    like: the rows, their handler and their refresh all left radio.py."""
    import json

    budgets = json.loads(
        (_ROOT / "quill" / "tools" / "module_size_budgets.json").read_text(encoding="utf-8")
    )
    table = budgets.get("budgets", budgets)
    lines = len((_ROOT / "quill" / "apps" / "radio.py").read_text(encoding="utf-8").splitlines())

    assert lines <= table["quill/apps/radio.py"]
    # The old inline wiring is gone, not merely duplicated.
    assert "self._play_menu_item_id = wx.NewIdRef()" not in _RADIO
