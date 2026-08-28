"""Quill Weather's Options menu: the four switches, and what each one says.

Extracted from ``quill/apps/weather.py`` under GATE-11 (extract, never
rebaseline). They are one family: every one of them is a persisted preference
that has to be **reflected back** as well as set, because two of them can
silently refuse -- a locked-down registry can decline the startup entry, and a
machine without the Windows scheduler cannot register the background check. A
menu tick that showed what you asked for rather than what happened would be
the app telling you something it does not know.
"""

from __future__ import annotations

from typing import Any

#: What each preference says when it is turned on, and when it is turned off.
_SAID: dict[str, tuple[str, str]] = {
    "app_start_in_tray": (
        "Quill Weather will start minimized to the tray.",
        "Quill Weather will start with its window open.",
    ),
    "app_close_to_tray": (
        "Closing the window will keep monitoring in the tray.",
        "Closing the window will exit Quill Weather.",
    ),
}


def _check_menu_item(host: Any, item_id: Any, state: bool) -> None:
    menu_bar = host.frame.GetMenuBar()
    if menu_bar is None:
        return
    item = menu_bar.FindItemById(item_id)
    if item is not None:
        item.Check(state)


def set_launch_at_startup(host: Any, enabled: bool) -> None:
    """Add or remove the per-user sign-in entry, and say what actually took."""
    from quill.platform.windows import weather_startup

    weather_startup.set_launch_at_startup(enabled)
    actual = weather_startup.is_launch_at_startup_enabled()
    _check_menu_item(host, host._startup_item_id, actual)
    host._announce(
        "Quill Weather will start with Windows."
        if actual
        else "Quill Weather will not start with Windows."
    )


def set_app_pref(host: Any, field: str, value: bool) -> None:
    """Persist one boolean app preference and say what it now means."""
    from quill.core.weather import settings as settings_mod

    data_dir = host._weather_data_dir()
    settings = settings_mod.load_settings(data_dir)
    setattr(settings, field, value)
    settings_mod.save_settings(data_dir, settings)
    on, off = _SAID.get(field, ("Setting saved.", "Setting saved."))
    host._announce(on if value else off)


def set_background_check(host: Any, enabled: bool) -> None:
    """Register or remove the OS scheduled task that checks alerts even when
    Quill Weather is not running. The cadence follows the monitor interval."""
    from quill.core.weather import monitor
    from quill.platform.windows import scheduled_task

    if not scheduled_task.is_windows():
        host._announce("Background alert checks need Windows.")
        reflect_background_check(host)
        return
    if enabled:
        interval = monitor.load_config(host._weather_data_dir()).interval_minutes
        scheduled_task.register(interval)
    else:
        scheduled_task.unregister()
    actual = scheduled_task.is_registered()
    reflect_background_check(host, actual)
    host._announce(
        "Quill Weather will check for alerts in the background, even when closed."
        if actual
        else "Background alert checks are off."
    )


def reflect_background_check(host: Any, checked: bool | None = None) -> None:
    """Tick the menu item to match what the scheduler actually holds."""
    from quill.platform.windows import scheduled_task

    state = scheduled_task.is_registered() if checked is None else checked
    _check_menu_item(host, host._background_item_id, state)
