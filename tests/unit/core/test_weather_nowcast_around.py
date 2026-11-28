"""Rain starting soon, the glance ahead, daylight change, chosen fields, Weather
Around Me, pollen, marine, the Open-Meteo gate, and the report extras."""

from __future__ import annotations

import urllib.error
from email.message import Message
from typing import Any

import pytest

from quill.core.weather import around, nowcast, open_meteo_limits, report_extras, sea_and_pollen
from quill.core.weather.models import WeatherLocation
from quill.core.weather.settings import WeatherSettings


def _cast(precip: list[float], *, snow: list[float] | None = None, code: int = 61) -> Any:
    times = [f"2026-11-27T15:{m:02d}" for m in (0, 15, 30, 45)] + [
        f"2026-11-27T16:{m:02d}" for m in (0, 15, 30, 45)
    ]
    return {
        "minutely_15": {
            "time": times[: len(precip)],
            "precipitation": precip,
            "snowfall": snow or [0.0] * len(precip),
            "weather_code": [code if p else 3 for p in precip],
        },
        "hourly": {
            "time": [f"2026-11-27T{h}:00" for h in (15, 16, 17, 18, 19)],
            "temperature_2m": [50, 49, 48, 47, 46],
            "precipitation_probability": [10, 20, 60, 30, 10],
            "weather_code": [3, 3, 61, 61, 3],
            "wind_speed_10m": [5, 6, 18, 9, 4],
        },
        "daily": {"time": ["2026-11-26", "2026-11-27"], "daylight_duration": [32000, 31880]},
    }


def _parse(data: Any, lat: float = 47.6, lon: float = -122.3, unit: str = "F") -> Any:
    return nowcast.parse(data, latitude=lat, longitude=lon, unit=unit)


def test_rain_starting_soon() -> None:
    cast = _parse(_cast([0, 0, 0.01, 0.02, 0.02, 0, 0, 0]))
    assert nowcast.rain_soon_text(cast) == "Light rain starting in about 30 minutes."


def test_rain_now_and_stopping() -> None:
    cast = _parse(_cast([0.05, 0.05, 0.05, 0, 0, 0, 0, 0]))
    assert nowcast.rain_soon_text(cast) == "Moderate rain now, stopping in about 45 minutes."


def test_dry_and_estimated_outside_native_coverage() -> None:
    cast = _parse(_cast([0] * 8), lat=-33.9, lon=151.2, unit="C")
    text = nowcast.rain_soon_text(cast)
    assert text.startswith("No rain or snow expected in the next 2 hours.")
    assert "estimated from hourly data" in text


def test_snow_is_named_snow() -> None:
    cast = _parse(_cast([0, 0, 0, 0, 0.01, 0.01, 0, 0], snow=[0, 0, 0, 0, 0.2, 0.2, 0, 0], code=73))
    assert nowcast.rain_soon_text(cast) == "Light snow starting in about an hour."


def test_daylight_and_glance() -> None:
    cast = _parse(_cast([0] * 8))
    assert nowcast.daylight_text(cast) == (
        "8 hours 51 minutes of daylight today, 2 minutes less than yesterday."
    )
    glance = nowcast.glance_text(cast)
    assert glance.startswith("Next 4 hours: 49 at 4:00 PM, falling to 46 by 7:00 PM.")
    assert "light rain at 5:00 PM" in glance.lower() or "rain at 5:00 PM" in glance
    assert "Chance of precipitation up to 60 percent." in glance
    assert "Wind up to 18 miles per hour." in glance


def test_extra_fields_follow_the_sent_units() -> None:
    assert nowcast.extra_field_text("wind_gusts_10m", 22.4, "mp/h", metric=False) == (
        "Wind gusts: 22 miles per hour."
    )
    assert nowcast.extra_field_text("visibility", 52800, "ft", metric=False) == (
        "Visibility: 10.0 miles."
    )
    assert nowcast.extra_field_text("snow_depth", 0.5, "m", metric=True) == (
        "Snow on the ground: 50 centimetres."
    )
    assert nowcast.extra_field_text("is_day", 0, "", metric=True) == "It is night."
    url = nowcast.request_url(1, 2, unit="F", extra_fields=["cape", "not_a_field"])
    assert url.endswith("current=cape") and "not_a_field" not in url


# -- around -------------------------------------------------------------------------


def _reply(precip: float = 0.0, code: int = 3, wind_from: float = 270, wind: float = 20) -> Any:
    return {
        "current": {
            "precipitation": precip,
            "snowfall": 0.0,
            "weather_code": code,
            "wind_speed_10m": wind,
            "wind_direction_10m": wind_from,
        }
    }


