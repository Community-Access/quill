"""QUILL's half of the Command Key: the command, its Tools row, its F11 key."""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.keymap import DEFAULT_KEYMAP
from quill.ui import command_key_hosts
from quill.ui.main_frame_command_key import COMMAND_KEY, CommandKeyMixin


class _Commands:
    def __init__(self) -> None:
        self.registered: list[tuple[str, str, str | None]] = []

    def register(self, command_id: str, title: str, _handler: Any, binding: str | None) -> None:
        self.registered.append((command_id, title, binding))


class _Frame(CommandKeyMixin):
    def __init__(self) -> None:
        self.commands = _Commands()

    def _binding_for(self, command_id: str) -> str:
        return DEFAULT_KEYMAP.get(command_id, "")


def test_f11_is_the_command_key_and_never_dictation() -> None:
    assert DEFAULT_KEYMAP[COMMAND_KEY] == "F11"
    assert DEFAULT_KEYMAP["tools.windows_dictation_command"] == "Ctrl+Alt+Shift+Q"
    assert DEFAULT_KEYMAP["tools.windows_dictation_toggle"] == "Ctrl+F11"
    dictation = [cid for cid, key in DEFAULT_KEYMAP.items() if key == "F11"]
    assert dictation == [COMMAND_KEY]


def test_the_command_is_registered_with_its_key() -> None:
    frame = _Frame()
    frame._register_command_key_commands()
    assert frame.commands.registered == [(COMMAND_KEY, "Say or Type a Command...", "F11")]


def test_f11_and_the_help_row_reach_the_shared_code(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _Frame()
    opened: list[str] = []
    monkeypatch.setattr(command_key_hosts, "quill_command_key", lambda _f: opened.append("box"))
    monkeypatch.setattr(
        command_key_hosts, "quill_what_can_i_say_here", lambda _f: opened.append("help")
    )
    frame.open_command_key()
    frame.show_what_can_i_say_here()
    assert opened == ["box", "help"]


def test_what_can_i_say_here_keeps_the_old_rows_id_and_key() -> None:
    assert DEFAULT_KEYMAP["help.what_can_i_do_here"] == "Ctrl+Alt+Shift+F1"
