"""One Weather History lookup, start to finish: cache, Open-Meteo, RCC-ACIS,
feed health, and the words. The window calls :func:`look_up` on a worker
thread and shows what comes back; nothing here touches wx.

Three kinds of lookup (:class:`Query`):

* ``on_this_day`` -- today's calendar date over the default number of years.
* ``same_date`` -- any calendar date over 1 to 85 years.
* ``range`` -- every day between two dates, at most a year.

For US places, a calendar-day lookup also asks RCC-ACIS for the nearest
station's 1991-2020 normals and its records for that day; those are cached
with the place, and a failure there only loses the station sentence, never
the rest of the answer (and is said, not hidden).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from quill.core.weather import acis, data_feed_health, history, history_text
from quill.core.weather._http import HTTP_ERRORS
from quill.core.weather.history_cache import DayRecord, HistoryCache


@dataclass(slots=True)
class Query:
    kind: str  # "on_this_day" | "same_date" | "range"
    month: int = 1
    day: int = 1
    years: int = history.DEFAULT_YEARS
    start: date | None = None
    end: date | None = None


@dataclass(slots=True)
class Lookup:
    """What the window shows: the summary, the rows, the credit line."""

    summary: str
    rows: list[DayRecord] = field(default_factory=list)
    credits: str = history_text.CREDIT_OPEN_METEO
    unit: str = "F"
    #: True when nothing at all could be fetched (every request failed).
    failed: bool = False


def climate_for(
    cache: HistoryCache,
    latitude: float,
    longitude: float,
    month: int,
    day: int,
    *,
    today: date,
    now: float,
    get: Callable[[str], Any],
    health: data_feed_health.DataFeedHealth | None,
) -> tuple[history_text.Climate | None, str]:
    """ACIS normals and records for a US place, and a failure sentence if any."""
    if not acis.is_us(latitude, longitude):
        return None, ""
    month_day = f"{month:02d}-{day:02d}"
    try:
        raw_station = cache.get_station(now)
        station = acis.Station.from_json(raw_station) if raw_station else None
        if station is None:
            station = acis.find_station(latitude, longitude, today=today, get=get)
            if station is None:
                return None, ""
            cache.put_station(station.to_json(), now)
        normals = cache.get_normals(month_day, station.sid)
        if normals is None:
            normals = acis.normals(station, month, day, get=get)
            cache.put_normals(month_day, normals)
        records = cache.get_records(month_day, station.sid, now)
        if records is None:
            records = acis.records(station, month, day, today=today, get=get)
            cache.put_records(month_day, records, now)
    except (*HTTP_ERRORS, KeyError, TypeError) as error:
        if health is not None:
            health.record_failure("rcc_acis", error, now)
        return None, "Station records: " + data_feed_health.failure_sentence("rcc_acis", error)
    if health is not None:
        health.record_success("rcc_acis", now)
    return history_text.Climate(station.display_name, normals, records), ""


def look_up(
    query: Query,
    *,
    place: str,
    latitude: float,
    longitude: float,
    unit: str,
    data_dir: Path | None,
    today: date | None = None,
    now: float | None = None,
    health: data_feed_health.DataFeedHealth | None = None,
    get_open_meteo: Callable[..., Any] | None = None,
    get_acis: Callable[[str], Any] | None = None,
    safe_mode: bool = False,
) -> Lookup:
    """Run one lookup. Raises :class:`history.HistoryError` only in Safe Mode or
    for impossible dates; every network failure becomes words in the result."""
    if safe_mode:
        raise history.HistoryError("Weather History is a network service and is off in Safe Mode.")
    today = today or date.today()
    now = time.time() if now is None else now
    cache = HistoryCache(data_dir, latitude, longitude)

    def outcome(feed: str, error: BaseException | None) -> None:
        if health is None:
            return
        if error is None:
            health.record_success(feed, now)
        else:
            health.record_failure(feed, error, now)

    if query.kind == "range":
        if query.start is None or query.end is None:
            raise history.HistoryError("A date range needs a start and an end date.")
        wanted = history.range_dates(query.start, query.end, today)
    else:
        if query.kind == "on_this_day":
            month, day = today.month, today.day
        else:
            month, day = query.month, query.day
        try:
            date(2024, month, day)
        except ValueError as exc:
            raise history.HistoryError(f"There is no such date as {month}/{day}.") from exc
        query.month, query.day = month, day
        wanted = history.same_date_dates(month, day, query.years, today)
    if not wanted:
        raise history.HistoryError("Those dates are outside 1940 to today.")

    result = history.fetch_days(
        latitude,
        longitude,
        wanted,
        today=today,
        cache=cache,
        now=now,
        get=get_open_meteo,
        on_outcome=outcome,
    )
    failure_text = ""
    if result.failed:
        feed, error = result.failures()[0]
        failure_text = data_feed_health.failure_sentence(feed, error)

    climate: history_text.Climate | None = None
    acis_note = ""
    if query.kind == "range":
        summary = history_text.range_summary(
            place,
            result.days,
            unit=unit,
            asked_days=len(wanted),
            failed_count=len(result.failed),
            failure_text=failure_text,
        )
    else:
        from quill.core.weather._http import http_json

        climate, acis_note = climate_for(
            cache,
            latitude,
            longitude,
            query.month,
            query.day,
            today=today,
            now=now,
            get=get_acis or http_json,
            health=health,
        )
        summary = history_text.same_date_summary(
            place,
            query.month,
            query.day,
            result.days,
            today=today,
            unit=unit,
            climate=climate,
            failed_count=len(result.failed),
            failure_text=failure_text,
            years_asked=len(wanted),
        )
        if acis_note:
            summary = f"{summary} {acis_note}"
    cache.save()
    return Lookup(
        summary=summary,
        rows=result.days,
        credits=history_text.credits_for(result.sources, used_acis=climate is not None),
        unit=unit,
        failed=not result.days and bool(result.failed),
    )
