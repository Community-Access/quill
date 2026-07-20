"""Tests for Collection CRUD and Trail persistence (PRD 16.1, 16.3)."""

from quill.apps.beacon.db import BeaconStore
from quill.apps.beacon.model import Beacon, Collection, Resource, Trail


def _store(tmp_path):
    return BeaconStore(str(tmp_path / "beacons.db"))


def test_put_and_get_collection(tmp_path):
    s = _store(tmp_path)
    col = Collection(name="Research", description="depth", sharing="shared", color="#abc")
    s.put_collection(col)
    got = s.collection_by_name("Research")
    assert got is not None
    assert got.description == "depth"
    assert got.sharing == "shared"
    assert got.color == "#abc"
    assert s.get_collection(got.collection_id).name == "Research"


def test_put_collection_updates_existing(tmp_path):
    s = _store(tmp_path)
    col = Collection(name="C", description="old")
    s.put_collection(col)
    col.description = "new"
    s.put_collection(col)
    assert s.collection_by_name("C").description == "new"
    assert len(s.list_collections()) == 1


def test_delete_collection_unlinks_members(tmp_path):
    s = _store(tmp_path)
    col = Collection(name="C")
    s.put_collection(col)
    res = Resource(title="R", type="web", primary_uri="https://x/r")
    b = Beacon(resource_id=res.resource_id, title="R", collections=["C"], in_inbox=False)
    s.put_beacon(b, resource=res)
    assert "C" in s.get_beacon(b.beacon_id).collections
    s.delete_collection(col.collection_id)
    assert s.collection_by_name("C") is None
    # Beacon still exists, just unlinked.
    got = s.get_beacon(b.beacon_id)
    assert got is not None
    assert got.collections == []


def test_delete_collection_reassign_moves_members(tmp_path):
    s = _store(tmp_path)
    src = Collection(name="Old")
    tgt = Collection(name="New")
    s.put_collection(src)
    s.put_collection(tgt)
    res = Resource(title="R", type="web", primary_uri="https://x/r")
    b = Beacon(resource_id=res.resource_id, title="R", collections=["Old"], in_inbox=False)
    s.put_beacon(b, resource=res)
    s.delete_collection(src.collection_id, reassign="New")
    got = s.get_beacon(b.beacon_id)
    assert got.collections == ["New"]


def test_trail_roundtrip(tmp_path):
    s = _store(tmp_path)
    res = Resource(title="A", type="web", primary_uri="https://x/a")
    b = Beacon(resource_id=res.resource_id, title="A", in_inbox=False)
    s.put_beacon(b, resource=res)
    steps = [{"beacon_id": b.beacon_id, "note": "start", "completed": False}]
    t = Trail(title="Learn", description="path", steps=steps)
    s.put_trail(t)
    got = s.get_trail(t.trail_id)
    assert got is not None
    assert got.title == "Learn"
    assert got.steps == steps
    assert any(tr.title == "Learn" for tr in s.list_trails())
