"""Tests for Quill Radio backup/restore (#1193 device migration)."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

from quill.core.radio import backup
from quill.core.radio.backup import (
    BACKUP_SUFFIX,
    RadioBackupError,
    create_backup,
    read_manifest,
    restore_backup,
)


def _seed(data_dir: Path) -> None:
    (data_dir / "radio_favorites.json").write_text('{"favorites": ["KEXP"]}', encoding="utf-8")
    (data_dir / "radio_history.json").write_text('{"close_action": "minimize"}', encoding="utf-8")
    # wake timer + schedule deliberately absent -> skipped, not an error.


def test_backup_bundles_present_files_and_a_manifest(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    _seed(data)
    dest = tmp_path / f"radio-backup{BACKUP_SUFFIX}"
    create_backup(data, dest, app_version="2.2.0")

    manifest = read_manifest(dest)
    assert manifest.app == "quill-radio"
    assert manifest.app_version == "2.2.0"
    assert set(manifest.data_files) == {"radio_favorites.json", "radio_history.json"}
    assert manifest.recordings == 0
    assert manifest.created  # timestamp present
    with zipfile.ZipFile(dest) as zf:
        assert "data/radio_favorites.json" in zf.namelist()
        assert "data/radio_wake_timer.json" not in zf.namelist()  # absent -> skipped


def test_round_trip_restores_the_state_files(tmp_path: Path) -> None:
    src_data = tmp_path / "src"
    src_data.mkdir()
    _seed(src_data)
    dest = tmp_path / f"b{BACKUP_SUFFIX}"
    create_backup(src_data, dest)

    new_data = tmp_path / "new"
    result = restore_backup(dest, new_data)
    assert set(result.data_files) == {"radio_favorites.json", "radio_history.json"}
    fav = (new_data / "radio_favorites.json").read_text(encoding="utf-8")
    hist = (new_data / "radio_history.json").read_text(encoding="utf-8")
    assert fav == '{"favorites": ["KEXP"]}'
    assert hist == '{"close_action": "minimize"}'


def test_recordings_included_only_on_request_and_restored(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    _seed(data)
    rec = tmp_path / "recordings"
    rec.mkdir()
    (rec / "KEXP 2026-07-21.mp3").write_bytes(b"AUDIO")
    dest = tmp_path / f"b{BACKUP_SUFFIX}"

    # Off by default: recordings not included.
    create_backup(data, dest, recordings_dir=rec, include_recordings=False)
    assert read_manifest(dest).recordings == 0

    # On request: included and restored into the new recordings folder.
    create_backup(data, dest, recordings_dir=rec, include_recordings=True)
    assert read_manifest(dest).recordings == 1
    new_data = tmp_path / "new"
    new_rec = tmp_path / "new-rec"
    result = restore_backup(dest, new_data, recordings_dir=new_rec)
    assert result.recordings == ("KEXP 2026-07-21.mp3",)
    assert (new_rec / "KEXP 2026-07-21.mp3").read_bytes() == b"AUDIO"


def test_restore_rejects_a_non_backup_zip(tmp_path: Path) -> None:
    bogus = tmp_path / "notes.zip"
    with zipfile.ZipFile(bogus, "w") as zf:
        zf.writestr("hello.txt", "hi")
    with pytest.raises(RadioBackupError, match="not a Quill Radio backup"):
        restore_backup(bogus, tmp_path / "new")


def test_restore_rejects_a_corrupt_file(tmp_path: Path) -> None:
    bad = tmp_path / "bad.qrbackup"
    bad.write_bytes(b"this is not a zip")
    with pytest.raises(RadioBackupError, match="not a valid"):
        restore_backup(bad, tmp_path / "new")


def test_restore_refuses_a_newer_schema(tmp_path: Path, monkeypatch) -> None:
    future = tmp_path / "future.qrbackup"
    with zipfile.ZipFile(future, "w") as zf:
        zf.writestr(
            "quill-radio-backup.json",
            '{"schema": 99, "app": "quill-radio", "data_files": []}',
        )
    with pytest.raises(RadioBackupError, match="newer version"):
        restore_backup(future, tmp_path / "new")


def test_restore_ignores_unknown_and_escaping_paths(tmp_path: Path) -> None:
    # A hostile archive: an unknown data file, a zip-slip path, and a valid one.
    evil = tmp_path / "evil.qrbackup"
    manifest = '{"schema": 1, "app": "quill-radio", "data_files": []}'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("quill-radio-backup.json", manifest)
        zf.writestr("data/radio_favorites.json", '{"ok": true}')
        zf.writestr("data/secrets.json", "nope")  # not an allowed name
        zf.writestr("data/../../escape.json", "nope")  # zip-slip attempt
    evil.write_bytes(buf.getvalue())
    new_data = tmp_path / "new"
    result = restore_backup(evil, new_data)
    assert result.data_files == ("radio_favorites.json",)
    assert (new_data / "radio_favorites.json").is_file()
    assert not (new_data / "secrets.json").exists()
    assert not (tmp_path / "escape.json").exists()  # never escaped the target dir


def test_create_backup_returns_dest_and_makes_parent(tmp_path: Path) -> None:
    data = tmp_path / "data"
    data.mkdir()
    _seed(data)
    dest = tmp_path / "nested" / "sub" / f"b{BACKUP_SUFFIX}"
    out = create_backup(data, dest)
    assert out == dest and dest.is_file()


def test_now_iso_is_utc_and_sortable() -> None:
    stamp = backup._now_iso()
    assert stamp.endswith("+00:00")
    assert stamp[:4].isdigit()
