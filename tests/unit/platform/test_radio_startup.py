"""Quill Radio Windows autostart helper: command shape, a distinct Run-key
value from QUILL's own and Quill Weather's, and safe no-ops off Windows."""

from __future__ import annotations

import sys

from quill.platform.windows import radio_startup


def test_launch_command_is_this_executable_quoted() -> None:
    cmd = radio_startup.launch_command()
    assert sys.executable in cmd
    assert cmd.startswith('"') and cmd.rstrip().endswith('"')
    assert "--tray" not in cmd  # Radio launches to its normal window, not the tray


def test_distinct_value_names_across_apps() -> None:
    from quill.platform.windows import startup as quill_startup
    from quill.platform.windows import weather_startup

    names = {
        radio_startup._VALUE_NAME,
        weather_startup._VALUE_NAME,
        quill_startup._VALUE_NAME,
    }
    assert len(names) == 3  # no collisions between the three sibling autostarts
    assert radio_startup._VALUE_NAME == "QuillRadio"


def test_no_ops_and_never_raise_off_windows() -> None:
    if radio_startup.is_windows():
        assert isinstance(radio_startup.is_launch_at_startup_enabled(), bool)
        return
    radio_startup.set_launch_at_startup(True)
    assert radio_startup.is_launch_at_startup_enabled() is False
    radio_startup.set_launch_at_startup(False)
