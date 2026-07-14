"""Tests for the podcast RSS/Atom feed reader (Safe Mode gate, parsing,
chapters/transcript extraction) -- no real network calls."""

from __future__ import annotations

import pytest

import quill.core.podcasts.feed_reader as feed_reader
from quill.core.podcasts.feed_reader import (
    FeedReaderError,
    _parse_duration,
    fetch_and_parse_feed,
    parse_feed,
    refuse_in_safe_mode,
)

_SAMPLE_FEED = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:podcast="https://podcastindex.org/namespace/1.0">
  <channel>
    <title>Great Show</title>
    <link>https://example.com</link>
    <image><url>https://example.com/art.png</url></image>
    <item>
      <title>Episode One</title>
      <guid>ep-1</guid>
      <enclosure url="https://example.com/ep1.mp3" type="audio/mpeg" length="123"/>
      <itunes:duration>30:15</itunes:duration>
      <description>First episode</description>
      <pubDate>Wed, 01 Jul 2026 00:00:00 GMT</pubDate>
      <podcast:chapters url="https://example.com/ep1-chapters.json" type="chapters+json"/>
      <podcast:transcript url="https://example.com/ep1.srt" type="application/srt"/>
    </item>
    <item>
      <title>Episode Two</title>
      <guid>ep-2</guid>
      <enclosure url="https://example.com/ep2.mp3" type="audio/mpeg" length="456"/>
      <itunes:duration>45:00</itunes:duration>
      <description>Second episode</description>
      <pubDate>Wed, 08 Jul 2026 00:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


def test_refuse_in_safe_mode_raises() -> None:
    with pytest.raises(FeedReaderError):
        refuse_in_safe_mode(True)
    refuse_in_safe_mode(False)  # no raise


def test_parse_feed_extracts_show_metadata() -> None:
    info = parse_feed(_SAMPLE_FEED)
    assert info.title == "Great Show"
    assert info.homepage == "https://example.com"
    assert info.artwork_url == "https://example.com/art.png"
    assert len(info.episodes) == 2


def test_parse_feed_extracts_episode_fields() -> None:
    info = parse_feed(_SAMPLE_FEED)
    ep1 = info.episodes[0]
    assert ep1.guid == "ep-1"
    assert ep1.title == "Episode One"
    assert ep1.audio_url == "https://example.com/ep1.mp3"
    assert ep1.duration_seconds == 30 * 60 + 15
    assert ep1.description == "First episode"


def test_parse_feed_scopes_chapters_and_transcript_to_correct_episode() -> None:
    info = parse_feed(_SAMPLE_FEED)
    ep1, ep2 = info.episodes
    assert ep1.chapters_url == "https://example.com/ep1-chapters.json"
    assert ep1.transcript_url == "https://example.com/ep1.srt"
    assert ep1.transcript_type == "application/srt"
    assert ep2.chapters_url == ""
    assert ep2.transcript_url == ""


def test_parse_feed_skips_entries_without_title_or_audio() -> None:
    feed = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>X</title>
<item><title></title><enclosure url="https://x/e.mp3"/></item>
<item><title>No Audio</title></item>
</channel></rss>
"""
    info = parse_feed(feed)
    assert info.episodes == []


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("30:15", 30 * 60 + 15),
        ("1:02:03", 3600 + 2 * 60 + 3),
        ("90", 90),
        ("", 0),
        ("garbage", 0),
        (None, 0),
    ],
)
def test_parse_duration(raw: object, expected: int) -> None:
    assert _parse_duration(raw) == expected


def test_fetch_and_parse_feed_refuses_in_safe_mode() -> None:
    with pytest.raises(FeedReaderError):
        fetch_and_parse_feed("https://example.com/feed.xml", safe_mode=True)


def test_fetch_feed_bytes_refuses_non_https() -> None:
    with pytest.raises(FeedReaderError):
        feed_reader._fetch_feed_bytes("http://example.com/feed.xml")


class _FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self, _n: int = -1) -> bytes:
        return self._payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_fetch_and_parse_feed_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        feed_reader.urllib.request, "urlopen", lambda *a, **k: _FakeResponse(_SAMPLE_FEED)
    )
    info = fetch_and_parse_feed("https://example.com/feed.xml")
    assert info.title == "Great Show"
    assert len(info.episodes) == 2


def test_fetch_feed_bytes_sends_basic_auth_header(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_urlopen(request: object, timeout: float, context: object) -> _FakeResponse:
        captured["headers"] = dict(request.headers)  # type: ignore[attr-defined]
        return _FakeResponse(_SAMPLE_FEED)

    monkeypatch.setattr(feed_reader.urllib.request, "urlopen", fake_urlopen)
    feed_reader._fetch_feed_bytes("https://example.com/feed.xml", username="user", password="pw")
    assert "Authorization" in captured["headers"]  # type: ignore[operator]


def test_fetch_feed_bytes_raises_on_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def always_fail(*_a: object, **_k: object) -> None:
        raise OSError("connection refused")

    monkeypatch.setattr(feed_reader.urllib.request, "urlopen", always_fail)
    with pytest.raises(FeedReaderError):
        feed_reader._fetch_feed_bytes("https://example.com/feed.xml")
