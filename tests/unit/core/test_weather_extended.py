"""QUILL Weather extended sources: Nominatim search (candidate lists) and the
Open-Meteo daily outlook. Parsing against inline fixtures; fetch paths stub the
shared http_json."""

from __future__ import annotations

import pytest

from quill.core.weather import geocoding, open_meteo
from quill.core.weather.geocoding import WeatherGeocodeError
from quill.core.weather.open_meteo import OpenMeteoError

# -- Nominatim search ---------------------------------------------------------


def test_search_returns_multiple_candidates(monkeypatch) -> None:
    seen: dict[str, str] = {}
    payload = [
        {
            "lat": "39.7817",
            "lon": "-89.6501",
            "display_name": "Springfield, Illinois",
            "address": {"city": "Springfield", "state": "Illinois"},
        },
        {
            "lat": "37.2090",
            "lon": "-93.2923",
            "display_name": "Springfield, Missouri",
            "address": {"city": "Springfield", "state": "Missouri"},
        },
    ]
    monkeypatch.setattr(geocoding, "http_json", lambda url: seen.update(url=url) or payload)
    results = geocoding.search("Springfield")
    assert "nominatim.openstreetmap.org/search" in seen["url"]
    assert [r.state for r in results] == ["Illinois", "Missouri"]
    assert results[0].display_name == "Springfield, Illinois"  # full_name disambiguates


def test_search_is_worldwide_not_us_only(monkeypatch) -> None:
    # #1187: search must not be limited to the US, so Brno, Czech Republic resolves.
    seen: dict[str, str] = {}
    payload = [
        {
            "lat": "49.1951",
            "lon": "16.6068",
            "display_name": "Brno, South Moravian Region, Czech Republic",
            "address": {"city": "Brno", "state": "South Moravian Region"},
        }
    ]
    monkeypatch.setattr(geocoding, "http_json", lambda url: seen.update(url=url) or payload)
    results = geocoding.search("Brno")
    assert "countrycodes" not in seen["url"]  # no US-only filter
    assert results[0].name == "Brno"
    assert "Czech Republic" in results[0].display_name


def test_open_meteo_fetch_report_builds_current_and_daily(monkeypatch) -> None:
    # #1187: non-US locations get a full Open-Meteo report (current + daily).
    from quill.core.weather.models import WeatherLocation

    payload = {
        "current": {
            "time": "2026-07-20T12:00",
            "temperature_2m": 21.0,
            "apparent_temperature": 20.0,
            "relative_humidity_2m": 55,
            "weather_code": 2,
            "wind_speed_10m": 8.0,
            "wind_direction_10m": 90,
            "cloud_cover": 40,
        },
        "daily": {
            "time": ["2026-07-20"],
            "weathercode": [2],
            "temperature_2m_max": [25.0],
            "temperature_2m_min": [15.0],
            "precipitation_probability_max": [10],
            "sunrise": ["2026-07-20T05:00"],
            "sunset": ["2026-07-20T21:00"],
            "uv_index_max": [6.0],
        },
    }
    monkeypatch.setattr(open_meteo, "http_json", lambda _url: payload)
    monkeypatch.setattr(open_meteo, "air_quality", lambda *_a, **_k: None)
    loc = WeatherLocation(display_name="Brno", latitude=49.1951, longitude=16.6068)

    report = open_meteo.fetch_report(loc, unit="C")

    assert report.current is not None
    assert report.current.temperature_c == 21.0
    assert report.current.text_description == "Partly cloudy"
    assert report.current.wind_direction == "E"  # 90 degrees
    assert len(report.daily) == 1
    assert any("Open-Meteo" in note for note in report.notes)


def test_fetch_report_worldwide_falls_back_to_open_meteo(monkeypatch) -> None:
    # #1187: NWS covers only the US; outside it, fall back to Open-Meteo.
    from quill.core.weather import nws
    from quill.core.weather.models import WeatherLocation, WeatherReport

    loc = WeatherLocation(display_name="Brno", latitude=49.1951, longitude=16.6068)
    sentinel = WeatherReport(location=loc)

    def _nws_fails(*_a, **_k):
        raise nws.WeatherError("Point is outside US coverage.")

    monkeypatch.setattr(nws, "fetch_report", _nws_fails)
    monkeypatch.setattr(open_meteo, "fetch_report", lambda *_a, **_k: sentinel)

    assert nws.fetch_report_worldwide(loc, temperature_unit="C") is sentinel


