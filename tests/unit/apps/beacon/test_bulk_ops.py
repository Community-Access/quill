"""Headless tests for bulk add-to-collection and remove-tag (PRD 18.5, 44.3).

Drives a real BeaconFrame against a temp data dir, patches the text-entry
prompt so no modal blocks, and asserts the store reflects the bulk change and
that a single composite undo entry was pushed.
"""

import tempfile

import pytest

from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")

from quill.apps.beacon.model import Beacon, Resource


@pytest.fixture
def frame(monkeypatch):
    data_dir = tempfile.mkdtemp()
    monkeypatch.setenv("QUILLBEACON_DATA", data_dir)
    app = shared_wx_app()
    from quill.apps.beacon.app import BeaconFrame

    # The tray icon and the capture bridge's HTTP thread are native resources
    # these tests never use; on the CI runner a frame carrying them crashed the
    # worker (access violation, 2026-10-18). The Beacon docs test skips them too.
    monkeypatch.setattr(BeaconFrame, "_start_tray", lambda self: None)
    monkeypatch.setattr(BeaconFrame, "_start_capture_bridge", lambda self: None)
    monkeypatch.setattr(BeaconFrame, "_setup_auto_sync", lambda self: None)
    # Selecting a row announces it; nothing here listens, so keep it off the
    # real screen-reader and speech bridge. Stubbed on the class, before the
    # frame binds ``self._announce`` to it. (The 2026-10-23 CI crash was the
    # results list's own bug: see app._VirtualRows.)
    from quill.apps.beacon.announce import Announcer

    monkeypatch.setattr(Announcer, "say", lambda self, *a, **k: None)
    f = BeaconFrame()
    yield f
    # Close the way the app closes (test_auto_sync.py has the story): a bare
    # Destroy() skips _on_close, leaving the sync timer, the capture bridge
    # thread and the store open, and the timer later fires into freed memory
    # in whatever test runs next -- the shard-2 access violation of 2026-10-18.
    f.Close()
    if f:
        f.Destroy()
    try:
        app.Destroy()
    except Exception:
        pass


def _seed(frame, title, *, tags=(), collections=()):
    res = Resource(title=title, type="web", primary_uri=f"https://x/{title}")
    b = Beacon(
        resource_id=res.resource_id,
        title=title,
        in_inbox=False,
        tags=list(tags),
        collections=list(collections),
    )
    frame.store.put_beacon(b, resource=res)
    return b


def _select_all(frame, beacons):
    frame.last_query = ""
    frame._refresh_results()
    n = frame.results.GetItemCount()
    for i in range(n):
        frame.results.SetItemState(i, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
    return [frame._results_cache[i] for i in range(n) if i < len(frame._results_cache)]


def test_bulk_add_to_collection(frame, monkeypatch):
    b1 = _seed(frame, "A")
    b2 = _seed(frame, "B")
    _select_all(frame, [b1, b2])
    monkeypatch.setattr(wx, "GetTextFromUser", lambda *a, **k: "Reading")
    frame._on_bulk_add_collection(None)
    for bid in (b1.beacon_id, b2.beacon_id):
        assert "Reading" in frame.store.get_beacon(bid).collections
    assert any(c.name == "Reading" for c in frame.store.list_collections())
    # One composite undo entry.
    assert frame.undo.depth() == 1


def test_bulk_remove_tag(frame, monkeypatch):
    b1 = _seed(frame, "A", tags=["research", "keep"])
    b2 = _seed(frame, "B", tags=["research"])
    _select_all(frame, [b1, b2])
    monkeypatch.setattr(wx, "GetTextFromUser", lambda *a, **k: "research")
    frame._on_bulk_remove_tag(None)
    assert frame.store.get_beacon(b1.beacon_id).tags == ["keep"]
    assert frame.store.get_beacon(b2.beacon_id).tags == []
    assert frame.undo.depth() == 1


def test_bulk_remove_tag_none_present(frame, monkeypatch):
    _seed(frame, "A", tags=[])
    _select_all(frame, [])
    captured = []
    monkeypatch.setattr(frame.announcer, "say", lambda m: captured.append(m))
    frame._on_bulk_remove_tag(None)
    assert any("no tags" in m.lower() or "none" in m.lower() for m in captured)


def test_bulk_add_collection_undo_restores(frame, monkeypatch):
    b1 = _seed(frame, "A")
    _select_all(frame, [b1])
    monkeypatch.setattr(wx, "GetTextFromUser", lambda *a, **k: "Reading")
    frame._on_bulk_add_collection(None)
    assert "Reading" in frame.store.get_beacon(b1.beacon_id).collections
    frame.undo.undo()
    assert "Reading" not in frame.store.get_beacon(b1.beacon_id).collections
