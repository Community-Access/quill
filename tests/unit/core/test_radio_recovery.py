"""Tests for self-healing stream recovery (issue #1065)."""

from __future__ import annotations

import pytest

from quill.core.radio import link_finder, radio_browser, triton
from quill.core.radio.link_finder import PageScanResult, PageStreamCandidate
from quill.core.radio.models import RadioStation
from quill.core.radio.recovery import (
    RecoveryResult,
    recover_stream,
    streamtheworld_mount,
)
from quill.core.radio.triton import TritonStream

_STW = "https://14613.live.streamtheworld.com/KMGLFM"


def _station(**kw: object) -> RadioStation:
    base = {
        "name": "Magic 104.1",
        "stream_url": "https://example.com/dead.mp3",
        "station_uuid": "",
        "homepage": "",
    }
    base.update(kw)
    return RadioStation(**base)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (_STW, "KMGLFM"),
        ("https://29306.live.streamtheworld.com/WABCFMAAC", "WABCFMAAC"),
        ("https://example.com/stream.mp3", ""),
        ("https://streamtheworld.com/", ""),
    ],
)
def test_streamtheworld_mount(url: str, expected: str) -> None:
    assert streamtheworld_mount(url) == expected


def test_safe_mode_short_circuits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        triton, "resolve_station_streams", lambda *a, **k: pytest.fail("no network in safe mode")
    )
    result = recover_stream(_station(stream_url=_STW), safe_mode=True)
    assert result == RecoveryResult(message="Stream recovery is off in Safe Mode.")


def test_strategy_a_reresolves_streamtheworld(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        triton,
        "resolve_station_streams",
        lambda mount: [
            TritonStream(
                url="https://29306.live.streamtheworld.com/KMGLFM", mount="KMGLFM", codec="MP3"
            )
        ],
    )
    result = recover_stream(_station(stream_url=_STW, station_uuid="u1"))
    assert result.source == "streamtheworld"
    assert result.station is not None
    assert result.station.stream_url == "https://29306.live.streamtheworld.com/KMGLFM"
    assert result.station.name == "Magic 104.1"  # identity preserved


def test_strategy_a_skips_when_resolve_returns_same_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        triton,
        "resolve_station_streams",
        lambda mount: [TritonStream(url=_STW, mount="KMGLFM", codec="MP3")],
    )
    # Same address that just failed -> no help; falls through to "not found".
    result = recover_stream(_station(stream_url=_STW), allow_website=False)
    assert result.station is None
    assert "Could not find" in result.message


