"""Tests for the headless CLI (plan section 5): capture, search, export.

Each test points the CLI at a temp data dir via QUILLBEACON_DATA so it never
touches the user's real library. The CLI's handlers are invoked through
``cli.main(argv)`` so the argparse wiring is exercised end to end.
"""

from __future__ import annotations

import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quill.apps.beacon import cli, db
from quill.apps.beacon.model import Beacon, Collection, Resource


def _seed(store, title="A", uri="https://x/a", collection="Read", note="", tags=None, type_="web"):
    res = Resource(title=title, type=type_, primary_uri=uri)
    b = Beacon(resource_id=res.resource_id, title=title, in_inbox=False, note=note, tags=tags or [])
    b.collections = [collection] if collection else []
    store.put_beacon(b, resource=res)
    return b


# -- capture -----------------------------------------------------------------


def test_capture_persists_and_prints(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("QUILLBEACON_DATA", str(tmp_path))
    rc = cli.main([
        "capture",
        "https://example.org/page",
        "--title",
        "Page",
        "--note",
        "a note",
        "--tags",
        "t1,t2",
    ])
    out = capsys.readouterr().out
    assert rc == 0
    assert "captured:" in out and "Page" in out
    store = db.BeaconStore(str(tmp_path / "QuillBeacon" / "beacons.db"))
    try:
        beacons = store.list_beacons()
        assert len(beacons) == 1
        assert beacons[0].title == "Page"
        assert "t1" in beacons[0].tags and "t2" in beacons[0].tags
        assert beacons[0].note == "a note"
    finally:
        store.close()


def test_capture_no_url_returns_2(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("QUILLBEACON_DATA", str(tmp_path))
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    rc = cli.main(["capture"])
    err = capsys.readouterr().err
    assert rc == 2
    assert "no URL" in err


# -- search ------------------------------------------------------------------


def test_search_prints_matches(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("QUILLBEACON_DATA", str(tmp_path))
    store = db.BeaconStore(str(tmp_path / "QuillBeacon" / "beacons.db"))
    _seed(store, "Python Tutorial", uri="https://py.org", note="good")
    _seed(store, "Rust Book", uri="https://rust.org")
    store.close()
    rc = cli.main(["search", "python"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Python Tutorial" in out
    assert "Rust Book" not in out
    assert "https://py.org" in out
    assert "note: good" in out


def test_search_json(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("QUILLBEACON_DATA", str(tmp_path))
    store = db.BeaconStore(str(tmp_path / "QuillBeacon" / "beacons.db"))
    _seed(store, "Python Tutorial", uri="https://py.org", tags=["lang"])
    store.close()
    rc = cli.main(["search", "--json", "--tag", "lang"])
    data = json.loads(capsys.readouterr().out)
    assert rc == 0
    assert len(data) == 1
    assert data[0]["title"] == "Python Tutorial"
    assert data[0]["url"] == "https://py.org"
    assert "lang" in data[0]["tags"]


def test_search_no_matches(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("QUILLBEACON_DATA", str(tmp_path))
    store = db.BeaconStore(str(tmp_path / "QuillBeacon" / "beacons.db"))
    _seed(store, "X")
    store.close()
    rc = cli.main(["search", "zzznotpresent"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "No matches" in out


# -- export ------------------------------------------------------------------


def test_export_text_to_stdout(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("QUILLBEACON_DATA", str(tmp_path))
    store = db.BeaconStore(str(tmp_path / "QuillBeacon" / "beacons.db"))
    _seed(store, "Alpha", uri="https://a.org")
    store.close()
    rc = cli.main(["export", "text"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "https://a.org" in out


def test_export_json_to_file(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("QUILLBEACON_DATA", str(tmp_path))
    store = db.BeaconStore(str(tmp_path / "QuillBeacon" / "beacons.db"))
    _seed(store, "Alpha", uri="https://a.org")
    store.close()
    dest = tmp_path / "out.json"
    rc = cli.main(["export", "json", "--path", str(dest)])
    assert rc == 0
    assert f"wrote {dest}" in capsys.readouterr().out
    data = json.loads(dest.read_text(encoding="utf-8"))
    assert any(b["title"] == "Alpha" for b in data["beacons"])


def test_export_collection_scope(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("QUILLBEACON_DATA", str(tmp_path))
    store = db.BeaconStore(str(tmp_path / "QuillBeacon" / "beacons.db"))
    store.put_collection(Collection(name="Read"))
    _seed(store, "In", uri="https://in.org", collection="Read")
    _seed(store, "Out", uri="https://out.org", collection="Other")
    store.close()
    rc = cli.main(["export", "text", "--collection", "Read"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "https://in.org" in out and "https://out.org" not in out


def test_export_bad_format(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("QUILLBEACON_DATA", str(tmp_path))
    # argparse choices reject this before any handler runs
    try:
        cli.main(["export", "bogus"])
    except SystemExit as e:
        assert e.code != 0
