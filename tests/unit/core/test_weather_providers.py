"""QUILL Weather providers: geocoding (Zippopotam) and the NWS client.

All parsing is exercised against inline fixtures; the few fetch paths stub the
shared http_json so no real network is touched.
"""

from __future__ import annotations

import pytest

from quill.core.weather import geocoding, nws
from quill.core.weather.geocoding import GeocodeResult, WeatherGeocodeError
from quill.core.weather.models import WeatherLocation
from quill.core.weather.nws import WeatherError

# -- geocoding ----------------------------------------------------------------


def test_parse_latlon_accepts_valid_and_rejects_out_of_range() -> None:
    r = geocoding.parse_latlon("32.22, -110.97")
    assert r is not None and r.latitude == 32.22 and r.longitude == -110.97
    assert geocoding.parse_latlon("999,999") is None
    assert geocoding.parse_latlon("Tucson") is None


def test_geocode_latlon_makes_no_network_call(monkeypatch) -> None:
    monkeypatch.setattr(
        geocoding, "http_json", lambda *a, **k: pytest.fail("no network for bare coords")
    )
    r = geocoding.geocode("32.2,-110.9")
    assert r.latitude == 32.2 and r.longitude == -110.9


def test_geocode_zip_hits_zippopotam(monkeypatch) -> None:
    seen: dict[str, str] = {}
    payload = {
        "post code": "85701",
        "places": [
            {
                "place name": "Tucson",
                "state abbreviation": "AZ",
                "latitude": "32.2139",
                "longitude": "-110.9694",
            }
        ],
    }
    monkeypatch.setattr(geocoding, "http_json", lambda url: seen.update(url=url) or payload)
    r = geocoding.geocode("85701")
    assert "zippopotam.us/us/85701" in seen["url"]
    assert r.name == "Tucson" and r.state == "AZ" and r.latitude == 32.2139
    assert r.display_name == "Tucson, AZ"


def test_geocode_city_state_hits_state_city_endpoint(monkeypatch) -> None:
    seen: dict[str, str] = {}
    payload = {
        "places": [
            {
                "place name": "Austin",
                "state abbreviation": "TX",
                "latitude": "30.27",
                "longitude": "-97.74",
            }
        ]
    }
    monkeypatch.setattr(geocoding, "http_json", lambda url: seen.update(url=url) or payload)
    r = geocoding.geocode("Austin, TX")
    assert "/us/TX/Austin" in seen["url"]
    assert r.state == "TX"


def test_geocode_refuses_in_safe_mode_for_network_but_allows_coords() -> None:
    with pytest.raises(WeatherGeocodeError):
        geocoding.geocode("85701", safe_mode=True)
    # bare coordinates need no network, so Safe Mode still resolves them
    assert geocoding.geocode("32.2,-110.9", safe_mode=True).latitude == 32.2


def test_geocode_unknown_place_raises(monkeypatch) -> None:
    monkeypatch.setattr(geocoding, "http_json", lambda url: {"places": []})
    with pytest.raises(WeatherGeocodeError):
        geocoding.geocode("00000")


def test_result_from_zippopotam_bad_shape_raises() -> None:
    with pytest.raises(WeatherGeocodeError):
        geocoding.result_from_zippopotam("junk", "x")
    with pytest.raises(WeatherGeocodeError):
        geocoding.result_from_zippopotam({"places": [{"latitude": "n/a"}]}, "x")


# -- NWS unit helpers ---------------------------------------------------------


def test_unit_conversions() -> None:
    assert nws.c_to_f(0) == 32.0
    assert nws.c_to_f(100) == 212.0
    assert nws.c_to_f(None) is None
    assert nws.mps_to_mph(10) == 22.4
    assert nws.degrees_to_compass(0) == "N"
    assert nws.degrees_to_compass(90) == "E"
    assert nws.degrees_to_compass(315) == "NW"
    assert nws.degrees_to_compass(None) == ""


# -- NWS parsers --------------------------------------------------------------


def test_point_from_json_extracts_grid_and_urls() -> None:
    data = {
        "properties": {
            "gridId": "TWC",
            "gridX": 91,
            "gridY": 116,
            "forecast": "https://api.weather.gov/gridpoints/TWC/91,116/forecast",
            "forecastHourly": "https://api.weather.gov/gridpoints/TWC/91,116/forecast/hourly",
            "observationStations": "https://api.weather.gov/gridpoints/TWC/91,116/stations",
            "forecastZone": "https://api.weather.gov/zones/forecast/AZZ504",
            "county": "https://api.weather.gov/zones/county/AZC019",
            "relativeLocation": {"properties": {"city": "Tucson", "state": "AZ"}},
        }
    }
    p = nws.point_from_json(data)
    assert p.office == "TWC" and p.grid_x == 91 and p.grid_y == 116
    assert p.forecast_zone == "AZZ504" and p.county_zone == "AZC019"
    assert p.city == "Tucson" and p.state == "AZ"


def test_point_from_json_bad_shape_raises() -> None:
    with pytest.raises(WeatherError):
        nws.point_from_json("nope")
    with pytest.raises(WeatherError):
        nws.point_from_json({"no_properties": True})


