"""One Weather on a Past Date lookup: the day, its comparison with normal, the
words, the credits, and feed health -- run on a worker thread by the window.

A failed request is a sentence that says so (:attr:`DayResult.error`); a reply
with nothing in it is a different sentence ("Open-Meteo has no data for...").
The comparison is best effort: if it cannot be fetched the day is still shown,
and the comparison line says why it is missing.

wx-free and strict-typed.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from quill.core.weather import acis, data_feed_health, past_day, past_day_text
from quill.core.weather._http import HTTP_ERRORS
from quill.core.weather.date_query import long_date
from quill.core.weather.history_cache import HistoryCache
from quill.core.weather.history_service import climate_for
from quill.core.weather.history_text import credits_for


@dataclass(slots=True)
class DayResult:
    day: past_day.PastDay | None
    text: str  # the day as lines, for the read-only box
    spoken: str  # said after a move, after the date
    credits: str
    error: str = ""  # set when the day itself could not be fetched


def look_up_day(
    day: date,
    *,
    place: str,
    latitude: float,
    longitude: float,
    units: past_day_text.Units,
    data_dir: Path | None,
    today: date | None = None,
    now: float | None = None,
    health: data_feed_health.DataFeedHealth | None = None,
    get_open_meteo: Callable[..., Any] | None = None,
    get_acis: Callable[[str], Any] | None = None,
) -> DayResult:
    today = today or date.today()
    now = time.time() if now is None else now
    cache = HistoryCache(data_dir, latitude, longitude)
    source = past_day.source_for(day, today)
    feed = "open_meteo_recent" if source == "recent" else "open_meteo_archive"

    def outcome(name: str, error: BaseException | None) -> None:
        if health is None:
            return
        if error is None:
            health.record_success(name, now)
        else:
            health.record_failure(name, error, now)

    try:
        found = past_day.fetch_day(
            latitude, longitude, day, today=today, cache=cache, now=now, get=get_open_meteo
        )
    except HTTP_ERRORS as error:
        outcome(feed, error)
        sentence = data_feed_health.failure_sentence(feed, error)
        cache.save()
        return DayResult(None, sentence, sentence, credits_for({source}, used_acis=False), sentence)
    outcome(feed, None)
    if found is None:
        cache.save()
        text = f"Open-Meteo has no data for {long_date(day)} in {place}."
        return DayResult(None, text, text, credits_for({source}, used_acis=False))

    climate = None
    note = ""
    sources = {source}
    if acis.is_us(latitude, longitude):
        from quill.core.weather._http import http_json

        climate, note = climate_for(
            cache,
            latitude,
            longitude,
            day.month,
            day.day,
            today=today,
            now=now,
            get=get_acis or http_json,
            health=health,
        )
    average = None
    if climate is None or not climate.normals:
        average = past_day.average_for(
            latitude,
            longitude,
            day,
            today=today,
            cache=cache,
            now=now,
            get=get_open_meteo,
            on_outcome=outcome,
        )
        sources.add("archive")
    compared = past_day_text.compared_line(found, units, climate=climate, average=average)
    if not compared:
        compared = note or "Compared with normal: not available for this date."
    cache.save()
    credits = credits_for(sources, used_acis=climate is not None)
    lines = past_day_text.day_lines(found, place, units, compared=compared)
    return DayResult(
        day=found,
        text="\n".join(lines),
        spoken=past_day_text.spoken_summary(found, place, units),
        credits=credits,
    )
