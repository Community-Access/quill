"""QUILL Lite's Command Key: F11 and What Can I Say Here reach the shared code.

QUILL Lite has no Command Key of its own (CLAUDE.md: QUILL Lite may never be
ahead of QUILL). Its two handlers hand the window to the shared module, and its
candidates are QUILL's catalogue rows under QUILL Lite's ids.
"""

from __future__ import annotations

from typing import Any

import pytest

from quill.core.lite.commands import COMMANDS
from quill.ui import command_key_hosts


def test_f11_hands_the_window_to_the_shared_command_key(
    lite_window: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    win = lite_window("hello")
    seen: list[Any] = []
    monkeypatch.setattr(command_key_hosts, "lite_command_key", seen.append)
    win.cmd_command_key()
    assert seen == [win]


def test_what_can_i_say_here_hands_the_window_over(
    lite_window: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    win = lite_window("hello")
    seen: list[Any] = []
    monkeypatch.setattr(command_key_hosts, "lite_what_can_i_say_here", seen.append)
    win.cmd_what_can_i_say_here()
    assert seen == [win]


def test_the_two_rows_have_quills_keys() -> None:
    keys = {handler: key for _menu, _label, key, handler, _kind in COMMANDS}
    assert keys["cmd_command_key"] == "F11"
    assert keys["cmd_what_can_i_say_here"] == "Ctrl+Alt+Shift+F1"
    assert keys["cmd_dictation_command"] == ""  # F11 is commands only now


def test_lite_has_no_command_key_code_of_its_own() -> None:
    """The second implementation is how the parity rule gets broken quietly."""
    from pathlib import Path

    apps = Path(__file__).resolve().parents[3] / "quill" / "apps"
    for path in apps.glob("lite*.py"):
        text = path.read_text(encoding="utf-8")
        assert "CommandKeySession(" not in text, path.name
        assert "from quill.core.command_catalogue.policy" not in text, path.name


def test_the_lite_host_reads_dimmed_rows_and_the_live_registry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Item:
        def __init__(self, enabled: bool) -> None:
            self.enabled = enabled

        def IsEnabled(self) -> bool:  # noqa: N802 - wx's name
            return self.enabled

    class _Registry:
        def get(self, command_id: str) -> object | None:
            return object() if command_id in {"lite.cmd_save", "lite.cmd_undo"} else None

        def unavailable_reason(self, _command_id: str) -> str:
            return ""

        def keybinding_for(self, command_id: str) -> str:
            return "Ctrl+S" if command_id == "lite.cmd_save" else ""

    class _App:
        def command_registry(self, _window: Any) -> _Registry:
            return _Registry()

    class _Window:
        app = _App()
        synced = 0
        _menu_items = {"cmd_undo": _Item(False), "cmd_save": _Item(True)}

        def _sync_enabled_items(self) -> None:
            _Window.synced += 1

        def _announce(self, _text: str) -> None:
            pass

    host = command_key_hosts._lite_host(_Window())
    assert _Window.synced == 1
    assert [(item.spec.id, item.key) for item in host.candidates()] == [("lite.cmd_save", "Ctrl+S")]
    assert [item.spec.id for item in host.elsewhere().unavailable] == ["lite.cmd_undo"]
