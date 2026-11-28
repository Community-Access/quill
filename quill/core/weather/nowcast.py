"""The next few hours, in words: a four-hour glance ahead and the change in
daylight since yesterday.

Both come from **one** Open-Meteo forecast request (:func:`fetch`):

* ``hourly`` for the next four hours -- the glance ahead: the temperature now
  and where it is heading, any change in the sky, the highest chance of
  precipitation, and the strongest wind when it is notable.
* ``daily`` ``daylight_duration`` for yesterday and today -- "8 hours 51
  minutes of daylight today, 2 minutes less than yesterday."

Units are asked for in the user's units. Pure parsing and wording are separate
from the one fetch, so all of it is testable without a network. wx-free and
strict-typed.
"""

from __future__ import annotations

import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from quill.core.weather.open_meteo import format_time, weather_code_text

GetJson = Callable[..., Any]

GLANCE_HOURS = 4


@dataclass(slots=True)
class Hour:
    time: str
    temperature: float | None
    precip_chance: int | None
    code: int | None
    wind: float | None


@dataclass(slots=True)
class Nowcast:
    current_time: str = ""
    hours: list[Hour] = field(default_factory=list)
    daylight_yesterday: float | None = None
    daylight_today: float | None = None
    metric: bool = False


def request_url(latitude: float, longitude: float, *, unit: str) -> str:
    metric = unit == "C"
    params: dict[str, Any] = {
        "latitude": f"{latitude:.4f}",
        "longitude": f"{longitude:.4f}",
        "current": "temperature_2m",
        "hourly": "temperature_2m,precipitation_probability,weather_code,wind_speed_10m",
        "forecast_hours": GLANCE_HOURS + 1,
        "past_hours": 0,
        "daily": "daylight_duration",
        "past_days": 1,
        "forecast_days": 1,
        "timezone": "auto",
        "temperature_unit": "celsius" if metric else "fahrenheit",
        "wind_speed_unit": "kmh" if metric else "mph",
    }
    return "https://api.open-meteo.com/v1/forecast?" + urllib.parse.urlencode(params)


def _at(values: Any, index: int) -> float | None:
    if isinstance(values, list) and index < len(values):
        value = values[index]
        if isinstance(value, int | float) and not isinstance(value, bool):
            return float(value)
    return None


def parse(data: Any, *, unit: str) -> Nowcast:
    """Parse the one forecast reply into a Nowcast (pure)."""
    cast = Nowcast(metric=unit == "C")
    if not isinstance(data, dict):
        return cast
    current = data.get("current")
    if isinstance(current, dict):
        cast.current_time = str(current.get("time", ""))
    hourly = data.get("hourly")
    if isinstance(hourly, dict):
        for i, when in enumerate(hourly.get("time") or []):
            when = str(when)
            if cast.current_time and when[:13] <= cast.current_time[:13]:
                continue  # the hour already under way
            code = _at(hourly.get("weather_code"), i)
            chance = _at(hourly.get("precipitation_probability"), i)
            cast.hours.append(
                Hour(
                    time=when,
                    temperature=_at(hourly.get("temperature_2m"), i),
                    precip_chance=round(chance) if chance is not None else None,
                    code=round(code) if code is not None else None,
                    wind=_at(hourly.get("wind_speed_10m"), i),
                )
            )
        cast.hours = cast.hours[:GLANCE_HOURS]
    daily = data.get("daily")
    if isinstance(daily, dict):
        lengths = daily.get("daylight_duration") or []
        cast.daylight_yesterday = _at(lengths, 0)
        cast.daylight_today = _at(lengths, 1)
    return cast


def fetch(
    latitude: float, longitude: float, *, unit: str = "F", get: GetJson | None = None
) -> Nowcast:
    """The one request. Raises the transport's errors (``HTTP_ERRORS``)."""
    if get is None:
        from quill.core.weather.open_meteo_limits import get_json

        get = get_json
    return parse(get(request_url(latitude, longitude, unit=unit)), unit=unit)


# -- words -----------------------------------------------------------------------


def _duration(seconds: float) -> str:
    total = round(seconds / 60)
    hours, minutes = divmod(total, 60)
    out = f"{hours} hour{'s' if hours != 1 else ''}"
    if minutes:
        out += f" {minutes} minute{'s' if minutes != 1 else ''}"
    return out


def daylight_text(cast: Nowcast) -> str:
    """'10 hours 15 minutes of daylight today, 2 minutes less than yesterday.'"""
    today, yesterday = cast.daylight_today, cast.daylight_yesterday
    if today is None:
        return ""
    lead = f"{_duration(today)} of daylight today"
    if yesterday is None:
        return lead + "."
    diff = today - yesterday
    if abs(diff) < 30:
        return f"{lead}, about the same as yesterday."
    minutes = round(abs(diff) / 60)
    amount = f"{minutes} minute{'s' if minutes != 1 else ''}"
    return f"{lead}, {amount} {'more' if diff > 0 else 'less'} than yesterday."


def _hour(iso: str) -> str:
    """'2026-11-27T17:00' -> '5 PM' (hourly data is always on the hour, and
    some synthesizers read ':00' as 'oh oh')."""
    return format_time(iso).replace(":00 ", " ")


def glance_text(cast: Nowcast, *, wind_word: str = "miles per hour") -> str:
    """The next four hours in two or three sentences, the first hour as 'now'."""
    hours = [h for h in cast.hours if h.temperature is not None]
    if not hours:
        return ""
    first, last = hours[0], hours[-1]
    t0, t1 = round(first.temperature or 0), round(last.temperature or 0)
    lead = f"Through {_hour(last.time)}"
    if t1 == t0:
        temps = f"{lead}: steady near {t0}."
    else:
        verb = "rising" if t1 > t0 else "falling"
        temps = f"{lead}: {t0} now, {verb} to {t1}."
    parts = [temps]
    changes: list[str] = []
    previous = ""
    for h in hours:
        sky = weather_code_text(h.code) if h.code is not None else ""
        if sky and sky != previous:
            when = "now" if h is first else f"from {_hour(h.time)}"
            changes.append(f"{sky.lower()} {when}")
            previous = sky
    if changes:
        parts.append(f"Sky: {', then '.join(changes)}.")
    chances = [h.precip_chance for h in hours if h.precip_chance is not None]
    if chances and max(chances) >= 20:
        parts.append(f"Chance of precipitation up to {max(chances)} percent.")
    winds = [h.wind for h in hours if h.wind is not None]
    if winds and max(winds) >= 15:
        parts.append(f"Wind up to {round(max(winds))} {wind_word}.")
    return " ".join(parts)
