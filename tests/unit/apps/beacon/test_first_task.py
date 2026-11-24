"""QuillBeacon's empty library names how to fill it (FUX-09)."""

import tempfile

import pytest

from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")

from quill.apps.beacon.model import Beacon, Resource  # noqa: E402


@pytest.fixture
def frame(monkeypatch):
    monkeypatch.setenv("QUILLBEACON_DATA", tempfile.mkdtemp())
    app = shared_wx_app()
    from quill.apps.beacon.announce import Announcer
    from quill.apps.beacon.app import BeaconFrame

    monkeypatch.setattr(BeaconFrame, "_start_tray", lambda self: None)
    monkeypatch.setattr(BeaconFrame, "_start_capture_bridge", lambda self: None)
    monkeypatch.setattr(BeaconFrame, "_setup_auto_sync", lambda self: None)
    monkeypatch.setattr(Announcer, "say", lambda self, *a, **k: None)
    f = BeaconFrame()
    yield f
    f.Close()  # the app's own close path (test_bulk_ops.py has the story)
    if f:
        f.Destroy()
    try:
        app.Destroy()
    except Exception:
        pass


def test_an_empty_library_names_new_bookmark_and_import_and_takes_focus(frame, monkeypatch) -> None:
    line = frame._first_task_line
    assert line.text == (
        "No bookmarks yet. New Bookmark (Ctrl+N) saves one, or Import (Ctrl+I) brings "
        "bookmarks or subscriptions in."
    )
    focused: list[str] = []
    monkeypatch.setattr(line.ctrl, "SetFocus", lambda: focused.append("line"))
    monkeypatch.setattr(frame.search_box, "SetFocus", lambda: focused.append("search"))
    from quill.apps.beacon import first_task

    first_task.focus_initial(frame)
    assert focused == ["line"]


def test_a_first_bookmark_hides_the_line(frame) -> None:
    res = Resource(title="Garden", type="web", primary_uri="https://x/garden")
    frame.store.put_beacon(Beacon(resource_id=res.resource_id, title="Garden"), resource=res)
    frame._refresh_results()
    assert not frame._first_task_line.shown


def test_a_search_with_no_match_is_not_an_empty_library(frame) -> None:
    res = Resource(title="Garden", type="web", primary_uri="https://x/garden")
    frame.store.put_beacon(Beacon(resource_id=res.resource_id, title="Garden"), resource=res)
    frame.search_box.ChangeValue("zebra")
    frame._refresh_results()
    assert not frame._first_task_line.shown
