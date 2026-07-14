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

    # Always UTF-8, never document.encoding: a snapshot is a recovery-only
    # artifact with no round-trip-fidelity requirement (unlike the real save
    # path's BRF byte-for-byte contract), and recovery.read_recovery_snapshot
    # always decodes it as UTF-8. A narrower document.encoding (e.g. "ascii"
    # for a BRF read) would raise UnicodeEncodeError the moment the in-memory
    # text gained a character outside that range -- crashing autosave itself.
    write_text_atomic(target, document.text, encoding="utf-8", newline="")

    snapshots = sorted(autosave_root.glob(f"{key}-*.snap"), reverse=True)
    for stale in snapshots[max_snapshots:]:
        stale.unlink(missing_ok=True)
    return target


def autosave_rich_document(
    document: Document, session_id: str, rtf_bytes: bytes, max_snapshots: int = 10
) -> Path:
    """Snapshot a rich-mode document's RTF bytes alongside the text snapshot.

    Rich mode (One Editor, Every Format) keeps real formatting in the native
    control; the plain-text ``.snap`` alone would recover the words but lose
    the formatting. The ``.rtfsnap`` carries the full RTF; recovery restores it
    through the surface's ``set_rtf`` when the recovered file is rich.
    Atomic for the same reason the text snapshot is: a truncated newest
    snapshot must never become the recovery source.
    """
    UUID(session_id)
    autosave_root = app_data_dir() / "autosave" / session_id
    autosave_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    key = _document_key(document)
    counter = 0
    target = autosave_root / f"{key}-{stamp}-{counter:03d}.rtfsnap"
    while target.exists():
        counter += 1
        target = autosave_root / f"{key}-{stamp}-{counter:03d}.rtfsnap"
    from quill.core.storage import write_bytes_atomic

    write_bytes_atomic(target, rtf_bytes)
    snapshots = sorted(autosave_root.glob(f"{key}-*.rtfsnap"), reverse=True)
    for stale in snapshots[max_snapshots:]:
        stale.unlink(missing_ok=True)
    return target


def latest_rich_autosave(document: Document, session_id: str) -> Path | None:
    """The newest ``.rtfsnap`` for this document in this session, or None."""
    UUID(session_id)
    autosave_root = app_data_dir() / "autosave" / session_id
    if not autosave_root.exists():
        return None
    snapshots = sorted(autosave_root.glob(f"{_document_key(document)}-*.rtfsnap"), reverse=True)
    return snapshots[0] if snapshots else None


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
