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
    kept, left_out, not_public = link_finder._apply_live_check(candidates)
    assert [c.url for c in kept] == ["http://radio.example.org:8000/live"]
    assert (left_out, not_public) == (0, 2)
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


# -- the review of #2006: never call a local link "not audio" --------------------------


def test_local_links_are_counted_apart_from_not_audio(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(net_public, "_proxy_for", lambda *_a: "")
    monkeypatch.setattr(
        link_finder.live_check,
        "check_urls",
        lambda urls, get, **k: {
            urls[0]: live_check.Verdict(live_check.NOT_AUDIO, note=live_check.NOT_PUBLIC),
            urls[1]: live_check.Verdict(live_check.NOT_AUDIO, note="a web page"),
            urls[2]: live_check.Verdict(live_check.NOT_AUDIO, note=live_check.NOT_PUBLIC),
        },
    )
    rows = [PageStreamCandidate(url=f"http://x{n}.example/", reason="a") for n in range(3)]
    kept, left_out, not_public = link_finder._apply_live_check(rows)
    assert (kept, left_out, not_public) == ([], 1, 2)


def test_a_page_of_only_local_links_says_so() -> None:
    from quill.core.radio.find_streams_text import summary_sentence

    assert summary_sentence([], checked=True, not_public=2) == (
        "Found 2 links on that page, but they are on this computer or your own network, "
        "which Find Streams does not scan. To list a server on your network, add it under "
        "My Servers in Browse Stations."
    )
    assert summary_sentence([], checked=True, not_public=1).startswith(
        "Found 1 link on that page, but it is on this computer"
    )


def test_a_page_of_local_and_not_audio_links_says_both() -> None:
    from quill.core.radio.find_streams_text import summary_sentence

    assert summary_sentence([], checked=True, left_out=3, not_public=2) == (
        "Found 5 links on that page: 3 were not audio, and 2 are on your own network, "
        "which Find Streams does not scan."
    )
    assert summary_sentence([], checked=True, left_out=1, not_public=1) == (
        "Found 2 links on that page: 1 was not audio, and 1 is on your own network, "
        "which Find Streams does not scan."
    )


def test_the_status_line_counts_local_links_apart() -> None:
    from quill.core.radio.find_streams_text import status_label

    rows = [PageStreamCandidate(url="https://s.example/live", reason="a", check="live")]
    assert status_label(rows, checked=True, left_out=3, not_public=2).endswith(
        "Left out 3 links that were not audio or no longer there, and 2 on your own network."
    )
    assert status_label(rows, checked=True, not_public=1).endswith(
        "Left out 1 link on your own network."
    )


def test_the_base_message_has_no_support_code_in_plain_words() -> None:
    assert net_public.NOT_PUBLIC_SENTENCE == (
        "That address is on this computer or your own network, which QUILL does not scan."
    )


@pytest.mark.usefixtures("no_network")
def test_search_all_says_the_sentence_not_the_support_code() -> None:
    from quill.core.radio import federated_browse

    rows, why = federated_browse._website("http://192.168.1.1/", safe_mode=False)
    assert rows == []
    assert why == NOT_PUBLIC_SENTENCE
    assert "QUILL-" not in why


def test_the_station_browser_says_the_sentence_not_the_support_code() -> None:
    from types import SimpleNamespace

    from quill.ui.radio.station_browser_dialog import StationBrowserDialog

    shown: list[str] = []
    fake = SimpleNamespace(
        _search_btn=SimpleNamespace(Enable=lambda _on: None),
        _status=SimpleNamespace(SetLabel=shown.append),
    )
    error = LinkFinderError("Could not reach that page: x")
    error.__cause__ = NotPublicAddress("x")
    StationBrowserDialog._on_website_scan_done(fake, [], error)  # type: ignore[arg-type]
    assert shown == [NOT_PUBLIC_SENTENCE]
