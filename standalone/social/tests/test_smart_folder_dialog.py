"""Headless tests for the smart-folder / saved-search dialog."""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from quill_social.model import SocialItem  # noqa: E402
from quill_social.services import smartfolder as smartfolder_svc  # noqa: E402
from quill_social.ui.feeds import SmartFolderDialog  # noqa: E402


@pytest.fixture
def app():
    try:
        application = wx.App()
    except Exception:  # pragma: no cover - no display
        pytest.skip("wx cannot initialize in this environment")
    yield application
    application.Destroy()


def test_build_rule_omits_empty_clauses(app):
    dlg = SmartFolderDialog(None)
    try:
        assert dlg.build_rule() == {}  # nothing set -> empty (rejected on OK)
        dlg.keyword.SetValue("python")
        dlg.unread.SetValue(True)
        dlg.min_engagement.SetValue(5)
        rule = dlg.build_rule()
        assert rule == {"keyword": "python", "unread": True, "min_engagement": 5}
    finally:
        dlg.Destroy()


def test_seeding_populates_fields(app):
    dlg = SmartFolderDialog(
        None,
        name="With media",
        rule={"has_media": True, "author": "ada"},
        folder_id="f1",
    )
    try:
        assert dlg.name.GetValue() == "With media"
        assert dlg.has_media.GetValue() is True
        assert dlg.author.GetValue() == "ada"
        assert dlg.result_folder_id == "f1"
        assert dlg.build_rule() == {"has_media": True, "author": "ada"}
    finally:
        dlg.Destroy()


def test_rule_matches_expected_items(app):
    dlg = SmartFolderDialog(None)
    try:
        dlg.keyword.SetValue("sale")
        rule = dlg.build_rule()
    finally:
        dlg.Destroy()
    items = [
        SocialItem(network="rss", remote_id="1", text="big SALE today"),
        SocialItem(network="rss", remote_id="2", text="nothing here"),
    ]
    hits = smartfolder_svc.evaluate(items, rule)
    assert [it.remote_id for it in hits] == ["1"]
