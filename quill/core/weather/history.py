"""Weather History: what the weather was on a date, the same date over many
years, or across a date range -- from Open-Meteo, keyless.

Two Open-Meteo services, routed by how old the date is:

* **The last 92 days** come from the forecast service with ``past_days``. It has
  no delay and is the same model as the forecast, so "yesterday" is there today.
* **Anything older** comes from the historical-weather service
  (``archive-api.open-meteo.com/v1/archive``), which is Copernicus ERA5
  reanalysis: every day from 1940 to about five days ago.

The same date over N years is one small request per year (a request for one
day counts as one call; one request spanning eighty years would count as
thousands), five at a time, and every answer is cached for good
(``history_cache``). A date range is one request per stretch of missing days.

Every request reports to ``data_feed_health``, and a failed request leaves its
dates in :attr:`HistoryResult.failed` -- "could not reach" is never mistaken for
"no data".

wx-free and strict-typed. The clock, the cache and the transport are passed in.
"""

from __future__ import annotations

import time
import urllib.parse
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from quill.core.error_codes import CodedError
from quill.core.weather._http import HTTP_ERRORS
from quill.core.weather.history_cache import DayRecord, HistoryCache

EARLIEST = date(1940, 1, 1)
RECENT_DAYS = 92
MAX_YEARS = 85
DEFAULT_YEARS = 20
MAX_RANGE_DAYS = 366
_WORKERS = 5
#: Open-Meteo counts a request covering more than two weeks as more than one call.
_DAYS_PER_CALL = 14
DAILY_FIELDS = (
    "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,"
    "snowfall_sum,wind_speed_10m_max"
)

GetJson = Callable[..., Any]


class HistoryError(CodedError):
    """A Weather History request could not be made at all (Safe Mode, bad dates)."""

    code = "QUILL-WEATHER-HISTORY-REQUEST"


def _default_get() -> GetJson:
    from quill.core.weather.open_meteo_limits import get_json

    return get_json


def route(day: date, today: date) -> str:
    """``recent`` for the last 92 days (and today), else ``archive``."""
    return "recent" if day >= today - timedelta(days=RECENT_DAYS) else "archive"


def _num(values: Any, index: int) -> float | None:
    if isinstance(values, list) and index < len(values):
        value = values[index]
        if isinstance(value, int | float) and not isinstance(value, bool):
            return float(value)
    return None


def days_from_json(data: Any, source: str) -> list[DayRecord]:
    """Parse an Open-Meteo ``daily`` block (metric units) into DayRecords."""
    daily = data.get("daily") if isinstance(data, dict) else None
    if not isinstance(daily, dict):
        return []
    out: list[DayRecord] = []
    for i, iso in enumerate(daily.get("time") or []):
        if not isinstance(iso, str):
            continue
        code = _num(daily.get("weather_code"), i)
        out.append(
            DayRecord(
                date=iso,
                code=round(code) if code is not None else None,
                high_c=_num(daily.get("temperature_2m_max"), i),
                low_c=_num(daily.get("temperature_2m_min"), i),
                precip_mm=_num(daily.get("precipitation_sum"), i),
                snow_cm=_num(daily.get("snowfall_sum"), i),
                wind_max_kmh=_num(daily.get("wind_speed_10m_max"), i),
                source=source,
            )
        )
    return out


def _query(latitude: float, longitude: float, **extra: Any) -> str:
    return urllib.parse.urlencode({
        "latitude": f"{latitude:.4f}",
        "longitude": f"{longitude:.4f}",
        "daily": DAILY_FIELDS,
        "timezone": "auto",
        **extra,
    })


def recent_url(latitude: float, longitude: float, past_days: int) -> str:
    past = max(1, min(RECENT_DAYS, past_days))
    return "https://api.open-meteo.com/v1/forecast?" + _query(
        latitude, longitude, past_days=past, forecast_days=1
    )


def archive_url(latitude: float, longitude: float, start: date, end: date) -> str:
    return "https://archive-api.open-meteo.com/v1/archive?" + _query(
        latitude, longitude, start_date=start.isoformat(), end_date=end.isoformat()
    )


def same_date_dates(month: int, day: int, years: int, today: date) -> list[date]:
    """The date in each of the last ``years`` years, newest first, starting this
    year when the date has come (today included). Feb 29 uses leap years only."""
    years = max(1, min(MAX_YEARS, years))
    out: list[date] = []
    year = today.year
    while len(out) < years and year >= EARLIEST.year:
        try:
            candidate = date(year, month, day)
        except ValueError:  # Feb 29 in a common year
            year -= 1
            continue
        if candidate <= today:
            out.append(candidate)
        year -= 1
    return out


