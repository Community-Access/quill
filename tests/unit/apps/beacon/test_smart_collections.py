"""Tests for Smart Collections / saved-search evaluation (PRD 15.6)."""

from quill.apps.beacon import search as searchmod
from quill.apps.beacon.db import BeaconStore
from quill.apps.beacon.model import Beacon, Resource, SavedSearch


def _store(tmp_path):
    return BeaconStore(str(tmp_path / "beacons.db"))


def _add(store, title, rtype, tags=None, collections=None, note=""):
    res = Resource(title=title, type=rtype, primary_uri=f"https://x/{title}")
    b = Beacon(
        resource_id=res.resource_id,
        title=title,
        note=note,
        in_inbox=False,
        tags=tags or [],
        collections=collections or [],
    )
    store.put_beacon(b, resource=res)
    return b


def test_saved_search_evaluates_live(tmp_path):
    s = _store(tmp_path)
    _add(s, "Ep1", "podcastEpisode")
    _add(s, "Ep2", "podcastEpisode")
    _add(s, "Page", "web")
    ss = SavedSearch(name="Pods", query="type:podcastEpisode", sort="added")
    s.put_saved_search(ss)
    got = searchmod.evaluate_saved_search(s, ss)
    titles = sorted(b.title for b in got)
    assert titles == ["Ep1", "Ep2"]


def test_smart_collection_reflects_changes(tmp_path):
    s = _store(tmp_path)
    ss = SavedSearch(name="Favs", query="favorite", sort="added")
    s.put_saved_search(ss)
    assert searchmod.evaluate_saved_search(s, ss) == []
    b = _add(s, "Starred", "web")
    b.favorite = True
    s.put_beacon(b)
    got = searchmod.evaluate_saved_search(s, ss)
    assert [b.title for b in got] == ["Starred"]


def test_saved_search_scope_collection(tmp_path):
    s = _store(tmp_path)
    s._ensure_collection("Research")
    s.conn.commit()
    _add(s, "In", "web", collections=["Research"])
    _add(s, "Out", "web")
    ss = SavedSearch(name="R", query="", scope_collection="Research")
    s.put_saved_search(ss)
    got = searchmod.evaluate_saved_search(s, ss)
    assert [b.title for b in got] == ["In"]


def test_saved_search_tag_and_note(tmp_path):
    s = _store(tmp_path)
    _add(s, "A", "web", tags=["tech"], note="important")
    _add(s, "B", "web", tags=["tech"])
    _add(s, "C", "web", note="important")
    ss = SavedSearch(name="T", query="tag:tech has:note", sort="added")
    s.put_saved_search(ss)
    got = searchmod.evaluate_saved_search(s, ss)
    assert [b.title for b in got] == ["A"]
