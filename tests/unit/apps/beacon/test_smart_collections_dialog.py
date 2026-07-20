"""Headless tests for the Smart Collections manager + editor (PRD 15.6)."""

import pytest

wx = pytest.importorskip("wx")

from quill.apps.beacon.db import BeaconStore
from quill.apps.beacon.dialogs import SmartCollectionEditorDialog, SmartCollectionsDialog
from quill.apps.beacon.model import SavedSearch


@pytest.fixture
def app():
    a = wx.App(False)
    yield a
    try:
        a.Destroy()
    except Exception:
        pass


def _store(tmp_path, *searches):
    s = BeaconStore(str(tmp_path / "sc.db"))
    for ss in searches:
        s.put_saved_search(ss)
    return s


def test_manager_lists_searches(app, tmp_path):
    s = _store(
        tmp_path,
        SavedSearch(name="Research", query="tag:research", sort="title"),
        SavedSearch(name="Podcasts", query="type:episode"),
    )
    f = wx.Frame(None)
    dlg = SmartCollectionsDialog(f, s)
    assert dlg.list.GetCount() == 2
    dlg.Destroy()
    f.Destroy()


def test_manager_delete_removes(app, tmp_path):
    s = _store(tmp_path, SavedSearch(name="A", query="tag:a"), SavedSearch(name="B", query="tag:b"))
    f = wx.Frame(None)
    dlg = SmartCollectionsDialog(f, s)
    first = s.list_saved_searches()[0]
    s.delete_saved_search(first.search_id)
    dlg._refresh()
    assert dlg.list.GetCount() == 1
    assert len(s.list_saved_searches()) == 1
    dlg.Destroy()
    f.Destroy()


def test_editor_round_trip(app, tmp_path, monkeypatch):
    s = _store(tmp_path, SavedSearch(name="Old", query="tag:old", sort="added"))
    ss = s.list_saved_searches()[0]
    f = wx.Frame(None)
    # EndModal asserts on a non-modal dialog; neutralize it for the test.
    monkeypatch.setattr(SmartCollectionEditorDialog, "EndModal", lambda self, code: None)
    ed = SmartCollectionEditorDialog(f, saved_search=ss)
    ed.name.SetValue("Renamed")
    ed.query.SetValue("type:episode")
    ed.sort.SetValue("title")
    ed.scope.SetValue("Reading")
    ed._on_save(None)
    r = ed.result()
    assert r == {
        "name": "Renamed",
        "query": "type:episode",
        "sort": "title",
        "scope_collection": "Reading",
    }
    # Persist via the manager's edit path.
    ss.name = r["name"]
    ss.query = r["query"]
    ss.sort = r["sort"]
    ss.scope_collection = r["scope_collection"]
    s.put_saved_search(ss)
    reloaded = s.get_saved_search(ss.search_id)
    assert reloaded.name == "Renamed" and reloaded.sort == "title"
    ed.Destroy()
    f.Destroy()


def test_editor_requires_name_and_query(app, tmp_path, monkeypatch):
    f = wx.Frame(None)
    monkeypatch.setattr(SmartCollectionEditorDialog, "EndModal", lambda self, code: None)
    monkeypatch.setattr(wx, "MessageBox", lambda *a, **k: None)
    ed = SmartCollectionEditorDialog(f, saved_search=None)
    ed.name.SetValue("")
    ed.query.SetValue("tag:x")
    ed._on_save(None)
    assert ed.result() is None
    ed.name.SetValue("Ok")
    ed.query.SetValue("")
    ed._on_save(None)
    assert ed.result() is None
    ed.Destroy()
    f.Destroy()
