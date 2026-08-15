"""Tests for the RadioBrowser browse axes (country/state/language/trending).

Pure request-shape and parsing tests: `_http_json` is replaced so no network is
touched. What these assert is the thing that actually breaks -- the URL we ask
for -- because every one of these axes is a correct-endpoint problem, not a
parsing problem. The trailing slash on /json/states is the case in point: the
API answers an empty list rather than an error when it is missing.
"""

from __future__ import annotations

import pytest

from quill.core.radio import radio_browser as rb


@pytest.fixture
def captured(monkeypatch):
    """Capture requested paths; return station-shaped or name-shaped JSON."""
    paths: list[str] = []

    def fake_http_json(path: str):
        paths.append(path)
        if "/json/stations" in path:
            return [
                {
                    "name": "Test FM",
                    "url_resolved": "https://a.example/s",
                    "stationuuid": "uuid-1",
                }
            ]
        return [{"name": "California", "stationcount": 10}, {"name": "Texas", "stationcount": 9}]

    monkeypatch.setattr(rb, "_http_json", fake_http_json)
    return paths


def test_list_states_scoped_to_a_country_keeps_the_required_trailing_slash(captured) -> None:
    # /json/states/{country}/{searchterm}: without the empty search term's slash
    # the API returns [] rather than an error, which reads as "no states".
    rb.list_states("Germany")
    assert "/json/states/Germany/?" in captured[0]


def test_list_states_unscoped_has_no_stray_slash(captured) -> None:
    rb.list_states()
    assert captured[0].startswith("/json/states?")


def test_list_states_url_quotes_a_country_with_spaces(captured) -> None:
    rb.list_states("The United States Of America")
    assert "/json/states/The%20United%20States%20Of%20America/?" in captured[0]


def test_list_languages_orders_by_station_count(captured) -> None:
    assert rb.list_languages() == ["California", "Texas"]  # names, whatever they are
    assert "/json/languages?" in captured[0]
    assert "order=stationcount" in captured[0] and "reverse=true" in captured[0]


def test_stations_by_state_filters_and_orders_by_clicks(captured) -> None:
    stations = rb.stations_by_state("Arizona", country="The United States Of America")
    assert [s.name for s in stations] == ["Test FM"]
    path = captured[0]
    assert "state=Arizona" in path
    assert "country=The+United+States+Of+America" in path
    assert "order=clickcount" in path and "hidebroken=true" in path


def test_stations_by_language_filters(captured) -> None:
    rb.stations_by_language("spanish")
    assert "language=spanish" in captured[0]


def test_trending_and_popular_are_different_endpoints(captured) -> None:
    rb.trending_stations(20)
    rb.popular_stations(20)
    assert "/json/stations/topclick/20" in captured[0]
    assert "/json/stations/topvote/20" in captured[1]


def test_recently_changed_uses_lastchange(captured) -> None:
    rb.recently_changed_stations(20)
    assert "/json/stations/lastchange/20" in captured[0]


def test_limits_are_clamped_to_the_api_maximum(captured) -> None:
    rb.trending_stations(9999)
    assert "/json/stations/topclick/200" in captured[0]
    captured.clear()
    rb.recently_changed_stations(0)
    assert "/json/stations/lastchange/1" in captured[0]


def test_blank_scopes_make_no_request(monkeypatch) -> None:
    def boom(path: str):
        raise AssertionError(f"no request expected, got {path}")

    monkeypatch.setattr(rb, "_http_json", boom)
    assert rb.stations_by_country("  ") == []
    assert rb.stations_by_state("") == []
    assert rb.stations_by_language("\t") == []


def test_every_axis_refuses_in_safe_mode(monkeypatch) -> None:
    def boom(path: str):
        raise AssertionError("safe mode must refuse before any request")

    monkeypatch.setattr(rb, "_http_json", boom)
    for call in (
        lambda: rb.list_states(safe_mode=True),
        lambda: rb.list_languages(safe_mode=True),
        lambda: rb.stations_by_country("Germany", safe_mode=True),
        lambda: rb.stations_by_state("Arizona", safe_mode=True),
        lambda: rb.stations_by_language("english", safe_mode=True),
        lambda: rb.trending_stations(safe_mode=True),
        lambda: rb.recently_changed_stations(safe_mode=True),
    ):
        with pytest.raises(rb.RadioBrowserError):
            call()
