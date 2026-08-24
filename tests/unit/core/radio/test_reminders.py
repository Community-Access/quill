"""Reminders: "tell me before this starts" (6.4, and section 7's floor).

A calendar that can only play what is on now is a calendar for somebody who was
already looking at it, so the reminder store lands with the calendar rather
than waiting for section 7.

Four rules carry the feature, and each is a way it could be useless instead:

* **A missed reminder still fires**, within a grace window. An app closed at
  6:55 should say what it missed when it opens; an app opened the next morning
  should not recite yesterday. Silence and recitation are both wrong.
* **It fires once.** A reminder that repeats every time the timer ticks is an
  alarm nobody can turn off.
* **Snooze counts from now**, not from when it was due -- somebody snoozing at
  7:04 a reminder that fired at 6:55 means nine minutes from now.
* **The announcement is about the programme, not about the reminder.** "Starts
  in ten minutes" is what somebody needs; "your 6:50 reminder" is a fact about
  the reminder.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from quill.core.radio import reminders as rem

NOW = datetime(2026, 8, 26, 18, 0, tzinfo=UTC)
SHOWTIME = datetime(2026, 8, 26, 19, 0, tzinfo=UTC)


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    return tmp_path


def _one(**kwargs) -> rem.Reminder:
    fields = {
        "reminder_id": "r1",
        "title": "Main Menu",
        "due": SHOWTIME,
    }
    fields.update(kwargs)
    return rem.Reminder(**fields)


# -- the store --------------------------------------------------------------------


def test_a_reminder_survives_a_restart(data_dir: Path) -> None:
    rem.add_reminder(data_dir, "Main Menu", SHOWTIME, kind=rem.KIND_EVENT, target="uid-1")

    back = rem.load_reminders(data_dir)

    assert [r.title for r in back] == ["Main Menu"]
    assert back[0].kind == rem.KIND_EVENT
    assert back[0].target == "uid-1"


def test_an_absent_file_reads_as_no_reminders(data_dir: Path) -> None:
    assert rem.load_reminders(data_dir) == []


def test_a_broken_file_reads_as_no_reminders_rather_than_raising(data_dir: Path) -> None:
    rem.store_path(data_dir).write_text("not json at all", encoding="utf-8")
    assert rem.load_reminders(data_dir) == []


def test_a_row_that_cannot_be_read_is_skipped_not_fatal(data_dir: Path) -> None:
    """A row from a newer build must cost that row, not the list."""
    rem.store_path(data_dir).write_text(
        json.dumps([
            {"reminder_id": "ok", "title": "Good", "due": SHOWTIME.isoformat()},
            {"title": "No id", "due": SHOWTIME.isoformat()},
            {"reminder_id": "no-time"},
            "not a row",
        ]),
        encoding="utf-8",
    )

    assert [r.title for r in rem.load_reminders(data_dir)] == ["Good"]


def test_reminders_come_back_soonest_first(data_dir: Path) -> None:
    rem.add_reminder(data_dir, "Later", SHOWTIME + timedelta(hours=2), target="b")
    rem.add_reminder(data_dir, "Sooner", SHOWTIME, target="a")

    assert [r.title for r in rem.load_reminders(data_dir)] == ["Sooner", "Later"]


def test_setting_a_second_reminder_on_one_thing_replaces_the_first(data_dir: Path) -> None:
    """Two reminders about one programme is a mistake made twice, not a wish."""
    rem.add_reminder(data_dir, "Main Menu", SHOWTIME, kind=rem.KIND_EVENT, target="uid-1")
    rem.add_reminder(
        data_dir, "Main Menu", SHOWTIME, kind=rem.KIND_EVENT, target="uid-1", lead_seconds=600
    )

    back = rem.load_reminders(data_dir)
    assert len(back) == 1
    assert back[0].lead_seconds == 600


def test_two_things_can_each_have_their_own_reminder(data_dir: Path) -> None:
    rem.add_reminder(data_dir, "A", SHOWTIME, kind=rem.KIND_EVENT, target="uid-1")
    rem.add_reminder(data_dir, "B", SHOWTIME, kind=rem.KIND_EVENT, target="uid-2")

    assert len(rem.load_reminders(data_dir)) == 2


def test_a_row_can_ask_whether_it_already_has_one(data_dir: Path) -> None:
    """So the menu offers Remove rather than a second Set -- a menu that cannot
    tell you what you already did is a menu you have to remember for."""
    rem.add_reminder(data_dir, "Main Menu", SHOWTIME, kind=rem.KIND_EVENT, target="uid-1")

    assert rem.find_for_target(data_dir, rem.KIND_EVENT, "uid-1") is not None
    assert rem.find_for_target(data_dir, rem.KIND_EVENT, "uid-2") is None
    assert rem.find_for_target(data_dir, rem.KIND_STATION, "uid-1") is None


def test_removing_one_says_whether_it_was_there(data_dir: Path) -> None:
    made = rem.add_reminder(data_dir, "Main Menu", SHOWTIME, target="uid-1")

    assert rem.remove_reminder(data_dir, made.reminder_id) is True
    assert rem.remove_reminder(data_dir, made.reminder_id) is False
    assert rem.load_reminders(data_dir) == []


def test_an_unknown_kind_reads_as_other_rather_than_as_damage(data_dir: Path) -> None:
    rem.store_path(data_dir).write_text(
        json.dumps([
            {"reminder_id": "r", "title": "X", "due": SHOWTIME.isoformat(), "kind": "hologram"}
        ]),
        encoding="utf-8",
    )
    assert rem.load_reminders(data_dir)[0].kind == rem.KIND_OTHER


# -- when it fires ----------------------------------------------------------------


def test_a_lead_time_moves_the_moment_earlier() -> None:
    assert _one(lead_seconds=600).fires_at == SHOWTIME - timedelta(minutes=10)


def test_when_it_starts_is_a_real_answer() -> None:
    assert _one(lead_seconds=0).fires_at == SHOWTIME


def test_nothing_fires_before_its_moment() -> None:
    assert rem.due_now([_one(lead_seconds=600)], NOW) == []


def test_it_fires_at_its_moment() -> None:
    ready = rem.due_now([_one(lead_seconds=600)], SHOWTIME - timedelta(minutes=10))
    assert len(ready) == 1


def test_a_reminder_missed_while_the_app_was_closed_still_fires() -> None:
    """An app shut at 6:55 should say what it missed when it opens."""
    ready = rem.due_now([_one()], SHOWTIME + timedelta(minutes=20))
    assert len(ready) == 1


def test_a_reminder_missed_long_ago_stays_quiet() -> None:
    """Being told at breakfast about a programme that ended at midnight is
    noise wearing a reminder's clothes."""
    late = SHOWTIME + timedelta(seconds=rem.GRACE_SECONDS + 60)
    assert rem.due_now([_one()], late) == []