def range_dates(start: date, end: date, today: date) -> list[date]:
    """Every day from start to end, clipped to 1940..today, at most a year."""
    if end < start:
        start, end = end, start
    start, end = max(start, EARLIEST), min(end, today)
    if end < start:
        return []
    count = min((end - start).days + 1, MAX_RANGE_DAYS)
    return [start + timedelta(days=i) for i in range(count)]


def _runs(days: Iterable[date]) -> list[tuple[date, date]]:
    """Contiguous stretches of the given days, as (first, last) pairs."""
    ordered = sorted(set(days))
    runs: list[tuple[date, date]] = []
    for d in ordered:
        if runs and (d - runs[-1][1]).days == 1:
            runs[-1] = (runs[-1][0], d)
        else:
            runs.append((d, d))
    return runs


@dataclass(slots=True)
class HistoryResult:
    """What a lookup found. ``failed`` holds dates whose request failed, with the
    feed and error, so the window can say "could not reach" for exactly those."""

    days: list[DayRecord] = field(default_factory=list)
    failed: dict[str, tuple[str, BaseException]] = field(default_factory=dict)
    sources: set[str] = field(default_factory=set)
    requests: int = 0

    def failures(self) -> list[tuple[str, BaseException]]:
        seen: dict[str, tuple[str, BaseException]] = {}
        for feed, error in self.failed.values():
            seen.setdefault(feed, (feed, error))
        return list(seen.values())


@dataclass(slots=True)
class _Job:
    feed: str
    url: str
    wanted: list[date]
    weight: int


def fetch_days(
    latitude: float,
    longitude: float,
    wanted: list[date],
    *,
    today: date,
    cache: HistoryCache,
    now: float | None = None,
    get: GetJson | None = None,
    on_outcome: Callable[[str, BaseException | None], None] | None = None,
    safe_mode: bool = False,
) -> HistoryResult:
    """Fetch the wanted days, from the cache first and Open-Meteo for the rest.

    ``on_outcome(feed, error_or_None)`` is called once per request, for feed
    health. Results come back newest first.
    """
    if safe_mode:
        raise HistoryError("Weather History is a network service and is off in Safe Mode.")
    now = time.time() if now is None else now
    get = get or _default_get()
    result = HistoryResult()
    found: dict[str, DayRecord] = {}
    recent: list[date] = []
    archive: list[date] = []
    for d in wanted:
        if d > today or d < EARLIEST:
            continue
        cached = cache.get_day(d.isoformat(), today=today, now=now)
        if cached is not None:
            found[cached.date] = cached
            result.sources.add(cached.source)
        else:
            (recent if route(d, today) == "recent" else archive).append(d)

    jobs: list[_Job] = []
    if recent:
        past = (today - min(recent)).days
        jobs.append(_Job("open_meteo_recent", recent_url(latitude, longitude, past), recent, 1))
    for first, last in _runs(archive):
        while first <= last:
            stop = min(last, first + timedelta(days=MAX_RANGE_DAYS - 1))
            span = (stop - first).days + 1
            chunk = [first + timedelta(days=i) for i in range(span)]
            weight = max(1, -(-span // _DAYS_PER_CALL))
            jobs.append(
                _Job(
                    "open_meteo_archive",
                    archive_url(latitude, longitude, first, stop),
                    chunk,
                    weight,
                )
            )
            first = stop + timedelta(days=1)

    def _run(job: _Job) -> tuple[_Job, Any, BaseException | None]:
        try:
            return job, get(job.url, weight=job.weight), None
        except HTTP_ERRORS as error:
            return job, None, error

    if jobs:
        with ThreadPoolExecutor(max_workers=min(_WORKERS, len(jobs))) as pool:
            outcomes = list(pool.map(_run, jobs))
        for job, data, error in outcomes:
            result.requests += 1
            if on_outcome is not None:
                on_outcome(job.feed, error)
            if error is not None:
                for d in job.wanted:
                    result.failed[d.isoformat()] = (job.feed, error)
                continue
            source = "recent" if job.feed == "open_meteo_recent" else "archive"
            wanted_iso = {d.isoformat() for d in job.wanted}
            for record in days_from_json(data, source):
                if record.date in wanted_iso and record.has_data:
                    cache.put_day(record, now)
                    found[record.date] = record
                    result.sources.add(source)
    result.days = sorted(found.values(), key=lambda r: r.date, reverse=True)
    return result
