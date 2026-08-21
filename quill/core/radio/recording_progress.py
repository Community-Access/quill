"""How far along a recording is, in words, for the status strip.

WHY THIS EXISTS
---------------
The focusable status bar (``ui.radio.status_bar``) had a Recording cell that
said ``Idle``, ``Recording``, or ``2 recording`` and nothing more, while the
sleep-timer cell immediately beside it said ``12 min left``. Somebody arrowing
across the bar to check on a capture learned only that one was running -- the
question they actually had ("how much have I got?") was answered by the cell
next door and not by this one.

THE HONESTY PROBLEM, WHICH IS THE WHOLE REASON THIS IS A MODULE
---------------------------------------------------------------
Every recording carries a ``minutes`` value, so "minutes remaining" looks like
a subtraction anyone could do inline. It is not, because ``minutes`` means two
completely different things:

* the listener asked for a duration -- a scheduled recording, or a length typed
  into Record Station. The end is a **decision**, and counting down to it is
  telling somebody what they asked to be told.
* the listener asked for nothing, so ``RadioRecorder.start`` fell back to
  ``settings.max_duration_minutes``, a **safety cap** that exists to stop a
  forgotten capture filling a disk. Counting down to *that* would announce an
  intention nobody ever expressed: "142 minutes left" reads as a plan, and the
  listener who pressed Record Now has no plan and is owed no number.

So a job records which of the two it was (``JobSnapshot.duration_requested``)
and this module counts down only for the first kind. For the second it counts
*up*, because elapsed time is true whatever the listener intended.

That distinction is also why the safety cap can be raised or lowered without
this text changing meaning, and why a reconnect carries the original flag
across rather than re-deriving it -- a continuation is handed the *remaining*
minutes as an explicit duration, which would otherwise silently promote an
open-ended capture into one that appears to have a deadline.

The module is pure: it takes snapshots and a clock and returns a string, so
every case below is a table test rather than something you have to run a
recording to see.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

#: Below this, a count is not worth showing as a number: "0 min left" reads as
#: finished and "1 min left" is close enough to wrong. Both edges say so in
#: words instead.
_SUB_MINUTE = timedelta(minutes=1)


@dataclass(frozen=True)
class RecordingProgress:
    """One running capture, reduced to what the status strip needs.

    Deliberately not ``JobSnapshot`` itself: this module is used by the status
    bar and the Recording Center, and neither should have to grow an import of
    the recorder's whole job model to render a line of text.
    """

    started_at: datetime
    minutes: int
    duration_requested: bool

    def elapsed(self, now: datetime) -> timedelta:
        """How long this capture has been running, never negative.

        A clock that moves backwards (a daylight-saving fall-back, an NTP step)
        would otherwise produce a negative elapsed time and a status cell
        reading "-59 min so far", which looks like a defect in the recorder
        rather than in the clock.
        """
        return max(timedelta(0), now - self.started_at)

    def remaining(self, now: datetime) -> timedelta | None:
        """Time left before the deliberate end, or ``None`` when there is none.

        ``None`` for an open-ended capture is the point of the type: callers
        cannot accidentally render a countdown to the safety cap, because there
        is no number here to render.
        """
        if not self.duration_requested or self.minutes <= 0:
            return None
        end = self.started_at + timedelta(minutes=self.minutes)
        return max(timedelta(0), end - now)


def _minutes_ceil(span: timedelta) -> int:
    """Round *span* up to whole minutes, matching the sleep timer's idiom."""
    return int((span.total_seconds() + 59) // 60)


def _minutes_floor(span: timedelta) -> int:
    """Round *span* down to whole minutes.

    Elapsed time floors and remaining time ceilings, on purpose: "18 min so
    far" should mean at least eighteen have passed, and "12 min left" should
    mean no more than twelve remain. Rounding both the same way would make one
    of the two overstate.
    """
    return int(span.total_seconds() // 60)


def _left_phrase(span: timedelta) -> str:
    if span < _SUB_MINUTE:
        return "less than a minute left"
    return f"{_minutes_ceil(span)} min left"


def _elapsed_phrase(span: timedelta) -> str:
    if span < _SUB_MINUTE:
        return "under a minute so far"
    return f"{_minutes_floor(span)} min so far"


def recording_cell_text(jobs: list[RecordingProgress], now: datetime) -> str:
    """The Recording cell's live value: ``Idle``, ``12 min left``, ``18 min so far``.

    With several captures running the count leads, and the time that follows is
    the **most urgent** one -- the soonest deliberate end if any capture has
    one, otherwise the longest-running. A status cell has room for one number,
    and of the numbers available the one that will matter first is the one
    worth the space.
    """
    if not jobs:
        return "Idle"
    remainings = [span for span in (job.remaining(now) for job in jobs) if span is not None]
    if remainings:
        phrase = _left_phrase(min(remainings))
    else:
        phrase = _elapsed_phrase(max(job.elapsed(now) for job in jobs))
    if len(jobs) == 1:
        return phrase
    return f"{len(jobs)} recordings, {phrase}"


def recording_cell_help(jobs: list[RecordingProgress], now: datetime) -> str:
    """The cell's one-line hint, which says what the number in it means.

    "12 min left" and "18 min so far" are different measurements sharing one
    cell, and which one you are looking at depends on how the capture was
    started -- something the listener has no way to see from the number alone.
    The hint is where that is said, so the cell text can stay short.
    """
    base = (
        "Recording status. Press Enter to start or stop recording "
        "the current station; right-click to stop all recordings."
    )
    if not jobs:
        return base
    if any(job.remaining(now) is not None for job in jobs):
        return base + " The time shown counts down to the length you asked for."
    return base + " The time shown is how long the recording has been running."
