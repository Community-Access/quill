"""Save Episode Audio As, waiting for a download it started (list.md 2.2).

The old shape asked "download it now? then run this command again", which is
honest about not blocking the UI thread and makes the listener the scheduler:
press the key, listen for a completion you have to be watching for, remember
what you were doing, press the key again. Earshot says **"Preparing audio file
for export"** and opens the save dialog when the bytes land.

A wait has four endings, and this file is mostly about the three that are not
success: the download fails, somebody cancels it from the Downloads window, or
it simply takes long enough that going on waiting silently is its own fault. A
verb that only handles the happy ending is a verb that hangs.

The decisions are pure (:mod:`quill.core.podcasts.audio_export`) and tested
here directly; the timer is driven by pushing ticks at it rather than by
sleeping, so the suite never waits on a clock.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from quill.core.podcasts import audio_export
from quill.core.podcasts.models import PodcastEpisode, PodcastShow

wx = pytest.importorskip("wx")

from quill.ui.podcasts.export_audio import (  # noqa: E402
    LIVE_TIMERS,
    copy_episode_path,
    export_episode_audio,
)


@pytest.fixture(scope="module", autouse=True)
def wx_app():
    app = wx.App()
    yield app
    app.Destroy()


@pytest.fixture
def frame():
    window = wx.Frame(None)
    yield window
    window.Destroy()


def _episode(guid: str = "ep1", *, downloaded: str = "") -> PodcastEpisode:
    return PodcastEpisode(
        guid=guid,
        title="Episode One",
        audio_url=f"https://example.com/{guid}.mp3",
        published="2026-07-01T00:00:00",
        downloaded_path=downloaded,
    )


def _show() -> PodcastShow:
    return PodcastShow(id="show-1", title="Test Show", feed_url="https://e/f.xml", episodes=[])


class _Queue:
    """A download queue whose one row the test moves through its states."""

    def __init__(self, status: str = "queued") -> None:
        self.enqueued: list[str] = []
        self.status = status
        self.destination = ""
        self.error = ""

    def enqueue(self, item_id: str, **_kwargs: object) -> None:
        self.enqueued.append(item_id)

    def get(self, _item_id: str) -> object | None:
        if self.status == "gone":
            return None
        return SimpleNamespace(status=self.status, destination=self.destination, error=self.error)


def _tick(frame, times: int = 1) -> None:
    """Fire the export's timer without waiting on a real clock.

    ``Notify`` is the timer's own "the interval elapsed" entry point, so this
    drives exactly the path a real tick takes -- including the id check that
    keeps one frame's timers out of each other's handlers. ``wx.TimerEvent``
    cannot be constructed from Python, so forging the event is not an option.
    """
    for _ in range(times):
        for timer in _timers(frame):
            timer.Notify()


def _timers(frame) -> list:
    return list(getattr(frame, LIVE_TIMERS, []))


# -- the pure decisions ----------------------------------------------------------


def test_a_completed_download_is_ready() -> None:
    assert audio_export.poll_state(SimpleNamespace(status="completed"), 1) == audio_export.READY


def test_a_failed_download_is_not_a_wait_that_carries_on() -> None:
    assert audio_export.poll_state(SimpleNamespace(status="failed"), 1) == audio_export.FAILED


def test_a_row_that_vanished_was_cancelled() -> None:
    """Reading "gone" as "still going" is how a wait becomes forever."""
    assert audio_export.poll_state(None, 1) == audio_export.CANCELLED
    assert audio_export.poll_state(SimpleNamespace(status="cancelled"), 1) == audio_export.CANCELLED


def test_a_download_still_running_keeps_waiting() -> None:
    for status in ("queued", "downloading", "paused"):
        assert audio_export.poll_state(SimpleNamespace(status=status), 5) == audio_export.WAITING


def test_the_wait_has_a_ceiling() -> None:
    """A progress-free wait past a few minutes cannot be told from a hang."""
    running = SimpleNamespace(status="downloading")
    assert audio_export.poll_state(running, audio_export.WAIT_CEILING_SECONDS - 1) == (
        audio_export.WAITING
    )
    assert audio_export.poll_state(running, audio_export.WAIT_CEILING_SECONDS) == (
        audio_export.GAVE_UP
    )


def test_giving_up_says_the_download_carries_on() -> None:
    """The waiting ended. The download did not, and the sentence says which."""
    said = audio_export.gave_up("Episode One")
    assert "still downloading" in said
    assert "Downloads window" in said


# -- the wait, end to end --------------------------------------------------------


def test_a_streamed_episode_starts_a_download_and_says_it_is_preparing(frame, tmp_path) -> None:
    queue = _Queue()
    said: list[str] = []
    episode = _episode()

    started = export_episode_audio(
        frame, queue, tmp_path, _show(), episode, announce=said.append, wx=wx
    )

    assert started is False, "nothing is saved yet -- the download only just began"
    assert queue.enqueued == ["ep1"]
    assert said == [audio_export.preparing("Episode One")]
    assert audio_export.PREPARING in said[0]
    assert _timers(frame), "and something is watching for the file"


def test_the_save_dialog_opens_when_the_download_lands(frame, tmp_path, monkeypatch) -> None:
    landed = tmp_path / "ep1.mp3"
    landed.write_bytes(b"the audio")
    destination = tmp_path / "mine.mp3"
    queue = _Queue()
    said: list[str] = []
    episode = _episode()

    export_episode_audio(frame, queue, tmp_path, _show(), episode, announce=said.append, wx=wx)

    monkeypatch.setattr(wx, "FileDialog", _dialog_choosing(destination))
    queue.status = "completed"
    queue.destination = str(landed)
    episode.downloaded_path = str(landed)
    _tick(frame)

    assert destination.read_bytes() == b"the audio"
    assert landed.exists(), "the managed copy survives -- this is a copy, not a move"
    assert any("Saved" in message for message in said)


def test_a_failed_download_says_so_rather_than_waiting_on(frame, tmp_path) -> None:
    queue = _Queue()
    said: list[str] = []

    export_episode_audio(frame, queue, tmp_path, _show(), _episode(), announce=said.append, wx=wx)
    queue.status = "failed"
    queue.error = "the host refused the connection"
    _tick(frame)

    assert "could not be downloaded" in said[-1]
    assert "host refused" in said[-1]
    assert _timers(frame) == [], "the wait let go of its timer"


def test_cancelling_the_download_ends_the_wait(frame, tmp_path) -> None:
    """Cancelled from the Downloads window, which the export cannot see."""
    queue = _Queue()
    said: list[str] = []

    export_episode_audio(frame, queue, tmp_path, _show(), _episode(), announce=said.append, wx=wx)
    queue.status = "gone"
    _tick(frame)

    assert "cancelled" in said[-1]
    assert _timers(frame) == [], "the wait let go of its timer"


def test_the_row_is_re_read_however_the_export_ended(frame, tmp_path) -> None:
    """The download changed the row, minutes after the click that started it."""
    queue = _Queue()
    refreshed: list[int] = []

    export_episode_audio(
        frame,
        queue,
        tmp_path,
        _show(),
        _episode(),
        announce=lambda _m: None,
        wx=wx,
        on_finished=lambda: refreshed.append(1),
    )
    assert refreshed == [], "not while it is still downloading"

    queue.status = "failed"
    _tick(frame)
    assert refreshed == [1]


def test_a_downloaded_episode_skips_the_wait_entirely(frame, tmp_path, monkeypatch) -> None:
    landed = tmp_path / "ep1.mp3"
    landed.write_bytes(b"audio")
    destination = tmp_path / "copy.mp3"
    monkeypatch.setattr(wx, "FileDialog", _dialog_choosing(destination))
    queue = _Queue()
    said: list[str] = []

    saved = export_episode_audio(
        frame,
        queue,
        tmp_path,
        _show(),
        _episode(downloaded=str(landed)),
        announce=said.append,
        wx=wx,
    )

    assert saved is True
    assert queue.enqueued == [], "nothing to fetch, so nothing is queued"
    assert not any(audio_export.PREPARING in message for message in said)


def test_a_download_recorded_but_missing_is_fetched_again(frame, tmp_path) -> None:
    """The episode says it has a file; the disk disagrees. Fetching it again is
    the useful answer, not a copy that raises."""
    queue = _Queue()
    said: list[str] = []

    export_episode_audio(
        frame,
        queue,
        tmp_path,
        _show(),
        _episode(downloaded=str(tmp_path / "vanished.mp3")),
        announce=said.append,
        wx=wx,
    )

    assert queue.enqueued == ["ep1"]
    assert audio_export.PREPARING in said[0]


# -- Copy File Path --------------------------------------------------------------


class _Clipboard:
    def __init__(self, *, opens: bool = True) -> None:
        self.text = ""
        self.opens = opens

    def Open(self) -> bool:  # noqa: N802 - wx naming
        return self.opens

    def SetData(self, data: object) -> None:  # noqa: N802 - wx naming
        self.text = data.GetText()

    def Flush(self) -> None:  # noqa: N802 - wx naming
        return None

    def Close(self) -> None:  # noqa: N802 - wx naming
        return None


def test_copy_path_copies_the_file_and_names_both_halves(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A full path read aloud is a line of separators; the name and the folder
    are the two things somebody is actually listening for."""
    audio = tmp_path / "ep1.mp3"
    audio.write_bytes(b"audio")
    clipboard = _Clipboard()
    monkeypatch.setattr(wx, "TheClipboard", clipboard)
    said: list[str] = []

    assert copy_episode_path(_episode(downloaded=str(audio)), announce=said.append, wx=wx) is True
    assert clipboard.text == str(audio)
    assert "ep1.mp3" in said[0]
    assert str(tmp_path) in said[0]


