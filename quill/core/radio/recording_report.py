"""One honest sentence about how a radio recording ended.

WHY THIS EXISTS
---------------
A real report (Rick, QUILLVille, 2026-10-18): a weekly 190-minute scheduled
recording, stopped with Stop All near its end, and afterwards no recording he
could find. Reading the recorder showed that stopping early was never the
problem -- but it also showed how little the app had told him along the way:

* every part of a dropped-and-resumed recording said "Recording saved" as it
  landed, so the same words meant "the show is safe" and "the stream just
  dropped";
* a show whose station went away for good at minute 40 ended with exactly the
  sentence a complete three-hour capture ends with, so the first sign of a
  short recording was opening it days later;
* the sentence gave a file name and nothing else -- not how long it was, not
  which folder it was in.

So the recorder now builds one :class:`RecordingReport` when a recording is
truly over (after any reconnect has been decided and parts have been joined),
and :func:`describe` turns it into the one sentence the listener hears and can
find again in Activity. Pure: a job, a path and a clock in; a value and a
string out.

wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Protocol

from quill.core.radio import recording_outcome

#: The listener pressed Stop (or Stop All, or closed the app).
STOPPED = "stopped"
#: The recording ran to the end it was given.
FINISHED = "finished"
#: The stream went away and did not come back before the recording's end.
ENDED_EARLY = "ended_early"

#: A drop this close to the scheduled end is the show ending, not a failure:
#: stations commonly cut the stream at the top of the hour, a few seconds
#: before the ``-t`` cap would have.
_EARLY_MARGIN_SECONDS = 90


class _Settings(Protocol):
    @property
    def reconnect_enabled(self) -> bool: ...


class _Job(Protocol):
    """The parts of ``recording.RecordingJob`` a report reads."""

    @property
    def job_id(self) -> str: ...
    @property
    def station_name(self) -> str: ...
    @property
    def started_at(self) -> datetime: ...
    @property
    def scheduled_end(self) -> datetime: ...
    @property
    def duration_requested(self) -> bool: ...
    @property
    def destination(self) -> Path: ...
    @property
    def final_destination(self) -> Path: ...
    @property
    def reconnect_attempt(self) -> int: ...
    @property
    def user_stopped(self) -> bool: ...
    @property
    def settings(self) -> _Settings: ...


@dataclass(frozen=True, slots=True)
class RecordingReport:
    """How one recording ended, and where it is now."""

    job_id: str
    station_name: str
    #: Where the recording is now (the joined file, or the first part when a
    #: join could not be done). ``None`` only if nothing landed at all.
    path: Path | None
    how: str  # STOPPED / FINISHED / ENDED_EARLY
    started_at: datetime
    ended_at: datetime
    #: The length the recording was given, when it was chosen (a schedule, a
    #: Record-for); 0 for an open-ended capture, which has no "early".
    planned_seconds: int = 0
    #: Plain-words cause of an early end ("the connection failed").
    reason: str = ""
    #: How many times the recording reconnected after a drop.
    reconnects: int = 0
    #: The finished file could not be moved out of the temporary folder.
    left_in_temp: bool = False

    @property
    def seconds(self) -> int:
        """Wall-clock length, start to end (reconnect waits included)."""
        return max(0, int((self.ended_at - self.started_at).total_seconds()))


def build_report(
    job: _Job,
    path: Path | None,
    *,
    dropped: bool,
    fatal: bool,
    stderr_tail: list[str],
    now: datetime,
) -> RecordingReport:
    """The report for *job*, which has just finished for good.

    *dropped* is the recorder's own verdict on the last part (it ended without
    being asked to); *fatal* says the stream refused or vanished rather than
    hiccuped. Called after the reconnect decision, so a Stop pressed during a
    reconnect wait reads as :data:`STOPPED`, which is what it was.
    """
    short = max(0, int((job.scheduled_end - now).total_seconds()))
    planned = 0
    if job.duration_requested:
        planned = max(0, int((job.scheduled_end - job.started_at).total_seconds()))
    if job.user_stopped:
        how, reason = STOPPED, ""
    elif not dropped or (planned and short < _EARLY_MARGIN_SECONDS):
        how, reason = FINISHED, ""
    else:
        how = ENDED_EARLY
        reason = _early_reason(job, fatal=fatal, stderr_tail=stderr_tail)
    left_in_temp = (
        path is not None
        and job.destination != job.final_destination
        and path.parent == job.destination.parent
    )
    return RecordingReport(
        job_id=job.job_id,
        station_name=job.station_name,
        path=path,
        how=how,
        started_at=job.started_at,
        ended_at=now,
        planned_seconds=planned,
        reason=reason,
        reconnects=job.reconnect_attempt,
        left_in_temp=left_in_temp,
    )


def _early_reason(job: _Job, *, fatal: bool, stderr_tail: list[str]) -> str:
    named = recording_outcome.reason_from_stderr(stderr_tail)
    if fatal:
        return named or "the station stopped sending the stream"
    if not job.settings.reconnect_enabled:
        return "the stream dropped, and reconnecting is turned off in Recording Settings"
    tries = job.reconnect_attempt
    if tries:
        noun = "attempt" if tries == 1 else "attempts"
        return (
            f"the station stopped responding and did not come back after {tries} reconnect {noun}"
        )
    return named or "the station stopped responding and did not come back"


def format_length(seconds: int) -> str:
    """``3 hours 4 minutes``, ``44 minutes``, ``1 hour``, ``under a minute``."""
    minutes = max(0, seconds) // 60
    if minutes < 1:
        return "under a minute"
    hours, minutes = divmod(minutes, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    return " ".join(parts)


def spoken_start(when: datetime) -> str:
    """``Friday 4:58 PM`` -- how a listener names a recording, unlike its file
    name (``WNYC - 2026-10-16 16-58-00.mp3`` reads as a string of dashes and is
    some thirty braille cells before anything useful)."""
    hour = when.hour % 12 or 12
    return f"{when:%A} {hour}:{when:%M} {'AM' if when.hour < 12 else 'PM'}"


def describe(report: RecordingReport) -> str:
    """What is said, and kept in Activity, when a recording is over.

    The fact the listener needs leads -- saved or not, how much, where -- and
    the cause of an early end comes last as its own sentence, so a braille
    reader can stop once they have what they need. The file name is left to
    Activity and Open Folder: the station and start time identify the
    recording in fewer words.
    """
    station = report.station_name or "Radio"
    what = f"{station}, started {spoken_start(report.started_at)}"
    saved_minutes = report.seconds // 60
    if report.how == ENDED_EARLY and report.planned_seconds:
        amount = f"{saved_minutes} of {report.planned_seconds // 60} minutes"
    else:
        amount = format_length(report.seconds)
    if report.path is None:
        where = ""
    elif report.left_in_temp:
        where = ", but not in your recordings folder: it is still in the temporary recording folder"
    else:
        where = f", in {report.path.parent.name or report.path.parent}"
    if report.how == ENDED_EARLY:
        verb = "ended early" if report.planned_seconds else "stopped on its own"
        return f"{station} recording {verb}. Saved {amount}{where}. Reason: {report.reason}."
    return f"Recording saved: {what}, {amount}{where}."
