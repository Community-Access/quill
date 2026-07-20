"""Headless tests for the unified Preferences dialog (Ctrl+Comma)."""

import tempfile

import pytest

wx = pytest.importorskip("wx")

from quill.apps.beacon.model import Beacon, Resource


@pytest.fixture
def frame(monkeypatch):
    data_dir = tempfile.mkdtemp()
    monkeypatch.setenv("QUILLBEACON_DATA", data_dir)
    app = wx.App(False)
    from quill.apps.beacon.app import BeaconFrame

    f = BeaconFrame()
    yield f
    f.Destroy()
    try:
        app.Destroy()
    except Exception:
        pass


def test_preferences_dialog_has_sections(frame):
    from quill.apps.beacon.dialogs import PreferencesDialog

    dlg = PreferencesDialog(frame, frame)
    try:
        assert dlg.SECTIONS == [
            "Accessibility",
            "Sync",
            "Capture Bridge",
            "Published Pages",
            "Routing Rules",
        ]
        assert dlg.sections.GetCount() == 5
        # Accessibility panel is shown first; its controls exist.
        assert dlg.verbosity is not None
        assert dlg.auto_sync is not None
    finally:
        dlg.Destroy()


def test_preferences_apply_changes_a11y_and_autosync(frame):
    from quill.apps.beacon.dialogs import PreferencesDialog

    dlg = PreferencesDialog(frame, frame)
    try:
        dlg.verbosity.SetValue("verbose")
        dlg.high_contrast.SetValue(True)
        dlg.reduced_motion.SetValue(True)
        # Pick "15 minutes" (index 2 in AUTO_SYNC_CHOICES).
        dlg.auto_sync.SetSelection(2)
        dlg._on_apply(None)
        r = dlg.result()
    finally:
        dlg.Destroy()
    assert r["verbosity"] == "verbose"
    assert r["high_contrast"] is True
    assert r["auto_sync_seconds"] == 900
    # Apply through the frame's testable path.
    frame._apply_preferences(r)
    assert frame.a11y.verbosity == "verbose"
    assert frame.a11y.high_contrast is True
    assert frame.sync.config.auto_sync_seconds == 900


def test_preferences_apply_off_autosync(frame):
    from quill.apps.beacon.dialogs import PreferencesDialog

    dlg = PreferencesDialog(frame, frame)
    try:
        dlg.auto_sync.SetSelection(0)  # Off
        dlg._on_apply(None)
        r = dlg.result()
    finally:
        dlg.Destroy()
    assert r["auto_sync_seconds"] == 0
    frame._apply_preferences(r)
    assert frame.sync.config.auto_sync_seconds == 0


def test_preferences_routing_panel_lists_and_reorders(frame):
    from quill.apps.beacon import routing
    from quill.apps.beacon.dialogs import PreferencesDialog

    routing.save_rules(
        frame.data_dir,
        [
            routing.Rule("github.com", "Code"),
            routing.Rule("recipe", "Cooking"),
        ],
    )
    dlg = PreferencesDialog(frame, frame)
    try:
        assert dlg._routing_list.GetCount() == 2
        # Move the second rule to the top; persisted order must follow.
        dlg._routing_list.SetSelection(1)
        dlg._on_routing_up(None)
        assert dlg._routing_list.GetSelection() == 0
        loaded = routing.load_rules(frame.data_dir)
        assert [r.keyword for r in loaded] == ["recipe", "github.com"]
        # Remove the now-first rule.
        dlg._routing_list.SetSelection(0)
        dlg._on_routing_remove(None)
        assert dlg._routing_list.GetCount() == 1
        assert [r.keyword for r in routing.load_rules(frame.data_dir)] == ["github.com"]
    finally:
        dlg.Destroy()


def test_routing_rule_dialog_requires_both_fields(frame, monkeypatch):
    from quill.apps.beacon.dialogs import RoutingRuleDialog

    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: None)
    dlg = RoutingRuleDialog(frame, collections=["Code"])
    try:
        dlg.keyword.SetValue("github.com")
        dlg.collection.SetValue("")
        dlg._on_ok(None)
        assert dlg.result() is None
        dlg.collection.SetValue("Code")
        dlg._on_ok(None)
        assert dlg.result() == {"keyword": "github.com", "collection": "Code"}
    finally:
        dlg.Destroy()


def test_preferences_publish_panel_lists_and_unpublishes(frame):
    from quill.apps.beacon.dialogs import PreferencesDialog

    # Seed + publish a collection via the frame's publisher.
    res = Resource(title="A", type="web", primary_uri="https://x/a")
    b = Beacon(resource_id=res.resource_id, title="A", in_inbox=False)
    b.collections = ["Read"]
    frame.store.put_beacon(b, resource=res)
    frame.current_scope = "collection:Read"
    frame._publish_current_collection()
    dlg = PreferencesDialog(frame, frame)
    try:
        assert dlg._pub_list.GetCount() == 1
        dlg._pub_list.SetSelection(0)
        dlg._on_unpublish(None)
        assert dlg._pub_list.GetCount() == 0
        assert not frame.publisher.is_published("Read")
    finally:
        dlg.Destroy()
