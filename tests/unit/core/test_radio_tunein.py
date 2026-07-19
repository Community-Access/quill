"""Tests for the TuneIn/RadioTime directory client (pure parsing; no network)."""

from __future__ import annotations

import pytest

import quill.core.radio.tunein as tunein
from quill.core.radio.tunein import (
    TuneInError,
    TuneInResult,
    browse_row_to_station,
    classify_nav,
    guide_id_from_page,
    nav_up_row,
    parse_directory_results,
    parse_tune_response,
    refuse_in_safe_mode,
)


def test_browse_row_and_classify_roundtrip() -> None:
    cat = browse_row_to_station(TuneInResult(guide_id="c9", title="Music", is_station=False))
    assert classify_nav(cat) == ("category", "c9")
    assert "[browse]" in cat.name  # a screen reader hears it's a folder
    assert cat.stream_url == ""

    sta = browse_row_to_station(
        TuneInResult(guide_id="s42", title="Jazz FM", subtitle="smooth", is_station=True)
    )
    assert classify_nav(sta) == ("station", "s42")
    assert sta.name == "Jazz FM" and sta.source == "TuneIn"
    assert sta.stream_url == ""  # unresolved until played

    assert classify_nav(nav_up_row()) == ("up", "")


def test_classify_nav_leaves_normal_stations_untouched() -> None:
    from quill.core.radio.models import RadioStation

    normal = RadioStation(name="WXYZ", stream_url="https://x/s", station_uuid="abc-123")
    assert classify_nav(normal) == ("", "")  # not a browse row -> normal playback


def test_refuse_in_safe_mode() -> None:
    with pytest.raises(TuneInError):
        refuse_in_safe_mode(True)
    refuse_in_safe_mode(False)  # no raise


def test_guide_id_from_page() -> None:
    assert guide_id_from_page("https://tunein.com/radio/BBC-Radio-1-s24939/") == "s24939"
    assert guide_id_from_page('config = {"guideId":"s99999"}') == "s99999"
    assert guide_id_from_page("https://example.com/nope") is None


_SEARCH_JSON = """
{
  "head": {"status": "200"},
  "body": [
    {"element": "outline", "type": "audio", "text": "BBC Radio 1",
     "guide_id": "s24939", "subtext": "The best new music", "image": "http://img/1.png"},
    {"element": "outline", "type": "link", "text": "Local Radio", "guide_id": "c57943"},
    {"element": "outline", "type": "audio", "text": "", "guide_id": "s1"},
    {"element": "outline", "type": "audio", "text": "No id here"}
  ]
}
"""


def test_parse_directory_results_stations_and_categories() -> None:
    results = parse_directory_results(_SEARCH_JSON)
    # The two well-formed rows survive; the title-less and id-less ones drop.
    by_id = {r.guide_id: r for r in results}
    assert set(by_id) == {"s24939", "c57943"}
    station = by_id["s24939"]
    assert station.is_station is True
    assert station.title == "BBC Radio 1"
    assert station.subtitle == "The best new music"
    assert station.image == "http://img/1.png"
    assert by_id["c57943"].is_station is False  # a browse category


def test_parse_directory_results_handles_nested_children() -> None:
    nested = """
    {"body": [{"element": "outline", "text": "Music", "guide_id": "c1", "children": [
        {"element": "outline", "type": "audio", "text": "Jazz FM", "guide_id": "s500"}
    ]}]}
    """
    ids = {r.guide_id for r in parse_directory_results(nested)}
    assert ids == {"c1", "s500"}


def test_parse_directory_results_bad_json_is_empty() -> None:
    assert parse_directory_results("not json") == []
    assert parse_directory_results("{}") == []


def test_parse_tune_response_returns_urls_and_skips_status() -> None:
    body = (
        "https://open.live.bbc.co.uk/mediaselector/bbc_radio_one?jwt_auth=ABC\n"
        "https://as-hls-ww.live.cf.md.bbci.co.uk/x.m3u8\n"
    )
    urls = parse_tune_response(body)
    assert urls == [
        "https://open.live.bbc.co.uk/mediaselector/bbc_radio_one?jwt_auth=ABC",
        "https://as-hls-ww.live.cf.md.bbci.co.uk/x.m3u8",
    ]


def test_parse_tune_response_error_status_is_empty() -> None:
    assert parse_tune_response("#STATUS: 400 Bad Request") == []
    assert parse_tune_response("") == []


def test_search_and_resolve_go_through_fetch(monkeypatch) -> None:
    calls: list[str] = []

    def fake_fetch(url: str) -> str:
        calls.append(url)
        if "Search.ashx" in url:
            return _SEARCH_JSON
        return "https://cdn.example/bbc.m3u8\n"

    monkeypatch.setattr(tunein, "_fetch", fake_fetch)
    results = tunein.search("bbc radio 1")
    assert any(r.guide_id == "s24939" for r in results)
    streams = tunein.resolve_station_streams("s24939")
    assert streams == ["https://cdn.example/bbc.m3u8"]
    assert any("query=bbc" in c.replace("+", " ").replace("%20", " ").lower() for c in calls)
    assert any("Tune.ashx" in c and "partnerId=RadioTime" in c for c in calls)


def test_search_empty_query_makes_no_request(monkeypatch) -> None:
    monkeypatch.setattr(
        tunein, "_fetch", lambda url: (_ for _ in ()).throw(AssertionError("no net"))
    )
    assert tunein.search("   ") == []
    assert tunein.resolve_station_streams("") == []


def test_to_radio_station_carries_source() -> None:
    result = tunein.TuneInResult(guide_id="s24939", title="BBC Radio 1", is_station=True)
    station = tunein.to_radio_station(result, "https://cdn/bbc.m3u8")
    assert station.source == "TuneIn"
    assert station.station_uuid == "s24939"
    assert station.stream_url == "https://cdn/bbc.m3u8"