def test_copy_path_refuses_when_there_is_no_file(tmp_path, monkeypatch) -> None:
    """A path to nothing is worse than no path."""
    clipboard = _Clipboard()
    monkeypatch.setattr(wx, "TheClipboard", clipboard)
    said: list[str] = []

    assert copy_episode_path(_episode(), announce=said.append, wx=wx) is False
    assert clipboard.text == "", "the clipboard keeps whatever it had"
    assert "no longer on this computer" in said[0]


def test_copy_path_reports_a_clipboard_that_will_not_open(tmp_path, monkeypatch) -> None:
    audio = tmp_path / "ep1.mp3"
    audio.write_bytes(b"audio")
    monkeypatch.setattr(wx, "TheClipboard", _Clipboard(opens=False))
    said: list[str] = []

    assert copy_episode_path(_episode(downloaded=str(audio)), announce=said.append, wx=wx) is False
    assert "clipboard" in said[0].lower()


# -- helpers ---------------------------------------------------------------------


def _dialog_choosing(destination: Path):
    class _FileDialog:
        def __init__(self, _parent: object, **_kwargs: object) -> None:
            pass

        def __enter__(self) -> _FileDialog:
            return self

        def __exit__(self, *_exc: object) -> bool:
            return False

        def ShowModal(self) -> int:  # noqa: N802 - wx naming
            return wx.ID_OK

        def GetPath(self) -> str:  # noqa: N802 - wx naming
            return str(destination)

    return _FileDialog