def test_rain_to_the_west_moving_toward_you() -> None:
    spots = around.points(40.0, -100.0)
    assert len(spots) == 17
    replies = [_reply() for _ in spots]
    west_inner = next(i for i, s in enumerate(spots) if s[0] == 270 and s[1] == 40.0)
    replies[west_inner] = _reply(0.5, 63, wind_from=270)  # westerly wind: it comes east
    east_outer = next(i for i, s in enumerate(spots) if s[0] == 90 and s[1] == 80.0)
    replies[east_outer] = _reply(0.5, 71, wind_from=270)
    lines = around.describe(around.parse(replies, 40.0, -100.0))
    assert lines[0] == "Dry here now."
    assert lines[1] == "Rain 25 miles west, moving toward you."
    assert lines[2] == "Snow 50 miles east, moving away."
    assert lines[-1] == around.CAVEAT


def test_nothing_around() -> None:
    lines = around.describe(around.parse([_reply() for _ in range(17)], 1, 2), metric=True)
    assert lines == [
        "Dry here now.",
        "No rain or snow within about 80 kilometres in any direction.",
    ]


def test_one_request_weighted_by_place_count() -> None:
    url, weight = around.request_url(40.0, -100.0)
    assert weight == 17 and url.count("%2C") >= 32


def test_offset_goes_the_right_way() -> None:
    lat, lon = around.offset(40.0, -100.0, 90, 80)
    assert abs(lat - 40.0) < 0.05 and lon > -100.0


# -- pollen and marine --------------------------------------------------------------


def test_pollen_is_europe_only() -> None:
    calls: list[str] = []
    assert sea_and_pollen.fetch_pollen(32, -110, get=lambda u, **k: calls.append(u)) is None
    assert calls == []
    pollen = sea_and_pollen.parse_pollen({"current": {"birch_pollen": 120.0, "grass_pollen": 4.0}})
    assert sea_and_pollen.pollen_text(pollen) == "Pollen: birch high, grass low."
    zero = sea_and_pollen.parse_pollen({"current": {"birch_pollen": 0.0}})
    assert sea_and_pollen.pollen_text(zero) == "Pollen: none in the air right now."


def test_marine_inland_is_none_and_coast_is_words() -> None:
    assert sea_and_pollen.parse_marine({"current": {"wave_height": None}}) is None
    marine = sea_and_pollen.parse_marine({
        "current": {
            "wave_height": 3.0,
            "wave_direction": 282,
            "wave_period": 13.7,
            "swell_wave_height": 2.98,
            "sea_surface_temperature": 19.2,
        }
    })
    assert sea_and_pollen.marine_text(marine) == (
        "Sea: waves 10 feet from the west every 14 seconds, swell 10 feet, "
        "sea temperature 67 degrees."
    )


# -- the Open-Meteo gate -----------------------------------------------------------


@pytest.fixture
def gate(monkeypatch: pytest.MonkeyPatch) -> Any:
    clock = {"t": 1_800_000_000.0}
    monkeypatch.setattr(open_meteo_limits.GATE, "clock", lambda: clock["t"])
    open_meteo_limits.GATE.reset()
    yield clock
    open_meteo_limits.GATE.reset()


def test_backs_off_after_429(gate: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def throttled(url: str) -> Any:
        calls.append(url)
        headers = Message()
        headers["Retry-After"] = "120"
        raise urllib.error.HTTPError(url, 429, "Too Many", headers, None)

    monkeypatch.setattr(open_meteo_limits, "http_json", throttled)
    url = "https://api.open-meteo.com/v1/forecast?x=1"
    with pytest.raises(urllib.error.HTTPError):
        open_meteo_limits.get_json(url)
    with pytest.raises(open_meteo_limits.OpenMeteoBusy, match="slow down"):
        open_meteo_limits.get_json(url)
    assert len(calls) == 1  # the second was never sent
    gate["t"] += 121
    with pytest.raises(urllib.error.HTTPError):
        open_meteo_limits.get_json(url)


def test_daily_budget_and_hosts(gate: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(open_meteo_limits, "http_json", lambda url: {})
    with pytest.raises(ValueError):
        open_meteo_limits.get_json("https://example.com/")
    open_meteo_limits.get_json("https://api.open-meteo.com/v1/x", weight=17)
    assert open_meteo_limits.GATE.used == 17
    monkeypatch.setattr(open_meteo_limits.GATE, "used", open_meteo_limits.DAILY_BUDGET)
    with pytest.raises(open_meteo_limits.OpenMeteoBusy, match="allows itself"):
        open_meteo_limits.get_json("https://api.open-meteo.com/v1/x")


# -- report extras -----------------------------------------------------------------


def test_extras_say_failures_and_skip_inland_after_one_ask() -> None:
    report_extras.forget_inland()
    location = WeatherLocation("Tucson", 32.2, -110.9, id="t")
    asked: list[str] = []

    def get(url: str, **_k: Any) -> Any:
        asked.append(url)
        if "marine-api" in url:
            return {"current": {"wave_height": None}}
        raise urllib.error.URLError("down")

    settings = WeatherSettings()
    first = report_extras.gather(location, settings, get=get)
    assert any("could not get this" in line for line in first.lines())
    assert not first.marine and not first.pollen
    report_extras.gather(location, settings, get=get)
    assert sum("marine-api" in u for u in asked) == 1
    assert not any("air-quality" in u for u in asked)  # not in Europe
    report_extras.forget_inland()
