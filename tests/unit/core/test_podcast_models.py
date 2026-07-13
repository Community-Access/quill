"""Tests for the Podcasts data model (pure; no network, no filesystem)."""

from __future__ import annotations

from quill.core.podcasts.models import PodcastEpisode, PodcastSettings, PodcastShow


def test_settings_to_dict_from_dict_round_trip() -> None:
    original = PodcastSettings(
        playback_mode="stream",
        retention="keep_last_n",
        retention_count=10,
        speed=1.5,
        download_root="D:/podcasts",
    )
    restored = PodcastSettings.from_dict(original.to_dict())
    assert restored == original


def test_settings_from_dict_defaults_on_missing_fields() -> None:
    settings = PodcastSettings.from_dict({})
    assert settings.playback_mode == "download"
    assert settings.retention == "keep_all"
    assert settings.retention_count == 5
    assert settings.speed == 1.0
    assert settings.download_root == ""


def test_settings_from_dict_coerces_junk_numeric_fields() -> None:
    settings = PodcastSettings.from_dict({"retention_count": "not a number", "speed": None})
    assert settings.retention_count == 5
    assert settings.speed == 1.0


def test_episode_from_dict_requires_guid_title_and_audio_url() -> None:
    assert PodcastEpisode.from_dict({"title": "X", "audio_url": "https://x"}) is None
    assert PodcastEpisode.from_dict({"guid": "g", "audio_url": "https://x"}) is None
    assert PodcastEpisode.from_dict({"guid": "g", "title": "X"}) is None
    assert PodcastEpisode.from_dict({}) is None


def test_episode_to_dict_from_dict_round_trip() -> None:
    original = PodcastEpisode(
        guid="g1",
        title="Episode One",
        audio_url="https://example.com/ep1.mp3",
        published="2026-07-01",
        duration_seconds=1830,
        description="Description text",
        chapters_url="https://example.com/ep1-chapters.json",
        transcript_url="https://example.com/ep1.srt",
        transcript_type="application/srt",
        downloaded_path="/data/ep1.mp3",
        mode_override="download",
        played=True,
        position_ms=45000,
    )
    restored = PodcastEpisode.from_dict(original.to_dict())
    assert restored == original


def test_show_find_episode() -> None:
    episode = PodcastEpisode(guid="g1", title="Ep", audio_url="https://x/e.mp3")
    show = PodcastShow(id="s1", title="Show", episodes=[episode])
    assert show.find_episode("g1") is episode
    assert show.find_episode("missing") is None


def test_show_to_dict_from_dict_round_trip_with_settings_and_episodes() -> None:
    episode = PodcastEpisode(guid="g1", title="Ep", audio_url="https://x/e.mp3")
    original = PodcastShow(
        id="s1",
        title="Show",
        feed_url="https://x/feed.xml",
        homepage="https://x",
        artwork_url="https://x/art.png",
        is_local=False,
        folder_id="f1",
        paused=True,
        is_favorite=True,
        route_to_inbox=True,
        inbox_default_folder_id="f2",
        settings=PodcastSettings(playback_mode="stream"),
        episodes=[episode],
    )
    restored = PodcastShow.from_dict(original.to_dict())
    assert restored == original


def test_show_from_dict_requires_id_and_title() -> None:
    assert PodcastShow.from_dict({"title": "X"}) is None
    assert PodcastShow.from_dict({"id": "s1"}) is None
    assert PodcastShow.from_dict({}) is None


def test_show_from_dict_tolerates_missing_settings_and_bad_episodes() -> None:
    show = PodcastShow.from_dict({
        "id": "s1",
        "title": "Show",
        "episodes": [
            {"guid": "bad"},
            "junk",
            {"guid": "g1", "title": "Ep", "audio_url": "https://x/e.mp3"},
        ],
    })
    assert show is not None
    assert show.settings is None
    assert len(show.episodes) == 1
    assert show.episodes[0].guid == "g1"
