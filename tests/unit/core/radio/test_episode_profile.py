"""The four Cast pulls: resume read-back, feed auth, per-show speed, chapters.

Everything here guards one promise: the shared library's knowledge follows a
subscribed episode into Radio's player -- read-only, so a Radio write can
never clobber Cast's open store.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core.podcasts.models import PodcastEpisode, PodcastSettings, PodcastShow
from quill.core.podcasts.radio_listens import (
    episode_playback_profile,
    feed_credentials,
)
from quill.core.podcasts.subscriptions import load_library, new_id, save_library
from quill.core.radio.models import RadioStation
from quill.ui.radio import episode_profile as ep

FEED = "https://feeds.example/show"
AUDIO = "https://cdn.example/ep1.mp3"


def _seed(tmp_path: Path, *, position_ms: int = 0, speed: float = 1.0) -> Path:
    library = load_library(tmp_path)
    show = PodcastShow(id=new_id(), title="The Show", feed_url=FEED)
    show.episodes = [
        PodcastEpisode(
            guid="g1",
            title="Episode 1",
            audio_url=AUDIO,
            position_ms=position_ms,
            chapters_url="https://cdn.example/ep1.chapters.json",
        )
    ]
    if speed != 1.0:
        show.settings = PodcastSettings(speed=speed)
    library.shows.append(show)
    save_library(tmp_path, library)
    return tmp_path


# -- the core profile ---------------------------------------------------------


def test_profile_carries_position_speed_and_chapters(tmp_path: Path) -> None:
    _seed(tmp_path, position_ms=1_200_000, speed=1.5)

    profile = episode_playback_profile(tmp_path, feed_url=FEED, audio_url=AUDIO)

    assert profile.position_ms == 1_200_000
    assert profile.speed == 1.5
    assert profile.chapters_url == "https://cdn.example/ep1.chapters.json"


def test_an_unfollowed_feed_answers_defaults(tmp_path: Path) -> None:
    profile = episode_playback_profile(tmp_path, feed_url=FEED, audio_url=AUDIO)
    assert (profile.position_ms, profile.speed, profile.chapters_url) == (0, 1.0, "")


def test_feed_credentials_apply_the_same_host_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed(tmp_path)
    library = load_library(tmp_path)
    library.shows[0].feed_username = "alice"
    save_library(tmp_path, library)
    from quill.core.podcasts import feed_auth

    monkeypatch.setattr(feed_auth, "load_feed_password", lambda _sid: "s3cret")

    assert feed_credentials(tmp_path, FEED) == ("alice", "s3cret")
    assert feed_credentials(tmp_path, "https://feeds.example/other-show") == ("", "")


# -- resume: the furthest position wins ---------------------------------------


def _episode_station() -> RadioStation:
    return RadioStation(
        name="Episode 1",
        stream_url=AUDIO,
        homepage=FEED,
        source="Subscribed Podcasts",
        is_recording=True,
    )


def test_a_cast_position_resumes_in_radio(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Twenty minutes into an episode in Cast; Enter on the row in Radio."""
    _seed(tmp_path, position_ms=1_200_000)
    from quill.core import paths
    from quill.core.radio.resume import ResumeStore
    from quill.ui.radio import resume_playback as rp

    monkeypatch.setattr(paths, "app_data_dir", lambda: tmp_path)
    rp.set_store_for_tests(ResumeStore(tmp_path))
    try:
        assert rp.saved_position_ms(_episode_station()) == 1_200_000
    finally:
        rp.set_store_for_tests(None)


def test_the_furthest_of_the_two_positions_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed(tmp_path, position_ms=600_000)
    from quill.core import paths
    from quill.core.radio.resume import ResumeStore
    from quill.ui.radio import resume_playback as rp

    monkeypatch.setattr(paths, "app_data_dir", lambda: tmp_path)
    store = ResumeStore(tmp_path)
    store.remember(AUDIO, 1_500_000, duration_ms=3_600_000, label="Episode 1")
    rp.set_store_for_tests(store)
    try:
        # Radio's own store is further along than Cast's record: keep it.
        assert rp.saved_position_ms(_episode_station()) == 1_500_000
    finally:
        rp.set_store_for_tests(None)


