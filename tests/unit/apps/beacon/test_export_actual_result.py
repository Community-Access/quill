"""Beacon's Export ends with what is now true (FUX-04).

It used to read the whole path aloud, folder by folder, and a
write that failed raised out of the menu command in silence. Now it names the
format, the file and its folder, and says when the file could not be written.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")


@pytest.fixture
def frame(monkeypatch):
    monkeypatch.setenv("QUILLBEACON_DATA", tempfile.mkdtemp())
    shared_wx_app()
    from quill.apps.beacon.app import BeaconFrame

    monkeypatch.setattr(BeaconFrame, "_start_tray", lambda self: None)
    monkeypatch.setattr(BeaconFrame, "_start_capture_bridge", lambda self: None)
    monkeypatch.setattr(BeaconFrame, "_setup_auto_sync", lambda self: None)
    f = BeaconFrame()
    said: list[str] = []
    monkeypatch.setattr(f.announcer, "say", lambda message, *a, **k: said.append(message))
    f.said = said
    yield f
    f.Close()
    if f:
        f.Destroy()


def test_export_names_the_format_the_file_and_its_folder(frame, tmp_path: Path) -> None:
    target = tmp_path / "Downloads" / "beacon.html"
    target.parent.mkdir()
    assert frame._write_export(str(target), "html", "HTML bookmarks") is True
    assert target.exists()
    assert frame.said == ["Exported your library as HTML bookmarks to beacon.html in Downloads."]


def test_an_export_that_could_not_be_written_says_so(frame, tmp_path: Path) -> None:
    target = tmp_path / "missing" / "beacon.json"
    assert frame._write_export(str(target), "json", "JSON archive") is False
    assert len(frame.said) == 1
    assert frame.said[0].startswith("Could not export to beacon.json in missing: ")
    assert str(tmp_path) not in frame.said[0], "the whole path is read aloud again"
