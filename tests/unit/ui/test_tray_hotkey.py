"""The chord parser behind each app's show/hide-to-tray global hotkey."""

from __future__ import annotations

from types import SimpleNamespace

from quill.ui.tray_hotkey import parse_hotkey

# A tiny wx stand-in: only the constants parse_hotkey touches.
_WX = SimpleNamespace(
    ACCEL_CTRL=0x02,
    ACCEL_ALT=0x01,
    ACCEL_SHIFT=0x04,
    WXK_F1=340,
    WXK_F5=344,
    WXK_HOME=313,
    WXK_RETURN=13,
)


def test_letter_chord_with_all_modifiers() -> None:
    flags, key = parse_hotkey(_WX, "Ctrl+Alt+Shift+R")
    assert flags == (_WX.ACCEL_CTRL | _WX.ACCEL_ALT | _WX.ACCEL_SHIFT)
    assert key == ord("R")


def test_unique_default_chords_differ_per_app() -> None:
    quill = parse_hotkey(_WX, "Ctrl+Alt+Shift+Q")
    radio = parse_hotkey(_WX, "Ctrl+Alt+Shift+R")
    weather = parse_hotkey(_WX, "Ctrl+Alt+Shift+W")
    assert len({quill, radio, weather}) == 3


def test_function_and_named_keys() -> None:
    assert parse_hotkey(_WX, "Ctrl+F5") == (_WX.ACCEL_CTRL, _WX.WXK_F5)
    assert parse_hotkey(_WX, "Alt+Home") == (_WX.ACCEL_ALT, _WX.WXK_HOME)
    assert parse_hotkey(_WX, "Ctrl+Enter") == (_WX.ACCEL_CTRL, _WX.WXK_RETURN)


def test_cmd_maps_to_ctrl() -> None:
    assert parse_hotkey(_WX, "Cmd+Q")[0] == _WX.ACCEL_CTRL


def test_empty_and_garbage_return_none() -> None:
    assert parse_hotkey(_WX, "") is None
    assert parse_hotkey(_WX, None) is None
    assert parse_hotkey(_WX, "Meta+Zzz") is None
    assert parse_hotkey(_WX, "Ctrl+F13") is None
