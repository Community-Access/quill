"""The feed reader after the Downcast import test (check.md bugs 1, 3, 4, 9, 13, 14).

Everything here drives the real ``fetch_and_parse_feed`` / ``_fetch_feed_bytes``
with a fake standing in for ``feed_auth.urlopen_auth_safe`` -- no network. The
fake can answer differently per address, raise an HTTP status, and report the
redirect hops a real opener would have followed, through the same thread-local
recorder the real redirect handler writes to.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from email.message import Message
from typing import Any

import pytest

from quill.core.podcasts import feed_auth, feed_problems, feed_reader
from quill.core.podcasts.feed_reader import FeedReaderError, FetchNotes

_FEED = b"""<?xml version="1.0"?><rss version="2.0"><channel>
<title>As It Happens</title>
<item><title>One</title><guid>one</guid><pubDate>Fri, 02 Oct 2026 10:00:00 GMT</pubDate>
<enclosure url="https://cbc.example/1.mp3" type="audio/mpeg"/></item>
</channel></rss>"""

#: ReMade (feeds.megaphone.fm/remade): still a feed, emptied by the publisher.
_EMPTY_FEED = b"""<?xml version="1.0"?><rss version="2.0"><channel>
<title>ReMade</title><description>A finished series.</description></channel></rss>"""

#: Crypto-Z's address now lands on an expired-domain sales page.
_EXPIRED_DOMAIN_PAGE = (
    b'<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    b"<title>euphonie.media -- established .media domain (6y) | ED.com</title>"
)


class _Response:
    def __init__(self, payload: bytes, headers: dict[str, str] | None = None) -> None:
        self._payload = payload
        message = Message()
        for name, value in (headers or {}).items():
            message[name] = value
        self.headers = message

    def read(self, _n: int = -1) -> bytes:
        return self._payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False


class _Server:
    """Answers per address; records every request it was sent."""

    def __init__(self) -> None:
        self.routes: dict[str, Any] = {}
        self.requests: list[urllib.request.Request] = []

    def __call__(self, request: urllib.request.Request, **_kwargs: object) -> _Response:
        self.requests.append(request)
        answer = self.routes[request.full_url]
        if callable(answer):
            answer = answer(request)
        if isinstance(answer, BaseException):
            raise answer
        payload, headers, hops = answer
        recorder = getattr(feed_auth._REDIRECTS, "hops", None)
        if recorder is not None:
            recorder.extend(hops)
        return _Response(payload, headers)

    @property
    def urls(self) -> list[str]:
        return [request.full_url for request in self.requests]


@pytest.fixture
def server(monkeypatch: pytest.MonkeyPatch) -> _Server:
    fake = _Server()
    monkeypatch.setattr(feed_auth, "urlopen_auth_safe", fake)
    monkeypatch.setattr("quill.core.net_retry.time.sleep", lambda _s: None)
    return fake


def _http(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://x.example/", code, "r", Message(), None)


# -- bug 1: one honest User-Agent, no GitHub in it --------------------------------


def test_the_user_agent_names_the_project_site_not_github(server: _Server) -> None:
    server.routes["https://www.cbc.ca/podcasting/includes/asithappens.xml"] = (_FEED, {}, [])
    feed_reader.fetch_and_parse_feed("https://www.cbc.ca/podcasting/includes/asithappens.xml")
    agent = server.requests[0].get_header("User-agent")
    assert agent.endswith("(podcast app; +https://www.quillforall.org)")
    assert "github" not in agent.lower()


# -- bug 3: a web page is not a healthy feed; an empty feed is not an error --------


def test_a_web_page_where_the_feed_was_is_a_failure_in_plain_words(server: _Server) -> None:
    url = "https://expireddomains.com/domain/euphonie.media?utm_source=redi"
    server.routes[url] = (_EXPIRED_DOMAIN_PAGE, {"Content-Type": "text/html"}, [])
    with pytest.raises(FeedReaderError) as caught:
        feed_reader.fetch_and_parse_feed(url)
    assert caught.value.kind == feed_problems.WEB_PAGE
    assert caught.value.args[0] == "This address returns a web page, not a podcast feed."


def test_an_emptied_feed_still_reads_as_a_feed_with_no_episodes(server: _Server) -> None:
    server.routes["https://feeds.megaphone.fm/remade"] = (_EMPTY_FEED, {}, [])
    info = feed_reader.fetch_and_parse_feed("https://feeds.megaphone.fm/remade")
    assert info.title == "ReMade"
    assert info.episodes == []


# -- bug 4: only a permanent move is reported as a new address ---------------------


@pytest.mark.parametrize(
    ("hops", "expected"),
    [
        # FSCast: 301 to Libsyn, then 302 to an internal destinations address.
        (
            [
                (301, "https://fscast.libsyn.com/rss"),
                (302, "https://rss.libsyn.com/shows/1/destinations/2.xml"),
            ],
            "",
        ),
        ([(302, "https://feeds.feedburner.com/TEDTalks_audio")], ""),
        ([(307, "https://b.example/feed")], ""),
        ([(301, "https://b.example/feed")], "https://b.example/feed"),
        ([(308, "https://b.example/feed")], "https://b.example/feed"),
        # Never a downgrade from https to plain http.
        ([(301, "http://b.example/feed")], ""),
    ],
)
def test_only_301_and_308_on_every_hop_move_a_feed(
    server: _Server, hops: list[tuple[int, str]], expected: str
) -> None:
    server.routes["https://a.example/feed"] = (_FEED, {}, hops)
    moved: list[str] = []
    notes = FetchNotes()
    feed_reader.fetch_and_parse_feed("https://a.example/feed", redirected_to=moved, notes=notes)
    assert notes.permanent_url == expected
    assert moved == ([expected] if expected else [])


def test_a_plain_http_feed_that_moved_within_http_is_reported(server: _Server) -> None:
    # Our Place: http to http. The old check ignored any http landing address.
    server.routes["https://www.ourplace-podcast.info/feed/podcast/"] = _http(404)
    server.routes["http://www.ourplace-podcast.info/feed/podcast/"] = (
        _FEED,
        {},
        [(301, "http://ourplace-podcast.info/feed/podcast/")],
    )
    notes = FetchNotes()
    feed_reader.fetch_and_parse_feed("http://www.ourplace-podcast.info/feed/podcast/", notes=notes)
    assert notes.permanent_url == "http://ourplace-podcast.info/feed/podcast/"


def test_the_redirect_handler_records_each_hop_it_follows() -> None:
    handler = feed_auth._AuthStrippingRedirectHandler()
    request = urllib.request.Request("https://a.example/feed")
    with feed_auth.recording_redirects() as hops:
        handler.redirect_request(request, None, 302, "Found", Message(), "https://b.example/x")
    assert hops == [(302, "https://b.example/x")]


# -- bug 9: conditional requests ---------------------------------------------------


def test_stored_validators_are_sent_and_a_304_is_nothing_new(server: _Server) -> None:
    server.routes["https://a.example/feed"] = _http(304)
    notes = FetchNotes(etag='"abc"', last_modified="Fri, 02 Oct 2026 10:00:00 GMT")
    info = feed_reader.fetch_and_parse_feed("https://a.example/feed", notes=notes)
    sent = server.requests[0]
    assert sent.get_header("If-none-match") == '"abc"'
    assert sent.get_header("If-modified-since") == "Fri, 02 Oct 2026 10:00:00 GMT"
    assert info.not_modified is True
    assert info.episodes == []


def test_the_responses_validators_are_kept_for_next_time(server: _Server) -> None:
    server.routes["https://a.example/feed"] = (
        _FEED,
        {"ETag": '"v2"', "Last-Modified": "Sat, 03 Oct 2026 10:00:00 GMT"},
        [],
    )
    notes = FetchNotes()
    feed_reader.fetch_and_parse_feed("https://a.example/feed", notes=notes)
    assert (notes.etag, notes.last_modified) == ('"v2"', "Sat, 03 Oct 2026 10:00:00 GMT")
    assert server.requests[0].get_header("If-none-match") is None


# -- bug 13: a feed over the cap says so ------------------------------------------


def test_a_feed_bigger_than_the_cap_is_marked_truncated(
    server: _Server, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(feed_reader, "_MAX_BYTES", len(_FEED) - 10)
    server.routes["https://a.example/feed"] = (_FEED, {}, [])
    info = feed_reader.fetch_and_parse_feed("https://a.example/feed")
    assert info.truncated is True


def test_the_cap_is_well_above_the_old_twenty_megabytes() -> None:
    assert feed_reader._MAX_BYTES > 20_000_000


# -- bug 14: https first for a plain-http address ---------------------------------


def test_a_plain_http_feed_is_read_over_https_when_it_can_be(server: _Server) -> None:
    server.routes["https://plain.example/feed"] = (_FEED, {}, [])
    notes = FetchNotes()
    info = feed_reader.fetch_and_parse_feed("http://plain.example/feed", notes=notes)
    assert server.urls == ["https://plain.example/feed"]
    assert notes.read_securely is True
    assert info.title == "As It Happens"


def test_it_falls_back_to_the_address_given_when_https_does_not_work(server: _Server) -> None:
    server.routes["https://plain.example/feed"] = urllib.error.URLError(
        ConnectionRefusedError(10061, "refused")
    )
    server.routes["http://plain.example/feed"] = (_FEED, {}, [])
    notes = FetchNotes()
    feed_reader.fetch_and_parse_feed("http://plain.example/feed", notes=notes)
    # One brief secure attempt -- not retried -- then the address as given.
    assert server.urls == ["https://plain.example/feed", "http://plain.example/feed"]
    assert notes.read_securely is False


def test_a_web_page_on_the_https_side_falls_back_too(server: _Server) -> None:
    server.routes["https://plain.example/feed"] = (_EXPIRED_DOMAIN_PAGE, {}, [])
    server.routes["http://plain.example/feed"] = (_FEED, {}, [])
    info = feed_reader.fetch_and_parse_feed("http://plain.example/feed")
    assert info.title == "As It Happens"


def test_a_refusal_over_https_is_never_retried_in_clear_text(server: _Server) -> None:
    server.routes["https://plain.example/feed"] = _http(403)
    with pytest.raises(FeedReaderError):
        feed_reader.fetch_and_parse_feed("http://plain.example/feed")
    assert server.urls == ["https://plain.example/feed"]


# -- bug 7: a failure raises with a plain sentence --------------------------------


def test_a_failure_raises_a_sentence_not_the_exception_text(server: _Server) -> None:
    import socket

    server.routes["https://xml.nfowars.example/Alex.rss"] = urllib.error.URLError(
        socket.gaierror(11001, "getaddrinfo failed")
    )
    with pytest.raises(FeedReaderError) as caught:
        feed_reader.fetch_and_parse_feed("https://xml.nfowars.example/Alex.rss")
    assert caught.value.args[0] == "This podcast's web address no longer exists."
    assert caught.value.kind == feed_problems.NO_SUCH_HOST
    assert "getaddrinfo" in caught.value.detail
