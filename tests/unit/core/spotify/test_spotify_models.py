"""Spotify model parsing and the podcast-model adapters."""

from __future__ import annotations

from quill.core.spotify.models import (
    SpotifyEpisode,
    SpotifyShow,
    SpotifyTrack,
    is_spotify_uri,
)

_TRACK_JSON = {
    "id": "t1",
    "uri": "spotify:track:t1",
    "name": "Song",
    "duration_ms": 210_000,
    "explicit": True,
    "artists": [{"name": "Alice"}, {"name": "Bob"}],
    "album": {"name": "The Album"},
}

_SHOW_JSON = {
    "id": "s1",
    "uri": "spotify:show:s1",
    "name": "My Show",
    "publisher": "A Publisher",
    "description": "About the show",
    "total_episodes": 12,
    "external_urls": {"spotify": "https://open.spotify.com/show/s1"},
    "images": [{"url": "https://img/1.jpg"}],
}

_EPISODE_JSON = {
    "id": "e1",
    "uri": "spotify:episode:e1",
    "name": "Episode One",
    "description": "First episode",
    "duration_ms": 1_800_500,
    "release_date": "2026-07-01",
    "show": {"name": "My Show", "publisher": "A Publisher"},
    "images": [{"url": "https://img/e1.jpg"}],
}


def test_track_from_json_joins_artists() -> None:
    track = SpotifyTrack.from_json(_TRACK_JSON)
    assert track.name == "Song"
    assert track.artist == "Alice, Bob"
    assert track.album == "The Album"
    assert track.duration_ms == 210_000
    assert track.explicit is True
    assert track.source == "spotify"


def test_show_from_json_and_podcast_adapter() -> None:
    show = SpotifyShow.from_json(_SHOW_JSON)
    assert show.publisher == "A Publisher"
    assert show.total_episodes == 12
    assert show.homepage == "https://open.spotify.com/show/s1"
    assert show.artwork_url == "https://img/1.jpg"

    podcast = show.to_podcast_show()
    assert podcast.id == "spotify:s1"
    assert podcast.title == "My Show"
    assert podcast.feed_url == ""  # Spotify shows have no public RSS feed
    assert podcast.homepage == "https://open.spotify.com/show/s1"


def test_episode_adapter_uses_uri_as_audio_url() -> None:
    episode = SpotifyEpisode.from_json(_EPISODE_JSON)
    assert episode.show_name == "My Show"
    assert episode.show_publisher == "A Publisher"

    podcast = episode.to_podcast_episode()
    # audio_url is the spotify: URI -- satisfies the non-empty invariant and is
    # the play token; is_spotify_uri is the source marker on the podcast side.
    assert podcast.audio_url == "spotify:episode:e1"
    assert is_spotify_uri(podcast.audio_url)
    assert podcast.guid == "spotify:episode:e1"
    assert podcast.title == "Episode One"
    assert podcast.duration_seconds == 1800  # ms rounded down to whole seconds


def test_from_json_tolerates_missing_fields() -> None:
    assert SpotifyTrack.from_json({}).name == "Untitled"
    assert SpotifyShow.from_json({}).homepage == ""
    assert SpotifyEpisode.from_json({}).show_name == ""


def test_is_spotify_uri() -> None:
    assert is_spotify_uri("spotify:episode:abc")
    assert not is_spotify_uri("https://example.com/ep.mp3")
