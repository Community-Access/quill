"""Weather Around Me: a spoken stand-in for radar.

Radar is a picture. What a listener wants from it is a sentence: "Rain 30
miles west, moving toward you." So Quill Weather samples the current weather
at the eight compass points on two rings around the place (about 25 and 50
miles out) plus the place itself -- seventeen points in **one** multi-location
Open-Meteo request -- and turns each wet point into a line, with the wind at
that point used to judge which way the rain or snow is heading.

Surface wind is only a rough guide to how a storm moves, so the report says so
once. Movement within 45 degrees of straight at the place is "moving toward
you"; within 45 degrees of straight away is "moving away"; anything else is
named by its heading.

wx-free and strict-typed; the transport is passed in for tests.
"""

from __future__ import annotations

import math
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from quill.core.weather import open_meteo

GetJson = Callable[..., Any]

BEARINGS = (0, 45, 90, 135, 180, 225, 270, 315)
#: Ring radii in kilometres (about 25 and 50 miles).
RINGS_KM = (40.0, 80.0)
_WET_CODES = frozenset(range(51, 100))
_EARTH_KM = 6371.0
#: Below this wind (km/h) a shower is said to be barely moving.
_STILL_KMH = 6.0
CAVEAT = "Movement is judged from the wind at each place, so treat it as a rough guide."


compass_name = open_meteo.compass_name  # one spelling of the eight points


def offset(latitude: float, longitude: float, bearing: float, km: float) -> tuple[float, float]:
    """The point ``km`` away on ``bearing`` (degrees from north), great-circle."""
    lat1, lon1, b = math.radians(latitude), math.radians(longitude), math.radians(bearing)
    d = km / _EARTH_KM
    lat2 = math.asin(math.sin(lat1) * math.cos(d) + math.cos(lat1) * math.sin(d) * math.cos(b))
    lon2 = lon1 + math.atan2(
        math.sin(b) * math.sin(d) * math.cos(lat1), math.cos(d) - math.sin(lat1) * math.sin(lat2)
    )
    return math.degrees(lat2), (math.degrees(lon2) + 540) % 360 - 180


@dataclass(slots=True)
class Sample:
    bearing: float | None  # None for the place itself
    km: float
    precipitation: float  # mm in the last 15 minutes
    snowfall: float
    code: int | None
    wind_kmh: float | None
    wind_from: float | None  # degrees the wind blows FROM

    @property
    def wet(self) -> bool:
        return self.precipitation > 0 or self.snowfall > 0 or (self.code or 0) in _WET_CODES


def points(latitude: float, longitude: float) -> list[tuple[float | None, float, float, float]]:
    """(bearing, km, lat, lon) for the place and every ring point."""
    out: list[tuple[float | None, float, float, float]] = [(None, 0.0, latitude, longitude)]
    for km in RINGS_KM:
        for bearing in BEARINGS:
            lat, lon = offset(latitude, longitude, bearing, km)
            out.append((float(bearing), km, lat, lon))
    return out


def request_url(latitude: float, longitude: float) -> tuple[str, int]:
    """The one multi-location request, and how many calls Open-Meteo counts it as."""
    spots = points(latitude, longitude)
    query = urllib.parse.urlencode({
        "latitude": ",".join(f"{p[2]:.4f}" for p in spots),
        "longitude": ",".join(f"{p[3]:.4f}" for p in spots),
        "current": "precipitation,snowfall,weather_code,wind_speed_10m,wind_direction_10m",
        "wind_speed_unit": "kmh",
        "timezone": "auto",
    })
    return "https://api.open-meteo.com/v1/forecast?" + query, len(spots)


def _num(block: dict[str, Any], key: str) -> float | None:
    value = block.get(key)
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    return None


def parse(data: Any, latitude: float, longitude: float) -> list[Sample]:
    """Pair each reply with its point. Open-Meteo returns a list in request order
    for several places (and a single object for one)."""
    replies = data if isinstance(data, list) else [data]
    samples: list[Sample] = []
    for spot, reply in zip(points(latitude, longitude), replies, strict=False):
        current = reply.get("current") if isinstance(reply, dict) else None
        if not isinstance(current, dict):
            continue
        code = _num(current, "weather_code")
        samples.append(
            Sample(
                bearing=spot[0],
                km=spot[1],
                precipitation=_num(current, "precipitation") or 0.0,
                snowfall=_num(current, "snowfall") or 0.0,
                code=round(code) if code is not None else None,
                wind_kmh=_num(current, "wind_speed_10m"),
                wind_from=_num(current, "wind_direction_10m"),
            )
        )
    return samples


def _what(sample: Sample) -> str:
    code = sample.code or 0
    if code >= 95:
        return "Thunderstorms"
    if sample.snowfall > 0 or code in (71, 73, 75, 77, 85, 86):
        return "Snow"
    if 51 <= code <= 57:
        return "Drizzle"
    if code in (66, 67):
        return "Freezing rain"
    if 80 <= code <= 82:
        return "Showers"
    return "Rain"


def _angle(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def movement(sample: Sample) -> str:
    """'moving toward you', 'moving away', 'moving northeast', or 'barely moving'."""
    if sample.bearing is None or sample.wind_from is None:
        return ""
    if sample.wind_kmh is not None and sample.wind_kmh < _STILL_KMH:
        return "barely moving"
    heading = (sample.wind_from + 180) % 360  # it travels downwind
    toward_place = (sample.bearing + 180) % 360
    off = _angle(heading, toward_place)
    if off <= 45:
        return "moving toward you"
    if off >= 135:
        return "moving away"
    return f"moving {compass_name(heading)}"


def distance_words(km: float, metric: bool) -> str:
    return f"{round(km)} kilometres" if metric else f"{round(km / 1.609344 / 5) * 5} miles"


def describe(samples: list[Sample], *, metric: bool = False) -> list[str]:
    """The report's lines: here first, then each direction's nearest wet point,
    the ones heading this way first."""
    here = next((s for s in samples if s.bearing is None), None)
    lines: list[str] = []
    if here is not None:
        lines.append(f"{_what(here)} here now." if here.wet else "Dry here now.")
    nearest: dict[float, Sample] = {}
    for s in samples:
        if s.bearing is None or not s.wet:
            continue
        if s.bearing not in nearest or s.km < nearest[s.bearing].km:
            nearest[s.bearing] = s
    if not nearest:
        reach = distance_words(max(RINGS_KM), metric)
        lines.append(f"No rain or snow within about {reach} in any direction.")
        return lines
    found = sorted(
        nearest.values(), key=lambda s: (movement(s) != "moving toward you", s.km, s.bearing)
    )
    for s in found:
        line = f"{_what(s)} {distance_words(s.km, metric)} {compass_name(s.bearing or 0)}"
        moving = movement(s)
        lines.append(f"{line}, {moving}." if moving else f"{line}.")
    dry = [compass_name(b) for b in BEARINGS if b not in nearest]
    if len(dry) >= 4:
        lines.append("Dry in every other direction.")  # a long list buries the news
    elif dry:
        named = dry[0] if len(dry) == 1 else f"{', '.join(dry[:-1])} and {dry[-1]}"
        lines.append(f"Dry to the {named}.")
    lines.append(CAVEAT)
    return lines


def fetch(latitude: float, longitude: float, *, get: GetJson | None = None) -> list[Sample]:
    if get is None:
        from quill.core.weather.open_meteo_limits import get_json

        get = get_json
    url, weight = request_url(latitude, longitude)
    return parse(get(url, weight=weight), latitude, longitude)
