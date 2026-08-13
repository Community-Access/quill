"""The Winamp classic-skin key map and its wiring in Recordings (#1344).

The map itself is wx-free on purpose, so the meaning of every key can be tested
without a display -- and so the standalone Media Player and Cast can adopt the
same map rather than growing a second one.
"""

from __future__ import annotations

import pytest

from quill.ui.radio import winamp_keys as wk


@pytest.mark.parametrize(
    ("key", "modifiers", "expected"),
    [
        ("X", {}, wk.ACTION_PLAY),
        ("C", {}, wk.ACTION_PAUSE),
        ("V", {}, wk.ACTION_STOP),
        ("V", {"shift": True}, wk.ACTION_STOP_FADE),
        ("B", {}, wk.ACTION_NEXT),
        ("Z", {}, wk.ACTION_PREVIOUS),
        ("LEFT", {}, wk.ACTION_BACK_5),
        ("RIGHT", {}, wk.ACTION_FORWARD_5),
        ("LEFT", {"shift": True}, wk.ACTION_BACK_30),
        ("RIGHT", {"shift": True}, wk.ACTION_FORWARD_30),
        ("T", {}, wk.ACTION_TOGGLE_TIME),
        ("J", {}, wk.ACTION_JUMP_TO_FILE),
        ("J", {"ctrl": True}, wk.ACTION_JUMP_TO_TIME),
        ("L", {}, wk.ACTION_OPEN),
        ("UP", {"ctrl": True}, wk.ACTION_VOLUME_UP),
        ("DOWN", {"ctrl": True}, wk.ACTION_VOLUME_DOWN),
    ],
)
def test_classic_transport_keys(key: str, modifiers: dict, expected: str) -> None:
    assert wk.resolve_winamp_action(key, **modifiers) == expected


def test_ctrl_t_is_not_claimed() -> None:
    """Quill Radio's What's Playing keeps Ctrl+T; the time toggle moved to T.

    The one place the map knowingly diverges from Winamp, documented in
    CONTROL_REFERENCE.md.
    """
    assert wk.resolve_winamp_action("T", ctrl=True) is None
    assert wk.resolve_winamp_action("T") == wk.ACTION_TOGGLE_TIME


def test_bare_arrows_up_and_down_stay_list_navigation() -> None:
    # Winamp's own Playlist Editor navigates with Up/Down; volume keeps Ctrl.
    assert wk.resolve_winamp_action("UP") is None
    assert wk.resolve_winamp_action("DOWN") is None


def test_unmapped_keys_pass_through() -> None:
    for key in ("A", "Q", "M", "P", "R", "S"):
        assert wk.resolve_winamp_action(key) is None
    assert wk.resolve_winamp_action("X", alt=True) is None
    assert wk.resolve_winamp_action("") is None


def test_every_action_has_a_spoken_label() -> None:
    for action in set(wk._MAP.values()):
        assert wk.ACTION_LABELS[action]


def test_documented_rows_match_the_live_map() -> None:
    labels = {label for _key, label in wk.keymap_rows()}
    assert labels == {wk.ACTION_LABELS[a] for a in set(wk._MAP.values())}


class _Wx:
    WXK_LEFT = 314
    WXK_UP = 315
    WXK_RIGHT = 316
    WXK_DOWN = 317


def test_normalize_key_code() -> None:
    wx = _Wx()
    assert wk.normalize_key_code(ord("X"), wx) == "X"
    assert wk.normalize_key_code(ord("x"), wx) == "X"
    assert wk.normalize_key_code(_Wx.WXK_LEFT, wx) == "LEFT"
    assert wk.normalize_key_code(_Wx.WXK_DOWN, wx) == "DOWN"
    assert wk.normalize_key_code(9, wx) == ""  # Tab is not ours


@pytest.mark.parametrize(
    ("typed", "expected"),
    [
        ("90", 90_000),
        ("1:30", 90_000),
        ("01:02:03", 3_723_000),
        ("0", 0),
        ("", None),
        ("   ", None),
        ("abc", None),
        ("1:2:3:4", None),
        ("-5", None),
    ],
)
def test_parse_time_to_ms(typed: str, expected: int | None) -> None:
    assert wk.parse_time_to_ms(typed) == expected