def test_periods_from_json_parses_and_limits() -> None:
    periods = {
        "properties": {
            "periods": [
                {
                    "name": "This Afternoon",
                    "temperature": 96,
                    "temperatureUnit": "F",
                    "shortForecast": "Slight Chance Showers",
                    "detailedForecast": "Hot.",
                    "windSpeed": "5 mph",
                    "windDirection": "WNW",
                    "probabilityOfPrecipitation": {"value": 20},
                    "isDaytime": True,
                },
                {
                    "name": "Tonight",
                    "temperature": 71,
                    "temperatureUnit": "F",
                    "shortForecast": "Clear",
                    "isDaytime": False,
                    "probabilityOfPrecipitation": {"value": None},
                },
                {"no_name": True},  # skipped
            ]
        }
    }
    out = nws.periods_from_json(periods, limit=1)
    assert len(out) == 1  # limit honored
    out = nws.periods_from_json(periods)
    assert [p.name for p in out] == ["This Afternoon", "Tonight"]
    assert out[0].precipitation_percent == 20 and out[0].wind_direction == "WNW"
    assert out[1].precipitation_percent is None and out[1].is_daytime is False


def test_observation_from_json_converts_units() -> None:
    # NWS reports SI with a unitCode: temperature degC, wind km/h.
    data = {
        "properties": {
            "textDescription": "Clear",
            "temperature": {"value": 33.0, "unitCode": "wmoUnit:degC"},
            "relativeHumidity": {"value": 31.7, "unitCode": "wmoUnit:percent"},
            "windSpeed": {"value": 22.212, "unitCode": "wmoUnit:km_h-1"},
            "windDirection": {"value": 90, "unitCode": "wmoUnit:degree_(angle)"},
            "station": "https://api.weather.gov/stations/KTUS",
            "timestamp": "2026-07-19T20:00:00+00:00",
        }
    }
    c = nws.observation_from_json(data)
    assert c.text_description == "Clear"
    assert c.temperature_c == 33.0 and c.temperature_f == 91.4
    assert c.humidity_percent == 32
    assert c.wind_speed_mph == 13.8  # 22.212 km/h, not treated as m/s
    assert c.wind_direction == "E" and c.station_id == "KTUS"


def test_observation_from_json_honors_fahrenheit_and_ms_units() -> None:
    data = {
        "properties": {
            "temperature": {"value": 50.0, "unitCode": "wmoUnit:degF"},
            "windSpeed": {"value": 10.0, "unitCode": "wmoUnit:m_s-1"},
        }
    }
    c = nws.observation_from_json(data)
    assert c.temperature_f == 50.0 and c.temperature_c == 10.0
    assert c.wind_speed_mph == 22.4  # 10 m/s


def test_observation_from_json_missing_values_are_none() -> None:
    c = nws.observation_from_json({"properties": {"temperature": {"value": None}}})
    assert c.temperature_f is None and c.wind_speed_mph is None


def test_alerts_from_json_sorts_most_severe_first() -> None:
    data = {
        "features": [
            {
                "properties": {
                    "id": "a1",
                    "event": "Heat Advisory",
                    "severity": "Moderate",
                    "urgency": "Expected",
                    "certainty": "Likely",
                }
            },
            {
                "properties": {
                    "id": "a2",
                    "event": "Tornado Warning",
                    "severity": "Extreme",
                    "urgency": "Immediate",
                    "certainty": "Observed",
                    "instruction": "Take shelter now.",
                }
            },
            {"properties": {"no_event": True}},  # skipped
        ]
    }
    alerts = nws.alerts_from_json(data)
    assert [a.event for a in alerts] == ["Tornado Warning", "Heat Advisory"]
    assert alerts[0].tier == "Critical" and alerts[1].tier == "Advisory"
    assert alerts[0].instruction == "Take shelter now."


# -- fetch orchestration ------------------------------------------------------


def _point_payload() -> dict:
    return {
        "properties": {
            "gridId": "TWC",
            "gridX": 1,
            "gridY": 2,
            "forecast": "https://api.weather.gov/f",
            "forecastHourly": "https://api.weather.gov/fh",
            "observationStations": "https://api.weather.gov/st",
            "forecastZone": "https://x/AZZ504",
            "county": "https://x/AZC019",
            "relativeLocation": {"properties": {"city": "Tucson", "state": "AZ"}},
        }
    }


def test_fetch_report_degrades_when_observation_fails(monkeypatch) -> None:
    from quill.core.weather._http import HTTP_ERRORS  # noqa: F401

    def fake(url: str):
        if "points/" in url:
            return _point_payload()
        if url.endswith("/f"):
            return {
                "properties": {
                    "periods": [
                        {
                            "name": "Now",
                            "temperature": 96,
                            "temperatureUnit": "F",
                            "shortForecast": "Hot",
                        }
                    ]
                }
            }
        if url.endswith("/st"):
            raise OSError("stations down")
        if "alerts/active" in url:
            return {"features": []}
        return {}

    monkeypatch.setattr(nws, "http_json", fake)
    loc = WeatherLocation(display_name="Home", latitude=32.2, longitude=-110.9)
    report = nws.fetch_report(loc)
    assert report.office == "TWC"
    assert [p.name for p in report.periods] == ["Now"]
    assert report.current is None
    assert any("Current conditions" in n for n in report.notes)
    assert report.location.resolved_name == "Tucson, AZ"


def test_resolve_point_and_alerts_refuse_in_safe_mode() -> None:
    with pytest.raises(WeatherError):
        nws.resolve_point(32.2, -110.9, safe_mode=True)
    with pytest.raises(WeatherError):
        nws.active_alerts(32.2, -110.9, safe_mode=True)
    with pytest.raises(WeatherError):
        nws.fetch_report(WeatherLocation("x", 32.2, -110.9), safe_mode=True)


def test_geocode_result_display_name_falls_back_to_query() -> None:
    r = GeocodeResult(latitude=1, longitude=2, name="", state="", query="1,2")
    assert r.display_name == "1,2"
