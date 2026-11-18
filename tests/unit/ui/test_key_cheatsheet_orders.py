"""The Key Cheatsheet in menu, name and key order (EdSharp's command list)."""

from __future__ import annotations

from types import SimpleNamespace

from quill.ui.main_frame_key_cheatsheet import KeyCheatsheetMixin


def _host() -> KeyCheatsheetMixin:
    commands = [
        SimpleNamespace(id="edit.find", title="Find..."),
        SimpleNamespace(id="file.open", title="Open..."),
    ]
    host = KeyCheatsheetMixin()
    host.commands = SimpleNamespace(list=lambda **_k: commands)  # type: ignore[assignment]
    host.keymap = {"edit.find": "Ctrl+F"}  # type: ignore[assignment]
    return host


def test_the_cheatsheet_text_follows_the_chosen_order() -> None:
    host = _host()
    assert host._build_cheatsheet_text("").splitlines()[0] == "Find...: Ctrl+F"
    menu = host._build_cheatsheet_text("", "menu").splitlines()
    assert menu[0] == "File menu:" and "Edit menu:" in menu
    key = host._build_cheatsheet_text("", "key").splitlines()
    assert key[0] == "Ctrl+F: Find..."
    assert host._build_cheatsheet_text("ctrl+f", "key") == "Ctrl+F: Find..."
