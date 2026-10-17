"""Listening for song changes while a recording runs (xradio2 4.8).

The recorder half of **Split the recording at each song change**. When a
recording starts with that setting on, a :class:`SongSplitter` starts one small
watcher for it: every :data:`POLL_SECONDS` it reads the stream's ICY
``StreamTitle`` (the same one short side connection What's Playing uses,
:func:`quill.core.radio.icy.read_stream_title`) and notes the moment the title
changes. When the recording is over, :meth:`SongSplitter.finish` hands those
moments to :mod:`quill.core.radio.recording_split`, which cuts the finished file
into one file per song.

Why its own watcher, rather than the title poll the player already runs: a
recording is often not the station you are listening to -- a scheduled show
records in the background while you play something else, or while nothing
plays at all. The watcher follows the stream being *recorded*.

Three decisions worth knowing:

* **The moment of a change is the midpoint** between the last poll that heard
  the old title and the first that heard the new one. The change happened
  somewhere in that window; the midpoint halves the worst-case error.
* **A title that is the station talking about itself** ("Live", the station's
  own name, an advert marker) is not a song, by the same rule Song History
  uses (:func:`quill.core.radio.song_history.is_noise_title`), so it never
  causes a cut.
* **A recording that dropped and reconnected is kept whole.** The gap while
  it reconnected is missing from the file but not from the clock, so every
  moment after the drop would land in the wrong place. Saying so is better
  than cutting songs in half.

GATE-9 / network egress: the watcher contacts only the stream URL being
recorded, which the recorder is already connected to, never a third party;
Safe Mode cannot reach it because the radio cannot record there. wx-free,
strict-typed; the tests drive it with a fake title reader and a fake clock.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.radio.recording_split import (
    SongChange,
    SplitOutcome,
    SplitPlan,
    describe_split,
    plan_split,
    split_recording,
)
from quill.core.radio.song_history import is_noise_title

logger = logging.getLogger(__name__)

__all__ = ["POLL_SECONDS", "SongSplitter", "SongTimeline"]

#: How often the watcher reads the title. Short enough that a cut is rarely
#: more than a few seconds off; long enough that a three-hour recording makes
#: about a thousand tiny requests rather than ten thousand.
POLL_SECONDS = 10.0

#: (stream url) -> the current raw title, "" when there is none.
TitleReader = Callable[[str], str]
#: The seconds clock (time.monotonic by default; a fake in the tests).
Clock = Callable[[], float]


@dataclass(slots=True)
class SongTimeline:
    """The song changes heard during one recording, measured from its start."""

    station_name: str = ""
    started: float = 0.0
    first_title: str = ""
    changes: list[SongChange] = field(default_factory=list)
    interrupted: bool = False
    _current: str = ""
    _last_heard: float = 0.0

    def hear(self, title: str, now: float) -> bool:
        """Note that the stream said *title* at *now*. Returns whether that
        was a song change worth cutting at."""
        if not title or is_noise_title(title, self.station_name):
            return False
        if not self._current:
            # The song already playing when the recording began: it names the
            # first file and is not a cut.
            self._current = title
            self._last_heard = now
            if not self.changes:
                self.first_title = title
            return False
        if title == self._current:
            self._last_heard = now
            return False
        moment = (self._last_heard + now) / 2.0
        self.changes.append(SongChange(max(0.0, moment - self.started), title))
        self._current = title
        self._last_heard = now
        return True


class _Watch:
    """One recording's watcher thread."""

    def __init__(
        self,
        url: str,
        timeline: SongTimeline,
        read_title: TitleReader,
        clock: Clock,
        poll_seconds: float,
    ) -> None:
        self.timeline = timeline
        self.stopped = threading.Event()
        self.lock = threading.Lock()
        self._url = url
        self._read = read_title
        self._clock = clock
        self._poll = poll_seconds
        self.thread = threading.Thread(target=self._run, name="radio-song-watch", daemon=True)

    def _run(self) -> None:
        while not self.stopped.is_set():
            self.poll_once()
            self.stopped.wait(self._poll)

    def poll_once(self) -> None:
        try:
            title = self._read(self._url)
        except Exception:  # noqa: BLE001 - a missed title must never touch the recording
            logger.debug("song watch: title read failed", exc_info=True)
            return
        with self.lock:
            if self.timeline.hear(title, self._clock()):
                logger.info("song watch: change at %.1fs", self.timeline.changes[-1].offset)