def test_the_grace_window_has_an_edge_and_it_is_inclusive() -> None:
    edge = SHOWTIME + timedelta(seconds=rem.GRACE_SECONDS)
    assert len(rem.due_now([_one()], edge)) == 1


def test_a_fired_reminder_never_fires_again(data_dir: Path) -> None:
    """A reminder that repeats on every timer tick is an alarm nobody can
    turn off."""
    made = rem.add_reminder(data_dir, "Main Menu", SHOWTIME, target="uid-1")
    assert len(rem.due_now(rem.load_reminders(data_dir), SHOWTIME)) == 1

    assert rem.mark_fired(data_dir, made.reminder_id, now=SHOWTIME) is True

    assert rem.due_now(rem.load_reminders(data_dir), SHOWTIME) == []
    assert rem.mark_fired(data_dir, made.reminder_id, now=SHOWTIME) is False


def test_several_due_at_once_come_back_soonest_first() -> None:
    early = _one(reminder_id="a", title="Early", due=SHOWTIME - timedelta(minutes=30))
    late = _one(reminder_id="b", title="Late", due=SHOWTIME)
    assert [r.title for r in rem.due_now([late, early], SHOWTIME)] == ["Early", "Late"]


# -- snooze -----------------------------------------------------------------------


def test_snooze_counts_from_now_not_from_when_it_was_due(data_dir: Path) -> None:
    """Somebody snoozing at 7:04 a reminder that fired at 6:55 means nine
    minutes from now, not nine minutes ago plus nine."""
    made = rem.add_reminder(data_dir, "Main Menu", SHOWTIME, target="uid-1")
    pressed = SHOWTIME + timedelta(minutes=9)

    assert rem.snooze(data_dir, made.reminder_id, 540, now=pressed) is True

    back = rem.load_reminders(data_dir)[0]
    assert back.fires_at == pressed + timedelta(seconds=540)


def test_a_snoozed_reminder_is_not_due_until_its_new_moment(data_dir: Path) -> None:
    made = rem.add_reminder(data_dir, "Main Menu", SHOWTIME, target="uid-1")
    rem.snooze(data_dir, made.reminder_id, 600, now=SHOWTIME)

    assert rem.due_now(rem.load_reminders(data_dir), SHOWTIME + timedelta(minutes=5)) == []
    assert len(rem.due_now(rem.load_reminders(data_dir), SHOWTIME + timedelta(minutes=10))) == 1


