"""Tests for UndoManager and beacon snapshot/restore (PRD 18.5, 44.3)."""

from quill.apps.beacon.db import BeaconStore
from quill.apps.beacon.model import Beacon, Resource
from quill.apps.beacon.undo import UndoManager, restore_beacons, snapshot_beacons


def _store(tmp_path):
    return BeaconStore(str(tmp_path / "beacons.db"))


def _add(store, title, tags=None, collections=None):
    res = Resource(title=title, type="web", primary_uri=f"https://x/{title}")
    b = Beacon(
        resource_id=res.resource_id,
        title=title,
        in_inbox=False,
        tags=tags or [],
        collections=collections or [],
    )
    store.put_beacon(b, resource=res)
    return b


def test_undo_manager_runs_inverse(tmp_path):
    log = []
    u = UndoManager(announcer=log.append)
    state = {"x": 1}
    u.push("set x", lambda: state.update(x=0))
    assert state["x"] == 1
    assert u.can_undo()
    label = u.undo()
    assert label == "set x"
    assert state["x"] == 0
    assert not u.can_undo()
    assert "Undid: set x" in log[-1]


def test_undo_empty_announces(tmp_path):
    log = []
    u = UndoManager(announcer=log.append)
    assert u.undo() is None
    assert "Nothing to undo" in log[-1]


def test_undo_limit_drops_oldest():
    u = UndoManager(limit=2)
    u.push("a", lambda: None)
    u.push("b", lambda: None)
    u.push("c", lambda: None)
    assert u.depth() == 2


def test_snapshot_restore_roundtrip(tmp_path):
    s = _store(tmp_path)
    b = _add(s, "Keep", tags=["t1"], collections=["C"])
    snaps = snapshot_beacons(s, [b.beacon_id])
    b.tags = ["t1", "t2"]
    b.favorite = True
    s.put_beacon(b)
    restore_beacons(s, snaps)
    got = s.get_beacon(b.beacon_id)
    assert got.tags == ["t1"]
    assert got.favorite is False
    assert got.collections == ["C"]


def test_restore_after_permanent_delete(tmp_path):
    s = _store(tmp_path)
    b = _add(s, "Gone", tags=["t"])
    snaps = snapshot_beacons(s, [b.beacon_id])
    s.delete_permanent(b.beacon_id)
    assert s.get_beacon(b.beacon_id) is None
    restore_beacons(s, snaps)
    got = s.get_beacon(b.beacon_id)
    assert got is not None
    assert got.title == "Gone"
    assert got.tags == ["t"]


def test_bulk_trash_undo(tmp_path):
    s = _store(tmp_path)
    b1 = _add(s, "A")
    b2 = _add(s, "B")
    ids = [b1.beacon_id, b2.beacon_id]
    snaps = snapshot_beacons(s, ids)
    for i in ids:
        s.trash(i)
    assert all(s.get_beacon(i).trashed for i in ids)
    restore_beacons(s, snaps)
    assert not any(s.get_beacon(i).trashed for i in ids)
