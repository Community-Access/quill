"""Headless tests for the Trail step-through dialog (PRD 17.4)."""

import pytest

wx = pytest.importorskip("wx")

from quill.apps.beacon.db import BeaconStore
from quill.apps.beacon.dialogs import TrailStepDialog
from quill.apps.beacon.model import Beacon, Resource, Trail


@pytest.fixture
def app():
    a = wx.App(False)
    yield a
    try:
        a.Destroy()
    except Exception:
        pass


def _store_with_trail(tmp_path):
    s = BeaconStore(str(tmp_path / "trail.db"))
    res = Resource(title="R", type="web", primary_uri="https://x")
    b = Beacon(resource_id=res.resource_id, title="Step beacon")
    s.put_beacon(b, resource=res)
    t = Trail(
        title="My Trail",
        description="a trail",
        steps=[
            {"beacon_id": b.beacon_id, "note": "first", "completed": False},
            {"beacon_id": b.beacon_id, "note": "second", "completed": True},
        ],
    )
    s.put_trail(t)
    return s, t


def test_trail_lists_steps_and_progress(app, tmp_path):
    s, t = _store_with_trail(tmp_path)
    f = wx.Frame(None)
    dlg = TrailStepDialog(f, s, t)
    assert dlg.list.GetCount() == 2
    label = dlg.progress.GetLabel()
    assert "Step 1 of 2" in label
    assert "1 of 2 completed" in label
    dlg.Destroy()
    f.Destroy()


def test_trail_next_persists_current_step(app, tmp_path):
    s, t = _store_with_trail(tmp_path)
    f = wx.Frame(None)
    dlg = TrailStepDialog(f, s, t)
    dlg._step(1)
    assert t.current_step == 1
    reloaded = s.get_trail(t.trail_id)
    assert reloaded.current_step == 1
    assert "Step 2 of 2" in dlg.progress.GetLabel()
    dlg.Destroy()
    f.Destroy()


def test_trail_previous_clamps(app, tmp_path):
    s, t = _store_with_trail(tmp_path)
    f = wx.Frame(None)
    dlg = TrailStepDialog(f, s, t)
    dlg._step(-1)  # already at 0
    assert t.current_step == 0
    dlg.Destroy()
    f.Destroy()


def test_trail_toggle_complete_persists(app, tmp_path):
    s, t = _store_with_trail(tmp_path)
    f = wx.Frame(None)
    dlg = TrailStepDialog(f, s, t)
    dlg._on_toggle_complete(None)  # step 0 -> completed
    assert t.steps[0]["completed"] is True
    reloaded = s.get_trail(t.trail_id)
    assert reloaded.steps[0]["completed"] is True
    assert "2 of 2 completed" in dlg.progress.GetLabel()
    dlg.Destroy()
    f.Destroy()


def test_trail_open_current_invokes_callback(app, tmp_path):
    s, t = _store_with_trail(tmp_path)
    opened = []
    f = wx.Frame(None)
    dlg = TrailStepDialog(f, s, t, on_open_beacon=lambda bid: opened.append(bid))
    dlg._on_open_current(None)
    assert opened == [t.steps[0]["beacon_id"]]
    dlg.Destroy()
    f.Destroy()


def test_trail_missing_beacon_label(app, tmp_path):
    s = BeaconStore(str(tmp_path / "trail2.db"))
    t = Trail(title="T", steps=[{"beacon_id": "nope", "note": "x"}])
    s.put_trail(t)
    f = wx.Frame(None)
    dlg = TrailStepDialog(f, s, t)
    assert "missing beacon" in dlg.list.GetString(0)
    dlg.Destroy()
    f.Destroy()
