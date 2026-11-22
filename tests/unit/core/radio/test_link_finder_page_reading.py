"""Find Streams: the places a page is read, HTTP-only sites, and the live check.

Ideas from Andre Louis's StreamSift (https://github.com/OnjLouis/StreamSift),
tested against recorded pages in ``fixtures/live_check``. No network: page
fetches and candidate probes are both answered from dictionaries.
"""

from __future__ import annotations

import ssl
import urllib.error
from pathlib import Path

import pytest

import quill.core.radio.link_finder as lf
from quill.core.radio.live_check import HttpReply
from quill.core.radio.page_links import StreamLinkParser, radio_co_stream
from quill.core.radio.stream_pick import pick_stream

_FIXTURES = Path(__file__).parent / "fixtures" / "live_check"
_HOME = "https://kxyz.example.org"


def _text(name: str) -> str:
    return (_FIXTURES / name).read_text(encoding="utf-8")


def _bytes(name: str) -> bytes:
    return (_FIXTURES / name).read_bytes()


def _pages(extra: dict[str, str] | None = None) -> dict[str, str]:
    script = "https://kxyz.example.org/wp-content/plugins/radio-player/js/radio-player.min.js"
    pages = {
        _HOME: _text("wordpress_station.html"),
        f"{script}?ver=2.1": _text("radio_player_script.js"),
        "https://kxyz.example.org/popup-player/": (
            '<audio src="https://pop.kxyz.example.org/live.mp3"></audio>'
        ),
        "http://ice.kxyz.example.org:8000/status-json.xsl": _text("icecast_status.json"),
    }
    pages.update(extra or {})
    return pages


