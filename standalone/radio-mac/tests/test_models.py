"""Tests for quill_radio_mac.core.models (the RadioStation record).

Covers to_dict/from_dict round trips, the lenient _coerce_int used for
loosely-typed JSON fields, rejection of records missing a name or
stream URL, and the accessible display/detail strings. No wx, no IO.
"""

from __future__ import annotations

from quill_radio_mac.core.models import RadioStation, _coerce_int


def _sample_station() -> RadioStation:
    return RadioStation(
        name="SomaFM Groove Salad",
        stream_url="https://ice.somafm.com/groovesalad-128-mp3",
        station_uuid="abc-123",
        homepage="https://somafm.com/groovesalad/",
        favicon="https://somafm.com/img/groovesalad.png",
        country="United States",
        language="english",
        tags=("ambient", "chill"),
        codec="MP3",
        bitrate_kbps=128,
        votes=4521,
    )


def test_round_trip_preserves_all_fields():
    station = _sample_station()
    rebuilt = RadioStation.from_dict(station.to_dict())
    assert rebuilt == station


def test_to_dict_serializes_tags_as_list():
    data = _sample_station().to_dict()
    assert data["tags"] == ["ambient", "chill"]


def test_from_dict_requires_name_and_stream_url():
    assert RadioStation.from_dict({"name": "", "stream_url": "x"}) is None
    assert RadioStation.from_dict({"name": "x", "stream_url": ""}) is None
    assert RadioStation.from_dict({"name": "  ", "stream_url": "  "}) is None
    assert RadioStation.from_dict({}) is None


def test_from_dict_defaults_optional_fields():
    station = RadioStation.from_dict({"name": "A", "stream_url": "http://a/s"})
    assert station is not None
    assert station.station_uuid == ""
    assert station.tags == ()
    assert station.bitrate_kbps == 0
    assert station.votes == 0


def test_from_dict_coerces_loose_numeric_strings():
    station = RadioStation.from_dict(
        {"name": "A", "stream_url": "u", "bitrate_kbps": "128.0", "votes": "42"}
    )
    assert station is not None
    assert station.bitrate_kbps == 128
    assert station.votes == 42


def test_from_dict_ignores_non_list_tags():
    station = RadioStation.from_dict({"name": "A", "stream_url": "u", "tags": "ambient"})
    assert station is not None
    assert station.tags == ()


def test_coerce_int_cases():
    assert _coerce_int(5) == 5
    assert _coerce_int(5.9) == 5
    assert _coerce_int("7") == 7
    assert _coerce_int("7.5") == 7
    assert _coerce_int("") == 0
    assert _coerce_int("   ") == 0
    assert _coerce_int("nope") == 0
    assert _coerce_int(None) == 0
    assert _coerce_int(True) == 0
    assert _coerce_int(False, default=3) == 3
    assert _coerce_int(object(), default=9) == 9


def test_display_name_with_and_without_country():
    with_country = _sample_station()
    assert with_country.display_name == "SomaFM Groove Salad (United States)"
    bare = RadioStation(name="Bare", stream_url="u")
    assert bare.display_name == "Bare"


def test_details_text_lists_known_fields():
    text = _sample_station().details_text
    assert "SomaFM Groove Salad" in text
    assert "Location/language: United States, english" in text
    assert "Tags: ambient, chill" in text
    assert "Format: MP3 128 kbps" in text
    assert "Community votes: 4521" in text
    assert "Homepage: https://somafm.com/groovesalad/" in text
    assert "Stream URL: https://ice.somafm.com/groovesalad-128-mp3" in text
