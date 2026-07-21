"""Tests for accessible calendar views (PRD 18.5)."""

from datetime import datetime
from zoneinfo import ZoneInfo

from quill_social.model import Campaign, DeliveryAttempt, Draft, Media, PublicationPlan
from quill_social.services import calendar as cal


def _ms(year, month, day, hour, minute, tz="UTC"):
    dt = datetime(year, month, day, hour, minute, tzinfo=ZoneInfo(tz))
    return int(dt.timestamp() * 1000)


def _plan(account, when, **kw):
    return PublicationPlan(
        account_id=account, network="mock", scheduled_for=when, **kw
    )


def test_agenda_ordering_and_fields():
    draft = Draft(text="Hello world\n\nsecond block", media=[Media(alt_text="a")])
    p_late = _plan("a1", _ms(2026, 7, 15, 12, 0), draft_id=draft.draft_id,
                   state="scheduled", campaign_id="camp1")
    p_early = _plan("a1", _ms(2026, 7, 14, 9, 0), draft_id=draft.draft_id,
                    state="queued")
    campaigns = {"camp1": Campaign(campaign_id="camp1", name="Launch")}
    entries = cal.agenda(
        [p_late, p_early], drafts={draft.draft_id: draft}, campaigns=campaigns
    )
    assert [e.plan_id for e in entries] == [p_early.plan_id, p_late.plan_id]
    late = entries[1]
    assert late.account_id == "a1"
    assert late.network == "mock"
    assert late.campaign == "Launch"
    assert late.state == "scheduled"
    assert late.media_count == 1
    assert "Hello world" in late.preview
    assert late.timezone == "UTC"
    # describe() exposes every field as text (accessibility baseline).
    text = late.describe()
    assert "Launch" in text and "scheduled" in text and "preview:" in text


def test_unscheduled_sorts_last():
    scheduled = _plan("a1", _ms(2026, 7, 14, 9, 0), state="scheduled")
    backlog = PublicationPlan(account_id="a1", state="draft", scheduled_for=None)
    entries = cal.agenda([backlog, scheduled])
    assert entries[0].plan_id == scheduled.plan_id
    assert entries[1].when_text == "Unscheduled"


def test_conflict_detection():
    a = _plan("a1", _ms(2026, 7, 14, 9, 0), state="scheduled")
    b = _plan("a1", _ms(2026, 7, 14, 9, 30), state="scheduled")  # 30 min apart
    c = _plan("a1", _ms(2026, 7, 14, 12, 0), state="scheduled")  # far away
    other = _plan("a2", _ms(2026, 7, 14, 9, 15), state="scheduled")  # other account
    pairs = cal.conflicts([a, b, c, other], min_spacing_min=60)
    assert len(pairs) == 1
    assert {pairs[0].first.plan_id, pairs[0].second.plan_id} == {a.plan_id, b.plan_id}
    assert pairs[0].gap_min == 30.0


def test_agenda_marks_conflicts():
    a = _plan("a1", _ms(2026, 7, 14, 9, 0), state="scheduled")
    b = _plan("a1", _ms(2026, 7, 14, 9, 30), state="scheduled")
    entries = cal.agenda([a, b], min_spacing_min=60)
    assert all(e.conflict for e in entries)


def test_no_conflicts_without_spacing():
    a = _plan("a1", _ms(2026, 7, 14, 9, 0), state="scheduled")
    b = _plan("a1", _ms(2026, 7, 14, 9, 1), state="scheduled")
    assert cal.conflicts([a, b], min_spacing_min=0) == []


def test_grouping_by_day_week_month():
    p1 = _plan("a1", _ms(2026, 7, 14, 9, 0), state="scheduled")  # Tue
    p2 = _plan("a1", _ms(2026, 7, 14, 15, 0), state="scheduled")  # same day
    p3 = _plan("a1", _ms(2026, 7, 21, 9, 0), state="scheduled")  # next week
    days = cal.group_by_day([p1, p2, p3])
    assert days["2026-07-14"] == [p1, p2]
    assert days["2026-07-21"] == [p3]
    weeks = cal.group_by_week([p1, p2, p3])
    assert len(weeks) == 2
    months = cal.group_by_month([p1, p2, p3])
    assert list(months.keys()) == ["2026-07"]
    assert len(months["2026-07"]) == 3


def test_failure_and_retry_state():
    plan = _plan("a1", _ms(2026, 7, 14, 9, 0), state="queued")
    plan.next_retry_at = _ms(2026, 7, 14, 10, 0)
    plan.attempts = [DeliveryAttempt(ok=False, error_kind="transient",
                                     error_message="timeout")]
    entries = cal.agenda([plan])
    assert entries[0].failure_state == "retry pending"
    assert entries[0].retry_count == 1
    assert entries[0].error_message == "timeout"


def test_grouping_timezone_shifts_day():
    # 03:00 UTC on 2026-07-15 is 2026-07-14 in America/New_York (UTC-4).
    plan = _plan("a1", _ms(2026, 7, 15, 3, 0), state="scheduled")
    days_utc = cal.group_by_day([plan], tz="UTC")
    days_ny = cal.group_by_day([plan], tz="America/New_York")
    assert "2026-07-15" in days_utc
    assert "2026-07-14" in days_ny
