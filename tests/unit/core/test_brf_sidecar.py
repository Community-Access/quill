from __future__ import annotations

from pathlib import Path

import pytest

from quill.core import storage
from quill.core.brf_sidecar import (
    BRFSidecar,
    BRFSidecarError,
    SidecarAnchor,
    SidecarNote,
    SidecarPosition,
    SidecarProofing,
    clear_sidecar,
    read_sidecar,
    sidecar_path,
    write_sidecar,
)


def _full_sidecar() -> BRFSidecar:
    return BRFSidecar(
        profile={"braille_save_sidecar": True, "cells_per_line": 40},
        position=SidecarPosition(
            last_offset=1234, braille_page=12, line=14, cell=31, print_page="7"
        ),
        proofing=SidecarProofing(
            last_proofed_braille_page=9,
            proofed_pages=[1, 2, 3, 9],
            pages_needing_review=[5, 6],
        ),
        anchors=[SidecarAnchor(braille_page=12, print_page="7", offset=1200, confidence=0.92)],
        notes=[SidecarNote(braille_page=12, text="check stanza break")],
    )


def test_sidecar_path_appends_quill_json(tmp_path: Path) -> None:
    assert sidecar_path(tmp_path / "notes.brf").name == "notes.brf.quill.json"


def test_round_trip_is_deep_equal(tmp_path: Path) -> None:
    brf = tmp_path / "notes.brf"
    original = _full_sidecar()
    write_sidecar(brf, original)
    restored = read_sidecar(brf)
    assert restored == original


def test_read_missing_returns_none(tmp_path: Path) -> None:
    assert read_sidecar(tmp_path / "absent.brf") is None


def test_interrupted_write_leaves_previous_file_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    brf = tmp_path / "notes.brf"
    write_sidecar(brf, _full_sidecar())
    before = sidecar_path(brf).read_bytes()

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise OSError("simulated crash during replace")

    monkeypatch.setattr(storage.os, "replace", _boom)
    with pytest.raises(OSError):
        write_sidecar(brf, BRFSidecar(position=SidecarPosition(last_offset=999)))

    # The original sidecar is untouched (atomic temp + os.replace).
    assert sidecar_path(brf).read_bytes() == before
    assert read_sidecar(brf) == _full_sidecar()


def test_malformed_json_raises(tmp_path: Path) -> None:
    brf = tmp_path / "notes.brf"
    sidecar_path(brf).write_text("{ not json", encoding="utf-8")
    with pytest.raises(BRFSidecarError):
        read_sidecar(brf)


def test_schema_violation_raises(tmp_path: Path) -> None:
    brf = tmp_path / "notes.brf"
    # proofed_pages must be a list of ints, not a string.
    sidecar_path(brf).write_text('{"proofing": {"proofed_pages": "nope"}}', encoding="utf-8")
    with pytest.raises(BRFSidecarError):
        read_sidecar(brf)


def test_clear_sidecar_removes_file_and_is_safe_when_absent(tmp_path: Path) -> None:
    brf = tmp_path / "notes.brf"
    write_sidecar(brf, _full_sidecar())
    assert sidecar_path(brf).exists()
    clear_sidecar(brf)
    assert not sidecar_path(brf).exists()
    clear_sidecar(brf)  # no error when already gone
