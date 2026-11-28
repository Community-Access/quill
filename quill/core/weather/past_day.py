"""One past day in full, for Weather on a Past Date: the daily summary and
every hour, from Open-Meteo, cached for good.

Routing follows :mod:`quill.core.weather.date_query`: a day more than five days
old comes from the historical-weather archive (Copernicus ERA5); a day in the
last five days, which the archive does not have yet, comes from the forecast
service's recent data. Either way it is **one** request with
``start_date == end_date``, in metric, and the result is stored in the place's
history cache (``HistoryCache.details``) so moving back to a day costs nothing.

The "compared with normal" figure uses RCC-ACIS normals and records for US
places (through ``history_service``); elsewhere it is the average for the date
over the last :data:`AVERAGE_YEARS` years, fetched as one window of
:data:`WINDOW_DAYS` days either side per year, so that moving a few days along
needs no new request.

wx-free and strict-typed; the transport, the clock and today are passed in.
"""

from __future__ import annotations

import time
import urllib.parse
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from typing import Any

from quill.core.weather import date_query, history
from quill.core.weather.history_cache import DayRecord, HistoryCache

GetJson = Callable[..., Any]

AVERAGE_YEARS = 10
WINDOW_DAYS = 15

DAILY_FIELDS = (
    "weather_code,temperature_2m_max,temperature_2m_min,apparent_temperature_max,"
    "apparent_temperature_min,precipitation_sum,snowfall_sum,precipitation_hours,"
    "wind_speed_10m_max,wind_gusts_10m_max,wind_direction_10m_dominant,sunrise,sunset,"
    "daylight_duration"
)
HOURLY_FIELDS = (
    "temperature_2m,apparent_temperature,precipitation,snowfall,weather_code,"
    "wind_speed_10m,wind_direction_10m,relative_humidity_2m"
)


@dataclass(slots=True)
class HourRow:
    time: str  # local ISO "2011-03-14T15:00"
    temperature_c: float | None = None
    feels_like_c: float | None = None
    precip_mm: float | None = None
    snow_cm: float | None = None
    code: int | None = None
    wind_kmh: float | None = None
    wind_from: float | None = None
    humidity: float | None = None


@dataclass(slots=True)
class PastDay:
    """One day in full, metric. ``source`` is ``archive`` or ``recent``."""

    date: str
    source: str = "archive"
    code: int | None = None
    high_c: float | None = None
    low_c: float | None = None
    feels_high_c: float | None = None
    feels_low_c: float | None = None
    precip_mm: float | None = None
    snow_cm: float | None = None
    precip_hours: float | None = None
    wind_max_kmh: float | None = None
    gust_max_kmh: float | None = None
    wind_from: float | None = None
    sunrise: str = ""
    sunset: str = ""
    daylight_s: float | None = None
    hours: list[HourRow] = field(default_factory=list)

    @property
    def has_data(self) -> bool:
        return self.high_c is not None or self.low_c is not None or bool(self.hours)

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_json(cls, raw: Any) -> PastDay | None:
        if not isinstance(raw, dict) or not isinstance(raw.get("date"), str):
            return None
        hours = [HourRow(**h) for h in raw.get("hours") or [] if isinstance(h, dict)]
        known = {k: raw[k] for k in cls.__dataclass_fields__ if k in raw and k != "hours"}
        try:
            return cls(**known, hours=hours)
        except TypeError:
            return None


def _num(block: Any, key: str, index: int) -> float | None:
    values = block.get(key) if isinstance(block, dict) else None
    if isinstance(values, list) and index < len(values):
        value = values[index]
        if isinstance(value, int | float) and not isinstance(value, bool):
            return float(value)
    return None


def _text(block: Any, key: str, index: int) -> str:
    values = block.get(key) if isinstance(block, dict) else None
    if isinstance(values, list) and index < len(values) and isinstance(values[index], str):
        return str(values[index])
    return ""


