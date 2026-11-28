"""The extra lines of a Weather Now report: rain starting soon, the glance
ahead, the change in daylight, pollen and the sea.

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
    pollen: str = ""
    marine: str = ""
    problems: list[str] = field(default_factory=list)

    def lines(self) -> list[str]:
        lines = (self.rain_soon, self.glance, self.daylight, self.pollen, self.marine)
        return [line for line in lines if line] + self.problems


def wind_word(settings: WeatherSettings) -> str:
    return "kilometres per hour" if settings.temperature_unit == "C" else "miles per hour"


class _Recorder:
    """Feed-health bookkeeping and the failure sentences for one gather."""

    def __init__(
        self, extras: Extras, health: data_feed_health.DataFeedHealth | None, now: float
    ) -> None:
        self.extras, self.health, self.now = extras, health, now

    def ok(self, feed: str) -> None:
        if self.health is not None:
            self.health.record_success(feed, self.now)

    def failed(self, feed: str, label: str, error: BaseException) -> None:
        if self.health is not None:
            self.health.record_failure(feed, error, self.now)
        sentence = data_feed_health.failure_sentence(feed, error)
        self.extras.problems.append(f"{label}: {sentence}")


def gather(
    location: WeatherLocation,
    settings: WeatherSettings,
    *,
    health: data_feed_health.DataFeedHealth | None = None,
    now: float | None = None,
    get: Callable[..., Any] | None = None,
    nowcast_only: bool = False,
) -> Extras:
    """Fetch and word whatever the settings ask for (the nowcast lines only, and
    all of them, when ``nowcast_only``, for Next Few Hours). Never raises a
    network error."""
    now = time.time() if now is None else now
    extras = Extras()
    record = _Recorder(extras, health, now)
    _gather_nowcast(location, settings, record, get=get, everything=nowcast_only)
    if not nowcast_only:
        _gather_sea_and_air(location, settings, record, get=get)
    return extras


def _gather_nowcast(
    location: WeatherLocation,
    settings: WeatherSettings,
    record: _Recorder,
    *,
    get: Callable[..., Any] | None,
    everything: bool,
) -> None:
    extras = record.extras
    want_rain = everything or settings.show_rain_soon
    want_glance = everything or settings.show_glance_ahead
    want_daylight = everything or settings.show_daylight_change
    if not (want_rain or want_glance or want_daylight):
        return
    try:
        cast = nowcast.fetch(
            location.latitude, location.longitude, unit=settings.temperature_unit, get=get
        )
    except HTTP_ERRORS as error:
        record.failed("open_meteo_nowcast", "The next few hours", error)
        return
    record.ok("open_meteo_nowcast")
    if want_rain:
        extras.rain_soon = nowcast.rain_soon_text(cast)
    if want_glance:
        extras.glance = nowcast.glance_text(cast, wind_word=wind_word(settings))
    if want_daylight:
        extras.daylight = nowcast.daylight_text(cast)


def _place_key(location: WeatherLocation) -> str:
    return f"{location.latitude:.2f},{location.longitude:.2f}"


def _gather_sea_and_air(
    location: WeatherLocation,
    settings: WeatherSettings,
    record: _Recorder,
    *,
    get: Callable[..., Any] | None,
) -> None:
    extras = record.extras
    lat, lon = location.latitude, location.longitude
    if settings.show_pollen and sea_and_pollen.in_europe(lat, lon):
        try:
            extras.pollen = sea_and_pollen.pollen_text(
                sea_and_pollen.fetch_pollen(lat, lon, get=get)
            )
        except HTTP_ERRORS as error:
            record.failed("open_meteo_pollen", "Pollen", error)
        else:
            record.ok("open_meteo_pollen")
    key = _place_key(location)
    with _INLAND_LOCK:
        inland = key in _INLAND
    if not settings.show_marine or inland:
        return
    try:
        marine = sea_and_pollen.fetch_marine(lat, lon, get=get)
    except HTTP_ERRORS as error:
        record.failed("open_meteo_marine", "Sea conditions", error)
        return
    record.ok("open_meteo_marine")
    if marine is None:
        with _INLAND_LOCK:
            _INLAND.add(key)
    extras.marine = sea_and_pollen.marine_text(marine, metric=settings.temperature_unit == "C")


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
