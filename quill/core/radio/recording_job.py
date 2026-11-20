"""One recording's state, and the clocks its deadline is measured on.

Extracted from ``recording.py`` under GATE-11 (extract, never rebaseline) when
the recorder's deadlines moved off the local wall clock (plan.md, Windows Radio
recording review, 2026-11-20). ``recording`` re-exports every name here, so
``from quill.core.radio.recording import RecordingJob`` keeps working.

wx-free, strict-typed.
"""

from __future__ import annotations

import subprocess
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from quill.core.audio.exact_optilab import ExactOptilab
from quill.core.radio.local_clock import local_now

if TYPE_CHECKING:
    from quill.core.radio.recording import RecordingSettings

#: Clocks, kept apart on purpose. ``local_now`` is the listener's wall clock and
#: is right for filenames and schedules, but it moves when the time zone or
#: daylight saving changes, so it must never measure a duration: a three-hour
#: zone shift half-way through a one-hour recording once made its reconnect ask
#: for 210 more minutes instead of 30. Deadlines are elapsed time on the
#: monotonic clock; the absolute end shown to people is UTC. Module-level so
#: tests can drive them (patch this module) without touching the machine's clock.
monotonic: Callable[[], float] = time.monotonic


def utc_now() -> datetime:
    return datetime.now(UTC)


def reconnect_wait(seconds: float) -> None:
    """Wait out the reconnect delay (a seam: tests replace it with a gate)."""
    threading.Event().wait(seconds)


@dataclass(slots=True)
class JobSnapshot:
    """An immutable, lock-free view of one active recording.

    The multi-recording replacement for the recorder's old scalar
    ``current_*`` getters: :meth:`RadioRecorder.active_jobs` returns one of
    these per running recording so the Recordings list, the resume marker, and
    the tray can each see every capture, not just "the" one.
    """

    job_id: str
    station_name: str
    stream_url: str
    destination: Path
    final_destination: Path
    started_at: datetime
    minutes: int
    filter_graph: str
    entry_id: str = ""
    #: True when the listener asked for this length, false when ``minutes`` is
    #: ``settings.max_duration_minutes`` standing in as a safety cap. Only the
    #: first kind may be counted down to -- see ``radio.recording_progress``,
    #: which explains why showing "142 min left" to somebody who pressed Record
    #: Now announces an intention they never expressed.
    duration_requested: bool = False
    #: The absolute, timezone-aware moment this recording is meant to end. It
    #: does not move across reconnects or clock changes, so a display counting
    #: down to it stays right after a drop (``minutes`` is the planned total).
    ends_at: datetime | None = None


@dataclass
class RecordingJob:
    """Everything one in-flight recording owns (concurrent recording).

    One recording == one job. Each job has its own ffmpeg process, its own
    recent-stderr tail (so two recordings can never cross-contaminate each
    other's fatal/transient reconnect verdict), its own reconnect counter and
    user-stopped flag, and its own Windows kill-on-close handle. Jobs live in
    :attr:`RadioRecorder._jobs` keyed by :attr:`job_id`. A reconnect reuses the
    same ``job_id`` (and the original ``started_at``/``scheduled_end``) so the
    Recordings row and the resume marker keep a stable identity across a drop.
    """

    job_id: str
    process: subprocess.Popen[bytes]
    destination: Path
    final_destination: Path
    station_name: str
    stream_url: str
    settings: RecordingSettings
    minutes: int
    filter_graph: str
    extension: str
    started_at: datetime
    scheduled_end: datetime
    entry_id: str = ""
    #: Carried onto every snapshot; see ``JobSnapshot.duration_requested``. A
    #: continuation inherits it rather than re-deriving it, because a reconnect
    #: is handed the *remaining* minutes as an explicit duration and would
    #: otherwise promote an open-ended capture into one with a deadline.
    duration_requested: bool = False
    #: The exact-OptiLab pass to run over the finished file, or None (the
    #: default) for "leave it as recorded". Carried on the job, not read from
    #: settings at the end, so a recording is post-processed the way it was
    #: started even if the listener changes their settings while it runs.
    exact: ExactOptilab | None = None
    #: Recent ffmpeg stderr (R4/13.3), inspected on a drop to decide fatal vs
    #: transient. Per-job so a second recording's stderr never poisons this
    #: job's verdict.
    stderr_tail: deque[str] = field(default_factory=lambda: deque(maxlen=32))
    #: Guards ``stderr_tail`` -- the drain thread appends/clears it while
    #: _monitor snapshots it, so both sides take this to avoid a "deque mutated
    #: during iteration" RuntimeError. (self._lock does not cover it: the drain
    #: thread never holds self._lock.)
    stderr_lock: threading.Lock = field(default_factory=threading.Lock)
    #: Windows kill-on-close job handle (R4/13.5); one per recording.
    win_job: object | None = None
    reconnect_attempt: int = 0
    #: The stderr drain thread; _monitor lets it finish so ffmpeg's last words
    #: (which say whether the stream dropped) are in the tail before it is read.
    drain: threading.Thread | None = None
    user_stopped: bool = False
    #: When the recording must end, on the monotonic clock (:func:`monotonic`):
    #: what every remaining-time decision is measured against, because it
    #: cannot be moved by a time-zone or daylight-saving change. ``None`` (a
    #: job built by hand in a test) falls back to ``scheduled_end``.
    deadline: float | None = None
    #: The same end as an absolute UTC moment, for display and reports.
    ends_at: datetime | None = None

    def seconds_left(self) -> float:
        """Seconds until the planned end (negative once it has passed)."""
        if self.deadline is not None:
            return self.deadline - monotonic()
        return (self.scheduled_end - local_now()).total_seconds()

    def snapshot(self) -> JobSnapshot:
        return JobSnapshot(
            job_id=self.job_id,
            station_name=self.station_name,
            stream_url=self.stream_url,
            destination=self.destination,
            final_destination=self.final_destination,
            started_at=self.started_at,
            minutes=self.minutes,
            filter_graph=self.filter_graph,
            entry_id=self.entry_id,
            duration_requested=self.duration_requested,
            ends_at=self.ends_at,
        )
