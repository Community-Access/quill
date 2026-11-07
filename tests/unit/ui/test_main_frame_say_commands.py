"""QUILL's half of the Say commands: rows and hooks, never a command of its own.

The handlers are ``quill.ui.say_commands``'s, the same ones QUILL Lite's table
names. What is checked here is what keeps it that way: this adapter defines no
``cmd_*``, every row it places is a QUILL Lite command on the same key, and the
hooks QUILL answers differently answer the way the shared handlers expect.
"""

from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

from quill.core.keymap import DEFAULT_KEYMAP
from quill.core.lite.commands import COMMANDS
from quill.core.lite.parity import COMMAND_EQUIVALENTS
from quill.ui import main_frame_say_commands as adapter
from quill.ui.main_frame_say_commands import SAY_ROWS, SayCommandsAdapterMixin

_SOURCE = Path(adapter.__file__)


def test_the_adapter_defines_no_command_of_its_own() -> None:
    tree = ast.parse(_SOURCE.read_text(encoding="utf-8"))
    defined = [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("cmd_")
    ]
    assert defined == []


def test_every_row_is_a_lite_command_on_the_same_key() -> None:
    lite_keys = {handler: key for _menu, _label, key, handler, _kind in COMMANDS if handler}
    for rows in SAY_ROWS.values():
        for command_id, _label, handler in rows:
            assert hasattr(SayCommandsAdapterMixin, handler), handler
            assert COMMAND_EQUIVALENTS[handler] == command_id
            assert DEFAULT_KEYMAP[command_id] == lite_keys[handler], command_id


class _Host(SayCommandsAdapterMixin):
    def __init__(self) -> None:
        self.said: list[tuple[str, bool]] = []
        tab = SimpleNamespace
        self._document_tabs = [
            tab(document=SimpleNamespace(name="one.md")),
            tab(document=SimpleNamespace(name="two.txt")),
        ]
        self._active_tab_index = 1

    def _announce(self, message: str, *, force: bool = False, sound: str = "") -> None:
        self.said.append((message, force))


def test_speech_is_forced_so_a_second_answer_is_never_collapsed() -> None:
    host = _Host()
    host._say_result("2:05 PM")
    assert host.said == [("2:05 PM", True)]


def test_the_documents_are_the_tabs_with_the_active_one_current() -> None:
    assert _Host()._say_open_documents() == (["one.md", "two.txt"], 1)


def test_say_windows_open_speaks_through_quill(monkeypatch) -> None:
    from quill.ui import say_commands

    now = [5.0]
    monkeypatch.setattr(say_commands, "time", SimpleNamespace(monotonic=lambda: now[0]))
    host = _Host()
    host.cmd_say_windows_open()
    now[0] += 0.2
    host.cmd_say_windows_open()
    assert [message for message, _ in host.said] == [
        "2 documents open",
        "2 documents: one.md, two.txt (current)",
    ]


def test_the_log_is_in_quills_own_data_folder() -> None:
    from quill.core.paths import app_data_dir

    assert _Host()._say_log_dir() == app_data_dir() / "logs"
