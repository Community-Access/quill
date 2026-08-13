"""What QUILL does when the disk is full, across all three writers (#1390/#1386).

The reported failure was not "a write failed" -- it was that a *backup* write
failing on a full disk aborted the real save, the close path swallowed the
exception, and the window closed with the document unsaved. So these tests
cover the three places QUILL writes a document's text and assert the rule for
each: the save is the thing that must survive, the backup and the autosave are
best-effort, and nothing closes on a failed save.
"""

from __future__ import annotations

import errno
from pathlib import Path

import pytest

from quill.core.backups import backup_document, read_backup_text
from quill.core.document import Document
from quill.ui.main_frame import MainFrame


def _frame() -> MainFrame:
    return MainFrame.__new__(MainFrame)


class _Wx:
    ICON_ERROR = 1
    OK = 2


# --------------------------------------------------------------------------- #
# backup writer
# --------------------------------------------------------------------------- #


def test_backup_is_written_utf8_and_atomically(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # An "ascii" document whose buffer has gained a non-ascii character used to
    # raise UnicodeEncodeError out of the backup -- and therefore out of save.
    monkeypatch.setattr("quill.core.backups.app_data_dir", lambda: tmp_path)
    document = Document(text="café — naïve", path=tmp_path / "n.txt", encoding="ascii")
    backup = backup_document(document)
    assert backup.read_text(encoding="utf-8") == "café — naïve"
    assert read_backup_text(backup) == "café — naïve"


def test_read_backup_text_falls_back_for_legacy_encodings(tmp_path: Path) -> None:
    legacy = tmp_path / "old.bak"
    legacy.write_bytes("café".encode("cp1252"))
    assert read_backup_text(legacy, "cp1252") == "café"


def test_backup_failure_does_not_abort_the_save(monkeypatch: pytest.MonkeyPatch) -> None:
    frame = _frame()
    statuses: list[str] = []
    frame._set_status = statuses.append  # type: ignore[method-assign]

    def _explode(_document: object) -> None:
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr("quill.ui.main_frame_write_safety.backup_document", _explode)
    frame._backup_before_save(Document(text="x"))  # must not raise
    assert statuses and "saving anyway" in statuses[0]


# --------------------------------------------------------------------------- #
# save failure wording
# --------------------------------------------------------------------------- #


def _capture_save_failure(error: OSError) -> tuple[list[str], list[str]]:
    frame = _frame()
    boxes: list[str] = []
    statuses: list[str] = []
    frame._wx = _Wx()  # type: ignore[assignment]
    frame._show_message_box = lambda message, *_a, **_k: boxes.append(message)  # type: ignore[method-assign]
    frame._set_status = statuses.append  # type: ignore[method-assign]
    frame._report_save_failure("notes.md", error, "Save")
    return boxes, statuses


def test_disk_full_save_failure_says_what_to_do() -> None:
    boxes, statuses = _capture_save_failure(OSError(errno.ENOSPC, "No space left on device"))
    assert "The disk is full" in boxes[0]
    assert "still open and unsaved" in boxes[0]
    assert statuses == ["Could not save notes.md"]


def test_read_only_save_failure_points_at_save_as() -> None:
    boxes, _ = _capture_save_failure(OSError(errno.EACCES, "Permission denied"))
    assert "read-only" in boxes[0]
    assert "Save As" in boxes[0]


def test_other_errors_keep_the_errno_text() -> None:
    boxes, _ = _capture_save_failure(OSError(errno.EIO, "I/O error"))
    assert "Could not save notes.md" in boxes[0]
    assert "I/O error" in boxes[0]


# --------------------------------------------------------------------------- #
# the close path
# --------------------------------------------------------------------------- #


def test_save_on_close_that_raises_cancels_the_close() -> None:
    frame = _frame()
    frame._wx = type("W", (), {"ID_CANCEL": 5, "ID_YES": 6, "ID_NO": 7, "ICON_ERROR": 1, "OK": 2})()
    frame.document = Document(text="unsaved", modified=True)
    frame._show_message_box = lambda *_a, **_k: None  # type: ignore[method-assign]
    frame._set_status = lambda *_a, **_k: None  # type: ignore[method-assign]
    frame._prompt_unsaved_changes_action = lambda *_a, **_k: 6  # type: ignore[method-assign]

    def _raise() -> None:
        raise OSError(errno.ENOSPC, "No space left on device")

    frame.save_file = _raise  # type: ignore[method-assign]
    # False means "do not close" -- the whole point of #1390.
    assert frame._prompt_to_save_active_document("closing") is False


def test_veto_after_failed_save_fires_once_then_lets_the_window_close() -> None:
    frame = _frame()
    frame._wx = _Wx()  # type: ignore[assignment]
    frame._show_message_box = lambda *_a, **_k: None  # type: ignore[method-assign]
    frame._document_tabs = [type("T", (), {"document": Document(text="x", modified=True)})()]
    assert frame._veto_close_after_failed_save() is True
    # #210 still holds: a second attempt must not be trapped.
    assert frame._veto_close_after_failed_save() is False


def test_no_veto_when_nothing_is_actually_unsaved() -> None:
    frame = _frame()
    frame._wx = _Wx()  # type: ignore[assignment]
    frame._document_tabs = [type("T", (), {"document": Document(text="x", modified=False)})()]
    assert frame._veto_close_after_failed_save() is False


# --------------------------------------------------------------------------- #
# autosave (#1386)
# --------------------------------------------------------------------------- #


def test_autosave_says_it_has_paused_once_after_repeated_failures() -> None:
    frame = _frame()
    spoken: list[str] = []
    frame._announce = spoken.append  # type: ignore[method-assign]
    error = OSError(errno.ENOSPC, "No space left on device")
    frame._note_autosave_failure(error)
    assert spoken == []  # one failure could be a blip
    frame._note_autosave_failure(error)
    assert len(spoken) == 1
    assert "Autosave paused" in spoken[0]
    assert "disk is full" in spoken[0]
    frame._note_autosave_failure(error)
    frame._note_autosave_failure(error)
    assert len(spoken) == 1  # said once, not per attempt
