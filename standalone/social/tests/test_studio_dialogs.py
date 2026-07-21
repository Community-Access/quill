"""Guarded smoke tests for the studio dialogs (PRD 18).

Each dialog is built headlessly against an in-memory ``SocialStore`` seeded with
a draft and a plan, exercised through a couple of non-modal methods, then
destroyed. No ``ShowModal``/``MainLoop`` is used so the suite runs on a headless
CI as long as wx can initialize.
"""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from quill_social.db import SocialStore  # noqa: E402
from quill_social.model import Campaign, Draft, PublicationPlan, now_ms  # noqa: E402
from quill_social.services import approvals as approvals_svc  # noqa: E402


@pytest.fixture
def app():
    try:
        application = wx.App()
    except Exception:  # pragma: no cover - no display
        pytest.skip("wx cannot initialize in this environment")
    yield application
    application.Destroy()


@pytest.fixture
def store():
    s = SocialStore(":memory:")
    camp = Campaign(name="Launch")
    s.put_campaign(camp)
    draft = Draft(name="Hello", text="Hello world\n\nsecond post", thread_mode=True)
    s.put_draft(draft)
    plan = PublicationPlan(
        draft_id=draft.draft_id,
        account_id="acct_1",
        network="mock",
        scheduled_for=now_ms() + 3_600_000,
        campaign_id=camp.campaign_id,
        state="scheduled",
    )
    s.put_plan(plan)
    plan2 = PublicationPlan(
        draft_id=draft.draft_id,
        account_id="acct_1",
        network="mock",
        scheduled_for=now_ms() + 3_600_000 + 60_000,
        state="scheduled",
    )
    s.put_plan(plan2)
    s._seed = {"draft": draft, "plan": plan}
    yield s
    s.close()


def test_drafts_dialog_select_and_delete(app, store):
    from quill_social.ui.studio import DraftsDialog

    dlg = DraftsDialog(None, store)
    try:
        assert dlg.list.GetItemCount() == 1
        dlg.list.Select(0)
        dlg._on_edit()
        assert dlg.chosen_draft_id == store._seed["draft"].draft_id

        dlg.list.Select(0)
        dlg._on_delete()
        assert dlg.list.GetItemCount() == 0
        assert store.list_drafts() == []
    finally:
        dlg.Destroy()


def test_agenda_dialog_switches_views(app, store):
    from quill_social.ui.studio import AgendaDialog

    dlg = AgendaDialog(None, store)
    try:
        assert dlg.list.GetItemCount() == 2
        for view in ("Day", "Week", "Month", "Agenda"):
            dlg.set_view(view)
            assert dlg.list.GetItemCount() == 2
        # Two plans one minute apart on the same account conflict at 30 min.
        assert "conflict" in dlg.conflicts.GetValue().lower()
    finally:
        dlg.Destroy()


def test_queue_schedule_dialog_add_slot_and_save(app, store):
    from quill_social.services import queue_schedule as qsched_svc
    from quill_social.ui.studio import QueueScheduleDialog

    dlg = QueueScheduleDialog(None, store)
    try:
        dlg.name.SetValue("Weekdays")
        dlg.slot_weekday.SetSelection(0)
        dlg.slot_hour.SetValue(9)
        dlg.slot_minute.SetValue(0)
        dlg._on_add_slot()
        assert dlg.slots_list.GetItemCount() == 1
        assert "slot" in dlg.preview.GetValue().lower()

        dlg._on_save()
        saved = qsched_svc.load_all(store)
        assert len(saved) == 1
        assert saved[0].name == "Weekdays"
        assert len(saved[0].slots) == 1
    finally:
        dlg.Destroy()


def test_approvals_dialog_request_and_approve(app, store):
    from quill_social.ui.studio import ApprovalsDialog

    dlg = ApprovalsDialog(None, store)
    try:
        # Contributor can submit a draft for review.
        dlg.role.SetSelection(list(approvals_svc.ROLES).index("contributor"))
        dlg.draft.SetSelection(0)
        dlg._on_request()
        records = approvals_svc.load_all(store)
        assert len(records) == 1
        assert records[0].state == "ready"
        assert len(records[0].audit) >= 1

        # An approver can now approve the selected record.
        dlg.role.SetSelection(list(approvals_svc.ROLES).index("approver"))
        dlg.list.Select(0)
        dlg._on_approve()
        records = approvals_svc.load_all(store)
        assert records[0].state == "approved"

        # A viewer is blocked from approving.
        assert not approvals_svc.can_perform("viewer", "approve")
    finally:
        dlg.Destroy()