def test_strategy_b_refreshes_from_directory(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(triton, "resolve_station_streams", lambda *a, **k: [])
    fresh = _station(stream_url="https://cdn.example.com/live", station_uuid="u1")
    monkeypatch.setattr(radio_browser, "lookup_station", lambda uuid, **k: fresh)
    result = recover_stream(_station(station_uuid="u1"))
    assert result.source == "directory"
    assert result.station is fresh


def test_strategy_b_ignores_unchanged_directory_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(triton, "resolve_station_streams", lambda *a, **k: [])
    same = _station(stream_url="https://example.com/dead.mp3", station_uuid="u1")
    monkeypatch.setattr(radio_browser, "lookup_station", lambda uuid, **k: same)
    result = recover_stream(_station(station_uuid="u1"), allow_website=False)
    assert result.station is None


def test_strategy_c_single_website_candidate_is_confident(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(triton, "resolve_station_streams", lambda *a, **k: [])
    monkeypatch.setattr(radio_browser, "lookup_station", lambda *a, **k: None)
    scan = PageScanResult(
        page_title="Magic 104.1",
        favicon_url="",
        candidates=[PageStreamCandidate(url="https://good.example.com/live", reason="audio tag")],
    )
    monkeypatch.setattr(link_finder, "scan_page_for_streams", lambda page, **k: scan)
    result = recover_stream(_station(homepage="https://magic104.com"))
    assert result.source == "website"
    assert result.station is not None
    assert result.station.stream_url == "https://good.example.com/live"


def test_strategy_c_lone_triton_hit_is_confident_even_beside_others(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(triton, "resolve_station_streams", lambda *a, **k: [])
    monkeypatch.setattr(radio_browser, "lookup_station", lambda *a, **k: None)
    scan = PageScanResult(
        page_title="",
        favicon_url="",
        candidates=[
            PageStreamCandidate(url="https://guess.example.com/maybe.mp3", reason="stream-shaped"),
            PageStreamCandidate(
                url="https://29306.live.streamtheworld.com/KMGLFM", reason="MP3 stream"
            ),
        ],
    )
    monkeypatch.setattr(link_finder, "scan_page_for_streams", lambda page, **k: scan)
    result = recover_stream(_station(homepage="https://magic104.com"))
    assert result.station is not None
    assert "streamtheworld" in result.station.stream_url


def test_strategy_c_lone_securenet_mount_is_confident_even_beside_others(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A station saved from a SecureNet player page self-heals on first failure.

    These are the three candidates the real Radio Once More player page yields
    (reported 2026-08-07): the true mount plus two ordinary links that happen to
    survive the scan. Before the mount counted as resolved, three candidates
    read as "ambiguous" and the station stayed broken purely because its page
    was chatty.
    """
    monkeypatch.setattr(triton, "resolve_station_streams", lambda *a, **k: [])
    monkeypatch.setattr(radio_browser, "lookup_station", lambda *a, **k: None)
    scan = PageScanResult(
        page_title="Radio Once More",
        favicon_url="",
        candidates=[
            PageStreamCandidate(
                url="https://ice66.securenetsystems.net/ROM",
                reason="stream from the station's player (ROM)",
            ),
            PageStreamCandidate(
                url="https://streamdb3web.securenetsystems.net", reason="stream-shaped"
            ),
            PageStreamCandidate(
                url="https://streamdb3web.securenetsystems.net/v5/index.cfm?retry=true",
                reason="stream-shaped",
            ),
        ],
    )
    monkeypatch.setattr(link_finder, "scan_page_for_streams", lambda page, **k: scan)
    result = recover_stream(_station(homepage="https://streamdb3web.securenetsystems.net/v5/ROM"))
    assert result.station is not None
    assert result.station.stream_url == "https://ice66.securenetsystems.net/ROM"


def test_strategy_c_two_securenet_mounts_stay_ambiguous(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Being a resolved mount promotes a *lone* hit, never a genuine choice."""
    monkeypatch.setattr(triton, "resolve_station_streams", lambda *a, **k: [])
    monkeypatch.setattr(radio_browser, "lookup_station", lambda *a, **k: None)
    scan = PageScanResult(
        page_title="",
        favicon_url="",
        candidates=[
            PageStreamCandidate(url="https://ice66.securenetsystems.net/ROM", reason="player"),
            PageStreamCandidate(url="https://ice25.securenetsystems.net/WARL", reason="player"),
        ],
    )
    monkeypatch.setattr(link_finder, "scan_page_for_streams", lambda page, **k: scan)
    result = recover_stream(_station(homepage="https://example.com"))
    assert result.station is None


def test_strategy_c_multiple_guesses_are_presented_not_played(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(triton, "resolve_station_streams", lambda *a, **k: [])
    monkeypatch.setattr(radio_browser, "lookup_station", lambda *a, **k: None)
    scan = PageScanResult(
        page_title="",
        favicon_url="",
        candidates=[
            PageStreamCandidate(url="https://a.example.com/one.mp3", reason="stream-shaped"),
            PageStreamCandidate(url="https://b.example.com/two.mp3", reason="stream-shaped"),
        ],
    )
    monkeypatch.setattr(link_finder, "scan_page_for_streams", lambda page, **k: scan)
    result = recover_stream(_station(homepage="https://magic104.com"))
    assert result.station is None
    assert len(result.candidates) == 2
    assert "2 possible streams" in result.message


def test_website_disabled_by_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(triton, "resolve_station_streams", lambda *a, **k: [])
    monkeypatch.setattr(radio_browser, "lookup_station", lambda *a, **k: None)
    monkeypatch.setattr(
        link_finder,
        "scan_page_for_streams",
        lambda *a, **k: pytest.fail("website scan must not run when allow_website=False"),
    )
    result = recover_stream(_station(homepage="https://magic104.com"), allow_website=False)
    assert result.station is None
    assert result.candidates == ()


def test_scans_failed_url_as_a_page_when_it_looks_like_a_website(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Gene pasted the site's play-button URL (a web page, not a stream); the
    # failed URL itself should be scanned when there's no homepage.
    monkeypatch.setattr(triton, "resolve_station_streams", lambda *a, **k: [])
    monkeypatch.setattr(radio_browser, "lookup_station", lambda *a, **k: None)
    scanned: list[str] = []

    def fake_scan(page: str, **_k: object) -> PageScanResult:
        scanned.append(page)
        return PageScanResult(page_title="", favicon_url="", candidates=[])

    monkeypatch.setattr(link_finder, "scan_page_for_streams", fake_scan)
    recover_stream(_station(stream_url="https://magic104.com/listen"))
    assert scanned == ["https://magic104.com/listen"]
