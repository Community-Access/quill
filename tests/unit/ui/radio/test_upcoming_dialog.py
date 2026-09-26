"""Upcoming lists scheduled recordings, and Go There leads somewhere (2026-09-25).

Two fixes with no coverage until now:

* ``_entry_moment`` tried only attribute names a ``RecordingScheduleEntry``
  does not have, so Upcoming never listed a single recording. It now asks the
  scheduler's own ``next_occurrence`` -- and a once-entry already in the past
  is left out rather than listed as though it were coming.
* ``open_target`` asked for ``open_schedule_recording`` and
  ``open_acb_calendar``, neither of which exists on any host, so Go There
  always said there was nowhere to go.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from quill.core.radio import reminders as rem
from quill.core.radio.recording_schedule import RecordingScheduleEntry
from quill.ui.radio import upcoming_dialog

NOW = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)


def _entry(recurrence: str, run_at: str, name: str = "Morning Show") -> RecordingScheduleEntry:
    return RecordingScheduleEntry(
        id=name,
        station_name=name,
        stream_url="https://s/live",
        recurrence=recurrence,  # type: ignore[arg-type]
        run_at=run_at,
    )


def test_a_scheduled_recording_has_a_moment() -> None:
    when = upcoming_dialog._entry_moment(_entry("daily", "2026-01-01T09:30"), NOW)
    assert when is not None
    assert when >= NOW, "a daily entry looks forward to its next occurrence"


def test_upcoming_lists_future_recordings_and_skips_past_ones(monkeypatch, tmp_path) -> None:
    future = (NOW + timedelta(days=2)).astimezone().strftime("%Y-%m-%dT%H:%M")
    past = (NOW - timedelta(days=2)).astimezone().strftime("%Y-%m-%dT%H:%M")
    entries = [_entry("once", past, "Gone Show"), _entry("once", future, "Coming Show")]
    monkeypatch.setattr(upcoming_dialog, "_recordings", lambda _host: entries)
    monkeypatch.setattr(rem, "load_reminders", lambda _d: [])

    rows = upcoming_dialog._gather(object(), tmp_path, NOW)

    labels = [label for label, _payload in rows]
    assert len(rows) == 1, labels
    assert labels[0].startswith("Recording: Coming Show")
    assert rows[0][1] is entries[1]


def test_go_there_on_a_recording_opens_schedule_recording() -> None:
    opened: list[str] = []

    class _Host:
        def _radio_open_schedule_recording(self) -> None:
            opened.append("schedule")

    said = upcoming_dialog.open_target(_Host(), _entry("daily", "2026-01-01T09:30"))
    assert opened == ["schedule"]
    assert said == "Opened Schedule Recording."


def test_go_there_on_a_recording_without_a_scheduler_says_so() -> None:
    said = upcoming_dialog.open_target(object(), _entry("daily", "2026-01-01T09:30"))
    assert said == "Scheduled recording is not available here."


def test_go_there_on_an_event_reminder_opens_the_calendar(monkeypatch) -> None:
    from quill.ui.radio import calendar_wiring

    hosts: list[object] = []
    monkeypatch.setattr(calendar_wiring, "open_calendar", hosts.append)
    host = object()
    reminder = rem.Reminder(reminder_id="r1", title="Main Menu", due=NOW, kind=rem.KIND_EVENT)

    said = upcoming_dialog.open_target(host, reminder)

    assert hosts == [host]
    assert said == "Opened the schedule. Main Menu is in it."


@pytest.mark.parametrize("kind", [rem.KIND_OTHER, rem.KIND_EPISODE])
def test_a_reminder_with_nowhere_to_go_says_so(kind: str) -> None:
    reminder = rem.Reminder(reminder_id="r1", title="Call Mom", due=NOW, kind=kind)
    said = upcoming_dialog.open_target(object(), reminder)
    assert said == "Call Mom: there is nowhere to go from here."
