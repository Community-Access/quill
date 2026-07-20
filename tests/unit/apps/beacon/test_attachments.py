"""Tests for Attachment and SavedSearch persistence (PRD 24.1, 15.6, 44.3)."""

from quill.apps.beacon.db import BeaconStore
from quill.apps.beacon.model import Attachment, Beacon, Resource, SavedSearch


def _store(tmp_path):
    return BeaconStore(str(tmp_path / "beacons.db"))


def test_put_and_get_attachment(tmp_path):
    s = _store(tmp_path)
    rid = s.put_resource(Resource(title="Doc", type="document")).resource_id
    bid = s.put_beacon(Beacon(resource_id=rid, title="Doc beacon")).beacon_id
    att = Attachment(
        beacon_id=bid,
        name="notes.txt",
        kind="file",
        uri="C:/tmp/notes.txt",
        mime="text/plain",
        size=42,
        fingerprint="abc",
        metadata={"imported": True},
    )
    s.put_attachment(att)
    got = s.attachments_for(bid)
    assert len(got) == 1
    assert got[0].name == "notes.txt"
    assert got[0].metadata == {"imported": True}
    assert got[0].size == 42


def test_attachment_update_upserts(tmp_path):
    s = _store(tmp_path)
    bid = s.put_beacon(Beacon(title="B")).beacon_id
    att = Attachment(beacon_id=bid, name="a", kind="note", content="hi")
    s.put_attachment(att)
    att.content = "hello world"
    s.put_attachment(att)
    got = s.attachments_for(bid)
    assert len(got) == 1
    assert got[0].content == "hello world"


def test_delete_attachment(tmp_path):
    s = _store(tmp_path)
    bid = s.put_beacon(Beacon(title="B")).beacon_id
    att = Attachment(beacon_id=bid, name="a")
    s.put_attachment(att)
    s.delete_attachment(att.attachment_id)
    assert s.attachments_for(bid) == []


def test_multiple_attachments_ordered(tmp_path):
    s = _store(tmp_path)
    bid = s.put_beacon(Beacon(title="B")).beacon_id
    a1 = Attachment(beacon_id=bid, name="first")
    a2 = Attachment(beacon_id=bid, name="second")
    s.put_attachment(a1)
    s.put_attachment(a2)
    names = [a.name for a in s.attachments_for(bid)]
    assert names == ["first", "second"]


def test_saved_search_crud(tmp_path):
    s = _store(tmp_path)
    ss = SavedSearch(name="Podcasts", query="type:podcast", sort="added")
    s.put_saved_search(ss)
    listed = s.list_saved_searches()
    assert len(listed) == 1
    assert listed[0].name == "Podcasts"
    assert listed[0].query == "type:podcast"

    got = s.get_saved_search(ss.search_id)
    assert got is not None
    assert got.sort == "added"

    ss.query = "type:podcast tag:tech"
    s.put_saved_search(ss)
    assert s.get_saved_search(ss.search_id).query == "type:podcast tag:tech"

    s.delete_saved_search(ss.search_id)
    assert s.list_saved_searches() == []
    assert s.get_saved_search(ss.search_id) is None


def test_saved_search_scope_collection(tmp_path):
    s = _store(tmp_path)
    ss = SavedSearch(
        name="In Research",
        query="tag:research",
        scope_collection="col_research",
    )
    s.put_saved_search(ss)
    got = s.get_saved_search(ss.search_id)
    assert got.scope_collection == "col_research"
