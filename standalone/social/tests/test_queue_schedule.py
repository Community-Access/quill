"""Tests for queue schedules (PRD 18.4, 18.2)."""

from datetime import datetime
from zoneinfo import ZoneInfo

from quill_social.services import queue_schedule as qs
from quill_social.services.queue_schedule import (
    BlackoutWindow,
    QueueSchedule,
    Slot,
)


def _ms(year, month, day, hour, minute, tz="UTC"):
    dt = datetime(year, month, day, hour, minute, tzinfo=ZoneInfo(tz))
    return int(dt.timestamp() * 1000)


def test_roundtrip_dict():
    sched = QueueSchedule(
        name="Weekdays",
        slots=[Slot(0, 9, 0), Slot(2, 17, 30)],
        timezone="America/New_York",
        min_spacing_min=60,
        daily_limit=2,
        blackout_windows=[BlackoutWindow(1, 2, "holiday")],
        quiet_start_min=1320,
        quiet_end_min=420,
    )
    back = QueueSchedule.from_dict(sched.to_dict())
    assert back.name == "Weekdays"
    assert back.slots[1].hour == 17 and back.slots[1].minute == 30
    assert back.blackout_windows[0].reason == "holiday"
    assert back.quiet_start_min == 1320


def test_slots_between_enumerates_weekly():
    # Monday and Wednesday at 09:00 UTC.
    sched = QueueSchedule(slots=[Slot(0, 9, 0), Slot(2, 9, 0)], timezone="UTC")
    # 2026-07-13 is a Monday.
    start = _ms(2026, 7, 13, 0, 0)
    end = _ms(2026, 7, 20, 0, 0)
    slots = qs.slots_between(sched, start, end)
    assert len(slots) == 2
    assert slots[0] == _ms(2026, 7, 13, 9, 0)  # Monday
    assert slots[1] == _ms(2026, 7, 15, 9, 0)  # Wednesday


def test_next_slot_after_reference():
    sched = QueueSchedule(slots=[Slot(0, 9, 0)], timezone="UTC")
    after = _ms(2026, 7, 13, 10, 0)  # Monday 10:00, past the 09:00 slot
    nxt = qs.next_slot(sched, after, now=after)
    assert nxt == _ms(2026, 7, 20, 9, 0)  # following Monday


def test_next_slot_respects_daily_limit():
    # Two slots on Monday; daily limit of 1, one already used -> skip to next week.
    sched = QueueSchedule(
        slots=[Slot(0, 9, 0), Slot(0, 15, 0)], timezone="UTC", daily_limit=1
    )
    after = _ms(2026, 7, 13, 0, 0)
    existing = [_ms(2026, 7, 13, 9, 0)]  # Monday 09:00 already taken
    nxt = qs.next_slot(sched, after, existing, now=after)
    # 15:00 same day would exceed the daily limit, so next is the following Monday.
    assert nxt == _ms(2026, 7, 20, 9, 0)


def test_next_slot_respects_spacing():
    sched = QueueSchedule(
        slots=[Slot(0, 9, 0), Slot(0, 9, 30)], timezone="UTC", min_spacing_min=60
    )
    after = _ms(2026, 7, 13, 0, 0)
    existing = [_ms(2026, 7, 13, 9, 0)]
    nxt = qs.next_slot(sched, after, existing, now=after)
    # 09:30 is within 60 min of the taken 09:00 slot -> skip to next week 09:00.
    assert nxt == _ms(2026, 7, 20, 9, 0)


def test_next_slot_respects_blackout():
    sched = QueueSchedule(slots=[Slot(0, 9, 0)], timezone="UTC")
    first = _ms(2026, 7, 13, 9, 0)
    sched.blackout_windows = [BlackoutWindow(first, first + 1, "maintenance")]
    after = _ms(2026, 7, 13, 0, 0)
    nxt = qs.next_slot(sched, after, now=after)
    assert nxt == _ms(2026, 7, 20, 9, 0)


def test_quiet_period_excludes_slot():
    # Slot at 23:00 UTC, quiet 22:00-07:00 -> excluded from enumeration.
    sched = QueueSchedule(
        slots=[Slot(0, 23, 0)], timezone="UTC",
        quiet_start_min=22 * 60, quiet_end_min=7 * 60,
    )
    start = _ms(2026, 7, 13, 0, 0)
    end = _ms(2026, 7, 20, 0, 0)
    assert qs.slots_between(sched, start, end) == []


def test_dst_spring_forward_correct_utc():
    # US DST begins 2026-03-08. A 09:00 America/New_York slot is UTC-05 before
    # and UTC-04 after, so the wall-clock hour maps to different UTC instants.
    sched = QueueSchedule(slots=[Slot(6, 9, 0)], timezone="America/New_York")
    # Sunday 2026-03-01 (before DST) and Sunday 2026-03-15 (after DST).
    before = qs.slots_between(
        sched, _ms(2026, 3, 1, 0, 0), _ms(2026, 3, 2, 0, 0)
    )
    after = qs.slots_between(
        sched, _ms(2026, 3, 15, 0, 0), _ms(2026, 3, 16, 0, 0)
    )
    assert len(before) == 1 and len(after) == 1
    # 09:00 EST = 14:00 UTC; 09:00 EDT = 13:00 UTC.
    assert before[0] == _ms(2026, 3, 1, 14, 0)
    assert after[0] == _ms(2026, 3, 15, 13, 0)


def test_persistence_roundtrip(store):
    sched = QueueSchedule(name="Persisted", slots=[Slot(0, 9, 0)])
    qs.save(store, sched)
    loaded = qs.load(store, sched.schedule_id)
    assert loaded is not None
    assert loaded.name == "Persisted"
    assert [s.schedule_id for s in qs.load_all(store)] == [sched.schedule_id]
