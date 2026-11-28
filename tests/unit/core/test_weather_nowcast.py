"""The next few hours: rain starting soon, the four-hour glance ahead, the
daylight change, the one request, and a failure said as a failure."""

from __future__ import annotations

import urllib.error
from typing import Any

from quill.core.weather import nowcast, report_extras
from quill.core.weather.models import WeatherLocation
from quill.core.weather.settings import WeatherSettings


def _reply(daylight: tuple[float, float] = (32000, 31880)) -> dict[str, Any]:
    return {
        "current": {"time": "2026-11-27T15:30"},
        "hourly": {
            "time": [f"2026-11-27T{h}:00" for h in (15, 16, 17, 18, 19)],
            "temperature_2m": [50, 49, 48, 47, 46],
            "precipitation_probability": [10, 20, 60, 30, 10],
            "weather_code": [3, 3, 61, 61, 3],
            "wind_speed_10m": [5, 6, 18, 9, 4],
        },
        "daily": {"time": ["2026-11-26", "2026-11-27"], "daylight_duration": list(daylight)},
    }


def test_the_hour_under_way_is_skipped() -> None:
    cast = nowcast.parse(_reply(), unit="F")
    assert [h.time[11:13] for h in cast.hours] == ["16", "17", "18", "19"]


def test_glance() -> None:
    glance = nowcast.glance_text(nowcast.parse(_reply(), unit="F"))
    assert glance.startswith("Through 7 PM: 49 now, falling to 46.")
    assert "Sky: overcast now, then light rain from 5 PM, then overcast from 7 PM." in glance
    assert "Chance of precipitation up to 60 percent." in glance
    assert "Wind up to 18 miles per hour." in glance


def test_daylight() -> None:
    assert nowcast.daylight_text(nowcast.parse(_reply(), unit="F")) == (
        "8 hours 51 minutes of daylight today, 2 minutes less than yesterday."
    )
    more = nowcast.parse(_reply((50000, 50070)), unit="C")
    assert nowcast.daylight_text(more) == (
        "13 hours 54 minutes of daylight today, 1 minute more than yesterday."
    )
    same = nowcast.parse(_reply((50000, 50010)), unit="C")
    assert nowcast.daylight_text(same).endswith("about the same as yesterday.")


def test_one_request_in_the_users_units() -> None:
    url = nowcast.request_url(1, 2, unit="C")
    assert "daily=daylight_duration" in url and "past_days=1" in url
    assert "temperature_unit=celsius" in url and "wind_speed_unit=kmh" in url


def test_extras_respect_settings_and_say_failures() -> None:
    location = WeatherLocation("Home", 47.6, -122.3, id="h")
    asked: list[str] = []

    def ok(url: str, **_k: Any) -> Any:
        asked.append(url)
        return _reply()

    settings = WeatherSettings()
    settings.show_pollen = settings.show_marine = False  # this test is about the nowcast
    settings.show_rain_soon = False
    settings.show_glance_ahead = False
    lines = report_extras.gather(location, settings, get=ok).lines()
    assert lines == ["8 hours 51 minutes of daylight today, 2 minutes less than yesterday."]
    settings.show_daylight_change = False
    assert report_extras.gather(location, settings, get=ok).lines() == []
    assert len(asked) == 1  # nothing wanted, nothing asked

    def down(url: str, **_k: Any) -> Any:
        raise urllib.error.URLError("down")

    failed = report_extras.gather(location, WeatherSettings(), get=down).lines()
    assert failed and "not the same as no data" in failed[0]


def _steps(precip: list[float], *, snow: list[float] | None = None, code: int = 61) -> Any:
    times = [f"2026-11-27T15:{m:02d}" for m in (0, 15, 30, 45)] + [
        f"2026-11-27T16:{m:02d}" for m in (0, 15, 30, 45)
    ]
    return {
        "minutely_15": {
            "time": times[: len(precip)],
            "precipitation": precip,
            "snowfall": snow or [0.0] * len(precip),
            "weather_code": [code if p else 3 for p in precip],
        }
    }


def _rain(data: Any, lat: float = 47.6, lon: float = -122.3, unit: str = "F") -> str:
    return nowcast.rain_soon_text(nowcast.parse(data, unit=unit, latitude=lat, longitude=lon))


def test_rain_starting_soon() -> None:
    assert _rain(_steps([0, 0, 0.01, 0.02, 0.02, 0, 0, 0])) == (
        "Light rain starting in about 30 minutes."
    )


def test_rain_now_and_stopping() -> None:
    assert _rain(_steps([0.05, 0.05, 0.05, 0, 0, 0, 0, 0])) == (
        "Moderate rain now, stopping in about 45 minutes."
    )


def test_dry_and_estimated_outside_native_coverage() -> None:
    text = _rain(_steps([0] * 8), lat=-33.9, lon=151.2, unit="C")
    assert text == (
        "No rain or snow expected in the next 2 hours. This is estimated from hourly data here."
    )


def test_snow_is_named_snow() -> None:
    data = _steps([0, 0, 0, 0, 0.01, 0.01, 0, 0], snow=[0, 0, 0, 0, 0.2, 0.2, 0, 0], code=73)
    assert _rain(data) == "Light snow starting in about an hour."


def test_the_request_asks_for_two_hours_of_15_minute_steps() -> None:
    url = nowcast.request_url(1, 2, unit="F")
    assert "minutely_15=precipitation%2Csnowfall%2Cweather_code" in url
    assert "forecast_minutely_15=8" in url and "precipitation_unit=inch" in url
