"""Check What QUILL Says: EdSharp's testSay (complete.md Part 4)."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.say_check import SAY_CHECK_COMMANDS, SayCheckRow, say_check_report
from quill.ui.main_frame_say_check import SayCheckMixin


def test_the_report_has_a_row_per_press_and_a_column_to_fill_in() -> None:
    text = say_check_report(
        [SayCheckRow("Say Time and Date", "Ctrl+Shift+T", ("9:30",), ("9:30", "Tuesday"))],
        reader="NVDA",
    )
    assert "(NVDA)" in text
    assert "| Say Time and Date | Ctrl+Shift+T | Once | 9:30 |  |  |" in text
    assert "| Say Time and Date | Ctrl+Shift+T | Twice | 9:30 / Tuesday |  |  |" in text
    assert "Your screen reader said" in text


def test_nothing_said_and_pipes_are_safe_in_the_table() -> None:
    text = say_check_report([SayCheckRow("X", "", (), ("a | b\nc",))])
    assert "| X | (no key) | Once | (nothing) |" in text
    assert "a \\| b c" in text


def test_each_command_is_run_twice_with_speech_and_windows_captured() -> None:
    runs: list[str] = []

    class Host(SayCheckMixin):
        def __init__(self) -> None:
            self.spoken: list[str] = []
            self.opened: list[str] = []
            self._announce = self.spoken.append
            self._show_modal_dialog = lambda *_a, **_k: 0

    host = Host()

    def run(command_id: str) -> None:
        runs.append(command_id)
        if command_id == "navigate.say_time":
            host._announce("9:30")
        else:
            host._show_modal_dialog(object(), "Windows Open")

    known = {"navigate.say_time": "Say Time", "window.say_windows_open": "Say Windows Open"}
    host.commands = SimpleNamespace(
        get=lambda cid: SimpleNamespace(title=known[cid], keybinding="") if cid in known else None,
        run=run,
    )
    out: list[tuple[str, str]] = []
    host._power_tools_open_text_in_new_buffer = lambda text, status: out.append((text, status))  # type: ignore[attr-defined]
    host._say_check_reader = lambda: ""  # type: ignore[method-assign]
    host.run_say_check()
    assert runs == ["navigate.say_time"] * 2 + ["window.say_windows_open"] * 2
    text, status = out[0]
    assert "| Say Time |  | Once | 9:30 |" not in text  # no key shows as (no key)
    assert "| Say Time | (no key) | Twice | 9:30 |" in text
    assert "(opens the Windows Open window)" in text
    assert status == "Checked what QUILL says for 2 commands"
    assert host.spoken == []  # nothing reached real speech during the run
    assert set(known) <= set(SAY_CHECK_COMMANDS)
    _unused: Any = None
