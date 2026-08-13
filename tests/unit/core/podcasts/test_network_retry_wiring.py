"""The three surfaces that adopted the transient retry (x.md item 10).

Testing the policy module on its own would not catch the thing most likely to
go wrong here: a call site that imports the helper and then does not actually
route its request through it. So each of these drives the real public
function with a fake ``urlopen`` and counts round trips.

The OPML sweep gets the closest look, because its failure mode is the
expensive one -- a "dead feed" verdict is what the import report offers to
prune out of somebody's subscription list.
"""

from __future__ import annotations

import urllib.error

import pytest

from quill.core.podcasts import feed_reader, itunes_search, opml_import


@pytest.fixture(autouse=True)
def _no_real_waiting(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the schedule, drop the wall-clock cost of honouring it."""
    monkeypatch.setattr("quill.core.net_retry.time.sleep", lambda _seconds: None)


def _http_error(code: int) -> urllib.error.HTTPError:
    return urllib.error.HTTPError("https://example.com/feed.xml", code, "reason", {}, None)  # type: ignore[arg-type]


class _Response:
    def __init__(self, payload: bytes, url: str = "") -> None:
        self._payload = payload
        self.url = url

    def read(self, _size: int = -1) -> bytes:
        return self._payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_exc: object) -> bool:
        return False


class _Flaky:
    """Fails *failures* times transiently, then answers."""

    def __init__(self, payload: bytes, failures: int, error: BaseException | None = None) -> None:
        self.payload = payload
        self.remaining = failures
        self.error = error or _http_error(503)
        self.calls = 0

    def __call__(self, *args: object, **kwargs: object) -> _Response:
        self.calls += 1
        if self.remaining > 0:
            self.remaining -= 1
            raise self.error
        return _Response(self.payload)


# -- feed refresh ------------------------------------------------------------

_FEED = b"""<?xml version="1.0"?><rss version="2.0"><channel>
<title>Test Show</title><item><title>One</title>
<enclosure url="https://example.com/1.mp3" type="audio/mpeg"/>
<guid>one</guid></item></channel></rss>"""


def test_a_feed_refresh_survives_two_server_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    flaky = _Flaky(_FEED, failures=2)
    monkeypatch.setattr(feed_reader.feed_auth, "urlopen_auth_safe", flaky)

    info = feed_reader.fetch_and_parse_feed("https://example.com/feed.xml")

    assert flaky.calls == 3
    assert info.title == "Test Show"


def test_a_feed_that_is_really_gone_costs_one_round_trip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[int] = []

    def always_404(*_args: object, **_kwargs: object) -> _Response:
        calls.append(1)
        raise _http_error(404)

    monkeypatch.setattr(feed_reader.feed_auth, "urlopen_auth_safe", always_404)

    with pytest.raises(feed_reader.FeedReaderError):
        feed_reader.fetch_and_parse_feed("https://example.com/feed.xml")
    assert len(calls) == 1


def test_a_sign_in_failure_is_not_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    """A 401 needs new credentials, not another identical attempt -- asking
    three times only delays the prompt that would fix it."""
    calls: list[int] = []

    def always_401(*_args: object, **_kwargs: object) -> _Response:
        calls.append(1)
        raise _http_error(401)

    monkeypatch.setattr(feed_reader.feed_auth, "urlopen_auth_safe", always_401)

    with pytest.raises(feed_reader.FeedAuthError):
        feed_reader.fetch_and_parse_feed("https://example.com/feed.xml")
    assert len(calls) == 1


# -- directory search --------------------------------------------------------

_ITUNES = (
    b'{"results": [{"collectionName": "Test Show", '
    b'"feedUrl": "https://example.com/feed.xml", "artistName": "Someone"}]}'
)


def test_itunes_search_survives_a_transient_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    flaky = _Flaky(_ITUNES, failures=1, error=TimeoutError("timed out"))
    monkeypatch.setattr(itunes_search.urllib.request, "urlopen", flaky)

    results = itunes_search.search_podcasts("test")

    assert flaky.calls == 2
    assert [r.title for r in results] == ["Test Show"]


def test_itunes_search_gives_up_after_the_schedule(monkeypatch: pytest.MonkeyPatch) -> None:
    flaky = _Flaky(_ITUNES, failures=99, error=_http_error(503))
    monkeypatch.setattr(itunes_search.urllib.request, "urlopen", flaky)

    with pytest.raises(itunes_search.ITunesSearchError):
        itunes_search.search_podcasts("test")
    assert flaky.calls == 3, "three attempts: the first plus the two scheduled retries"


# -- the OPML reachability sweep ---------------------------------------------


def test_a_feed_that_blips_is_not_reported_dead(monkeypatch: pytest.MonkeyPatch) -> None:
    """The verdict this sweep produces is what the report offers to prune, so
    one 503 must never be the reason a live subscription is deleted."""
    flaky = _Flaky(b"<rss/>", failures=2, error=_http_error(503))
    monkeypatch.setattr(opml_import.urllib.request, "urlopen", flaky)

    result = opml_import.probe_feed("https://example.com/feed.xml")

    assert result.ok is True
    assert result.error == ""
    assert flaky.calls == 3


def test_a_genuinely_dead_feed_is_still_one_round_trip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """What keeps a sweep over a dead list fast."""
    calls: list[int] = []

    def always_404(*_args: object, **_kwargs: object) -> _Response:
        calls.append(1)
        raise _http_error(404)

    monkeypatch.setattr(opml_import.urllib.request, "urlopen", always_404)

    result = opml_import.probe_feed("https://example.com/feed.xml")

    assert result.ok is False
    assert "404" in result.error
    assert len(calls) == 1


def test_a_private_feed_is_still_reachable_and_not_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """401 keeps its established meaning -- alive, worth keeping -- and the
    retry never blurs that into a network failure."""
    calls: list[int] = []

    def always_401(*_args: object, **_kwargs: object) -> _Response:
        calls.append(1)
        raise _http_error(401)

    monkeypatch.setattr(opml_import.urllib.request, "urlopen", always_401)

    result = opml_import.probe_feed("https://example.com/feed.xml")

    assert result.ok is True
    assert len(calls) == 1


def test_the_sweep_uses_the_shorter_schedule() -> None:
    """A sweep runs over thousands of feeds, so its waits are deliberately
    a third of the single-refresh ones."""
    from quill.core.net_retry import DEFAULT_BACKOFF

    assert opml_import._PROBE_BACKOFF == (0.5, 1.0)
    assert sum(opml_import._PROBE_BACKOFF) < sum(DEFAULT_BACKOFF)


def test_probe_feed_still_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """The sweep runs it across a thread pool; one exploding probe must not
    be able to take the sweep with it."""

    def explode(*_args: object, **_kwargs: object) -> _Response:
        raise OSError("the socket layer fell over")

    monkeypatch.setattr(opml_import.urllib.request, "urlopen", explode)

    result = opml_import.probe_feed("https://example.com/feed.xml")
    assert result.ok is False
