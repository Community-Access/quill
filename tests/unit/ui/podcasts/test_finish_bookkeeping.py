"""Finishing an episode: one bookkeeping path for every way it finishes
(earshot.md F1), and delete-after-play that waits for the player to let go of
a file it still has open."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from quill.core.podcasts.models import PodcastEpisode, PodcastSettings
from quill.ui.podcasts.finish_bookkeeping import record_finish
from tests.wx_session import patch_call_after


class _Host:
    def __init__(self, settings: PodcastSettings) -> None:
        self._podcast_library = SimpleNamespace(effective_settings=lambda _show: settings)
        self.shared: list[tuple[int, bool]] = []
        self.flushed: list[bool] = []
        self.saves = 0

    def _podcast_share_place(self, _show: Any, _episode: Any, ms: int, *, finished: bool) -> None:
        self.shared.append((ms, finished))

    def _podcast_flush_stats(self, *, completed: bool = False) -> None:
        self.flushed.append(completed)

    def _save_podcast_library(self) -> None:
        self.saves += 1


def _episode(tmp_path: Any) -> PodcastEpisode:
    audio = tmp_path / "ep.mp3"
    audio.write_bytes(b"x")
    return PodcastEpisode(
        guid="g", title="T", audio_url="https://e/x.mp3", downloaded_path=str(audio), position_ms=5
    )


def test_a_finish_marks_played_shares_and_counts(tmp_path: Any) -> None:
    host = _Host(PodcastSettings())
    episode = _episode(tmp_path)
    record_finish(host, object(), episode)
    assert episode.played is True and episode.position_ms == 0
    assert host.shared == [(0, True)]
    assert host.flushed == [True]


def test_an_open_file_is_deleted_only_after_the_player_lets_go(
    tmp_path: Any, monkeypatch: Any
) -> None:
    host = _Host(PodcastSettings(delete_after_play=True))
    episode = _episode(tmp_path)
    queued: list[Any] = []
    capture = patch_call_after(monkeypatch, lambda func, *a, **k: queued.append(func))
    record_finish(host, object(), episode, file_still_open=True)
    assert episode.downloaded_path  # not yet: the engine still has it open
    assert len(capture.calls) == 1
    queued[0]()  # the next turn of the event loop, after the engine closed
    assert episode.downloaded_path == ""
    assert host.saves == 1


def test_nothing_is_scheduled_when_nothing_would_be_deleted(
    tmp_path: Any, monkeypatch: Any
) -> None:
    host = _Host(PodcastSettings())
    capture = patch_call_after(monkeypatch)
    record_finish(host, object(), _episode(tmp_path), file_still_open=True)
    assert capture.calls == []
