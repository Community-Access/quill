"""Headless smoke tests for the Attachments dialog (PRD 24.1, 44.3).

wx is available on the build machine; these instantiate the dialog against a
real (temp) store and exercise the pure list/refresh logic plus add/remove
through the store. They skip if a wx app cannot be created.
"""

import pytest

wx = pytest.importorskip("wx")

from quill.apps.beacon.db import BeaconStore
from quill.apps.beacon.dialogs import AttachmentsDialog
from quill.apps.beacon.model import Attachment, Beacon, Resource


@pytest.fixture
def app():
    a = wx.App(False)
    yield a
    try:
        a.Destroy()
    except Exception:
        pass


@pytest.fixture
def store_and_beacon(tmp_path):
    s = BeaconStore(str(tmp_path / "att.db"))
    res = Resource(title="T", type="web", primary_uri="https://x")
    b = Beacon(resource_id=res.resource_id, title="T")
    s.put_beacon(b, resource=res)
    return s, b


def test_label_formats_by_kind(app):
    assert (
        AttachmentsDialog._label(Attachment(name="memo", kind="note", content="hello"))
        == "[note] memo"
    )
    assert AttachmentsDialog._label(Attachment(kind="url", uri="https://x")) == "[url] https://x"
    assert AttachmentsDialog._label(Attachment(kind="file", uri="C:/x.pdf")) == "[file] C:/x.pdf"
    # note with no name falls back to a content preview.
    assert AttachmentsDialog._label(Attachment(kind="note", content="a" * 80)).startswith("[note] ")


def test_dialog_lists_existing(app, store_and_beacon):
    s, b = store_and_beacon
    s.put_attachment(Attachment(beacon_id=b.beacon_id, name="m1", kind="note", content="hi"))
    s.put_attachment(Attachment(beacon_id=b.beacon_id, name="u1", kind="url", uri="https://y"))
    f = wx.Frame(None)
    dlg = AttachmentsDialog(f, s, b.beacon_id, b.title)
    assert dlg.list.GetCount() == 2
    dlg.Destroy()
    f.Destroy()


def test_dialog_remove_updates_list(app, store_and_beacon):
    s, b = store_and_beacon
    att = Attachment(beacon_id=b.beacon_id, name="m1", kind="note", content="hi")
    s.put_attachment(att)
    f = wx.Frame(None)
    dlg = AttachmentsDialog(f, s, b.beacon_id, b.title)
    assert dlg.list.GetCount() == 1
    s.delete_attachment(att.attachment_id)
    dlg._refresh()
    assert dlg.list.GetCount() == 0
    dlg.Destroy()
    f.Destroy()
