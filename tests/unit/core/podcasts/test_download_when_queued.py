"""Queued episodes download at once, whatever the show's playback mode (Chris Nova)."""

from __future__ import annotations

from quill.core.podcasts import acquisition, queue, queue_events
from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary


def _library(mode: str = "stream") -> tuple[PodcastLibrary, PodcastShow]:
    library = PodcastLibrary()
    show = PodcastShow(id="s", title="Show", feed_url="https://x/feed")
    show.episodes = [
        PodcastEpisode(guid="g1", title="One", audio_url="https://x/1.mp3"),
        PodcastEpisode(guid="g2", title="Two", audio_url="https://x/2.mp3"),
    ]
    library.shows.append(show)
    library.apply_show_override(show, playback_mode=mode)
    return library, show


def test_every_way_into_the_queue_is_heard() -> None:
    heard: list[tuple[str, str]] = []
    queue_events.set_listener(lambda show_id, guid: heard.append((show_id, guid)))
    try:
        library, _show = _library()
        assert queue.add_to_queue(library, "s", "g1")
        assert library.queue_episode("s", "g2", "Auto-Queue")
        queue.play_next(library, "s", "g1")  # already queued: moved, not re-heard
        assert not queue.add_to_queue(library, "s", "g1")
        assert heard == [("s", "g1"), ("s", "g2")]
    finally:
        queue_events.set_listener(None)


def test_a_failing_listener_never_stops_queueing() -> None:
    def broken(_show_id: str, _guid: str) -> None:
        raise RuntimeError("boom")

    queue_events.set_listener(broken)
    try:
        library, _show = _library()
        assert queue.add_to_queue(library, "s", "g1")
    finally:
        queue_events.set_listener(None)


def test_a_streaming_show_downloads_a_queued_episode_at_once() -> None:
    library, show = _library("stream")
    assert acquisition.download_when_queued(library, show, show.episodes[0])


def test_not_when_off_downloaded_stream_only_or_paused() -> None:
    library, show = _library()
    episode = show.episodes[0]
    library.settings.auto_download_queued = False
    assert not acquisition.download_when_queued(library, show, episode)
    library.settings.auto_download_queued = True
    episode.downloaded_path = "C:/ep.mp3"
    assert not acquisition.download_when_queued(library, show, episode)
    episode.downloaded_path = ""
    episode.mode_override = "stream"
    assert not acquisition.download_when_queued(library, show, episode)
    episode.mode_override = ""
    show.paused = True
    assert not acquisition.download_when_queued(library, show, episode)
