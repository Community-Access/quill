"""Best-effort Spotify-episode -> public-RSS-enclosure fuzzy matcher."""

from __future__ import annotations

import pytest

from quill.core.podcasts.itunes_search import PodcastSearchResult
from quill.core.spotify import rss_match
from quill.core.spotify.models import SpotifyEpisode

_FEED = b"""<?xml version="1.0"?>
<rss><channel>
  <item><title>Episode 42: The Big One</title>
    <enclosure url="https://cdn.example.com/ep42.mp3"/></item>
  <item><title>Episode 41: Something Else</title>
    <enclosure url="https://cdn.example.com/ep41.mp3"/></item>
</channel></rss>
"""


def _result(title: str, feed_url: str, artist: str = "") -> PodcastSearchResult:
    return PodcastSearchResult(title=title, feed_url=feed_url, artist=artist)


def test_directory_feeds_ranks_and_thresholds() -> None:
    def search(term: str) -> list[PodcastSearchResult]:
        return [
            _result("The Big Show", "https://feeds/good.xml", artist="Acme Media"),
            _result("Completely Different Program", "https://feeds/bad.xml", artist="Nope"),
        ]

    feeds = rss_match.directory_feeds("The Big Show", "Acme Media", search=search)
    assert feeds == ["https://feeds/good.xml"]  # weak match filtered out


def test_episode_from_feed_matches_above_threshold() -> None:
    match = rss_match.episode_from_feed(
        "https://feeds/good.xml",
        "Episode 42: The Big One",
        fetch=lambda url: _FEED,
    )
    assert match is not None
    assert match.url == "https://cdn.example.com/ep42.mp3"
    assert match.feed_url == "https://feeds/good.xml"


def test_episode_from_feed_returns_none_below_threshold() -> None:
    match = rss_match.episode_from_feed(
        "https://feeds/good.xml",
        "Totally Unrelated Bonus Content XYZ",
        fetch=lambda url: _FEED,
    )
    assert match is None


def test_episode_from_feed_handles_fetch_failure() -> None:
    def boom(url: str) -> bytes:
        raise OSError("network down")

    assert rss_match.episode_from_feed("https://feeds/x.xml", "anything", fetch=boom) is None


def test_find_public_enclosure_end_to_end() -> None:
    episode = SpotifyEpisode(
        id="e",
        uri="spotify:episode:e",
        name="Episode 42: The Big One",
        show_name="The Big Show",
        show_publisher="Acme Media",
    )

    def search(term: str) -> list[PodcastSearchResult]:
        return [_result("The Big Show", "https://feeds/good.xml", artist="Acme Media")]

    match = rss_match.find_public_enclosure(episode, search=search, fetch=lambda url: _FEED)
    assert match is not None
    assert match.url == "https://cdn.example.com/ep42.mp3"


def test_find_public_enclosure_needs_a_show_name() -> None:
    episode = SpotifyEpisode(id="e", uri="spotify:episode:e", name="x", show_name="")
    result = rss_match.find_public_enclosure(episode, search=lambda t: [], fetch=lambda u: b"")
    assert result is None


def test_refuse_in_safe_mode() -> None:
    with pytest.raises(rss_match.SpotifyRssMatchError):
        rss_match.refuse_in_safe_mode(True)
    rss_match.refuse_in_safe_mode(False)

    episode = SpotifyEpisode(id="e", uri="spotify:episode:e", name="x", show_name="Show")
    with pytest.raises(rss_match.SpotifyRssMatchError):
        rss_match.find_public_enclosure(episode, safe_mode=True)
