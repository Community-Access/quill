"""The extra lines of a Weather Now report: rain starting soon, the glance
ahead, the daylight change, chosen fields, pollen and the sea.

``gather`` makes at most three requests -- the one nowcast request (only when
one of its lines is wanted), pollen (only in Europe) and marine (only where a
place has sea data; an inland place is remembered for the session so it is not
asked again) -- and records each with ``data_feed_health``. A failed request
becomes a sentence saying so, never a missing line that reads as "nothing to
report".

wx-free and strict-typed.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from quill.core.weather import data_feed_health, nowcast, sea_and_pollen
from quill.core.weather._http import HTTP_ERRORS
from quill.core.weather.models import WeatherLocation
from quill.core.weather.settings import WeatherSettings

_INLAND: set[str] = set()
_INLAND_LOCK = threading.Lock()


@dataclass(slots=True)
class Extras:
    rain_soon: str = ""
    glance: str = ""
    daylight: str = ""
    fields: str = ""
    pollen: str = ""
    marine: str = ""
    problems: list[str] = field(default_factory=list)

    def lines(self) -> list[str]:
        out = [self.rain_soon, self.glance, self.daylight, self.fields, self.pollen, self.marine]
        return [line for line in out if line] + self.problems


def wind_word(settings: WeatherSettings) -> str:
    return "kilometres per hour" if settings.temperature_unit == "C" else "miles per hour"


def _place_key(location: WeatherLocation) -> str:
    return f"{location.latitude:.2f},{location.longitude:.2f}"


def gather(
    location: WeatherLocation,
    settings: WeatherSettings,
    *,
    health: data_feed_health.DataFeedHealth | None = None,
    now: float | None = None,
    get: Callable[..., Any] | None = None,
    nowcast_only: bool = False,
) -> Extras:
    """Fetch and word whatever the settings ask for. Never raises a network error."""
    now = time.time() if now is None else now
    extras = Extras()

    def ok(feed: str) -> None:
        if health is not None:
            health.record_success(feed, now)

    def failed(feed: str, label: str, error: BaseException) -> None:
        if health is not None:
            health.record_failure(feed, error, now)
        extras.problems.append(f"{label}: {data_feed_health.failure_sentence(feed, error)}")

    lat, lon = location.latitude, location.longitude
    wants_cast = nowcast_only or any((
        settings.show_rain_soon,
        settings.show_glance_ahead,
        settings.show_daylight_change,
        bool(settings.report_fields),
    ))
    if wants_cast:
        try:
            cast = nowcast.fetch(
                lat,
                lon,
                unit=settings.temperature_unit,
                extra_fields=[] if nowcast_only else settings.report_fields,
                get=get,
            )
        except HTTP_ERRORS as error:
            failed("open_meteo_nowcast", "The next few hours", error)
        else:
            ok("open_meteo_nowcast")
            if settings.show_rain_soon or nowcast_only:
                extras.rain_soon = nowcast.rain_soon_text(cast)
            if settings.show_glance_ahead or nowcast_only:
                extras.glance = nowcast.glance_text(cast, wind_word=wind_word(settings))
            if settings.show_daylight_change or nowcast_only:
                extras.daylight = nowcast.daylight_text(cast)
            if not nowcast_only:
                extras.fields = nowcast.extras_text(cast, settings.report_fields)
    if nowcast_only:
        return extras
    metric = settings.temperature_unit == "C"
    if settings.show_pollen and sea_and_pollen.in_europe(lat, lon):
        try:
            extras.pollen = sea_and_pollen.pollen_text(
                sea_and_pollen.fetch_pollen(lat, lon, get=get)
            )
            ok("open_meteo_pollen")
        except HTTP_ERRORS as error:
            failed("open_meteo_pollen", "Pollen", error)
    key = _place_key(location)
    with _INLAND_LOCK:
        inland = key in _INLAND
    if settings.show_marine and not inland:
        try:
            marine = sea_and_pollen.fetch_marine(lat, lon, get=get)
            ok("open_meteo_marine")
        except HTTP_ERRORS as error:
            failed("open_meteo_marine", "Sea conditions", error)
        else:
            if marine is None:
                with _INLAND_LOCK:
                    _INLAND.add(key)
            extras.marine = sea_and_pollen.marine_text(marine, metric=metric)
    return extras


def forget_inland() -> None:
    """For tests: forget which places had no sea data."""
    with _INLAND_LOCK:
        _INLAND.clear()


def attach(report: Any, settings: WeatherSettings, data_dir: Any) -> Any:
    """Gather the extras for a fetched report and keep them on it (for the
    Weather Center's worker). Returns the report, so it wraps a fetch call."""
    from quill.core.weather.models import WeatherReport

    if not isinstance(report, WeatherReport):
        return report
    health = data_feed_health.shared(data_dir) if data_dir is not None else None
    report.extras = gather(report.location, settings, health=health).lines()
    if health is not None:
        data_feed_health.save(data_dir, health)
    return report


def fetch_report(
    location: WeatherLocation, settings: WeatherSettings, data_dir: Any, *, safe_mode: bool
) -> Any:
    """The Weather Center's whole fetch: the report as the settings shape it,
    then its extras. Raises ``nws.WeatherError`` like the report fetch does."""
    from quill.core.weather import nws

    report = nws.fetch_report_worldwide(
        location,
        safe_mode=safe_mode,
        daily_days=settings.daily_outlook_days,
        hourly_hours=settings.hourly_hours,
        temperature_unit=settings.temperature_unit,
    )
    return attach(report, settings, data_dir)
