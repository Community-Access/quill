"""Find Streams, stream recovery and the live check read only the public internet.

What a page names on this computer or the listener's own network is never
contacted: not the page typed, not a link the live check would open, not a
broken favourite's homepage. The sentence says why, and points at My Servers.
"""

from __future__ import annotations

import socket
from typing import Any

import pytest

from quill.core import net_public
from quill.core.net_public import NotPublicAddress
from quill.core.radio import link_finder, live_check, radio_browser, triton
from quill.core.radio.find_streams_text import NOT_PUBLIC_SENTENCE, failure_sentence
from quill.core.radio.link_finder import LinkFinderError, PageStreamCandidate
from quill.core.radio.models import RadioStation
from quill.core.radio.recovery import recover_stream


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("the network was used")

    monkeypatch.setattr(socket, "getaddrinfo", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(net_public, "_proxy_for", lambda *_a: "")


@pytest.mark.parametrize(
    "typed",
    [
        "http://192.168.1.1/",
        "192.168.1.1",
        "localhost:8000",
        "http://nas.local/radio",
        "http://169.254.169.254/latest/meta-data/",
        "http://[::1]:8000/",
    ],
)
@pytest.mark.usefixtures("no_network")
def test_a_typed_local_address_is_refused_with_the_sentence(typed: str) -> None:
    with pytest.raises(LinkFinderError) as caught:
        link_finder.scan_page_for_streams(typed, check_live=True)
    assert failure_sentence(caught.value) == NOT_PUBLIC_SENTENCE


def test_the_sentence_points_at_my_servers() -> None:
    assert "My Servers in Browse Stations" in NOT_PUBLIC_SENTENCE
    assert failure_sentence(NotPublicAddress("x")) == NOT_PUBLIC_SENTENCE


def test_a_refused_link_is_left_out_not_listed(monkeypatch: pytest.MonkeyPatch) -> None:
    contacted: list[str] = []
    monkeypatch.setattr(net_public, "_proxy_for", lambda *_a: "")
    monkeypatch.setattr(net_public, "_lookup", lambda host, port: ["93.184.216.34"])

    def connect(address: str, port: int, *_a: Any) -> Any:
        contacted.append(f"{address}:{port}")
        raise ConnectionRefusedError("refused")

    monkeypatch.setattr(net_public, "_connect_pinned", connect)
    candidates = [
        PageStreamCandidate(url="http://192.168.1.20:8000/stream", reason="audio tag"),
        PageStreamCandidate(url="http://router/admin.mp3", reason="audio tag"),
        PageStreamCandidate(url="http://radio.example.org:8000/live", reason="audio tag"),
    ]
    kept, left_out = link_finder._apply_live_check(candidates)
    assert [c.url for c in kept] == ["http://radio.example.org:8000/live"]
    assert left_out == 2
    assert contacted == ["93.184.216.34:8000"]  # only the public link was opened


def test_the_live_check_verdict_for_a_refused_address() -> None:
    verdict = live_check._failure(NotPublicAddress("x"))
    assert verdict.state == live_check.NOT_AUDIO
    assert verdict.note == live_check.NOT_PUBLIC


@pytest.mark.usefixtures("no_network")
def test_recovery_never_reads_a_homepage_on_the_local_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(triton, "resolve_station_streams", lambda *a, **k: [])
    monkeypatch.setattr(radio_browser, "lookup_station", lambda *a, **k: None)
    station = RadioStation(
        name="Directory entry",
        stream_url="https://radio.example.org/dead.mp3",
        homepage="http://192.168.1.1/",
    )
    result = recover_stream(station)
    assert result.station is None
    assert not result.candidates
