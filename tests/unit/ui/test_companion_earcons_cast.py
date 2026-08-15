"""QUILL Cast's three earcons fire on real state changes only (#1302).

Download start, download completion and an episode ending are states Cast
changed through in silence, so the cues are posted at the state-change
callbacks themselves rather than riding an announcement. The download-status
callback also carries every progress chunk, so the interesting assertion here
is that a forty-chunk download makes one sound, not forty.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from quill.core.sound_events import SoundEvent
from quill.ui.main_frame_podcasts import PodcastsMixin


class _Queue:
    def __init__(self, active: int = 1) -> None:
        self.active = active

    def active_count(self) -> int:
        return self.active


class _Host(PodcastsMixin):
    def __init__(self, *, active: int = 1) -> None:
        self._podcast_download_queue = _Queue(active)
        self._podcast_manager_dialog = None
        self._podcast_library = SimpleNamespace(
            find_show=lambda _id: None,
            effective_settings=lambda _show: SimpleNamespace(),
        )
        self.spoken: list[tuple[str, str]] = []
        # 1.1.0: the statistics accumulator and the chapter-skip marks are
        # part of the mixin's state, initialized by _init_podcast_session in
        # the real host. This fake only exercises the earcon paths, so it
        # supplies the two attributes those paths touch on the way past.
        self._init_podcast_session()

    def _announce(self, message: str, *, force: bool = False, sound: str = "") -> None:
        self.spoken.append((message, sound))

    def _refresh_statusbar(self) -> None: ...
    def _save_podcast_library(self) -> None: ...
    def _podcast_play_next_from_queue(self, **_kwargs: object) -> None: ...


@pytest.fixture
def cues(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    posted: list[str] = []
    # Two call sites since the playback cache landed: the episode-finished cue
    # is still in main_frame_podcasts, the two download cues moved out with the
    # transfer callbacks into PodcastTransfersMixin. Patch both, so this stays
    # a test of "which cue fires" rather than of where the code lives.
    monkeypatch.setattr("quill.ui.main_frame_podcasts.post_cue", posted.append)
    monkeypatch.setattr("quill.ui.main_frame_podcast_transfers.post_cue", posted.append)
    return posted


def _item(status: str = "downloading") -> Any:
    return SimpleNamespace(status=status, show_id="s1", episode_guid="e1", destination="ep.mp3")


def test_a_batch_of_downloads_cues_once_not_once_per_progress_chunk(cues: list[str]) -> None:
    host = _Host()
    for _ in range(40):
        host._apply_podcast_download_status(_item())
    assert cues == [SoundEvent.CAST_DOWNLOAD_STARTED]


def test_the_download_cue_is_armed_again_once_the_queue_drains(cues: list[str]) -> None:
    host = _Host()
    host._apply_podcast_download_status(_item())
    host._podcast_download_queue.active = 0
    host._apply_podcast_download_status(_item("completed"))
    host._podcast_download_queue.active = 1
    host._apply_podcast_download_status(_item())
    assert cues == [SoundEvent.CAST_DOWNLOAD_STARTED, SoundEvent.CAST_DOWNLOAD_STARTED]


def test_a_queued_item_that_has_not_started_does_not_cue(cues: list[str]) -> None:
    host = _Host()
    host._apply_podcast_download_status(_item("queued"))
    assert cues == []


def test_a_finished_download_cues_download_complete(cues: list[str]) -> None:
    host = _Host()
    host._apply_podcast_download_completed(_item("completed"))
    assert cues == [SoundEvent.CAST_DOWNLOAD_COMPLETE]


def test_an_episode_reaching_its_end_cues_episode_finished(cues: list[str]) -> None:
    episode = SimpleNamespace(played=False, position_ms=1234, downloaded_path="")
    show = SimpleNamespace(find_episode=lambda _guid: episode)
    host = _Host()
    host._podcast_library = SimpleNamespace(
        find_show=lambda _id: show,
        effective_settings=lambda _show: SimpleNamespace(retention="keep"),
    )
    host._on_podcast_episode_finished("s1", "e1")
    assert cues == [SoundEvent.CAST_EPISODE_FINISHED]
    assert episode.played is True


def test_an_unknown_episode_does_not_cue(cues: list[str]) -> None:
    host = _Host()
    host._on_podcast_episode_finished("missing", "e1")
    assert cues == []
