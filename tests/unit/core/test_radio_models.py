"""Tests for the RadioStation model (pure; no network)."""

from __future__ import annotations

from quill.core.radio.models import RadioStation


def test_display_name_includes_country_when_known() -> None:
    station = RadioStation(name="WXYZ", stream_url="https://example.com/stream", country="Canada")
    assert station.display_name == "WXYZ (Canada)"


def test_display_name_omits_country_when_unknown() -> None:
    station = RadioStation(name="WXYZ", stream_url="https://example.com/stream")
    assert station.display_name == "WXYZ"


def test_details_text_includes_key_fields() -> None:
    station = RadioStation(
        name="WXYZ",
        stream_url="https://example.com/stream",
        country="Canada",
        language="English",
        tags=("jazz", "smooth"),
        codec="MP3",
        bitrate_kbps=128,
        votes=42,
        homepage="https://example.com",
    )
    text = station.details_text
    assert "WXYZ" in text
    assert "Canada" in text and "English" in text
    assert "jazz, smooth" in text
    assert "MP3" in text and "128 kbps" in text
    assert "42" in text
    assert "https://example.com" in text.split()
    assert "https://example.com/stream" in text.split()


def test_to_dict_from_dict_round_trip() -> None:
    original = RadioStation(
        name="WXYZ",
        stream_url="https://example.com/stream",
        station_uuid="abc-123",
        homepage="https://example.com",
        favicon="https://example.com/favicon.ico",
        country="Canada",
        language="English",
        tags=("jazz", "smooth"),
        codec="MP3",
        bitrate_kbps=128,
        votes=42,
    )
    restored = RadioStation.from_dict(original.to_dict())
    assert restored == original


def test_from_dict_requires_name_and_stream_url() -> None:
    assert RadioStation.from_dict({"name": "", "stream_url": "https://x"}) is None
    assert RadioStation.from_dict({"name": "X", "stream_url": ""}) is None
    assert RadioStation.from_dict({}) is None


def test_from_dict_preserves_listener_saved_somafm_favorites() -> None:
    for data in (
        {"name": "Old favorite", "stream_url": "https://ice.somafm.com/live"},
        {
            "name": "Old favorite",
            "stream_url": "https://stream.example.org/live",
            "homepage": "https://somafm.com/",
        },
        {
            "name": "Old favorite",
            "stream_url": "https://stream.example.org/live",
            "source": "SomaFM",
        },
    ):
        station = RadioStation.from_dict(data)
        assert station is not None
        assert station.stream_url == data["stream_url"]


def test_from_dict_tolerates_junk_numeric_fields() -> None:
    station = RadioStation.from_dict({
        "name": "WXYZ",
        "stream_url": "https://example.com/stream",
        "bitrate_kbps": "not a number",
        "votes": None,
    })
    assert station is not None
    assert station.bitrate_kbps == 0
    assert station.votes == 0


def test_from_dict_coerces_float_and_string_numbers() -> None:
    station = RadioStation.from_dict({
        "name": "WXYZ",
        "stream_url": "https://example.com/stream",
        "bitrate_kbps": 128.0,
        "votes": "42",
    })
    assert station is not None
    assert station.bitrate_kbps == 128
    assert station.votes == 42
