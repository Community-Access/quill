from __future__ import annotations

from pathlib import Path

from quill.ui.main_frame_vault import relative_note_path


def test_note_under_vault_returns_posix_relpath() -> None:
    assert relative_note_path(Path("/vault"), Path("/vault/sub/note.md")) == "sub/note.md"


def test_note_outside_vault_returns_none() -> None:
    assert relative_note_path(Path("/vault"), Path("/elsewhere/note.md")) is None


def test_no_document_path_returns_none() -> None:
    assert relative_note_path(Path("/vault"), None) is None


def test_no_vault_root_returns_none() -> None:
    assert relative_note_path(None, Path("/vault/note.md")) is None