def test_an_ordinary_recording_never_touches_the_library(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from quill.core import paths
    from quill.core.radio.resume import ResumeStore
    from quill.ui.radio import resume_playback as rp

    monkeypatch.setattr(
        paths, "app_data_dir", lambda: (_ for _ in ()).throw(AssertionError("library read"))
    )
    rp.set_store_for_tests(ResumeStore(tmp_path))
    try:
        chapter = RadioStation(name="Ch 1", stream_url="https://a/x.mp3", is_recording=True)
        assert rp.saved_position_ms(chapter) == 0  # and no AssertionError raised
    finally:
        rp.set_store_for_tests(None)


# -- the player-side application ----------------------------------------------


def _host(station: RadioStation | None, *, rate: float = 1.0) -> SimpleNamespace:
    host = SimpleNamespace(
        _state=SimpleNamespace(station=station),
        _playback_rate=rate,
        _play_token=7,
        _youtube_stream=None,
        is_seekable=lambda: True,
    )
    host.speed_calls = []
    host.set_speed = lambda rate: host.speed_calls.append(rate)
    return host


def test_apply_profile_sets_the_shows_speed_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed(tmp_path, speed=1.5)
    from quill.core import paths

    monkeypatch.setattr(paths, "app_data_dir", lambda: tmp_path)
    host = _host(_episode_station())

    ep.apply_profile(host)
    assert host.speed_calls == [1.5]

    # A session speed the listener chose is never overridden.
    chosen = _host(_episode_station(), rate=2.0)
    ep.apply_profile(chosen)
    assert chosen.speed_calls == []


def test_apply_profile_ignores_ordinary_stations(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core import paths

    monkeypatch.setattr(
        paths, "app_data_dir", lambda: (_ for _ in ()).throw(AssertionError("library read"))
    )
    host = _host(RadioStation(name="Jazz FM", stream_url="https://ice/x"))
    ep.apply_profile(host)  # no library read, no speed call, no crash
    assert host.speed_calls == []


def test_chapters_prefer_the_video_then_the_episode() -> None:
    episode_chapters = [SimpleNamespace(start_ms=0, title="Intro")]
    video_chapters = [SimpleNamespace(start_ms=0, title="Video intro")]

    host = _host(_episode_station())
    host._episode_chapters = episode_chapters
    assert ep.chapters_for(host) == episode_chapters

    host._youtube_stream = SimpleNamespace(chapters=video_chapters)
    assert ep.chapters_for(host) == video_chapters

    host.is_seekable = lambda: False
    assert ep.chapters_for(host) == []


def test_a_stale_chapters_fetch_is_discarded(monkeypatch: pytest.MonkeyPatch) -> None:
    from quill.core.podcasts import chapters as chapters_module

    fetched = [SimpleNamespace(start_ms=0, title="Ch 1")]
    monkeypatch.setattr(chapters_module, "fetch_and_parse_chapters", lambda url, **_kw: fetched)

    class _InlineThread:
        def __init__(self, target: object, **_kw: object) -> None:
            self._target = target

        def start(self) -> None:
            self._target()

    monkeypatch.setattr(ep.threading, "Thread", _InlineThread)

    host = _host(_episode_station())
    host._episode_chapters = []
    ep._fetch_chapters_async(host, "https://cdn.example/c.json", "")
    assert host._episode_chapters == fetched

    # Playback moved on before the fetch landed: the result is discarded.
    stale = _host(_episode_station())
    stale._episode_chapters = []
    original_token = stale._play_token

    def _bump_then_fetch(url: str, **_kw: object) -> list:
        stale._play_token = original_token + 1
        return fetched

    monkeypatch.setattr(chapters_module, "fetch_and_parse_chapters", _bump_then_fetch)
    ep._fetch_chapters_async(stale, "https://cdn.example/c.json", "")
    assert stale._episode_chapters == []
