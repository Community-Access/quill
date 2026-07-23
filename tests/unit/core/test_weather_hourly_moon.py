"""Hourly forecast parsing and moon integration into the daily outlook,
rendering, and settings round-trip. Pure -- no network, no wx."""

from __future__ import annotations

from quill.core.weather import nws, open_meteo, render
from quill.core.weather import settings as settings_mod
from quill.core.weather.models import DailyOutlook, HourlyPeriod
from quill.core.weather.settings import WeatherSettings

# -- NWS hourly parser --------------------------------------------------------

_HOURLY_FIXTURE = {
    "properties": {
        "periods": [
            {
                "startTime": "2026-07-19T15:00:00-07:00",
                "temperature": 99,
                "temperatureUnit": "F",
                "shortForecast": "Sunny",
                "probabilityOfPrecipitation": {"value": 0},
                "windSpeed": "10 mph",
                "windDirection": "SW",
                "isDaytime": True,
            },
            {
                "startTime": "2026-07-19T16:30:00-07:00",
                "temperature": 97,
                "temperatureUnit": "F",
                "shortForecast": "Slight Chance Showers",
                "probabilityOfPrecipitation": {"value": 20},
                "windSpeed": "12 mph",
                "windDirection": "SW",
                "isDaytime": True,
            },
        ]
    }
}


def test_hourly_from_json_parses_rows() -> None:
    rows = nws.hourly_from_json(_HOURLY_FIXTURE)
    assert [r.temperature for r in rows] == [99, 97]
    assert rows[0].time == "3 PM"
    assert rows[1].time == "4:30 PM"  # off-the-hour keeps the minutes
    assert rows[0].precipitation_percent == 0
    assert rows[1].precipitation_percent == 20


def test_hourly_from_json_respects_limit() -> None:
    assert len(nws.hourly_from_json(_HOURLY_FIXTURE, limit=1)) == 1


def test_friendly_hour_edges() -> None:
    assert nws._friendly_hour("2026-01-01T00:00:00-05:00") == "12 AM"
    assert nws._friendly_hour("2026-01-01T12:00:00-05:00") == "12 PM"
    assert nws._friendly_hour("bogus") == ""


def test_hourly_line_is_spoken() -> None:
    period = HourlyPeriod(
        time="3 PM",
        temperature=99,
        temperature_unit="F",
        short_forecast="Sunny",
        precipitation_percent=20,
    )
    line = period.line
    assert "3 PM: 99 degrees Fahrenheit, Sunny." in line
    assert "20 percent chance of precipitation." in line


def test_fetch_report_pulls_hourly(monkeypatch) -> None:
    from quill.core.weather.models import WeatherLocation

    point = nws.PointMetadata(
        office="TWC",
        grid_x=1,
        grid_y=1,
        forecast_url="https://api.weather.gov/f",
        hourly_forecast_url="https://api.weather.gov/h",
        observation_stations_url="",
        forecast_zone="AZZ",
        county_zone="AZC",
        city="Tucson",
        state="AZ",
        time_zone="America/Phoenix",
    )
    monkeypatch.setattr(nws, "resolve_point", lambda *a, **k: point)

    def fake_http(url: str, **_kw):
        if url == "https://api.weather.gov/h":
            return _HOURLY_FIXTURE
        return {"properties": {"periods": []}}

    monkeypatch.setattr(nws, "http_json", fake_http)
    monkeypatch.setattr(nws, "active_alerts", lambda *a, **k: [])
    loc = WeatherLocation(display_name="Tucson", latitude=32.22, longitude=-110.97)
    report = nws.fetch_report(loc, daily_days=0, hourly_hours=12)
    assert [h.temperature for h in report.hourly] == [99, 97]


