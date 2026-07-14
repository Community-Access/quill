"""Remember where the user stopped listening in each audiobook.

A tiny app-data store mapping a book file (path + size, so a rebuilt file
starts fresh) to the last playhead position. The Workbench player resumes
there on open and records on close. Atomic writes; wx-free, strict-typed.
"""

from __future__ import annotations

import json
from pathlib import Path

_FILE_NAME = "listening_positions.json"
_MAX_ENTRIES = 200


def _store_path(data_dir: Path) -> Path:
    return data_dir / _FILE_NAME


def _key(book: Path) -> str:
    try:
        size = book.stat().st_size
    except OSError:
        size = 0
    return f"{book.resolve()}|{size}"


def load_position_ms(data_dir: Path, book: Path) -> int:
    """The saved position for *book*, or 0 (start) when unknown/stale."""
    try:
        raw = json.loads(_store_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    value = raw.get(_key(book)) if isinstance(raw, dict) else None
    try:
        return max(0, int(value))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def save_position_ms(data_dir: Path, book: Path, position_ms: int) -> None:
    """Record *position_ms* for *book* (oldest entries pruned; best-effort)."""
    from quill.core.storage import write_json_atomic

    path = _store_path(data_dir)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        entries: dict[str, int] = raw if isinstance(raw, dict) else {}
    except (OSError, ValueError):
        entries = {}
    entries.pop(_key(book), None)
    entries[_key(book)] = max(0, int(position_ms))
    while len(entries) > _MAX_ENTRIES:
        entries.pop(next(iter(entries)))
    try:
        write_json_atomic(path, entries)
    except OSError:
        pass
