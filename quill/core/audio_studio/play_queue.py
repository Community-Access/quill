"""Audio Studio chapter play queue (Phase 2 port-in).

A simple ordered list of books (with a starting chapter) the host steps
through: ``next_entry`` advances and wraps, so a finished book hands off to
the next, then back to the first. Persisted as atomic JSON. wx-free,
strict-typed. ``next_entry`` is named to avoid shadowing the builtin ``next``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.storage import write_json_atomic

_FILE_NAME = "audio_studio_play_queue.json"


@dataclass(slots=True)
class QueueEntry:
    """One queued book plus the chapter to start it at."""

    path: str
    title: str
    chapter: int = 0

    def to_dict(self) -> dict[str, object]:
        return {"path": self.path, "title": self.title, "chapter": self.chapter}

    @staticmethod
    def from_dict(data: object) -> QueueEntry | None:
        if not isinstance(data, dict):
            return None
        path = str(data.get("path", ""))
        if not path:
            return None
        return QueueEntry(
            path=path,
            title=str(data.get("title", "")),
            chapter=int(data.get("chapter", 0) or 0),
        )


@dataclass(slots=True)
class PlayQueue:
    """The queue plus the index of the currently-playing entry (-1 = none)."""

    entries: list[QueueEntry] = field(default_factory=list)
    current_index: int = -1

    @property
    def is_empty(self) -> bool:
        return not self.entries


def add(queue: PlayQueue, entry: QueueEntry) -> None:
    """Append ``entry`` unless its path is already queued (dedup by path)."""
    if any(e.path == entry.path for e in queue.entries):
        return
    queue.entries.append(entry)


def at(queue: PlayQueue, index: int) -> QueueEntry | None:
    """Return the entry at ``index``, or None when out of range."""
    if 0 <= index < len(queue.entries):
        return queue.entries[index]
    return None


def next_entry(queue: PlayQueue) -> QueueEntry | None:
    """Advance ``current_index`` (wrapping) and return the entry there."""
    if not queue.entries:
        return None
    queue.current_index = (queue.current_index + 1) % len(queue.entries)
    return queue.entries[queue.current_index]


def remove(queue: PlayQueue, path: str) -> None:
    """Drop the entry with ``path``; keep ``current_index`` in range."""
    queue.entries = [e for e in queue.entries if e.path != path]
    _clamp_index(queue)


def clear(queue: PlayQueue) -> None:
    """Empty the queue and reset the current index."""
    queue.entries = []
    queue.current_index = -1


def _clamp_index(queue: PlayQueue) -> None:
    if not queue.entries:
        queue.current_index = -1
    elif queue.current_index >= len(queue.entries):
        queue.current_index = len(queue.entries) - 1


def _store_path(data_dir: Path) -> Path:
    return data_dir / _FILE_NAME


def load_queue(data_dir: Path) -> PlayQueue:
    """Read the queue (an absent or broken file reads as empty)."""
    try:
        raw = json.loads(_store_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return PlayQueue()
    if not isinstance(raw, dict):
        return PlayQueue()
    queue = PlayQueue()
    entries_raw = raw.get("entries")
    if isinstance(entries_raw, list):
        for entry in entries_raw:
            parsed = QueueEntry.from_dict(entry)
            if parsed is not None:
                queue.entries.append(parsed)
    try:
        queue.current_index = int(raw.get("current_index", -1))
    except (TypeError, ValueError):
        queue.current_index = -1
    _clamp_index(queue)
    return queue


def save_queue(data_dir: Path, queue: PlayQueue) -> None:
    """Persist the queue atomically (temp file + ``os.replace``)."""
    write_json_atomic(
        _store_path(data_dir),
        {
            "entries": [e.to_dict() for e in queue.entries],
            "current_index": queue.current_index,
        },
    )
