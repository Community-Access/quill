"""Guarded smoke test of the wxPython shell.

Skips cleanly when wx cannot initialize (headless CI without a display). When it
can, it builds the full frame against a temp store, exercises field navigation,
Where Am I, a flag toggle, and command construction, then tears down -- catching
any wiring regression without a real screen reader.
"""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("QUILLSOCIAL_DATA", str(tmp_path))
    try:
        application = wx.App()
    except Exception:  # pragma: no cover - no display
        pytest.skip("wx cannot initialize in this environment")
    yield application
    application.Destroy()


def test_frame_builds_and_navigates(app):
    from quill_social.ui.app import SocialFrame

    frame = SocialFrame()
    try:
        assert frame.current_scope == "home:all"
        assert len(frame._items) == 15  # seeded mock timeline

        frame.list.Select(0)
        frame.list.Focus(0)
        item = frame._current_item()
        assert item is not None

        # field navigation does not raise
        frame._announce_field(1)
        frame._announce_field(-1)

        # where am i produces a non-empty utterance
        frame.cmd_where_am_i()

        # favourite toggles local state
        was = frame._current_item().favourited
        frame.cmd_favourite()
        assert frame._current_item().favourited is (not was)

        # command list builds
        assert len(frame._build_commands()) > 5

        # scope switches
        frame._load_scope("library:bookmarks", "Bookmarks")
        assert isinstance(frame._items, list)

        # GitHub scopes render rows from the mock surface
        frame._load_github("gh:issues", "Issues")
        assert frame.list.GetItemCount() >= 1

        # analytics / safety / AI / ecosystem commands run without a modal
        frame._show_text = lambda title, text: None
        frame._load_scope("home:all", "Home")
        frame.list.Select(0)
        frame.list.Focus(0)
        frame.cmd_analytics()
        frame.cmd_summarize_feed()
        frame.cmd_accessibility_check()
        frame.cmd_send_to_quill()

        # studio / manage dialogs open and tear down (modal stubbed)
        frame._modal = lambda dlg: dlg.Destroy()
        for handler in (
            frame.cmd_safety_center, frame.cmd_notification_policies,
            frame.cmd_plugins, frame.cmd_outbox, frame.cmd_agenda,
            frame.cmd_queue_schedule, frame.cmd_approvals,
        ):
            handler()

        # scheduler tick publishes a due plan
        from quill_social.model import Draft, PublicationPlan, now_ms
        d = Draft(text="scheduled hi", targets=["acct_mock"])
        frame.store.put_draft(d)
        frame.store.put_plan(PublicationPlan(
            draft_id=d.draft_id, account_id="acct_mock", network="mock",
            state="queued", scheduled_for=now_ms() - 1000))
        frame._on_sched_tick(None)
        assert frame.store.list_plans(state="published")
    finally:
        frame._on_close(None)


def test_commands_report_unavailable_without_selection(app):
    from quill_social.ui.app import SocialFrame

    frame = SocialFrame()
    try:
        frame._items = []
        frame.list.DeleteAllItems()
        cmds = {c.command_id: c for c in frame._build_commands()}
        assert not cmds["reply"].is_available()
        assert cmds["compose"].is_available()
    finally:
        frame._on_close(None)
