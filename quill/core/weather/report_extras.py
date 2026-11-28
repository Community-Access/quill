"""The extra lines of a Weather Now report: rain starting soon, the glance
ahead and the change in daylight.

``gather`` makes at most one request (the nowcast, only when one of its lines is
wanted) and records it with ``data_feed_health``. A failed request becomes a
sentence saying so, never a missing line that reads as "nothing to report".

wx-free and strict-typed.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from quill.core.weather import data_feed_health, nowcast
from quill.core.weather._http import HTTP_ERRORS
from quill.core.weather.models import WeatherLocation
from quill.core.weather.settings import WeatherSettings


@dataclass(slots=True)
class Extras:
    rain_soon: str = ""
    glance: str = ""
    daylight: str = ""
    problems: list[str] = field(default_factory=list)

    def lines(self) -> list[str]:
        lines = (self.rain_soon, self.glance, self.daylight)
        return [line for line in lines if line] + self.problems


def wind_word(settings: WeatherSettings) -> str:
    return "kilometres per hour" if settings.temperature_unit == "C" else "miles per hour"


def gather(
    location: WeatherLocation,
    settings: WeatherSettings,
    *,
    health: data_feed_health.DataFeedHealth | None = None,
    now: float | None = None,
    get: Callable[..., Any] | None = None,
    nowcast_only: bool = False,
) -> Extras:
    """Fetch and word whatever the settings ask for (everything when
    ``nowcast_only``, for Next Few Hours). Never raises a network error."""
    now = time.time() if now is None else now
    extras = Extras()
    want_rain = nowcast_only or settings.show_rain_soon
    want_glance = nowcast_only or settings.show_glance_ahead
    want_daylight = nowcast_only or settings.show_daylight_change
    if not (want_rain or want_glance or want_daylight):
        return extras
    try:
        cast = nowcast.fetch(
            location.latitude, location.longitude, unit=settings.temperature_unit, get=get
        )
    except HTTP_ERRORS as error:
        if health is not None:
            health.record_failure("open_meteo_nowcast", error, now)
        sentence = data_feed_health.failure_sentence("open_meteo_nowcast", error)
        extras.problems.append(f"The next few hours: {sentence}")
        return extras
    if health is not None:
        health.record_success("open_meteo_nowcast", now)
    if want_rain:
        extras.rain_soon = nowcast.rain_soon_text(cast)
    if want_glance:
        extras.glance = nowcast.glance_text(cast, wind_word=wind_word(settings))
    if want_daylight:
        extras.daylight = nowcast.daylight_text(cast)
    return extras


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
