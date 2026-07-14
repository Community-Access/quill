"""Regression test for #612 (phantom QUILL Key sticking on R and S).

``_menu_label`` builds the text passed to ``wx.Menu.Append``. Anything
after a literal ``\\t`` in that text is parsed by wxWidgets as a real
native keyboard accelerator (``wxGetAccelFromString``), independent of
the QUILL Key chord dispatcher. ``format_binding_for_display`` turns a
chord binding like ``"Ctrl+Shift+Grave, R"`` into ``"QUILL Key + R"``
for human-facing display -- but that string's final ``+``-segment is a
bare, recognized key name, so wx silently bound plain ``R`` (and ``S``)
as real accelerators that fired their menu commands outside the chord
dispatcher entirely (#612). The chord display must therefore never sit
in the tab-accelerator slot; it must follow the label as plain text.
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.core.menu_customization import MenuCustomization
from quill.ui.main_frame import MainFrame


def _build_frame(*, keybinding_for) -> MainFrame:
    frame = MainFrame.__new__(MainFrame)
    frame.settings = SimpleNamespace(quill_key_binding="Ctrl+Shift+Grave")
    frame._menu_customization = MenuCustomization()
    frame.commands = SimpleNamespace(keybinding_for=keybinding_for)
    return frame


def test_chord_binding_label_has_no_tab_accelerator() -> None:
    """A QUILL Key chord must not land after a literal tab (#612)."""
    frame = _build_frame(keybinding_for=lambda _cid: "Ctrl+Shift+Grave, R")
    label = frame._menu_label("&Start / Pause", "tools.read_aloud_start_pause")
    assert "\t" not in label
    assert "QUILL Key + R" in label


def test_plain_binding_label_keeps_tab_accelerator() -> None:
    """A real, non-chord shortcut still gets the native accelerator slot."""
    frame = _build_frame(keybinding_for=lambda _cid: "Ctrl+S")
    label = frame._menu_label("&Save", "file.save")
    assert label == "&Save\tCtrl+S"


def test_no_binding_returns_plain_label() -> None:
    frame = _build_frame(keybinding_for=lambda _cid: None)
    label = frame._menu_label("&About", "help.about")
    assert label == "&About"


def test_cmd_binding_label_translates_to_ctrl_for_native_accelerator() -> None:
    """macOS-only variant of #612: DEFAULT_KEYMAP spells the Command key "Cmd"
    (Find &Next uses "Cmd+G" on darwin), but wx's menu-label accelerator
    parser does not reliably recognize the literal token "Cmd" -- it drops
    the modifier and keeps the bare key, silently binding plain G/g as a
    native accelerator that intercepted every G/g keystroke in the editor.
    "Ctrl" is what wx already renders as the Command-key glyph on macOS, so
    the native-parsed tab slot must say "Ctrl+G", never "Cmd+G"."""
    frame = _build_frame(keybinding_for=lambda _cid: "Cmd+G")
    label = frame._menu_label("Find &Next", "edit.find_next")
    assert label == "Find &Next\tCtrl+G"
    assert "Cmd" not in label


def test_cmd_shift_binding_label_translates_to_ctrl_for_native_accelerator() -> None:
    frame = _build_frame(keybinding_for=lambda _cid: "Cmd+Shift+G")
    label = frame._menu_label("Find &Previous", "edit.find_previous")
    assert label == "Find &Previous\tCtrl+Shift+G"
