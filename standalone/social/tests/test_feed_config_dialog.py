"""Headless tests for the per-feed configuration dialog.

Skips cleanly when wx cannot initialize. Builds the dialog against a real
Subscription, exercises non-modal methods (field edits, rule add/remove/reorder,
build), then destroys it. No ShowModal or MainLoop runs.
"""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from quill_social.services.subscriptions import Subscription  # noqa: E402
from quill_social.ui.feeds import FeedConfigDialog, _interval_choices  # noqa: E402


@pytest.fixture
def app():
    try:
        application = wx.App()
    except Exception:  # pragma: no cover - no display
        pytest.skip("wx cannot initialize in this environment")
    yield application
    application.Destroy()


def _sub(**kw) -> Subscription:
    base = dict(account_id="acct1", feed_url="https://a.example/feed", title="A Feed")
    base.update(kw)
    return Subscription(**base)


def test_build_reflects_field_edits(app):
    dlg = FeedConfigDialog(None, _sub(refresh_interval_s=900, retention_days=0))
    try:
        dlg.title.SetValue("Renamed")
        dlg.interval.SetStringSelection("Every hour")
        dlg.retention.SetValue(30)
        dlg.full_text.SetValue(True)
        dlg.notify.SetValue(False)
        out = dlg.build_subscription()
        assert out.title == "Renamed"
        assert out.refresh_interval_s == 3600
        assert out.retention_days == 30
        assert out.full_text is True
        assert out.notify is False
        # Durable identity preserved.
        assert out.account_id == "acct1"
        assert out.feed_url == "https://a.example/feed"
    finally:
        dlg.Destroy()


def test_manual_only_interval(app):
    dlg = FeedConfigDialog(None, _sub(refresh_interval_s=900))
    try:
        dlg.interval.SetStringSelection("Manual only (no auto-refresh)")
        assert dlg.build_subscription().refresh_interval_s == 0
    finally:
        dlg.Destroy()


def test_keyword_rules_add_remove_reorder(app):
    dlg = FeedConfigDialog(None, _sub())
    try:
        dlg.keyword.SetValue("spoilers")
        dlg.action.SetStringSelection("hide")
        dlg._on_add_rule(None)
        dlg.keyword.SetValue("urgent")
        dlg.action.SetStringSelection("star")
        dlg._on_add_rule(None)
        assert [r["keyword"] for r in dlg._rules] == ["spoilers", "urgent"]

        # Move the second rule up.
        dlg.rule_list.SetSelection(1)
        dlg._move(-1)
        assert [r["keyword"] for r in dlg._rules] == ["urgent", "spoilers"]

        # Remove the first.
        dlg.rule_list.SetSelection(0)
        dlg._on_remove_rule(None)
        out = dlg.build_subscription()
        assert out.filters == [{"keyword": "spoilers", "action": "hide"}]
    finally:
        dlg.Destroy()


def test_empty_keyword_is_rejected(app):
    dlg = FeedConfigDialog(None, _sub())
    try:
        dlg.keyword.SetValue("   ")
        dlg._on_add_rule(None)
        assert dlg._rules == []  # blank keyword never added
    finally:
        dlg.Destroy()


def test_existing_rules_prepopulate(app):
    sub = _sub(filters=[{"keyword": "ads", "action": "mark_read"}])
    dlg = FeedConfigDialog(None, sub)
    try:
        assert dlg.rule_list.GetCount() == 1
        assert "Mark read: ads" == dlg.rule_list.GetString(0)
    finally:
        dlg.Destroy()


def test_current_nonpreset_interval_is_selectable():
    choices = _interval_choices(777)  # not a preset
    assert 777 in {secs for _lbl, secs in choices}
    # And presets are still present.
    assert 3600 in {secs for _lbl, secs in choices}
