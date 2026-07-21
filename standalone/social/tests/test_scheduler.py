"""Tests for the scheduler state machine (PRD 18.8, 18.12)."""

from quill_social.adapters.base import AdapterError
from quill_social.model import Draft, PublicationPlan
from quill_social.services import scheduler as sch
from tests.conftest import ScriptedAdapter


def test_transition_table():
    assert sch.can_transition("queued", "publishing")
    assert sch.can_transition("publishing", "published")
    assert sch.can_transition("failed", "queued")
    assert not sch.can_transition("published", "queued")
    assert not sch.can_transition("cancelled", "queued")


def test_backoff_grows_and_caps():
    assert sch.backoff_ms(0) == 30_000
    assert sch.backoff_ms(1) == 60_000
    assert sch.backoff_ms(2) == 120_000
    assert sch.backoff_ms(99) == 3_600_000


def test_needs_review():
    assert sch.needs_review("validation")
    assert sch.needs_review("permission")
    assert sch.needs_review("privacy")
    assert not sch.needs_review("transient")


def _plan_and_draft():
    draft = Draft(text="hi", targets=["a1"], visibility="public")
    plan = PublicationPlan(draft_id=draft.draft_id, account_id="a1", network="mock")
    return plan, draft


def test_process_plan_success():
    plan, draft = _plan_and_draft()
    adapter = ScriptedAdapter(["ok"])
    result = sch.process_plan(plan, adapter, draft, now=1000)
    assert result.published
    assert result.plan.state == "published"
    assert result.plan.remote_id == "r1"
    assert result.plan.attempts[-1].ok


def test_process_plan_transient_schedules_retry():
    plan, draft = _plan_and_draft()
    adapter = ScriptedAdapter([AdapterError("timeout", kind="transient")])
    result = sch.process_plan(plan, adapter, draft, now=1000)
    assert not result.published
    assert result.retry_scheduled
    assert result.plan.state == "queued"
    assert result.plan.next_retry_at == 1000 + 30_000


def test_process_plan_permission_needs_review():
    plan, draft = _plan_and_draft()
    adapter = ScriptedAdapter([AdapterError("nope", kind="permission")])
    result = sch.process_plan(plan, adapter, draft, now=1000)
    assert result.review_required
    assert result.plan.state == "failed"
    assert result.plan.next_retry_at is None


def test_process_plan_gives_up_after_max_retries():
    plan, draft = _plan_and_draft()
    # Pre-load MAX_RETRIES prior failed attempts.
    from quill_social.model import DeliveryAttempt
    plan.attempts = [DeliveryAttempt(ok=False, error_kind="transient")
                     for _ in range(sch.MAX_RETRIES)]
    adapter = ScriptedAdapter([AdapterError("timeout", kind="transient")])
    result = sch.process_plan(plan, adapter, draft, now=1000)
    assert result.plan.state == "failed"
    assert not result.retry_scheduled


def test_scheduler_run_due_publishes(store):
    draft = Draft(text="scheduled body", targets=["a1"])
    store.put_draft(draft)
    plan = PublicationPlan(draft_id=draft.draft_id, account_id="a1", network="mock",
                           state="queued", scheduled_for=500)
    store.put_plan(plan)
    adapter = ScriptedAdapter(["ok"])
    scheduler = sch.Scheduler(store, lambda _aid: adapter, clock=lambda: 1000)
    results = scheduler.run_due()
    assert len(results) == 1
    assert results[0].published
    assert store.get_plan(plan.plan_id).state == "published"


def test_scheduler_skips_future_plans(store):
    draft = Draft(text="later", targets=["a1"])
    store.put_draft(draft)
    plan = PublicationPlan(draft_id=draft.draft_id, account_id="a1", network="mock",
                           state="scheduled", scheduled_for=10_000)
    store.put_plan(plan)
    scheduler = sch.Scheduler(store, lambda _aid: ScriptedAdapter(["ok"]),
                              clock=lambda: 1000)
    assert scheduler.run_due() == []
    assert store.get_plan(plan.plan_id).state == "scheduled"
