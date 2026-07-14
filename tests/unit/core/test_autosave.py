from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from quill.core.autosave import autosave_document, latest_autosave
from quill.core.document import Document


def test_autosave_document_creates_snapshot(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    session_id = str(uuid4())
    document = Document(text="draft")

    snapshot = autosave_document(document, session_id)
    assert snapshot.exists()
    assert snapshot.suffix == ".snap"
    assert snapshot.read_text(encoding="utf-8") == "draft"


def test_autosave_keeps_most_recent_snapshots(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    session_id = str(uuid4())
    document = Document(text="v1")

    for index in range(5):
        document.set_text(f"v{index}")
        autosave_document(document, session_id, max_snapshots=3)

    autosave_dir = tmp_path / "autosave" / session_id
    snapshots = list(autosave_dir.glob("*.snap"))
    assert len(snapshots) == 3


def test_latest_autosave_returns_most_recent(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    session_id = str(uuid4())
    document = Document(text="a")
    autosave_document(document, session_id)
    document.set_text("b")
    second = autosave_document(document, session_id)

    latest = latest_autosave(document, session_id)
    assert latest == second


def test_autosave_rejects_invalid_session_id() -> None:
    with pytest.raises(ValueError):
        autosave_document(Document(text="x"), "not-a-uuid")


def test_autosave_document_survives_narrow_encoding_with_wide_characters(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Regression: a BRF (or any ascii-encoded) document that gains a
    character outside its declared encoding must not crash autosave.

    A live crash report showed a UnicodeEncodeError ('ascii' codec can't
    encode U+2004 THREE-PER-EM SPACE) from this exact path -- the document's
    ``encoding`` was "ascii" (the BRF-read default) but the in-memory text
    had picked up a wide character via abbreviation expansion. The snapshot
    is a recovery-only artifact, always read back as UTF-8 by
    ``recovery.read_recovery_snapshot`` regardless of the source document's
    encoding, so it must always be *written* as UTF-8 too.
    """
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path))
    session_id = str(uuid4())
    text_with_wide_char = "before after"
    document = Document(text=text_with_wide_char, encoding="ascii")

    snapshot = autosave_document(document, session_id)

    assert snapshot.read_text(encoding="utf-8") == text_with_wide_char
