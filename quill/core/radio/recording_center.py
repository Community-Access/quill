"""The Recordings window's headline: what is happening, and what happens next.

WHY THIS IS A SUMMARY AND NOT A NEW WINDOW
------------------------------------------
The obvious reading of "there should be one recording center" is that the
Recordings window and the Schedule window need merging. They do not, and it is
worth writing down why, because building the obvious thing would have made the
app worse.

``recordings_index.list_recordings`` already returns **one** list holding
active captures, finished files and scheduled entries together, and the
Recordings window already shows all three with counts and the output folder.
The two windows are not two views of the same thing: one is the shelf, the
other is the form you fill in to add to it. A third window showing the same
list again is precisely the second surface that drifts from the first, which
this codebase has paid for more than once (two transcript readers, two copies
of the search-within-a-folder knowledge, four apps wearing one icon).

What was genuinely missing was smaller and more useful: the window could tell
you there were three scheduled recordings and could not tell you **when the
next one is**. That fact lived only inside the scheduled rows, so answering
"am I covered tonight?" meant finding those rows and reading their recurrence
text. The status line counted things instead of saying what was about to
happen.

So this module builds the sentence the window leads with:

    "Recording The Moonstone, 42 min left. Next: KFI at 11:00 tomorrow.
    14 recorded, in D:\\Music\\Quill Radio Recordings."

Pure: snapshots and a clock in, one string out.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from quill.core.radio.recording_progress import RecordingProgress, recording_cell_text

#: Statuses this module reasons about, mirrored from ``recordings_index`` rather
#: than imported to keep this module free of the folder-scanning half.
STATUS_RECORDING = "Recording"
STATUS_RECORDED = "Recorded"
STATUS_SCHEDULED = "Scheduled"
#: A once-only schedule that has already run. Counting it as "scheduled"
#: forever is the exact fault this module exists to fix -- it is a promise the
#: app has already kept, and saying it is still coming is worse than silence.
STATUS_COMPLETED = "Completed"


@dataclass(frozen=True, slots=True)
class NextUp:
    """The soonest scheduled recording, and when it starts."""

    station_name: str
    starts_at: datetime


def _relative_day(when: datetime, now: datetime) -> str:
    """ "today", "tomorrow", or a weekday name -- how a person says a date.

    Never a bare date for anything inside a week. "Thursday" is something
    somebody can act on without counting; "2026-08-27" is a lookup. Past a week
    the weekday stops being unambiguous, so the date comes back.
    """
    today = now.date()
    days = (when.date() - today).days
    if days <= 0:
        return "today"
    if days == 1:
        return "tomorrow"
    if days < 7:
        return when.strftime("%A")
    return when.strftime("%Y-%m-%d")


def describe_next(next_up: NextUp | None, now: datetime) -> str:
    """ "KFI at 11:00 tomorrow", or "" when nothing is scheduled.

    The station leads because it is what somebody is checking on; the time
    follows because it is the answer to the question the station raised.
    """
    if next_up is None:
        return ""
    when = next_up.starts_at
    clock = when.strftime("%H:%M")
    soon = when - now
    # Inside the hour, minutes are more use than a wall-clock time: "in 12
    # minutes" tells you whether you can leave the room.
    if timedelta(0) <= soon < timedelta(hours=1):
        minutes = max(1, int((soon.total_seconds() + 59) // 60))
        unit = "minute" if minutes == 1 else "minutes"
        return f"{next_up.station_name} in {minutes} {unit}"
    return f"{next_up.station_name} at {clock} {_relative_day(when, now)}"


def summary_line(
    *,
    active: list[RecordingProgress],
    next_up: NextUp | None,
    recorded_count: int,
    scheduled_count: int,
    folder: str,
    now: datetime,
    completed_count: int = 0,
) -> str:
    """The whole headline, in the order somebody wants to hear it.

    Now, next, then the shelf. A listener opening this window is asking one of
    three questions in that order of urgency -- "is it recording?", "will it
    catch tonight's show?", "where did last night's go?" -- and a summary that
    led with a file count would answer the least pressing one first.

    The active clause reuses ``recording_progress`` rather than re-deriving
    elapsed and remaining, so the sentence here and the status-strip cell can
    never disagree about the same recording -- including on the point that an
    open-ended capture has no deadline to count down to.
    """
    parts: list[str] = []
    if active:
        parts.append(f"Recording, {recording_cell_text(active, now)}")
    else:
        parts.append("Not recording")
    described = describe_next(next_up, now)
    if described:
        parts.append(f"next: {described}")
        if completed_count:
            parts.append(f"{completed_count} completed")
    elif scheduled_count:
        # Scheduled entries exist but none has a next occurrence -- every one is
        # disabled, or a once-only that already ran. Saying "3 scheduled" and
        # stopping there is what sent people hunting through the rows.
        clause = f"{scheduled_count} scheduled, none coming up"
        parts.append(f"{clause}, {completed_count} completed" if completed_count else clause)
    elif completed_count:
        # The zero is said out loud rather than folded into "nothing scheduled",
        # because *why* there is nothing scheduled is the whole answer here: the
        # once-only recording somebody set up has already happened. "Nothing
        # scheduled" on its own reads as though the schedule was lost.
        parts.append(f"{scheduled_count} scheduled, {completed_count} completed")
    else:
        parts.append("nothing scheduled")
    shelf = "1 recorded" if recorded_count == 1 else f"{recorded_count} recorded"
    parts.append(shelf)
    # Each clause is its own sentence, so each starts as one. A screen reader
    # applies sentence-final prosody at a full stop, and "Not recording.
    # nothing scheduled." reads as one run-on with a stumble in the middle --
    # the same fault the 3.0 sweep fixed across seventy-one announcements.
    line = ". ".join(part[:1].upper() + part[1:] for part in parts) + "."
    return f"{line} In {folder}." if folder else line


def summary_from_rows(
    rows: list[object],
    schedule_entries: list[object],
    *,
    folder: str,
    now: datetime,
) -> str:
    """The headline, straight from the Recordings window's own row snapshot.

    The window already holds one list containing active, recorded and scheduled
    rows (``recordings_index.list_recordings``), so the whole derivation is done
    here rather than half in the dialog: counting the statuses, turning the live
    captures into progress records, and finding the next occurrence are one
    thought, and splitting them across two files is how the sentence and the
    rows drift into disagreeing.
    """
    recorded = sum(1 for row in rows if getattr(row, "status", "") == STATUS_RECORDED)
    scheduled = sum(1 for row in rows if getattr(row, "status", "") == STATUS_SCHEDULED)
    completed = sum(1 for row in rows if getattr(row, "status", "") == STATUS_COMPLETED)
    active: list[RecordingProgress] = []
    for row in rows:
        started = getattr(row, "started_at", None)
        if getattr(row, "status", "") != STATUS_RECORDING or not isinstance(started, datetime):
            continue
        active.append(
            RecordingProgress(
                started_at=started,
                minutes=int(getattr(row, "scheduled_minutes", 0) or 0),
                duration_requested=bool(getattr(row, "duration_requested", False)),
            )
        )
    return summary_line(
        active=active,
        next_up=next_from_entries(schedule_entries, now),
        recorded_count=recorded,
        scheduled_count=scheduled,
        completed_count=completed,
        folder=folder,
        now=now,
    )


def next_from_entries(entries: list[object], now: datetime) -> NextUp | None:
    """The soonest upcoming occurrence across *entries*, or ``None``.

    Takes schedule entries and asks each for its own next occurrence, rather
    than parsing ``run_at`` here: recurrence, weekday and time-zone handling all
    live in ``recording_schedule`` and a second implementation of that arithmetic
    would be wrong about the same daylight-saving edge the first one was fixed
    for.

    Disabled entries are skipped, and so is anything whose next occurrence is in
    the past -- a schedule that cannot fire is not something "coming up".
    """
    from quill.core.radio.recording_schedule import _to_absolute, next_occurrence

    # ``next_occurrence`` returns an **absolute** moment (it resolves each
    # entry's own time zone), while callers reasonably hand in a plain
    # ``datetime.now()``. Comparing the two raises "can't compare offset-naive
    # and offset-aware datetimes", which is how the Recordings manager came to
    # fail to refresh at all. Normalised with recording_schedule's own rule --
    # naive means system-local -- rather than a second copy of it, for the same
    # reason this function delegates the recurrence arithmetic there.
    now_abs = _to_absolute(now)

    best: NextUp | None = None
    for entry in entries:
        if not bool(getattr(entry, "enabled", True)):
            continue
        try:
            when = next_occurrence(entry, now)  # type: ignore[arg-type]
        except Exception:  # noqa: BLE001 - one bad entry must not lose the rest
            continue
        if when is None or _to_absolute(when) < now_abs:
            continue
        if best is None or when < best.starts_at:
            best = NextUp(
                station_name=str(getattr(entry, "station_name", "") or "a station"),
                starts_at=when,
            )
    return best
