"""Quill Weather's own answers to "did you do the step?".

The shared half -- peer windows, the probe protocol, the never-guess rule --
is :mod:`quill.ui.tutorial_checks`. Weather's own questions are few, because
Weather is a small app with one serious job: did a place get added, and is the
watch running?

Both are read from the live app rather than from a keystroke, so adding a
place through the menu, the button or the palette all count, and starting the
watch from the tray counts exactly as much as starting it from the menu.
"""

from __future__ import annotations

from typing import Any

_CHECKS: dict[str, str] = {
    "location-added": "your saved places grew",
    "monitoring-on": "the watch is running",
    "monitoring-off": "the watch is stopped",
    "monitoring-paused": "alert checks are paused",
}


def _location_count(host: Any) -> int | None:
    """How many places are saved, or None when it cannot be read."""
    try:
        from quill.core.weather import locations as locations_mod

        store = locations_mod.load_locations(host._weather_data_dir())
        return len(store.locations)
    except Exception:  # noqa: BLE001 - an unreadable store is "cannot tell", not a failure
        return None


def _monitoring(host: Any) -> bool | None:
    checker = getattr(host, "_weather_monitoring_active", None)
    if not callable(checker):
        return None
    try:
        return bool(checker())
    except Exception:  # noqa: BLE001 - see above
        return None


def _paused(host: Any) -> bool | None:
    value = getattr(host, "_weather_monitor_paused", None)
    return bool(value) if isinstance(value, bool) else None


class WeatherProbe:
    """Weather's :class:`~quill.ui.tutorial_checks.CheckProbe`."""

    def known(self) -> frozenset[str]:
        return frozenset(_CHECKS)

    def snapshot(self, host: Any) -> dict[str, Any]:
        return {
            "locations": _location_count(host),
            "monitoring": _monitoring(host),
            "paused": _paused(host),
        }

    def answer(self, check: str, host: Any, baseline: dict[str, Any]) -> tuple[bool, str] | None:
        if check not in _CHECKS:
            return None
        said = _CHECKS[check]
        if check == "location-added":
            before, now = baseline.get("locations"), _location_count(host)
            return (before is not None and now is not None and now > before, said)
        if check == "monitoring-on":
            return (_monitoring(host) is True, said)
        if check == "monitoring-off":
            return (_monitoring(host) is False, said)
        # monitoring-paused
        return (_paused(host) is True, said)


#: The one instance; it holds no state of its own.
PROBE = WeatherProbe()
