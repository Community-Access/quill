"""Tests for the Radio Paradise source -- pure, no network.

The fixture is trimmed from a live ``list_chan`` reply of 2026-08-26, including
the two things that shape the code: ``current_listeners`` arrives as a *string*,
and Serenity offers only two of the six qualities. Every stream name asserted
here was requested against the live server before it was written down; the
station named itself in its own ``icy-name`` header each time.
"""

from __future__ import annotations

import json

import pytest

from quill.core.radio import browse_sources as bs
from quill.core.radio import radio_paradise as rp

_LIST_CHAN = json.dumps([
    {"chan": "0", "title": "The Main Mix", "slug": "main-mix", "current_listeners": "6623"},
    {"chan": "1", "title": "Mellow Mix", "slug": "mellow", "current_listeners": "3036"},
    {"chan": "42", "title": "Serenity", "slug": "serenity", "current_listeners": "61"},
    {"chan": "945", "title": "KFAT", "slug": "kfat", "current_listeners": "141"},
    {"chan": "9", "title": "No Slug", "current_listeners": "1"},
])


def _by_name(payload: str = _LIST_CHAN) -> dict[str, object]:
    return {station.name: station for station in rp.parse_channels(payload)}


# --- the naming pattern, verified against the live server ----------------------


def test_the_main_mix_uses_codec_names_not_its_slug() -> None:
    rows = _by_name()
    assert rows["The Main Mix (320k AAC)"].stream_url == (
        "https://stream.radioparadise.com/aac-320"
    )
    assert rows["The Main Mix (192k MP3)"].stream_url == (
        "https://stream.radioparadise.com/mp3-192"
    )
    assert rows["The Main Mix (FLAC (lossless))"].stream_url == (
        "https://stream.radioparadise.com/flacm"
    )


def test_every_other_channel_uses_its_slug() -> None:
    rows = _by_name()
    assert rows["Mellow Mix (128k AAC)"].stream_url == (
        "https://stream.radioparadise.com/mellow-128"
    )
    assert rows["KFAT (FLAC (lossless))"].stream_url == (
        "https://stream.radioparadise.com/kfat-flacm"
    )


def test_serenity_offers_only_the_two_qualities_it_actually_has() -> None:
    """A row that 404s at play time is worse than a row that is not offered."""
    serenity = [name for name in _by_name() if name.startswith("Serenity")]
    assert sorted(serenity) == ["Serenity (64k AAC+)", "Serenity (FLAC (lossless))"]
    rows = _by_name()
    assert rows["Serenity (64k AAC+)"].stream_url == "https://stream.radioparadise.com/serenity"
    assert rows["Serenity (FLAC (lossless))"].stream_url == (
        "https://stream.radioparadise.com/serenity-flac"
    )


def test_radio_2050_is_added_because_the_api_omits_it() -> None:
    rows = _by_name()
    assert rows["Radio 2050 (320k AAC)"].stream_url == (
        "https://stream.radioparadise.com/radio2050-320"
    )


def test_a_channel_with_no_slug_is_skipped() -> None:
    assert not any(name.startswith("No Slug") for name in _by_name())


# --- the rows themselves -------------------------------------------------------


def test_the_best_lossy_quality_is_offered_first() -> None:
    """The first row per channel is what Enter lands on."""
    names = [station.name for station in rp.parse_channels(_LIST_CHAN)]
    assert names[0] == "The Main Mix (320k AAC)"
    assert names[5] == "The Main Mix (FLAC (lossless))"


def test_listeners_are_read_from_the_string_the_api_sends() -> None:
    rows = _by_name()
    assert rows["The Main Mix (320k AAC)"].listeners == 6623
    # ...and are the channel's, so every quality row of that channel agrees.
    assert rows["The Main Mix (32k AAC+)"].listeners == 6623
    # Radio 2050 is not in the API, so it claims no audience rather than zero
    # listeners -- which reads the same but is not the same claim.
    assert rows["Radio 2050 (320k AAC)"].listeners == 0


def test_flac_declares_no_bitrate_rather_than_inventing_one() -> None:
    rows = _by_name()
    flac = rows["The Main Mix (FLAC (lossless))"]
    assert flac.codec == "FLAC" and flac.bitrate_kbps == 0
    assert "Format: FLAC" in flac.details_text


def test_live_listeners_reach_the_details_panel_and_read_as_live() -> None:
    text = _by_name()["The Main Mix (320k AAC)"].details_text
    assert "Live listeners: 6,623" in text
    assert "Community votes" not in text


def test_no_station_carries_a_radio_browser_uuid() -> None:
    assert all(station.station_uuid == "" for station in rp.parse_channels(_LIST_CHAN))


def test_garbage_still_yields_the_channel_the_api_never_mentions() -> None:
    """A shape change should cost the rows it broke, not the ones it did not."""
    for payload in ("", "not json", "{}"):
        names = [station.name for station in rp.parse_channels(payload)]
        assert names and all(name.startswith("Radio 2050") for name in names)


# --- Safe Mode and search ------------------------------------------------------


def test_safe_mode_refuses_the_fetch() -> None:
    with pytest.raises(rp.RadioParadiseError):
        rp.fetch_stations(safe_mode=True)


def test_search_returns_nothing_in_safe_mode_rather_than_raising() -> None:
    assert rp.search_stations("mellow", safe_mode=True) == []


def test_search_matches_channel_names_and_the_station_itself(monkeypatch) -> None:
    monkeypatch.setattr(rp, "fetch_stations", lambda **_kw: rp.parse_channels(_LIST_CHAN))
    assert all("Mellow" in s.name for s in rp.search_stations("mellow"))
    # Somebody searching for the station by name gets all of its channels.
    assert len(rp.search_stations("radio paradise")) == len(rp.parse_channels(_LIST_CHAN))


def test_the_branch_is_flat_and_playable(monkeypatch) -> None:
    monkeypatch.setattr(rp, "fetch_stations", lambda **_kw: rp.parse_channels(_LIST_CHAN))
    nodes = bs.browse("radioparadise")
    assert nodes and not any(node.is_folder for node in nodes)
    assert nodes[0].label.startswith("The Main Mix")


def test_a_failing_api_is_an_empty_branch_not_an_exception(monkeypatch) -> None:
    def _fail(**_kw):
        raise rp.RadioParadiseError("down")

    monkeypatch.setattr(rp, "fetch_stations", _fail)
    assert bs.browse("radioparadise") == []