def parse(data: Any, iso: str, source: str) -> PastDay | None:
    """The one day out of an Open-Meteo reply (pure)."""
    if not isinstance(data, dict):
        return None
    daily = data.get("daily")
    times = daily.get("time") if isinstance(daily, dict) else None
    if not isinstance(times, list) or iso not in times:
        return None
    i = times.index(iso)
    code = _num(daily, "weather_code", i)
    day = PastDay(
        date=iso,
        source=source,
        code=round(code) if code is not None else None,
        high_c=_num(daily, "temperature_2m_max", i),
        low_c=_num(daily, "temperature_2m_min", i),
        feels_high_c=_num(daily, "apparent_temperature_max", i),
        feels_low_c=_num(daily, "apparent_temperature_min", i),
        precip_mm=_num(daily, "precipitation_sum", i),
        snow_cm=_num(daily, "snowfall_sum", i),
        precip_hours=_num(daily, "precipitation_hours", i),
        wind_max_kmh=_num(daily, "wind_speed_10m_max", i),
        gust_max_kmh=_num(daily, "wind_gusts_10m_max", i),
        wind_from=_num(daily, "wind_direction_10m_dominant", i),
        sunrise=_text(daily, "sunrise", i),
        sunset=_text(daily, "sunset", i),
        daylight_s=_num(daily, "daylight_duration", i),
    )
    hourly = data.get("hourly")
    for j, when in enumerate(hourly.get("time") or [] if isinstance(hourly, dict) else []):
        if not (isinstance(when, str) and when.startswith(iso)):
            continue
        hcode = _num(hourly, "weather_code", j)
        day.hours.append(
            HourRow(
                time=when,
                temperature_c=_num(hourly, "temperature_2m", j),
                feels_like_c=_num(hourly, "apparent_temperature", j),
                precip_mm=_num(hourly, "precipitation", j),
                snow_cm=_num(hourly, "snowfall", j),
                code=round(hcode) if hcode is not None else None,
                wind_kmh=_num(hourly, "wind_speed_10m", j),
                wind_from=_num(hourly, "wind_direction_10m", j),
                humidity=_num(hourly, "relative_humidity_2m", j),
            )
        )
    return day if day.has_data else None


def source_for(day: date, today: date) -> str:
    lag = today - timedelta(days=date_query.ARCHIVE_LAG_DAYS)
    return "recent" if day > lag else "archive"


def day_url(latitude: float, longitude: float, day: date, today: date) -> str:
    host = (
        "https://api.open-meteo.com/v1/forecast?"
        if source_for(day, today) == "recent"
        else "https://archive-api.open-meteo.com/v1/archive?"
    )
    return host + urllib.parse.urlencode({
        "latitude": f"{latitude:.4f}",
        "longitude": f"{longitude:.4f}",
        "start_date": day.isoformat(),
        "end_date": day.isoformat(),
        "daily": DAILY_FIELDS,
        "hourly": HOURLY_FIELDS,
        "timezone": "auto",
    })


def fetch_day(
    latitude: float,
    longitude: float,
    day: date,
    *,
    today: date,
    cache: HistoryCache,
    now: float | None = None,
    get: GetJson | None = None,
) -> PastDay | None:
    """The day from the cache, or one request. None means the service answered
    with no data for it; a failed request raises (``HTTP_ERRORS``)."""
    now = time.time() if now is None else now
    iso = day.isoformat()
    cached = cache.get_detail(iso, today=today, now=now)
    if cached is not None:
        found = PastDay.from_json(cached)
        if found is not None:
            return found
    if get is None:
        from quill.core.weather.open_meteo_limits import get_json

        get = get_json
    source = source_for(day, today)
    found = parse(get(day_url(latitude, longitude, day, today)), iso, source)
    if found is not None:
        cache.put_detail(iso, found.to_json(), now)
        cache.put_day(
            DayRecord(
                date=iso,
                code=found.code,
                high_c=found.high_c,
                low_c=found.low_c,
                precip_mm=found.precip_mm,
                snow_cm=found.snow_cm,
                wind_max_kmh=found.wind_max_kmh,
                source=source,
            ),
            now,
        )
    return found


def average_for(
    latitude: float,
    longitude: float,
    day: date,
    *,
    today: date,
    cache: HistoryCache,
    now: float | None = None,
    get: GetJson | None = None,
    on_outcome: Callable[[str, BaseException | None], None] | None = None,
) -> tuple[float | None, float | None, int]:
    """(average high, average low, years) for the calendar date over the last
    :data:`AVERAGE_YEARS` years before *day*'s year, from Open-Meteo.

    Each year is fetched as a window of days either side, all cached, so the
    neighbouring dates are free. Years that fail are left out of the average.
    """
    wanted: list[date] = []
    targets: list[date] = []
    for back in range(1, AVERAGE_YEARS + 1):
        target = date_query.shift(day, years=-back)
        if target < date_query.EARLIEST:
            break
        targets.append(target)
        for offset in range(-WINDOW_DAYS, WINDOW_DAYS + 1):
            candidate = target + timedelta(days=offset)
            if date_query.EARLIEST <= candidate <= today:
                wanted.append(candidate)
    result = history.fetch_days(
        latitude, longitude, wanted, today=today, cache=cache, now=now, get=get,
        on_outcome=on_outcome,
    )  # fmt: skip
    by_date = {r.date: r for r in result.days}
    highs = [by_date[t.isoformat()].high_c for t in targets if t.isoformat() in by_date]
    lows = [by_date[t.isoformat()].low_c for t in targets if t.isoformat() in by_date]
    good_highs = [h for h in highs if h is not None]
    good_lows = [v for v in lows if v is not None]
    if not good_highs:
        return None, None, 0
    mean_low = sum(good_lows) / len(good_lows) if good_lows else None
    return sum(good_highs) / len(good_highs), mean_low, len(good_highs)
