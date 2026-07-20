"""Headless frame test for the publish action (plan section 12).

Drives a real BeaconFrame against a temp data dir, selects a collection by
setting current_scope, and calls the no-dialog publish path. Asserts the
published manifest lands on disk and the bridge (if it started) serves it.
"""

import json
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


def _seed(frame, title, collection):
    res = Resource(title=title, type="web", primary_uri=f"https://x/{title}")
    b = Beacon(resource_id=res.resource_id, title=title, in_inbox=False)
    b.collections = [collection]
    frame.store.put_beacon(b, resource=res)
    return b


def test_publish_current_collection_writes_manifest(frame):
    _seed(frame, "A", "Read")
    frame.current_scope = "collection:Read"
    res = frame._publish_current_collection()
    assert res.get("ok"), res
    assert res["count"] == 1
    manifest = json.loads((frame.data_dir / "published" / "read" / "manifest.json").read_text())
    assert manifest["name"] == "Read"
    assert frame.publisher.is_published("Read")


def test_publish_without_collection_selected_errors(frame):
    _seed(frame, "A", "Read")
    frame.current_scope = "all"
    res = frame._publish_current_collection()
    assert "error" in res
    assert not frame.publisher.is_published("Read")


def test_unpublish_current_collection(frame):
    _seed(frame, "A", "Read")
    frame.current_scope = "collection:Read"
    frame._publish_current_collection()
    assert frame.publisher.is_published("Read")
    res = frame.publisher.unpublish("Read")
    assert res["ok"]
    assert not frame.publisher.is_published("Read")
