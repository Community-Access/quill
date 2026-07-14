"""``MainFrame._parse_keybinding`` must understand "Cmd" as a modifier.

DEFAULT_KEYMAP spells macOS-only bindings with "Cmd" (navigate.back_location /
navigate.forward_location, and window.next_document / window.previous_document
-- see keymap.py). wx has no separate ACCEL_CMD flag: wx.ACCEL_CTRL is what
already maps to the Command key in a wx.AcceleratorTable on macOS. Before this
fix, "_parse_keybinding" only recognized "ctrl"/"shift"/"alt" and returned
None for any "Cmd+..." binding, so "_apply_accelerators" silently skipped it
and the command had no keyboard shortcut at all on any platform.
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.ui.main_frame import MainFrame


def _build_frame() -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame._wx = SimpleNamespace(ACCEL_CTRL=1, ACCEL_SHIFT=2, ACCEL_ALT=4)
    return frame


def test_cmd_modifier_parses_the_same_as_ctrl() -> None:
    frame = _build_frame()
    assert frame._parse_keybinding("Cmd+[") == frame._parse_keybinding("Ctrl+[")


def test_cmd_shift_bracket_parses_to_ctrl_and_shift_flags() -> None:
    frame = _build_frame()
    flags, key_code = frame._parse_keybinding("Cmd+Shift+]")
    assert flags == 1 | 2  # ACCEL_CTRL | ACCEL_SHIFT
    assert key_code == ord("]")


def test_lowercase_command_word_also_parses() -> None:
    frame = _build_frame()
    assert frame._parse_keybinding("Command+Q") == frame._parse_keybinding("Ctrl+Q")


def test_unknown_modifier_still_returns_none() -> None:
    frame = _build_frame()
    assert frame._parse_keybinding("Foo+X") is None
