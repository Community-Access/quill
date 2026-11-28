"""US station records and 1991-2020 normals from NOAA's Regional Climate
Centers (RCC-ACIS, ``data.rcc-acis.org``) -- keyless, public US government data.

Reanalysis (ERA5) is a model's best estimate on a grid; a record high is a
thermometer reading at a real station, often going back to the 1800s. So for US
places Weather History asks ACIS for three things:

* **The nearest good station** (``StnMeta``): one still reporting, with a long
  daily record of high, low and precipitation. Chosen once a year per place.
* **The 1991-2020 normals** for a calendar day (``StnData`` with ``normal``).
* **The records** for a calendar day (``StnData``, one value per year on that
  date, reduced to the extreme and the year it happened).

Requests are GETs with ACIS's ``params`` query (so they go through the one
weather egress chokepoint, ``_http.http_json``). Values come back in degrees
Fahrenheit and inches; ``M`` is missing and ``T`` is a trace. They are stored
in metric, like everything else in the history cache.

wx-free and strict-typed; the transport is passed in for tests.
"""

from __future__ import annotations

import json
import math
import urllib.parse
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from quill.core.weather._http import http_json

_BASE = "https://data.rcc-acis.org"
#: A station must have reported within this many days to count as current.
_CURRENT_WITHIN_DAYS = 45
#: Search boxes, in degrees, tried in turn until a station is found.
_SEARCH_BOXES = (0.35, 0.8)
TRACE_INCHES = 0.001
_COMPASS = frozenset("N NNE NE ENE E ESE SE SSE S SSW SW WSW W WNW NW NNW".split())

GetJson = Callable[[str], Any]


def is_us(latitude: float, longitude: float) -> bool:
    """A generous box around the US states and territories ACIS covers."""
    conus = 24.0 <= latitude <= 50.0 and -125.5 <= longitude <= -66.0
    alaska = 51.0 <= latitude <= 72.0 and (-180.0 <= longitude <= -129.0 or longitude >= 172.0)
    hawaii = 18.5 <= latitude <= 22.5 and -161.0 <= longitude <= -154.5
    islands = 17.5 <= latitude <= 18.7 and -67.5 <= longitude <= -64.5  # PR, USVI
    return conus or alaska or hawaii or islands


def _url(endpoint: str, params: dict[str, Any]) -> str:
    return f"{_BASE}/{endpoint}?" + urllib.parse.urlencode({
        "params": json.dumps(params, separators=(",", ":"))
    })


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance (haversine)."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371.0 * 2 * math.asin(math.sqrt(min(1.0, a)))


@dataclass(slots=True)
class Station:
    sid: str
    name: str
    latitude: float
    longitude: float
    first_year: int
    distance_km: float

    def to_json(self) -> dict[str, Any]:
        return {
            "sid": self.sid,
            "name": self.name,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "first_year": self.first_year,
            "distance_km": round(self.distance_km, 1),
        }

    @classmethod
    def from_json(cls, raw: dict[str, Any]) -> Station | None:
        try:
            return cls(
                sid=str(raw["sid"]),
                name=str(raw.get("name", "")),
                latitude=float(raw["latitude"]),
                longitude=float(raw["longitude"]),
                first_year=int(raw["first_year"]),
                distance_km=float(raw.get("distance_km", 0.0)),
            )
        except (KeyError, TypeError, ValueError):
            return None

    @property
    def display_name(self) -> str:
        """'TUCSON INTERNATIONAL AIRPORT' -> 'Tucson International Airport'."""
        return " ".join(w if w in _COMPASS else w.capitalize() for w in self.name.split())


def _parse_year(value: Any) -> int | None:
    if isinstance(value, str) and len(value) >= 4 and value[:4].isdigit():
        return int(value[:4])
    return None


def stations_from_meta(data: Any, latitude: float, longitude: float, today: date) -> list[Station]:
    """Usable stations from a StnMeta reply, best first.

    Usable means: high, low and precipitation all have a daily record, and all
    three were reported within the last ``_CURRENT_WITHIN_DAYS`` days. Best
    means nearest, with a short record (under 30 years) counted as 40 km
    further away, because a record is only as good as its length.
    """
    meta = data.get("meta") if isinstance(data, dict) else None
    if not isinstance(meta, list):
        return []
    cutoff = (today - timedelta(days=_CURRENT_WITHIN_DAYS)).isoformat()
    scored: list[tuple[float, Station]] = []
    for item in meta:
        if not isinstance(item, dict):
            continue
        ranges = item.get("valid_daterange")
        ll = item.get("ll")
        sids = item.get("sids")
        if not (isinstance(ranges, list) and len(ranges) >= 3 and isinstance(ll, list)):
            continue
        if not isinstance(sids, list) or not sids:
            continue
        starts: list[int] = []
        current = True
        for span in ranges[:3]:
            if not (isinstance(span, list) and len(span) == 2):
                current = False
                break
            year = _parse_year(span[0])
            if year is None or not isinstance(span[1], str) or span[1] < cutoff:
                current = False
                break
            starts.append(year)
        if not current:
            continue
        try:
            lon, lat = float(ll[0]), float(ll[1])
        except (TypeError, ValueError, IndexError):
            continue
        first_year = max(starts)
        sid = str(sids[0]).split(" ")[0]
        km = distance_km(latitude, longitude, lat, lon)
        penalty = 40.0 if today.year - first_year < 30 else 0.0
        station = Station(sid, str(item.get("name", "")), lat, lon, first_year, km)
        scored.append((km + penalty, station))
    scored.sort(key=lambda pair: pair[0])
    return [s for _score, s in scored]


