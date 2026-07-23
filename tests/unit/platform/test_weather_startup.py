"""Quill Weather Windows autostart helper. The registry writes are Windows-only;
off Windows every function is a safe no-op, which is what these assert. The
command shape (its own value name + the --tray flag) is checked directly."""

from __future__ import annotations

import sys

from quill.platform.windows import weather_startup


def test_launch_command_uses_this_executable_and_tray_flag() -> None:
    cmd = weather_startup.launch_command()
    assert sys.executable in cmd
    assert cmd.strip().endswith("--tray")
    assert cmd.startswith('"')  # the exe path is quoted


def test_distinct_value_name_from_main_quill() -> None:
    from quill.platform.windows import startup as main_startup

    # Must not collide with QUILL's own autostart entry.
    assert weather_startup._VALUE_NAME != main_startup._VALUE_NAME
    assert weather_startup._VALUE_NAME == "QuillWeather"


def test_no_ops_and_never_raise_off_windows() -> None:
    if weather_startup.is_windows():
        # On a real Windows box we don't want the test mutating the registry;
        # just confirm the query path returns a bool without raising.
        assert isinstance(weather_startup.is_launch_at_startup_enabled(), bool)
        return
    # Off Windows: enabling reports False and nothing raises.
    weather_startup.set_launch_at_startup(True)
    assert weather_startup.is_launch_at_startup_enabled() is False
    weather_startup.set_launch_at_startup(False)  # idempotent no-op
