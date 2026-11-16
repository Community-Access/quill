"""This device's Listening Places file is replaced only while it is still ours
(earshot.md E3). Pure: a temporary folder, no network."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.sync.listening_places import (
    PlaceRecord,
    device_file_path,
    write_device_file,
)
from quill.core.sync.listening_places_guard import ListeningPlacesWriteError
from quill.core.sync.places_interchange import sync_interchange


def _record(position_ms: int) -> PlaceRecord:
    return PlaceRecord(
        id="podcast:guid:abc",
        position_ms=position_ms,
        updated_at=f"2026-11-15T10:00:{position_ms // 1000 % 60:02d}Z",
    )


def _write(folder: Path, position_ms: int) -> bool:
    return write_device_file(
        folder, device_id="dev1", device_label="Desk", app="test/1", records=[_record(position_ms)]
    )


def test_a_file_this_device_wrote_is_replaced(tmp_path: Path) -> None:
    assert _write(tmp_path, 1_000) is True
    assert _write(tmp_path, 2_000) is True
    data = json.loads(device_file_path(tmp_path, "dev1").read_text(encoding="utf-8"))
    assert data["records"][0]["position_ms"] == 2_000


def test_a_changed_file_is_left_untouched_and_explained(tmp_path: Path) -> None:
    _write(tmp_path, 1_000)
    target = device_file_path(tmp_path, "dev1")
    data = json.loads(target.read_text(encoding="utf-8"))
    data["records"][0]["position_ms"] = 999_000  # somebody else edited it
    changed = json.dumps(data)
    target.write_text(changed, encoding="utf-8")
    with pytest.raises(ListeningPlacesWriteError, match="left untouched"):
        _write(tmp_path, 2_000)
    assert target.read_text(encoding="utf-8") == changed


def test_an_unreadable_file_is_left_untouched(tmp_path: Path) -> None:
    target = device_file_path(tmp_path, "dev1")
    target.parent.mkdir(parents=True)
    target.write_text("not json at all", encoding="utf-8")
    with pytest.raises(ListeningPlacesWriteError):
        _write(tmp_path, 1_000)
    assert target.read_text(encoding="utf-8") == "not json at all"


def test_our_own_file_without_a_fingerprint_is_still_ours(tmp_path: Path) -> None:
    _write(tmp_path, 1_000)
    target = device_file_path(tmp_path, "dev1")
    target.with_suffix(".fingerprint").unlink()  # first write after an update
    assert _write(tmp_path, 2_000) is True


def test_a_file_naming_another_device_is_never_replaced(tmp_path: Path) -> None:
    target = device_file_path(tmp_path, "dev1")
    target.parent.mkdir(parents=True)
    target.write_text(
        json.dumps({"format": "listening-places/1", "device": "other", "records": []}),
        encoding="utf-8",
    )
    with pytest.raises(ListeningPlacesWriteError):
        _write(tmp_path, 1_000)


def test_a_failed_write_is_an_error_not_a_quiet_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def refuse(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr("quill.core.storage.write_json_atomic", refuse)
    with pytest.raises(ListeningPlacesWriteError, match="disk full"):
        _write(tmp_path, 1_000)


def test_sync_says_so_once_and_in_its_own_words(tmp_path: Path) -> None:
    from types import SimpleNamespace

    remote = tmp_path / "Dropbox"
    target = device_file_path(remote, "dev1")
    target.parent.mkdir(parents=True)
    target.write_text("written by something else", encoding="utf-8")
    report = sync_interchange(
        data_dir=tmp_path / "data",
        remote_dir=remote,
        device_id="dev1",
        device_label="Desk",
        library=SimpleNamespace(shows=[], folders=[]),
        save_library=lambda _library: None,
    )
    assert any(
        problem.startswith("This computer's Listening Places file") for problem in report.problems
    )
    assert not any("Could not write to the sync folder" in p for p in report.problems)
    assert target.read_text(encoding="utf-8") == "written by something else"
