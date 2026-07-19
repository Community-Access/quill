"""Deterministic, unit-aware text rendering for QUILL Weather (PRD 6.2, 9.6).

Pure functions that turn a normalized report into the exact strings the UI
shows (and, later, speaks). No wx, no clock, no randomness -- so the Quick
Weather line and every panel are unit-tested character-for-character. Speech
reuses these same strings when the speech phase lands, so text and audio can
never drift apart.
"""

from __future__ import annotations

from quill.core.weather.models import CurrentConditions, WeatherReport
from quill.core.weather.settings import WeatherSettings


def convert_temp(fahrenheit: float | None, unit: str) -> float | None:
    if fahrenheit is None:
        return None
    return round((fahrenheit - 32) * 5 / 9, 1) if unit == "C" else fahrenheit


def convert_wind_mph(mph: float | None, unit: str) -> float | None:
    if mph is None:
        return None
    factor = {"mph": 1.0, "km/h": 1.609344, "kts": 0.868976, "m/s": 0.44704}.get(unit, 1.0)
    return round(mph * factor, 1)


def temp_str(fahrenheit: float | None, settings: WeatherSettings) -> str:
    value = convert_temp(fahrenheit, settings.temperature_unit)
    if value is None:
        return "unknown"
    shown = int(round(value))
    return f"{shown} deg {settings.temperature_unit}"


def wind_str(mph: float | None, direction: str, settings: WeatherSettings) -> str:
    value = convert_wind_mph(mph, settings.wind_unit)
    if value is None:
        return "calm"
    shown = int(round(value))
    if shown == 0:
        return "calm"
    dir_part = f"{direction} " if direction else ""
    return f"{dir_part}{shown} {settings.wind_unit}".strip()


def current_conditions_line(current: CurrentConditions, settings: WeatherSettings) -> str:
    """One readable sentence of current conditions."""
    parts: list[str] = []
    if current.text_description:
        parts.append(current.text_description)
    if current.temperature_f is not None:
        parts.append(temp_str(current.temperature_f, settings))
    if current.wind_speed_mph is not None:
        parts.append(f"wind {wind_str(current.wind_speed_mph, current.wind_direction, settings)}")
    if current.humidity_percent is not None:
        parts.append(f"humidity {int(current.humidity_percent)} percent")
    return ", ".join(parts) if parts else "No current observation available."


def quick_weather_line(report: WeatherReport, settings: WeatherSettings) -> str:
    """The one-line Quick Weather summary (PRD 6.2), composed per the user's
    include-toggles. Deterministic and speech-ready."""
    loc = report.location.resolved_name or report.location.label
    bits: list[str] = [f"{loc}."]
    current = report.current
    if current and current.temperature_f is not None:
        lead = temp_str(current.temperature_f, settings)
        if current.text_description:
            lead += f" and {current.text_description.lower()}"
        bits.append(lead + ".")
    if settings.quick_include_wind and current and current.wind_speed_mph:
        bits.append(f"Wind {wind_str(current.wind_speed_mph, current.wind_direction, settings)}.")
    if settings.quick_include_humidity and current and current.humidity_percent is not None:
        bits.append(f"Humidity {int(current.humidity_percent)} percent.")
    if settings.quick_include_alert_count:
        n = report.active_alert_count
        if n == 0:
            bits.append("No active alerts.")
        else:
            top = report.alerts[0].event
            bits.append(f"{n} active alert{'' if n == 1 else 's'}; highest is {top}.")
    return " ".join(bits)


def filtered_alerts(report: WeatherReport, settings: WeatherSettings) -> list:
    """The report's alerts passing the user's severity floor and mute list,
    still sorted most-severe first."""
    return [a for a in report.alerts if settings.alert_passes(a.severity, a.event)]