def test_fetch_report_skips_hourly_when_zero(monkeypatch) -> None:
    from quill.core.weather.models import WeatherLocation

    point = nws.PointMetadata(
        office="TWC",
        grid_x=1,
        grid_y=1,
        forecast_url="https://api.weather.gov/f",
        hourly_forecast_url="https://api.weather.gov/h",
        observation_stations_url="",
        forecast_zone="",
        county_zone="",
        city="",
        state="",
        time_zone="",
    )
    monkeypatch.setattr(nws, "resolve_point", lambda *a, **k: point)
    calls: list[str] = []

    def fake_http(url: str, **_kw):
        calls.append(url)
        return {"properties": {"periods": []}}

    monkeypatch.setattr(nws, "http_json", fake_http)
    monkeypatch.setattr(nws, "active_alerts", lambda *a, **k: [])
    loc = WeatherLocation(display_name="x", latitude=1.0, longitude=2.0)
    nws.fetch_report(loc, daily_days=0, hourly_hours=0)
    assert "https://api.weather.gov/h" not in calls  # no hourly pull when off


# -- moon in the daily outlook ------------------------------------------------

_DAILY_FIXTURE = {
    "utc_offset_seconds": -25200,  # -7h (US Mountain)
    "daily": {
        "time": ["2000-01-21"],
        "weathercode": [0],
        "temperature_2m_max": [55],
        "temperature_2m_min": [40],
        "precipitation_probability_max": [10],
        "sunrise": ["2000-01-21T07:25"],
        "sunset": ["2000-01-21T17:40"],
        "uv_index_max": [3],
    },
}


def test_daily_from_json_fills_moon_when_located() -> None:
    rows = open_meteo.daily_from_json(
        _DAILY_FIXTURE, unit="F", latitude=32.22, longitude=-110.97, utc_offset_hours=-7.0
    )
    assert rows[0].moon_phase == "Full Moon"  # 2000-01-21 is a full moon
    assert rows[0].moon_illumination_percent == 100
    assert rows[0].moonrise  # a full moon rises in the evening


def test_daily_from_json_omits_moon_without_coordinates() -> None:
    rows = open_meteo.daily_from_json(_DAILY_FIXTURE, unit="F")
    assert rows[0].moon_phase == ""
    assert rows[0].moonrise == ""


def test_daily_line_includes_moon() -> None:
    day = DailyOutlook(
        date="2000-01-21",
        weekday="Friday",
        high_temp=55,
        low_temp=40,
        temperature_unit="F",
        condition="Clear",
        moon_phase="Full Moon",
        moon_illumination_percent=100,
        moonrise="6:40 PM",
        moonset="7:49 AM",
    )
    line = day.line
    assert "Moon full moon, 100 percent lit." in line
    assert "Moonrise 6:40 PM, moonset 7:49 AM." in line


# -- moon rendering + settings ------------------------------------------------


def test_moon_phrase_and_block_gate() -> None:
    today = DailyOutlook(
        date="2000-01-21",
        weekday="Friday",
        high_temp=55,
        low_temp=40,
        temperature_unit="F",
        condition="Clear",
        moon_phase="Full Moon",
        moon_illumination_percent=100,
        moonrise="6:40 PM",
        moonset="7:49 AM",
    )
    phrase = render.moon_phrase(today)
    assert "full moon" in phrase and "100 percent lit" in phrase
    assert "rises at 6:40 PM and sets at 7:49 AM" in phrase

    from quill.core.weather.models import CurrentConditions

    current = CurrentConditions(temperature_f=50.0, text_description="Clear")
    on = WeatherSettings()
    on.show_moon = True
    assert "moon" in render.current_conditions_block(current, today, on).lower()
    off = WeatherSettings()
    off.show_moon = False
    assert "moon" not in render.current_conditions_block(current, today, off).lower()


def test_settings_round_trip_moon_and_hourly(tmp_path) -> None:
    s = WeatherSettings()
    s.show_moon = False
    s.hourly_hours = 6
    settings_mod.save_settings(tmp_path, s)
    loaded = settings_mod.load_settings(tmp_path)
    assert loaded.show_moon is False
    assert loaded.hourly_hours == 6


def test_hourly_hours_clamped() -> None:
    s = WeatherSettings()
    s.hourly_hours = 999
    s.normalized()
    assert s.hourly_hours == 48
