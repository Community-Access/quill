"""Beacon's pre-sync snapshots, said as what they are rather than as file names.

Sync History listed its rollback points as ``sync_1732456789012.db``: a
millisecond count, which tells nobody which sync it came before, and a
rollback overwrote the library with no way back if the wrong row was chosen
(FUX-05, "recovery that speaks in terms of the person's work"). This module
words a snapshot by when it was taken and how big it is, and keeps the library
as it was before a rollback as one more snapshot, so the rollback can itself
be rolled back from the same list.

wx-free, so it is tested without a window.
"""

from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

__all__ = [
    "ROLLBACK_PREFIX",
    "SYNC_PREFIX",
    "confirm_rollback",
    "keep_before_rollback",
    "rollback_failed",
    "rolled_back",
    "snapshot_label",
    "snapshot_size",
    "stamp_of",
]

#: A snapshot taken before a sync.
SYNC_PREFIX = "sync_"
#: The library as it was before a rollback: the way back from that rollback.
ROLLBACK_PREFIX = "rollback_"


def stamp_of(name: str) -> int:
    """The millisecond stamp in a snapshot's file name, or 0."""
    for prefix in (SYNC_PREFIX, ROLLBACK_PREFIX):
        if name.startswith(prefix) and name.endswith(".db"):
            try:
                return int(name[len(prefix) : -len(".db")])
            except ValueError:
                return 0
    return 0


def snapshot_size(size: int) -> str:
    """``1.2 MB``, ``340 KB``, ``900 bytes``."""
    if size >= 1_000_000:
        return f"{size / 1_000_000:.1f} MB"
    if size >= 1_000:
        return f"{size // 1_000} KB"
    return f"{size} bytes"


def _when(stamp: int, now: datetime | None) -> str:
    from quill.core.action_feedback import when_said

    if stamp <= 0:
        return "at an unknown time"
    return when_said(datetime.fromtimestamp(stamp / 1000), now)


def _when_and_kind(entry: dict[str, Any], now: datetime | None) -> tuple[str, str]:
    name = str(entry.get("name", ""))
    stamp = int(entry.get("created", 0) or 0) or stamp_of(name)
    kind = "rollback" if name.startswith(ROLLBACK_PREFIX) else "sync"
    return _when(stamp, now), kind


def snapshot_label(entry: dict[str, Any], now: datetime | None = None) -> str:
    """One row: ``Today at 2:14 PM, before a sync, 1.2 MB``.

    The time leads, so the rows differ from their first word and first-letter
    navigation in the list means something; the size tells two close ones apart.
    """
    when, kind = _when_and_kind(entry, now)
    size = snapshot_size(int(entry.get("size", 0) or 0))
    return f"{when[0].upper()}{when[1:]}, before a {kind}, {size}"


def confirm_rollback(entry: dict[str, Any], now: datetime | None = None) -> str:
    """The question Roll Back asks: what comes back, what happens to the library now."""
    when, kind = _when_and_kind(entry, now)
    return (
        f"Roll the library back to how it was before the {kind} {when}? "
        "Your library as it is now is kept as a snapshot first, so you can roll back "
        "to it from this list. The sync commit log is kept."
    )


def rolled_back(entry: dict[str, Any], now: datetime | None = None) -> str:
    """What a finished rollback says."""
    when, kind = _when_and_kind(entry, now)
    return (
        f"Rolled the library back to how it was before the {kind} {when}. The library "
        "as it was is kept in Sync History, as the snapshot before this rollback."
    )


def rollback_failed() -> str:
    """What a rollback that did not happen says: nothing changed."""
    return "The library was not rolled back, and nothing in it was changed. It is open again."


def rollback_outcome(entry: dict[str, Any], backup_name: str, ok: bool) -> str:
    """The one sentence a rollback ends with, whichever way it went.

    The frame says it on a short delay, after Sync History has closed, so the
    dialog closing is not announced over it.
    """
    return rolled_back(entry or {"name": backup_name}) if ok else rollback_failed()


def keep_before_rollback(db_file: str | Path, backup_dir: Path, stamp_ms: int) -> Path | None:
    """Copy the live library aside before a rollback overwrites it.

    The store is closed by then, so the database file holds everything
    committed. Returns the copy, or ``None`` when it could not be made -- and a
    rollback that cannot keep the way back does not go ahead.
    """
    source = Path(db_file)
    if not source.is_file():
        return None
    target = backup_dir / f"{ROLLBACK_PREFIX}{stamp_ms}.db"
    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    except OSError:
        return None
    return target
