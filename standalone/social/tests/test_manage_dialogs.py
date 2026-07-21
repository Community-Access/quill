"""Headless smoke tests for the management dialogs (PRD 25, 27, 32, 34).

Skips cleanly when wx cannot initialize. Each dialog is built against an
in-memory store seeded through the real services, a couple of non-modal methods
are exercised, then the dialog is destroyed. No ShowModal or MainLoop runs.
"""

from __future__ import annotations

import pytest

wx = pytest.importorskip("wx")

from quill_social.db import SocialStore  # noqa: E402
from quill_social.model import SocialItem  # noqa: E402
from quill_social.services import moderation as moderation_svc  # noqa: E402
from quill_social.services import notifications as notif_svc  # noqa: E402
from quill_social.services.moderation import Filter, MuteBlock  # noqa: E402
from quill_social.services.notifications import NotificationPolicy  # noqa: E402
from quill_social.services.outbox import Outbox, OutboxItem  # noqa: E402
from quill_social.services.plugins import PluginManifest, PluginRegistry  # noqa: E402
from quill_social.ui import manage  # noqa: E402


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
    yield s
    s.close()


def _seed_filter(store) -> Filter:
    flt = Filter(name="Politics", criteria={"text": "election"}, action="hide")
    return moderation_svc.save_filter(store, flt)


def _seed_items(store) -> None:
    store.upsert_item(SocialItem(remote_id="a", text="the election is soon", author_handle="@x"))
    store.upsert_item(SocialItem(remote_id="b", text="a cat photo", author_handle="@y"))


def test_filter_editor_builds_filter(app):
    dlg = manage.FilterEditorDialog(None)
    try:
        dlg.name.SetValue("No spoilers")
        dlg._criteria["text"].SetValue("spoiler")
        dlg.action.SetStringSelection("warn")
        flt = dlg.build_filter()
        assert flt.name == "No spoilers"
        assert flt.criteria == {"text": "spoiler"}
        assert flt.action == "warn"
        assert flt.enabled is True
    finally:
        dlg.Destroy()


def test_filter_editor_preserves_id_when_editing(app):
    original = Filter(name="Keep", criteria={"author": "@spam"}, action="hide")
    dlg = manage.FilterEditorDialog(None, filter=original)
    try:
        built = dlg.build_filter()
        assert built.filter_id == original.filter_id
        assert built.created == original.created
        assert built.criteria == {"author": "@spam"}
    finally:
        dlg.Destroy()


def test_safety_center_preview_and_counts(app, store):
    _seed_filter(store)
    _seed_items(store)
    moderation_svc.save_muteblock(store, MuteBlock(target="@troll", kind="block"))
    dlg = manage.SafetyCenterDialog(None, store)
    try:
        assert len(dlg._filters) == 1
        assert len(dlg._muteblocks) == 1
        hidden, warned, total = dlg.preview_counts(dlg._filters[0])
        assert total == 2
        assert hidden == 1  # only the election post matches
        assert warned == 0
        dlg.filter_list.Select(0)
        dlg._update_preview()
        assert "hide 1" in dlg.preview.GetLabel()
    finally:
        dlg.Destroy()


def test_safety_center_add_and_remove_muteblock(app, store):
    dlg = manage.SafetyCenterDialog(None, store)
    try:
        dlg.mb_target.SetValue("@noisy")
        dlg.mb_kind.SetStringSelection("mute")
        dlg._on_add_muteblock(None)
        assert len(moderation_svc.load_muteblocks(store)) == 1
        dlg.mb_list.Select(0)
        dlg._on_remove_muteblock(None)
        assert moderation_svc.load_muteblocks(store) == []
    finally:
        dlg.Destroy()


def test_notification_policies_load_and_save(app, store):
    seeded = NotificationPolicy(account_id="", category="mention", speak=False, digest=True)
    notif_svc.save_policy(store, seeded)
    dlg = manage.NotificationPoliciesDialog(None, store)
    try:
        dlg.category.SetStringSelection("mention")
        dlg._load_category()
        assert dlg._flags["speak"].GetValue() is False
        assert dlg._flags["digest"].GetValue() is True
        dlg._flags["speak"].SetValue(True)
        dlg.quiet_start.SetValue("22:00")
        dlg.quiet_end.SetValue("07:00")
        dlg._on_save(None)
        reloaded = notif_svc.get_policy(store, "", "mention")
        assert reloaded.speak is True
        start, end = manage.load_quiet_hours(store, "")
        assert start == 1320 and end == 420
    finally:
        dlg.Destroy()


def test_plugin_manager_lists_and_toggles(app, store):
    manifest = PluginManifest(
        id="p1",
        name="Alt Text Helper",
        version="1.0",
        kind="a11y",
        declared_permissions=["read_posts"],
        entry="plug:main",
    )
    manage.save_plugin_manifest(store, manifest)
    PluginRegistry(store).load(manifest)  # persist default state via the service
    dlg = manage.PluginManagerDialog(None, store)
    try:
        assert dlg.plugin_list.GetItemCount() == 1
        assert dlg.registry.is_enabled(manifest) is True
        dlg.plugin_list.Select(0)
        dlg._set_enabled(False)
        assert dlg.registry.is_enabled(manifest) is False
        dlg.safe_mode.SetValue(True)
        dlg._on_safe_mode(None)
        assert dlg.registry.safe_mode is True
    finally:
        dlg.Destroy()


def test_outbox_lists_and_removes(app, store):
    outbox = Outbox(store)
    outbox.enqueue(OutboxItem(account_id="acct1", network="mastodon", text="hi"))
    dlg = manage.OutboxDialog(None, store)
    try:
        assert dlg.item_list.GetItemCount() == 1
        assert "closed" in dlg.breaker_text.GetLabel()
        dlg.item_list.Select(0)
        dlg._on_remove(None)
        assert Outbox(store).list() == []
    finally:
        dlg.Destroy()