@pytest.fixture
def site(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    fetched: list[str] = []
    pages = _pages()

    def fetch(url: str) -> str:
        fetched.append(url)
        if url not in pages:
            raise lf.LinkFinderError(f"not recorded: {url}")
        return pages[url]

    monkeypatch.setattr(lf, "_fetch_html", fetch)
    return fetched


def _urls() -> list[str]:
    return [c.url for c in lf.scan_page_for_streams(_HOME).candidates]


def test_player_data_attributes_are_read_including_comma_lists(site: list[str]) -> None:
    urls = _urls()
    assert "https://stream.kxyz.example.org:8443/live" in urls
    assert "https://stream.kxyz.example.org/backup" in urls
    assert "https://stream2.kxyz.example.org/aac" in urls
    # A lazily loaded image (data-src on an <img>) is not a stream.
    assert not any(u.endswith((".png", ".jpg")) for u in urls)


def test_key_url_config_is_read_after_unescaping_even_with_no_extension(site: list[str]) -> None:
    urls = _urls()
    assert "https://cast.kxyz.example.org/radio/8000/radio" in urls
    assert "https://cast.kxyz.example.org/hls/radio/live.m3u8" in urls
    assert "https://kxyz.example.org/art.jpg" not in urls


def test_base_href_changes_what_relative_links_mean(site: list[str]) -> None:
    assert "https://kxyz.example.org/site/podcasts/episode-12.mp3" in _urls()


def test_an_address_written_as_plain_text_is_found(site: list[str]) -> None:
    assert "https://stream.kxyz.example.org/live.m3u" in _urls()


def test_a_radio_co_embed_maps_to_its_stream(site: list[str]) -> None:
    assert "https://streaming.radio.co/sd71de59b3/listen" in _urls()
    assert radio_co_stream("https://player.radio.co/sd71de59b3/mini") == (
        "https://streaming.radio.co/sd71de59b3/listen"
    )
    assert radio_co_stream("https://player.radio.co/about") == ""
    assert radio_co_stream("https://evil.example/sd71de59b3/") == ""


def test_the_sites_own_player_script_is_read_and_no_other(site: list[str]) -> None:
    urls = _urls()
    assert "https://cast.kxyz.example.org/radio/8000/radio.mp3" in urls
    assert not any("menu.js" in u or "jquery" in u for u in site)


def test_a_window_open_pop_up_player_is_followed(site: list[str]) -> None:
    assert "https://pop.kxyz.example.org/live.mp3" in _urls()


def test_an_icecast_status_page_lists_its_mounts(site: list[str]) -> None:
    result = lf.scan_page_for_streams(_HOME)
    by_url = {c.url: c for c in result.candidates}
    # A proxy's own localhost listen URL is rewritten to the server asked.
    assert by_url["http://ice.kxyz.example.org:8000/live"].label == "KXYZ 88.1 Live"
    assert "http://ice.kxyz.example.org:8000/aac" in by_url
    assert not any(u.endswith("status.xsl") for u in by_url)


def test_status_xsl_m3u_links_are_the_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    pages = {
        "https://ice.example.org:8000/status.xsl": _text("icecast_status.html"),
    }

    def fetch(url: str) -> str:
        if url not in pages:
            raise lf.LinkFinderError("no JSON here")
        return pages[url]

    monkeypatch.setattr(lf, "_fetch_html", fetch)
    urls = [
        c.url
        for c in lf.scan_page_for_streams("https://ice.example.org:8000/status.xsl").candidates
    ]
    assert "https://ice.example.org:8000/live.m3u" in urls


def test_a_parser_alone_reads_no_network() -> None:
    parser = StreamLinkParser(_HOME)
    parser.feed(_text("wordpress_station.html"))
    assert parser.script_urls == [
        "https://kxyz.example.org/wp-content/plugins/radio-player/js/radio-player.min.js?ver=2.1"
    ]
    assert parser.popup_urls == ["https://kxyz.example.org/popup-player/"]
    assert parser.status_urls == ["http://ice.kxyz.example.org:8000/status.xsl"]


# -- HTTP-only station sites --------------------------------------------------


@pytest.mark.parametrize(
    "failure",
    [
        urllib.error.URLError(ConnectionRefusedError("refused")),
        urllib.error.URLError(TimeoutError("timed out")),
        urllib.error.URLError(ssl.SSLError("wrong version number")),
        TimeoutError("timed out"),
    ],
)
def test_a_site_with_no_https_is_read_over_http(
    monkeypatch: pytest.MonkeyPatch, failure: BaseException
) -> None:
    calls: list[str] = []

    def get(url: str) -> str:
        calls.append(url)
        if url.startswith("https://"):
            raise failure
        return "<html>plain</html>"

    monkeypatch.setattr(lf, "_http_get_text", get)
    assert "plain" in lf._fetch_html("https://community.example.org/")
    assert calls == ["https://community.example.org/", "http://community.example.org/"]


def test_a_missing_host_or_a_404_earns_no_http_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    import socket

    for failure in (
        urllib.error.URLError(socket.gaierror("Name or service not known")),
        urllib.error.HTTPError("https://x.example/", 404, "Not Found", {}, None),  # type: ignore[arg-type]
    ):
        calls: list[str] = []

        def get(url: str, failure: BaseException = failure, calls: list[str] = calls) -> str:
            calls.append(url)
            raise failure

        monkeypatch.setattr(lf, "_http_get_text", get)
        with pytest.raises(lf.LinkFinderError):
            lf._fetch_html("https://x.example/")
        assert calls == ["https://x.example/"]


# -- the live check, end to end ------------------------------------------------


def _probe_from(replies: dict[str, HttpReply | BaseException]):  # type: ignore[no-untyped-def]
    def probe(url: str, _timeout: float) -> HttpReply:
        answer = replies.get(url, urllib.error.URLError(TimeoutError("timed out")))
        if isinstance(answer, BaseException):
            raise answer
        return answer

    return probe


def test_checked_live_streams_come_first_and_non_audio_is_left_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = (
        "<html><body>"
        '<a href="https://k.example/old-page/stream">Old stream page</a>'
        '<a href="https://k.example/podcast/ep1.mp3">Episode 1</a>'
        '<a href="https://k.example/unknown.pls">Mystery</a>'
        '<audio src="https://k.example/live"></audio>'
        "</body></html>"
    )
    monkeypatch.setattr(lf, "_fetch_html", lambda url: page)
    mp3 = _bytes("mp3_prefix.bin")
    monkeypatch.setattr(
        lf,
        "_probe",
        _probe_from({
            "https://k.example/old-page/stream": HttpReply(
                200, {"Content-Type": "text/html"}, _bytes("html_200.html")
            ),
            "https://k.example/podcast/ep1.mp3": HttpReply(
                200, {"Content-Type": "audio/mpeg", "Content-Length": "9000000"}, mp3
            ),
            "https://k.example/live": HttpReply(
                200, {"Content-Type": "audio/mpeg", "icy-name": "K Live", "icy-br": "128"}, mp3
            ),
        }),
    )
    result = lf.scan_page_for_streams("k.example", check_live=True)
    assert result.checked and result.left_out == 1
    assert [(c.url, c.check) for c in result.candidates] == [
        ("https://k.example/live", "live"),
        ("https://k.example/unknown.pls", "not checked"),
        ("https://k.example/podcast/ep1.mp3", "file"),
    ]
    live = result.candidates[0]
    assert (live.stream_name, live.codec, live.bitrate_kbps) == ("K Live", "MP3", 128)
    # pick_stream trusts the one checked live stream over the guesses.
    assert pick_stream(result.candidates).url == "https://k.example/live"


def test_without_the_check_nothing_is_probed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        lf, "_fetch_html", lambda url: '<audio src="https://k.example/live"></audio>'
    )
    monkeypatch.setattr(lf, "_probe", lambda *a: pytest.fail("probed without check_live"))
    result = lf.scan_page_for_streams("k.example")
    assert not result.checked and result.candidates[0].check == ""


def test_the_https_copy_of_a_stream_is_preferred(monkeypatch: pytest.MonkeyPatch) -> None:
    page = '<a href="http://s.example/live.mp3">a</a><a href="https://s.example/live.mp3">b</a>'
    monkeypatch.setattr(lf, "_fetch_html", lambda url: page)
    assert [c.url for c in lf.scan_page_for_streams("k.example").candidates] == [
        "https://s.example/live.mp3"
    ]


def test_but_a_working_http_copy_beats_a_dead_https_one(monkeypatch: pytest.MonkeyPatch) -> None:
    page = '<a href="http://s.example:8000/live.mp3">a</a><a href="https://s.example:8000/live.mp3">b</a>'
    monkeypatch.setattr(lf, "_fetch_html", lambda url: page)
    monkeypatch.setattr(
        lf,
        "_probe",
        _probe_from({
            "http://s.example:8000/live.mp3": HttpReply(200, {}, _bytes("aac_prefix.bin"))
        }),
    )
    candidates = lf.scan_page_for_streams("k.example", check_live=True).candidates
    assert [(c.url, c.check) for c in candidates] == [("http://s.example:8000/live.mp3", "live")]
