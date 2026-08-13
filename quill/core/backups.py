from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha1
from pathlib import Path

from quill.core.document import Document
from quill.core.paths import app_data_dir


def backup_document(document: Document) -> Path:
    backup_root = app_data_dir() / "backups" / _document_key(document)
    backup_root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = backup_root / f"{stamp}.bak"
    suffix = 1
    while backup_path.exists():
        backup_path = backup_root / f"{stamp}-{suffix}.bak"
        suffix += 1
    # Atomic, and always UTF-8 -- the same contract as core.autosave (#1390).
    # A .bak is a recovery-only artifact with no round-trip-fidelity
    # requirement, so writing it in the document's own (possibly narrow)
    # encoding only bought a UnicodeEncodeError the moment the buffer gained a
    # character outside that range -- and that error aborted the *save*, not
    # just the backup. Atomicity matters for the same reason it does for the
    # autosave snapshot: a truncated .bak must never become what a user
    # restores. read_backup_text decodes UTF-8 first and falls back for files
    # written by older builds.
    from quill.core.storage import write_text_atomic

    write_text_atomic(backup_path, document.text, encoding="utf-8", newline="")
    return backup_path


def read_backup_text(backup_path: Path, fallback_encoding: str = "utf-8") -> str:
    """Read a ``.bak`` written by any QUILL build.

    Backups are UTF-8 as of 1.0.1; older ones used the document's encoding, so
    a decode failure retries in *fallback_encoding* rather than stranding a
    user in front of a backup they cannot restore.
    """
    try:
        return backup_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return backup_path.read_text(encoding=fallback_encoding, errors="replace")


def list_backups(document_path: Path) -> list[Path]:
    doc = Document(path=document_path)
    backup_root = app_data_dir() / "backups" / _document_key(doc)
    if not backup_root.exists():
        return []
    return sorted(backup_root.glob("*.bak"), key=_backup_sort_key, reverse=True)


def _document_key(document: Document) -> str:
    seed = str(document.path.resolve()) if document.path else "untitled"
    return sha1(seed.encode("utf-8")).hexdigest()


def _backup_sort_key(path: Path) -> tuple[str, int]:
    stem = path.stem
    timestamp, separator, suffix = stem.partition("-")
    if not separator:
        return timestamp, 0
    try:
        return timestamp, int(suffix)
    except ValueError:
        return timestamp, 0
