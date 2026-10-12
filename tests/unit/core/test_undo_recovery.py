from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.undo_last import hold_files
from quill.core.undo_recovery import (
    MARKER,
    UndoRecoveryError,
    prepare_restore,
    recover,
    restore_files,
)


def test_restore_does_not_overwrite_a_new_file_and_keeps_recovery(tmp_path: Path) -> None:
    source = tmp_path / "episode.mp3"
    source.write_bytes(b"old audio")
    directory = tmp_path / "hold"
    held = hold_files([source], directory)
    source.write_bytes(b"new audio")

    assert restore_files(held) == (0, 1)
    assert source.read_bytes() == b"new audio"
    assert next(iter(held)).read_bytes() == b"old audio"
    assert (directory / MARKER).exists()

    source.unlink()
    assert recover(directory) == (1, 0)
    assert source.read_bytes() == b"old audio"
    assert not (directory / MARKER).exists()


def test_interrupted_restore_survives_startup_cleanup(tmp_path: Path) -> None:
    from quill.ui import undo_last_ui

    source = tmp_path / "episode.mp3"
    source.write_bytes(b"audio")
    directory = tmp_path / undo_last_ui.HELD_DIR_NAME / ("a" * 32)
    held = hold_files([source], directory)
    prepare_restore(held)

    undo_last_ui.sweep_holding_dir(directory.parent)

    assert source.read_bytes() == b"audio"
    assert not directory.exists()


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {"version": True, "files": []},
        {"version": 2, "files": []},
        {"version": 1, "files": "invalid"},
        {"version": 1, "files": [{"held": "../outside", "original": "relative"}]},
        {"version": 1, "files": [{"held": "0000-ep.mp3", "original": "relative"}]},
    ],
)
def test_invalid_recovery_preserves_the_held_directory(tmp_path: Path, payload: object) -> None:
    directory = tmp_path / "hold"
    directory.mkdir()
    audio = directory / "0000-ep.mp3"
    audio.write_bytes(b"safe")
    (directory / MARKER).write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(UndoRecoveryError):
        recover(directory)
    assert audio.read_bytes() == b"safe"


def test_missing_recovery_copy_is_reported_not_claimed_as_restored(tmp_path: Path) -> None:
    directory = tmp_path / "hold"
    directory.mkdir()
    held = {directory / "0000-missing.mp3": tmp_path / "missing.mp3"}
    assert restore_files(held) == (0, 1)
    assert (directory / MARKER).exists()
