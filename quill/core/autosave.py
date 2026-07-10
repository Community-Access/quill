from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha1
from pathlib import Path
from uuid import UUID

from quill.core.document import Document
from quill.core.paths import app_data_dir


def autosave_document(document: Document, session_id: str, max_snapshots: int = 10) -> Path:
    UUID(session_id)
    autosave_root = app_data_dir() / "autosave" / session_id
    autosave_root.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    key = _document_key(document)
    # Always carry a zero-padded counter suffix so that, when two saves land in
    # the same microsecond stamp (the Windows clock is coarse), the filenames
    # still sort in write order. A bare "{key}-{stamp}.snap" would sort *after*
    # "{key}-{stamp}-000.snap" because '.' > '-', which previously made
    # latest_autosave return the older snapshot.
    counter = 0
    target = autosave_root / f"{key}-{stamp}-{counter:03d}.snap"
    while target.exists():
        counter += 1
        target = autosave_root / f"{key}-{stamp}-{counter:03d}.snap"
    # Write atomically (temp + os.replace) so a crash or interruption mid-write
    # can't leave a truncated snapshot at the final path — that partial file
    # would sort as the newest .snap and become the recovery source, so the
    # user would recover a half-written document instead of the last good one.
    from quill.core.storage import write_text_atomic

    write_text_atomic(target, document.text, encoding=document.encoding, newline="")

    snapshots = sorted(autosave_root.glob(f"{key}-*.snap"), reverse=True)
    for stale in snapshots[max_snapshots:]:
        stale.unlink(missing_ok=True)
    return target


def latest_autosave(document: Document, session_id: str) -> Path | None:
    UUID(session_id)
    autosave_root = app_data_dir() / "autosave" / session_id
    if not autosave_root.exists():
        return None
    snapshots = sorted(autosave_root.glob(f"{_document_key(document)}-*.snap"), reverse=True)
    if not snapshots:
        return None
    return snapshots[0]


def _document_key(document: Document) -> str:
    seed = str(document.path.resolve()) if document.path else "untitled"
    return sha1(seed.encode("utf-8")).hexdigest()
