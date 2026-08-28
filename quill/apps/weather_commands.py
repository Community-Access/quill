"""Quill Weather's commands, by name: the palette table, and the tutorials' door.

Weather drove its whole menu from bound menu items and had no command ids at
all, which cost it two things. The **Command Palette** -- which every app in
the family carries -- could not reach a single weather verb, so the one surface
built for "do a thing by name" was the one surface that could not do the thing
this app is for. And a **tutorial step could not name a verb**, because a step
names a command and there were none; every lesson would have had to hard-code a
key and go stale the first time somebody rebound one.

The ids are registered with the keys the menu labels already advertise
(``APP_KEYMAPS["weather"]``), so nothing about the menus changes. They simply
have names now.
"""

from __future__ import annotations

from typing import Any


def register_weather_commands(host: Any) -> None:
    """Put every Weather verb in the app's command palette."""
    for command_id, title, handler in (
        ("weather.now", "Weather: Weather Now...", host.open_weather_center),
        ("weather.quick", "Weather: Quick Weather", host.weather_quick),
        (
            "weather.alerts",
            "Weather: Active Alerts...",
            lambda: host.open_weather_center(focus_alerts=True),
        ),
        ("weather.add_location", "Weather: Add Location...", host.open_weather_add_location),
        ("weather.settings", "Weather: Settings...", host.open_weather_settings),
        ("weather.test_alert", "Weather: Test Alert", host.weather_test_alert),
        (
            "weather.monitor_toggle",
            "Weather: Start or Stop Weather Monitoring",
            host.toggle_weather_monitoring,
        ),
        (
            "weather.monitor_pause",
            "Weather: Pause or Resume Alert Checks",
            host.toggle_weather_monitoring_pause,
        ),
        ("weather.tutorials", "Weather: Tutorials...", host.open_weather_tutorials),
    ):
        host.commands.try_register(
            command_id, title, handler, host._binding_for(command_id), feature_id="core.weather"
        )
    # The NOAA rows exist only where the radio half is installed and enabled,
    # which is the same condition their menu items are built under.
    if getattr(host, "listen_local_noaa_radio", None) is None:
        return
    for command_id, title, handler in (
        (
            "weather.noaa_listen",
            "Weather: Listen to your Local NOAA Weather Radio",
            host.listen_local_noaa_radio,
        ),
        (
            "weather.noaa_update",
            "Weather: Update NOAA Weather Radio Directory",
            host.update_noaa_radio_directory,
        ),
    ):
        host.commands.try_register(
            command_id, title, handler, host._binding_for(command_id), feature_id="core.weather"
        )