def find_station(
    latitude: float, longitude: float, *, today: date, get: GetJson = http_json
) -> Station | None:
    """The best current station near a US place, or None when there is none."""
    for box in _SEARCH_BOXES:
        west, south = longitude - box, latitude - box
        bbox = f"{west:.3f},{south:.3f},{longitude + box:.3f},{latitude + box:.3f}"
        data = get(
            _url(
                "StnMeta",
                {
                    "bbox": bbox,
                    "elems": "maxt,mint,pcpn",
                    "meta": "name,sids,ll,valid_daterange",
                },
            )
        )
        found = stations_from_meta(data, latitude, longitude, today)
        if found:
            return found[0]
    return None


def _value(raw: Any) -> float | None:
    """ACIS value -> float. 'T' (trace) is a tiny positive amount; 'M' is None."""
    if not isinstance(raw, str):
        return None
    text = raw.strip().rstrip("ASR")  # flags ACIS may append to a value
    if text == "T":
        return TRACE_INCHES
    try:
        return float(text)
    except ValueError:
        return None


def f_to_c(value: float | None) -> float | None:
    return None if value is None else (value - 32.0) * 5.0 / 9.0


def in_to_mm(value: float | None) -> float | None:
    return None if value is None else value * 25.4


def _calendar_date(month: int, day: int, year: int) -> date:
    try:
        return date(year, month, day)
    except ValueError:
        return date(year, 2, 28)


def normals(station: Station, month: int, day: int, *, get: GetJson = http_json) -> dict[str, Any]:
    """The 1991-2020 normal high, low and precipitation for a calendar day, metric."""
    iso = _calendar_date(month, day, 2024).isoformat()  # a leap year, for Feb 29
    data = get(
        _url(
            "StnData",
            {
                "sid": station.sid,
                "sdate": iso,
                "edate": iso,
                "elems": [
                    {"name": "maxt", "normal": "1"},
                    {"name": "mint", "normal": "1"},
                    {"name": "pcpn", "normal": "1"},
                ],
            },
        )
    )
    rows = data.get("data") if isinstance(data, dict) else None
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], list):
        raise ValueError("ACIS normals reply had no data")
    row = rows[0] + [None] * 4
    return {
        "station": station.sid,
        "high_c": f_to_c(_value(row[1])),
        "low_c": f_to_c(_value(row[2])),
        "precip_mm": in_to_mm(_value(row[3])),
    }


#: (key, element, reduce): warmest high, coldest high, warmest low, coldest
#: low, wettest day, snowiest day.
_RECORD_ELEMS = (
    ("warmest_high", "maxt", "max"),
    ("coldest_high", "maxt", "min"),
    ("warmest_low", "mint", "max"),
    ("coldest_low", "mint", "min"),
    ("wettest", "pcpn", "max"),
    ("snowiest", "snow", "max"),
)


def last_completed(month: int, day: int, today: date) -> date:
    """The most recent occurrence of the calendar day strictly before today."""
    this_year = _calendar_date(month, day, today.year)
    return this_year if this_year < today else _calendar_date(month, day, today.year - 1)


def records(
    station: Station, month: int, day: int, *, today: date, get: GetJson = http_json
) -> dict[str, Any]:
    """The station's records for a calendar day, through its last occurrence.

    Each record is ``{"value": metric, "year": int}``; temperatures in degrees
    Celsius, precipitation in millimetres, snow in centimetres.
    """
    end = last_completed(month, day, today)
    start = _calendar_date(month, day, max(station.first_year, 1850))
    if start > end:
        raise ValueError("station record is too short for this date")
    elems = [
        {
            "name": name,
            "interval": [1, 0, 0],
            "duration": 1,
            "smry": {"reduce": reduce, "add": "date"},
            "smry_only": 1,
        }
        for _key, name, reduce in _RECORD_ELEMS
    ]
    data = get(
        _url(
            "StnData",
            {
                "sid": station.sid,
                "sdate": start.isoformat(),
                "edate": end.isoformat(),
                "elems": elems,
            },
        )
    )
    smry = data.get("smry") if isinstance(data, dict) else None
    if not isinstance(smry, list):
        raise ValueError("ACIS records reply had no summary")
    out: dict[str, Any] = {
        "station": station.sid,
        "since": station.first_year,
        "through": end.year,
    }
    for (key, name, _reduce), entry in zip(_RECORD_ELEMS, smry, strict=False):
        if not (isinstance(entry, list) and len(entry) >= 2):
            continue
        raw, year = _value(entry[0]), _parse_year(entry[1])
        if raw is None or year is None:
            continue
        if name in ("maxt", "mint"):
            value = f_to_c(raw)
        elif name == "pcpn":
            value = in_to_mm(raw)
        else:
            value = raw * 2.54  # snow, inches -> centimetres
        if name in ("pcpn", "snow") and raw <= TRACE_INCHES:
            continue  # a "record" of a trace is no record
        out[key] = {"value": value, "year": year}
    return out