def _read_icy_title(url: str) -> str:
    from quill.core.radio.icy import read_stream_title

    return read_stream_title(url)


class SongSplitter:
    """Owns every recording's song watcher and the split at the end.

    The recorder calls :meth:`connection` each time a recording's ffmpeg
    starts (a continuation marks the recording interrupted), :meth:`finish`
    with the finished file, and :meth:`discard` / :meth:`cancel_all` when a
    recording ends with nothing to keep or the app closes.
    """

    def __init__(
        self,
        *,
        read_title: TitleReader | None = None,
        clock: Clock = time.monotonic,
        poll_seconds: float = POLL_SECONDS,
        split: Callable[[SplitPlan], SplitOutcome] | None = None,
        start_threads: bool = True,
    ) -> None:
        # None means the module's own reader, looked up when a watch starts
        # rather than bound here, so the test suite can swap it for a fake.
        self._read = read_title
        self._clock = clock
        self._poll = poll_seconds
        self._split: Callable[[SplitPlan], SplitOutcome] = split or split_recording
        self._start_threads = start_threads
        self._lock = threading.Lock()
        self._watches: dict[str, _Watch] = {}

    def watching(self, job_id: str) -> bool:
        with self._lock:
            return job_id in self._watches

    def connection(
        self,
        job_id: str,
        stream_url: str,
        *,
        station_name: str = "",
        enabled: bool,
        continuation: bool,
    ) -> None:
        """A recording's ffmpeg just started. Begin watching a new recording
        when the setting is on; mark a watched one interrupted on reconnect."""
        with self._lock:
            existing = self._watches.get(job_id)
            if continuation:
                if existing is not None:
                    existing.timeline.interrupted = True
                return
            if not enabled or existing is not None:
                return
            timeline = SongTimeline(station_name=station_name, started=self._clock())
            reader = self._read or _read_icy_title
            watch = _Watch(stream_url, timeline, reader, self._clock, self._poll)
            self._watches[job_id] = watch
        if self._start_threads:
            watch.thread.start()

    def poll_now(self, job_id: str) -> None:
        """Read the title once, now (the tests' way to drive a watcher)."""
        with self._lock:
            watch = self._watches.get(job_id)
        if watch is not None:
            watch.poll_once()

    def _stop(self, job_id: str) -> _Watch | None:
        with self._lock:
            watch = self._watches.pop(job_id, None)
        if watch is not None:
            watch.stopped.set()
        return watch

    def discard(self, job_id: str) -> None:
        self._stop(job_id)

    def cancel_all(self) -> None:
        with self._lock:
            watches = list(self._watches.values())
            self._watches.clear()
        for watch in watches:
            watch.stopped.set()

    def finish(self, job_id: str, path: Path | None, *, lead_trim: float = 0.0) -> str:
        """Split the finished recording at the songs heard; returns the
        sentence to say ("" when this recording was not being split).

        *path* is the finished file, or ``None`` when its parts could not be
        joined (then it is kept as it is, and said so). *lead_trim* is what the
        pre-roll guard cut from the front.
        """
        watch = self._stop(job_id)
        if watch is None:
            return ""
        with watch.lock:
            timeline = watch.timeline
            duration = self._clock() - timeline.started
            changes = list(timeline.changes)
            first = timeline.first_title
            interrupted = timeline.interrupted
        if path is None:
            return "The recording was not split into songs: its parts could not be joined first."

        if interrupted:
            return (
                f"Kept {path.name} as one recording: the stream dropped while it "
                "recorded, so the song changes no longer line up with the audio."
            )
        plan = plan_split(path, changes, duration=duration, first_title=first, lead_trim=lead_trim)
        outcome = self._split(plan)
        return describe_split(outcome)
