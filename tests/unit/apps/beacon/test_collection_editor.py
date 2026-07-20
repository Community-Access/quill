"""Headless tests for editing existing collections (PRD 16.1).

Covers the Collection Editor dialog pre-fill + collection_id carry-through, and
the frame wiring that edits the selected collection instead of always creating.
"""

import tempfile

import pytest

wx = pytest.importorskip("wx")

from quill.apps.beacon.model import Collection


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


# -- dialog ------------------------------------------------------------------


def test_dialog_prefills_and_carries_id(frame):
    from quill.apps.beacon.dialogs import CollectionEditorDialog

    col = Collection(name="Read", description="old", sharing="shared", color="#abc")
    frame.store.put_collection(col)
    names = [c.name for c in frame.store.list_collections()]
    dlg = CollectionEditorDialog(frame, collection=col, existing_names=names)
    try:
        assert dlg.name.GetValue() == "Read"
        assert dlg.description.GetValue() == "old"
        assert dlg.sharing.GetValue() == "shared"
        assert dlg.color.GetValue() == "#abc"
        # Edit the description and save.
        dlg.description.SetValue("updated")
        dlg._done(None)
        r = dlg.result()
    finally:
        dlg.Destroy()
    assert r["collection_id"] == col.collection_id
    assert r["description"] == "updated"


def test_dialog_create_has_no_id(frame):
    from quill.apps.beacon.dialogs import CollectionEditorDialog

    dlg = CollectionEditorDialog(frame, existing_names=[])
    try:
        dlg.name.SetValue("Fresh")
        dlg._done(None)
        r = dlg.result()
    finally:
        dlg.Destroy()
    assert r["collection_id"] is None
    assert r["name"] == "Fresh"


# -- frame wiring -----------------------------------------------------------


class _FakeDialog:
    """Replaces CollectionEditorDialog to drive _on_collection_editor headlessly."""

    captured = {}

    def __init__(self, parent, *, collection=None, existing_names=None):
        _FakeDialog.captured = {
            "collection": collection,
            "existing_names": list(existing_names or []),
        }
        self._result = None

    def ShowModal(self):
        # Simulate the user editing the description.
        col = _FakeDialog.captured["collection"]
        self._result = {
            "collection_id": col.collection_id if col else None,
            "name": col.name if col else "New",
            "description": "edited description",
            "parent_id": None,
            "sharing": "private",
            "color": "",
        }
        return wx.ID_OK

    def result(self):
        return self._result

    def Destroy(self):
        pass


def test_frame_edits_selected_collection(monkeypatch, frame):
    import quill.apps.beacon.app as appmod

    col = Collection(name="Read", description="old")
    frame.store.put_collection(col)
    frame.current_scope = "collection:Read"
    monkeypatch.setattr(appmod, "CollectionEditorDialog", _FakeDialog)

    frame._on_collection_editor(None)

    # The dialog was opened in edit mode against the selected collection.
    assert _FakeDialog.captured["collection"] is not None
    assert _FakeDialog.captured["collection"].name == "Read"
    # The existing collection was updated in place (same id, new description).
    updated = frame.store.collection_by_name("Read")
    assert updated.collection_id == col.collection_id
    assert updated.description == "edited description"
    assert len(frame.store.list_collections()) == 1  # no duplicate created


def test_frame_creates_when_no_collection_selected(monkeypatch, frame):
    import quill.apps.beacon.app as appmod

    frame.current_scope = ""  # nothing selected
    monkeypatch.setattr(appmod, "CollectionEditorDialog", _FakeDialog)

    frame._on_collection_editor(None)

    assert _FakeDialog.captured["collection"] is None
    new = frame.store.collection_by_name("New")
    assert new is not None
    assert new.description == "edited description"
