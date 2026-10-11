from __future__ import annotations

from types import SimpleNamespace

import pytest

from quill.core.radio import website_overrides


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("radio.example.org/now", "https://radio.example.org/now"),
        ("http://radio.example.org", "http://radio.example.org"),
        (
            "https://radio.example.org:8443/listen?channel=1",
            "https://radio.example.org:8443/listen?channel=1",
        ),
        ("", None),
        ("javascript:alert(1)", None),
        ("https://user:password@radio.example.org", None),
        ("https://radio example.org", None),
        ("https://radio.example.org:99999", None),
    ],
)
def test_normalize_website_validates_http_addresses(value: str, expected: str | None) -> None:
    assert website_overrides.normalize_website(value) == expected


def test_local_override_wins_without_changing_the_provider_station() -> None:
    station = SimpleNamespace(
        source="SomaFM",
        station_uuid="",
        name="Groove Salad",
        stream_url="https://stream.example.org/groovesalad",
        homepage="https://somafm.com/groovesalad",
    )
    key = website_overrides.station_key(station)
    assert key
    assert (
        website_overrides.website_for(station, {key: "https://example.org/my-station"})
        == "https://example.org/my-station"
    )
    assert station.homepage == "https://somafm.com/groovesalad"


def test_stations_sharing_a_stream_do_not_share_overrides_when_names_differ() -> None:
    one = SimpleNamespace(
        source="Radio Browser",
        station_uuid="",
        name="Station One",
        stream_url="https://shared.example.org/live",
    )
    two = SimpleNamespace(
        source="Radio Browser",
        station_uuid="",
        name="Station Two",
        stream_url="https://shared.example.org/live",
    )
    assert website_overrides.station_key(one) != website_overrides.station_key(two)


def test_an_empty_override_deliberately_clears_a_provider_website() -> None:
    station = SimpleNamespace(
        source="SomaFM",
        station_uuid="",
        name="Groove Salad",
        stream_url="https://stream.example.org/groovesalad",
        homepage="https://somafm.com/groovesalad",
    )
    assert (
        website_overrides.website_for(station, {website_overrides.station_key(station): ""}) == ""
    )
