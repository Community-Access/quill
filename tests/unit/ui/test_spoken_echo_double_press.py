"""Behaviour of the Spoken Echo capture + double-press shortcut.

These exercise the two MainFrame methods in isolation (bound onto a light stub)
so the logic is covered without standing up a full wx frame.
"""

from __future__ import annotations

from types import SimpleNamespace

from quill.ui.main_frame import MainFrame


class _Stub:
    _ECHO_DOUBLE_PRESS_COMMANDS = MainFrame._ECHO_DOUBLE_PRESS_COMMANDS
    _ECHO_DOUBLE_PRESS_WINDOW = MainFrame._ECHO_DOUBLE_PRESS_WINDOW
    _record_spoken = MainFrame._record_spoken
    _maybe_echo_on_double_press = MainFrame._maybe_echo_on_double_press

    def __init__(self, *, enabled: bool = True) -> None:
        self.settings = SimpleNamespace(spoken_echo_on_double_press=enabled)
        self.echo_calls = 0

    def show_spoken_echo(self) -> None:
        self.echo_calls += 1


def test_record_spoken_populates_history_lazily() -> None:
    stub = _Stub()
    assert getattr(stub, "_spoken_echo_history", None) is None
    stub._record_spoken("Saved")
    stub._record_spoken("Saved")  # consecutive dup dropped
    stub._record_spoken("Modified")
    assert list(stub._spoken_echo_history) == ["Saved", "Modified"]


def test_double_press_opens_echo_for_informational_command() -> None:
    stub = _Stub()
    cmd = "format.describe_formatting"
    assert stub._maybe_echo_on_double_press(cmd) is False  # first press runs normally
    assert stub.echo_calls == 0
    assert stub._maybe_echo_on_double_press(cmd) is True  # rapid second press -> echo
    assert stub.echo_calls == 1
    # Third press re-runs the command (returns False) rather than re-opening.
    assert stub._maybe_echo_on_double_press(cmd) is False
    assert stub.echo_calls == 1


def test_double_press_ignored_for_non_informational_command() -> None:
    stub = _Stub()
    assert stub._maybe_echo_on_double_press("file.save") is False
    assert stub._maybe_echo_on_double_press("file.save") is False
    assert stub.echo_calls == 0


def test_double_press_respects_setting_off() -> None:
    stub = _Stub(enabled=False)
    cmd = "document.summary"
    assert stub._maybe_echo_on_double_press(cmd) is False
    assert stub._maybe_echo_on_double_press(cmd) is False
    assert stub.echo_calls == 0


def test_slow_second_press_is_not_a_double_press() -> None:
    stub = _Stub()
    cmd = "view.announce_contrast"
    stub._maybe_echo_on_double_press(cmd)
    # Simulate the first press happening well outside the window.
    stub._last_echo_command_at -= 5.0
    assert stub._maybe_echo_on_double_press(cmd) is False
    assert stub.echo_calls == 0
