"""Which places are watched, and when: every state transition."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from quill.core.weather import alert_rules as ar
from quill.core.weather import place_watch as pw
from quill.core.weather.models import WeatherAlert

FRI_NOON = datetime(2026, 12, 4, 12, 0)  # a Friday
PLACES = [("home", "Home"), ("work", "Work"), ("cabin", "Cabin")]


def _state(pid: str, muted: set[str], watches: pw.PlaceWatches, now: datetime = FRI_NOON):
    return pw.state_of(pid, muted, watches, now)


def test_default_watches_every_place() -> None:
    watches = pw.PlaceWatches()
    assert all(_state(pid, set(), watches) is pw.WatchState.WATCHING for pid, _l in PLACES)
    assert pw.summary_sentence(PLACES, set(), watches, FRI_NOON) == "Watching 3 of 3 places."


def test_off_is_not_checked_and_keeps_the_place() -> None:
    state = _state("cabin", {"cabin"}, pw.PlaceWatches())
    assert state is pw.WatchState.OFF and not state.checked


# -- snooze -----------------------------------------------------------------------


@pytest.mark.parametrize(("choice", "hours"), [("1 hour", 1), ("4 hours", 4), ("12 hours", 12)])
def test_snooze_lengths_and_expiry(choice: str, hours: int) -> None:
    watches = pw.PlaceWatches()
    end = pw.snooze(watches.rule("cabin"), choice, FRI_NOON)
    assert end == FRI_NOON + timedelta(hours=hours)
    assert _state("cabin", set(), watches, FRI_NOON + timedelta(hours=hours, seconds=-1)) is (
        pw.WatchState.SNOOZED
    )
    assert _state("cabin", set(), watches, end) is pw.WatchState.WATCHING


def test_snooze_until_tomorrow_morning() -> None:
    watches = pw.PlaceWatches()
    end = pw.snooze(watches.rule("cabin"), "Until tomorrow morning", FRI_NOON)
    assert end == datetime(2026, 12, 5, 7, 0)


def test_snoozed_place_is_still_checked_but_quiet() -> None:
    watches = pw.PlaceWatches()
    pw.snooze(watches.rule("cabin"), "4 hours", FRI_NOON)
    state = _state("cabin", set(), watches)
    assert state.checked and state.quiet


def test_snooze_end_is_said_once() -> None:
    watches = pw.PlaceWatches()
    pw.snooze(watches.rule("cabin"), "1 hour", FRI_NOON)
    labels = {"cabin": "Cabin"}
    assert pw.due_notices(set(), watches, labels, FRI_NOON + timedelta(minutes=30)) == []
    later = FRI_NOON + timedelta(hours=1, minutes=1)
    assert pw.due_notices(set(), watches, labels, later) == [
        "The snooze for Cabin has ended. It is being watched again."
    ]
    assert pw.due_notices(set(), watches, labels, later) == []


def test_ending_a_snooze_by_hand_says_nothing_later() -> None:
    watches = pw.PlaceWatches()
    pw.snooze(watches.rule("cabin"), "1 hour", FRI_NOON)
    pw.end_snooze(watches.rule("cabin"))
    assert _state("cabin", set(), watches) is pw.WatchState.WATCHING
    assert pw.due_notices(set(), watches, {"cabin": "Cabin"}, FRI_NOON + timedelta(hours=2)) == []


# -- watch until ----------------------------------------------------------------------


def test_watch_until_turns_a_place_on_then_ends_by_itself_and_says_so_once() -> None:
    watches = pw.PlaceWatches()
    until = FRI_NOON + timedelta(days=2)
    pw.set_watch_until(watches.rule("cabin"), until)
    muted = {"cabin"}
    assert _state("cabin", muted, watches) is pw.WatchState.WATCHING
    assert "watched until" in pw.describe_state("cabin", muted, watches, FRI_NOON)
    assert _state("cabin", muted, watches, until - timedelta(seconds=1)) is pw.WatchState.WATCHING
    ended = _state("cabin", muted, watches, until)
    assert ended is pw.WatchState.ENDED and not ended.checked
    labels = {"cabin": "Cabin"}
    notices = pw.due_notices(muted, watches, labels, until)
    assert notices == ["The temporary watch for Cabin has ended. It is no longer watched."]
    assert pw.due_notices(muted, watches, labels, until + timedelta(hours=1)) == []


def test_parse_until() -> None:
    assert pw.parse_until("2026-12-06 18:00", FRI_NOON) == datetime(2026, 12, 6, 18, 0)
    assert pw.parse_until("", FRI_NOON) is None
    with pytest.raises(ValueError, match="already passed"):
        pw.parse_until("2026-12-01 18:00", FRI_NOON)
    with pytest.raises(ValueError, match="like 2026"):
        pw.parse_until("next week", FRI_NOON)


# -- schedules ------------------------------------------------------------------------


def test_schedule_boundaries_start_inclusive_end_exclusive() -> None:
    watches = pw.PlaceWatches()
    watches.rule("work").schedule = pw.parse_schedule("Mon-Fri 08:00-18:00")
    at = lambda h, m=0, day=0: _state(  # noqa: E731 - a tiny local helper
        "work", set(), watches, datetime(2026, 12, 4, h, m) + timedelta(days=day)
    )
    assert at(7, 59) is pw.WatchState.OUTSIDE_SCHEDULE
    assert at(8, 0) is pw.WatchState.WATCHING
    assert at(17, 59) is pw.WatchState.WATCHING
    assert at(18, 0) is pw.WatchState.OUTSIDE_SCHEDULE
    assert at(12, 0, day=1) is pw.WatchState.OUTSIDE_SCHEDULE  # Saturday
    assert at(12, 0, day=3) is pw.WatchState.WATCHING  # Monday


def test_schedule_across_midnight_and_parsing() -> None:
    night = pw.parse_schedule("Sat,Sun 22:00-06:00")
    assert night is not None
    assert night.active_at(datetime(2026, 12, 5, 23, 0))
    assert night.active_at(datetime(2026, 12, 6, 5, 59))
    assert not night.active_at(datetime(2026, 12, 6, 6, 0))
    assert pw.parse_schedule("weekdays 8:00-18:00") is not None
    assert pw.parse_schedule("") is None
    with pytest.raises(ValueError):
        pw.parse_schedule("whenever")
    with pytest.raises(ValueError):
        pw.parse_schedule("Mon-Fri 25:00-18:00")
    assert pw.parse_schedule("Mon-Fri 08:00-18:00").describe() == (  # type: ignore[union-attr]
        "weekdays from 8:00 AM to 6:00 PM"
    )


# -- groups and bulk changes ---------------------------------------------------------------


def test_groups_watch_and_unwatch_together() -> None:
    watches = pw.PlaceWatches()
    watches.rule("home").groups = ["Family"]
    watches.rule("cabin").groups = ["Family", "Travel"]
    watches.rule("work").groups = ["Work"]
    assert watches.groups() == ["Family", "Travel", "Work"]
    muted = pw.set_group(set(), watches, "family", watched=False)
    assert muted == {"home", "cabin"}
    assert pw.set_group(muted, watches, "Family", watched=True) == set()


def test_watch_all_none_and_invert() -> None:
    ids = [pid for pid, _l in PLACES]
    assert pw.watch_all({"home"}) == set()
    assert pw.watch_none(ids) == {"home", "work", "cabin"}
    assert pw.invert(ids, {"home"}) == {"work", "cabin"}


# -- Extreme break-through and what is said ---------------------------------------------------


def _alert(severity: str) -> WeatherAlert:
    return WeatherAlert(
        id=severity, event="Tornado Warning", severity=severity, urgency="Immediate"
    )


def test_a_snoozed_place_holds_everything_below_extreme() -> None:
    choices = ar.AlertChoices()
    held = ar.decide(_alert("Severe"), "cabin", choices, None, silenced="a snooze")
    assert held.hidden and held.reason == "a snooze"
    through = ar.decide(_alert("Extreme"), "cabin", choices, None, silenced="a snooze")
    assert not through.hidden


def test_break_through_can_be_turned_off_and_then_nothing_passes() -> None:
    choices = ar.AlertChoices(quiet=ar.QuietHours(extreme_breaks_through=False))
    assert ar.decide(_alert("Extreme"), "cabin", choices, None, silenced="its schedule").hidden


def test_summary_and_not_watched_reasons() -> None:
    watches = pw.PlaceWatches()
    pw.snooze(watches.rule("cabin"), "Until tomorrow morning", FRI_NOON)
    watches.rule("work").schedule = pw.parse_schedule("Mon-Fri 13:00-18:00")
    muted = {"home"}
    assert pw.summary_sentence(PLACES, muted, watches, FRI_NOON) == (
        "Watching 0 of 3 places. Home is not watched, switched off. "
        "Work is outside its schedule, weekdays from 1:00 PM to 6:00 PM. "
        "Cabin is snoozed until Dec 5 at 7:00 AM."
    )
    lines = pw.not_watched_lines(PLACES, muted, watches, FRI_NOON)
    assert [line.split(":")[0] for line in lines] == ["Home", "Work", "Cabin"]
    assert (
        pw.row_text("home", "Home", muted, watches, FRI_NOON) == "Home, not watched, switched off"
    )


# -- persistence ---------------------------------------------------------------------------------


def test_round_trip_and_damaged_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    watches = pw.PlaceWatches()
    rule = watches.rule("cabin")
    rule.groups = ["Travel"]
    pw.snooze(rule, "4 hours", FRI_NOON)
    pw.set_watch_until(rule, FRI_NOON + timedelta(days=1))
    rule.schedule = pw.parse_schedule("Sat,Sun 10:00-14:00")
    pw.save_watches(tmp_path, watches)
    assert pw.load_watches(tmp_path) == watches
    kept: list[str] = []
    monkeypatch.setattr(
        "quill.core.migration_backup.backup_corrupt_file", lambda name, path: kept.append(name)
    )
    (tmp_path / "weather_place_watch.json").write_text("{", encoding="utf-8")
    assert pw.load_watches(tmp_path).rules == {}
    assert kept == ["weather_place_watch"]