def test_snoozing_a_fired_reminder_brings_it_back(data_dir: Path) -> None:
    made = rem.add_reminder(data_dir, "Main Menu", SHOWTIME, target="uid-1")
    rem.mark_fired(data_dir, made.reminder_id, now=SHOWTIME)

    rem.snooze(data_dir, made.reminder_id, 600, now=SHOWTIME)

    assert rem.load_reminders(data_dir)[0].is_done is False


def test_a_snooze_is_never_shorter_than_a_minute(data_dir: Path) -> None:
    """A five-second snooze is a reminder that has not stopped."""
    made = rem.add_reminder(data_dir, "Main Menu", SHOWTIME, target="uid-1")
    rem.snooze(data_dir, made.reminder_id, 5, now=SHOWTIME)

    assert rem.load_reminders(data_dir)[0].fires_at == SHOWTIME + timedelta(seconds=60)


# -- upcoming and missed ----------------------------------------------------------


def test_upcoming_is_what_is_still_ahead() -> None:
    past = _one(reminder_id="a", title="Gone", due=NOW - timedelta(hours=1))
    ahead = _one(reminder_id="b", title="Ahead", due=SHOWTIME)
    assert [r.title for r in rem.upcoming([past, ahead], NOW)] == ["Ahead"]


def test_a_missed_reminder_is_named_rather_than_dropped() -> None:
    """Deleting them behind somebody's back is how "I set a reminder and heard
    nothing" becomes unanswerable."""
    old = _one(due=NOW - timedelta(seconds=rem.GRACE_SECONDS + 60))
    assert [r.reminder_id for r in rem.expired([old], NOW)] == ["r1"]


def test_a_reminder_that_fired_is_not_missed() -> None:
    old = _one(due=NOW - timedelta(days=1), fired_at=NOW.isoformat())
    assert rem.expired([old], NOW) == []


# -- what it says -----------------------------------------------------------------


def test_the_announcement_is_about_the_programme_not_the_reminder() -> None:
    said = rem.announcement(_one(lead_seconds=600), SHOWTIME - timedelta(minutes=10))
    assert said == "Reminder: Main Menu starts in 10 minutes."


def test_a_reminder_at_the_moment_says_it_is_starting_now() -> None:
    assert "starting now" in rem.announcement(_one(), SHOWTIME)


def test_a_late_reminder_says_how_late() -> None:
    said = rem.announcement(_one(), SHOWTIME + timedelta(minutes=12))
    assert "started 12 minutes ago" in said


def test_a_note_travels_with_the_announcement() -> None:
    """7.2: a link, or a message to yourself."""
    said = rem.announcement(_one(note="Call in on 800-555-0000."), SHOWTIME)
    assert said.endswith("Call in on 800-555-0000.")


def test_a_day_ahead_reads_in_days_not_minutes() -> None:
    far = _one(due=SHOWTIME + timedelta(days=2))
    assert "2 days" in rem.announcement(far, SHOWTIME)


def test_a_row_names_the_thing_then_when_then_how_early() -> None:
    row = rem.row_label(_one(lead_seconds=600), NOW)
    assert row.startswith("Main Menu, ")
    assert "10 minutes before" in row


def test_a_high_priority_row_says_so() -> None:
    row = rem.row_label(_one(priority=rem.PRIORITY_HIGH), NOW)
    assert "high priority" in row


def test_a_missed_row_says_missed_and_a_done_row_says_done() -> None:
    missed = _one(due=NOW - timedelta(seconds=rem.GRACE_SECONDS + 60))
    done = _one(fired_at=NOW.isoformat())
    assert "missed" in rem.row_label(missed, NOW)
    assert "done" in rem.row_label(done, NOW)


def test_the_written_time_needs_no_glibc() -> None:
    """``%-d`` and ``%-I`` raise on Windows, which is what this ships on."""
    written = rem.spoken_when(datetime(2026, 8, 26, 7, 5, tzinfo=UTC))
    assert ":05" in written
    assert "07:" not in written, "a padded hour reads as 'oh seven'"


def test_every_lead_choice_has_a_label() -> None:
    for seconds, label in rem.LEAD_CHOICES:
        assert rem.lead_label(seconds) == label


def test_an_unoffered_lead_time_still_reads() -> None:
    assert rem.lead_label(420) == "7 minutes before"