def test_search_latlon_is_local_single_result(monkeypatch) -> None:
    monkeypatch.setattr(
        geocoding, "http_json", lambda *a, **k: pytest.fail("no network for coords")
    )
    results = geocoding.search("32.2, -110.9")
    assert len(results) == 1 and results[0].latitude == 32.2


def test_search_refuses_in_safe_mode() -> None:
    with pytest.raises(WeatherGeocodeError):
        geocoding.search("Tucson", safe_mode=True)


def test_results_from_nominatim_skips_bad_rows() -> None:
    data = [
        {"lat": "1.0", "lon": "2.0", "display_name": "A", "address": {"town": "A", "state": "TX"}},
        {"lat": "bad"},  # skipped
        "junk",  # skipped
    ]
    results = geocoding.results_from_nominatim(data, "x")
    assert len(results) == 1 and results[0].name == "A"


# -- Open-Meteo daily outlook -------------------------------------------------


def test_weather_code_text_and_weekday() -> None:
    assert open_meteo.weather_code_text(0) == "Clear"
    assert open_meteo.weather_code_text(95) == "Thunderstorm"
    assert open_meteo.weather_code_text(999) == "Unknown"
    assert open_meteo.weekday_name("2026-07-20") == "Monday"  # a known Monday
    assert open_meteo.weekday_name("bad") == ""


def test_daily_from_json_parses_rows_and_astro() -> None:
    data = {
        "daily": {
            "time": ["2026-07-20", "2026-07-21"],
            "weathercode": [0, 95],
            "temperature_2m_max": [98.4, 90.1],
            "temperature_2m_min": [74.6, 72.0],
            "precipitation_probability_max": [0, 60],
            "sunrise": ["2026-07-20T05:42", "2026-07-21T05:43"],
            "sunset": ["2026-07-20T19:38", "2026-07-21T19:37"],
            "uv_index_max": [9, 8],
        }
    }
    rows = open_meteo.daily_from_json(data, unit="F")
    assert len(rows) == 2
    assert rows[0].weekday == "Monday" and rows[0].high_temp == 98 and rows[0].low_temp == 75
    assert rows[0].condition == "Clear"
    assert rows[0].sunrise == "5:42 AM" and rows[0].sunset == "7:38 PM" and rows[0].uv_index == 9
    assert rows[0].line == (
        "Monday, July 20: Clear. High 98, low 75 degrees. Sunrise 5:42 AM, sunset 7:38 PM."
    )
    assert rows[1].condition == "Thunderstorm" and rows[1].precipitation_percent == 60
    assert "60 percent chance of precipitation" in rows[1].line


def test_fetch_reads_cloud_cover_and_refuses_safe_mode(monkeypatch) -> None:
    seen: dict[str, str] = {}
    monkeypatch.setattr(
        open_meteo,
        "http_json",
        lambda url: (
            seen.update(url=url)
            or {"current": {"cloud_cover": 42}, "daily": {"time": [], "weathercode": []}}
        ),
    )
    data = open_meteo.fetch(32.2, -110.9, days=10, unit="C")
    assert "api.open-meteo.com/v1/forecast" in seen["url"]
    assert "forecast_days=10" in seen["url"] and "temperature_unit=celsius" in seen["url"]
    assert "current=cloud_cover" in seen["url"]
    assert data.cloud_cover_percent == 42
    with pytest.raises(OpenMeteoError):
        open_meteo.fetch(32.2, -110.9, safe_mode=True)


def test_daily_forecast_clamps_days(monkeypatch) -> None:
    seen: dict[str, str] = {}
    monkeypatch.setattr(open_meteo, "http_json", lambda url: seen.update(url=url) or {})
    open_meteo.daily_forecast(1, 2, days=99)
    assert "forecast_days=16" in seen["url"]  # capped at Open-Meteo's max


def test_air_quality_parses_and_categorizes(monkeypatch) -> None:
    seen: dict[str, str] = {}
    monkeypatch.setattr(
        open_meteo,
        "http_json",
        lambda url: seen.update(url=url) or {"current": {"us_aqi": 142, "pm2_5": 33.4}},
    )
    aq = open_meteo.air_quality(32.2, -110.9)
    assert "air-quality-api.open-meteo.com" in seen["url"]
    assert aq is not None and aq.us_aqi == 142
    assert aq.category == "Unhealthy for sensitive groups" and aq.pm2_5 == 33.4
    assert open_meteo.aqi_category(30) == "Good" and open_meteo.aqi_category(500) == "Hazardous"


def test_air_quality_none_on_failure(monkeypatch) -> None:
    def boom(url):
        raise OSError("down")

    monkeypatch.setattr(open_meteo, "http_json", boom)
    assert open_meteo.air_quality(1, 2) is None
