"""The Radio -> Cast listening handoff.

Radio appends the latest word on each podcast episode it played; Cast folds
those records into its own library at launch. The file is a handoff, not a
shared store -- Radio never writes Cast's stores, so nothing can be
clobbered no matter which app is open.
"""

from __future__ import annotations

import json
import time

from quill.core.podcasts.models import PodcastEpisode, PodcastShow
from quill.core.podcasts.radio_listens import (
    _read,
    merge_radio_listens,
    merge_summary,
    record_listen,
)
from quill.core.podcasts.subscriptions import PodcastLibrary


def _library_with_episode(
    feed: str = "https://a.example/feed", audio: str = "https://a.example/1.mp3"
) -> tuple[PodcastLibrary, PodcastEpisode]:
    episode = PodcastEpisode(guid="g1", title="Episode One", audio_url=audio)
    show = PodcastShow(id="s1", title="Aardvark Hour", feed_url=feed, episodes=[episode])
    library = PodcastLibrary()
    library.shows.append(show)
    return library, episode


# --- recording (the Radio side) -------------------------------------------------


def test_record_keeps_the_latest_word_per_episode(tmp_path) -> None:
    record_listen(tmp_path, feed_url="https://f", audio_url="https://a/1.mp3", position_ms=1000)
    record_listen(tmp_path, feed_url="https://f", audio_url="https://a/1.mp3", position_ms=5000)
    record_listen(tmp_path, feed_url="https://f", audio_url="https://a/2.mp3", position_ms=2000)
    records = _read(tmp_path)
    assert len(records) == 2  # one per episode, not a keystroke log
    by_audio = {row["audio"]: row for row in records}
    assert by_audio["https://a/1.mp3"]["position_ms"] == 5000


def test_record_refuses_records_it_could_never_match(tmp_path) -> None:
    record_listen(tmp_path, feed_url="", audio_url="https://a/1.mp3", position_ms=1000)
    record_listen(tmp_path, feed_url="https://f", audio_url="", position_ms=1000)
    assert _read(tmp_path) == []


# --- merging (the Cast side) ----------------------------------------------------


def test_merge_sets_position_and_consumes_the_record(tmp_path) -> None:
    library, episode = _library_with_episode()
    record_listen(
        tmp_path,
        feed_url="https://a.example/feed",
        audio_url="https://a.example/1.mp3",
        position_ms=90_000,
    )
    updated, finished = merge_radio_listens(tmp_path, library)
    assert (updated, finished) == (1, 0)
    assert episode.position_ms == 90_000
    assert not episode.played
    assert _read(tmp_path) == []  # matched -> consumed


def test_merge_marks_finished_played_with_place_cleared(tmp_path) -> None:
    library, episode = _library_with_episode()
    episode.position_ms = 50_000
    record_listen(
        tmp_path,
        feed_url="https://a.example/feed",
        audio_url="https://a.example/1.mp3",
        position_ms=3_600_000,
        finished=True,
    )
    updated, finished = merge_radio_listens(tmp_path, library)
    assert (updated, finished) == (1, 1)
    assert episode.played
    assert episode.position_ms == 0  # replaying starts at the top


def test_merge_never_rewinds_an_episode_cast_already_finished(tmp_path) -> None:
    library, episode = _library_with_episode()
    episode.played = True
    record_listen(
        tmp_path,
        feed_url="https://a.example/feed",
        audio_url="https://a.example/1.mp3",
        position_ms=90_000,
    )
    updated, _finished = merge_radio_listens(tmp_path, library)
    assert updated == 0
    assert episode.played and episode.position_ms == 0


def test_unmatched_records_wait_for_the_feed_to_arrive(tmp_path) -> None:
    # The episode may simply not be fetched into Cast's library yet.
    library, _episode = _library_with_episode()
    record_listen(
        tmp_path,
        feed_url="https://other.example/feed",
        audio_url="https://other.example/9.mp3",
        position_ms=1_000,
    )
    updated, _finished = merge_radio_listens(tmp_path, library)
    assert updated == 0
    assert len(_read(tmp_path)) == 1  # kept for a later merge


def test_stale_unmatched_records_are_dropped(tmp_path) -> None:
    stale = {
        "feed": "https://gone.example/feed",
        "audio": "https://gone.example/9.mp3",
        "position_ms": 1000,
        "finished": False,
        "at": time.time() - 40 * 24 * 3600,
    }
    (tmp_path / "radio-listens.json").write_text(json.dumps([stale]), encoding="utf-8")
    library, _episode = _library_with_episode()
    merge_radio_listens(tmp_path, library)
    assert _read(tmp_path) == []


def test_merge_survives_a_garbage_file(tmp_path) -> None:
    (tmp_path / "radio-listens.json").write_text("{not json", encoding="utf-8")
    library, _episode = _library_with_episode()
    assert merge_radio_listens(tmp_path, library) == (0, 0)


def test_merge_summary_says_something_only_when_something_happened() -> None:
    assert merge_summary(0, 0) == ""
    assert "1 episode finished" in merge_summary(1, 1)
    assert "3 episodes updated" in merge_summary(3, 1)
