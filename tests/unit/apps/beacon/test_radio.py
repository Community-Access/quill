"""Tests for radio depth: validation, alternates, program capture (PRD 9.1)."""

from quill.apps.beacon import radio
from quill.apps.beacon.model import TYPE_RADIO_PROGRAM, TYPE_RADIO_STATION


def test_validate_no_fetcher_returns_not_checked():
    r = radio.validate_stream("https://stream.example/live")
    assert r["reachable"] is None
    assert r["message"] == "not checked"


def test_validate_reachable():
    def fetcher(url, timeout):
        return (200, "audio/mpeg")

    r = radio.validate_stream("https://x", fetcher=fetcher)
    assert r["reachable"] is True
    assert r["mime"] == "audio/mpeg"


def test_validate_redirect_ok():
    def fetcher(url, timeout):
        return (302, "audio/ogg")

    r = radio.validate_stream("https://x", fetcher=fetcher)
    assert r["reachable"] is True


def test_validate_unreachable_status():
    def fetcher(url, timeout):
        return (404, "")

    r = radio.validate_stream("https://x", fetcher=fetcher)
    assert r["reachable"] is False


def test_validate_fetcher_none_result():
    def fetcher(url, timeout):
        return None

    r = radio.validate_stream("https://x", fetcher=fetcher)
    assert r["reachable"] is False
    assert r["message"] == "unreachable"


def test_validate_fetcher_raises_is_safe():
    def fetcher(url, timeout):
        raise ConnectionError("boom")

    r = radio.validate_stream("https://x", fetcher=fetcher)
    assert r["reachable"] is False
    assert "boom" in r["message"]


def test_validate_empty_url():
    r = radio.validate_stream("", fetcher=lambda u, t: (200, ""))
    assert r["reachable"] is None


def test_alternate_streams_scheme_flip():
    alts = radio.alternate_streams("https://stream.example/live")
    assert "http://stream.example/live" in alts
    assert "https://stream.example/live" not in alts


def test_alternate_streams_playlist_guesses():
    alts = radio.alternate_streams("https://radio.example/play.pls")
    assert any(a.endswith("/stream") for a in alts)
    assert any(a.endswith("/live") for a in alts)


def test_alternate_streams_dedupes_and_excludes_original():
    alts = radio.alternate_streams("https://x.example/listen.m3u")
    assert "https://x.example/listen.m3u" not in alts
    assert len(alts) == len(set(alts))


def test_alternate_streams_empty():
    assert radio.alternate_streams("") == []
    assert radio.alternate_streams("not a url") == []


def test_capture_program_builds_resource_and_beacon():
    b, res = radio.capture_program(
        station="KQED",
        program="Morning Edition",
        host="A Martinez",
        start_ms=21600000,
        end_ms=32400000,
        url="https://kqed.org/stream",
    )
    assert res.type == TYPE_RADIO_PROGRAM
    assert res.creator == "A Martinez"
    assert b.title == "Morning Edition"
    assert "KQED" in b.tags
    assert res.metadata["station"] == "KQED"
    assert b.locations[0].media_start_ms == 21600000


def test_station_from_stream_stores_alternates():
    b, res = radio.station_from_stream("https://radio.example/play.pls", title="Radio Example")
    assert res.type == TYPE_RADIO_STATION
    assert res.metadata["alternates"]
    assert b.title == "Radio Example"
