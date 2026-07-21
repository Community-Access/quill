"""Tests for recurring content plans (PRD 18.9)."""

from datetime import datetime
from zoneinfo import ZoneInfo

from quill_social.services import recurring as rc
from quill_social.services.recurring import RecurringPlan


def _ms(year, month, day, hour=9, tz="UTC"):
    dt = datetime(year, month, day, hour, 0, tzinfo=ZoneInfo(tz))
    return int(dt.timestamp() * 1000)


def test_periodic_next_occurrence():
    anchor = _ms(2026, 7, 6)  # Monday
    plan = RecurringPlan(kind="fixed", content="weekly", anchor_ms=anchor,
                         interval_days=7)
    # Just after the anchor -> next week.
    nxt = rc.next_occurrence(plan, anchor)
    assert nxt == _ms(2026, 7, 13)
    # Before the anchor -> the anchor itself.
    assert rc.next_occurrence(plan, anchor - 1) == anchor


def test_rotating_variants_rotate():
    plan = RecurringPlan(
        kind="rotating",
        variants=["A", "B", "C"],
        anchor_ms=_ms(2026, 7, 6),
        interval_days=7,
    )
    occ = rc.materialize(plan, 4)
    assert [o.text for o in occ] == ["A", "B", "C", "A"]
    assert [o.cycle_index for o in occ] == [0, 1, 2, 3]


def test_expiration_stops_occurrences():
    plan = RecurringPlan(
        kind="fixed",
        content="x",
        anchor_ms=_ms(2026, 7, 6),
        interval_days=7,
        expiration_ms=_ms(2026, 7, 20),  # allows 07-06, 07-13, 07-20 only
    )
    occ = rc.materialize(plan, 10)
    assert len(occ) == 3
    assert occ[-1].scheduled_for == _ms(2026, 7, 20)
    assert rc.next_occurrence(plan, _ms(2026, 7, 20)) is None


def test_review_after_cycles_flag():
    plan = RecurringPlan(
        kind="fixed", content="x", anchor_ms=_ms(2026, 7, 6),
        interval_days=1, review_after_cycles=2,
    )
    occ = rc.materialize(plan, 4)
    # cycles 0,1,2,3 -> review due when (cycle+1) % 2 == 0 -> cycles 1 and 3.
    assert [o.review_due for o in occ] == [False, True, False, True]


def test_duplicate_content_warning():
    plan = RecurringPlan(
        kind="fixed", content="same", anchor_ms=_ms(2026, 7, 6), interval_days=1
    )
    occ = rc.materialize(plan, 3)
    assert occ[0].duplicate is False
    assert occ[1].duplicate is True and occ[2].duplicate is True
    assert any("duplicate" in w for w in occ[1].warnings)


def test_pause_after_failures_stops():
    plan = RecurringPlan(
        kind="fixed", content="x", anchor_ms=_ms(2026, 7, 6), interval_days=7,
        pause_after_failures=3, failure_count=3,
    )
    assert rc.should_pause(plan)
    assert rc.materialize(plan, 5) == []
    assert rc.next_occurrence(plan, _ms(2026, 7, 6) - 1) is None


def test_ai_unverified_flag():
    plan = RecurringPlan(
        kind="fixed", content="fact", anchor_ms=_ms(2026, 7, 6), interval_days=7,
        ai_generated=True, ai_verified=False,
    )
    occ = rc.materialize(plan, 1)
    assert occ[0].ai_unverified is True
    assert any("not verified" in w for w in occ[0].warnings)
    plan.ai_verified = True
    assert rc.materialize(plan, 1)[0].ai_unverified is False


def test_event_relative_single_occurrence():
    event = _ms(2026, 8, 1, 12)
    plan = RecurringPlan(kind="event_relative", content="reminder",
                         event_ms=event, offset_ms=-3_600_000)  # 1h before
    occ_ms = rc.next_occurrence(plan, 0)
    assert occ_ms == event - 3_600_000
    # After the event time there are no further occurrences.
    assert rc.next_occurrence(plan, event) is None


def test_anniversary_yearly():
    anchor = _ms(2026, 8, 1, 12)
    plan = RecurringPlan(kind="anniversary", content="happy anniversary",
                         anchor_ms=anchor)
    nxt = rc.next_occurrence(plan, anchor)
    assert nxt == _ms(2027, 8, 1, 12)


def test_persistence_roundtrip(store):
    plan = RecurringPlan(kind="rotating", variants=["A", "B"],
                         anchor_ms=_ms(2026, 7, 6), interval_days=7)
    rc.save(store, plan)
    loaded = rc.load(store, plan.plan_id)
    assert loaded is not None
    assert loaded.variants == ["A", "B"]
    assert [p.plan_id for p in rc.load_all(store)] == [plan.plan_id]
