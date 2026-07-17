"""Audio Studio per-book prefs (Phase 2 port-in).

Each book can remember its own volume and mute state, overriding the shared
default for that book only -- the same idea as Radio's per-station favorite
volume (``quill/core/radio/favorites.py``), applied to audiobooks. Persisted
as atomic JSON. ``volume_percent == -1`` means "no preference; use the
default". wx-free, strict-typed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.storage import write_json_atomic

_FILE_NAME = "audio_studio_book_prefs.json"


@dataclass(slots=True)
class BookPrefs:
    """One book's saved volume/mute (``volume_percent == -1`` = unset)."""

    volume_percent: int = -1
    muted: bool = False

    def to_dict(self) -> dict[str, object]:
        return {"volume_percent": self.volume_percent, "muted": self.muted}

    @staticmethod
    def from_dict(data: object) -> BookPrefs:
        if not isinstance(data, dict):
            return BookPrefs()
        vol = data.get("volume_percent", -1)
        try:
            vol = int(vol)
        except (TypeError, ValueError):
            vol = -1
        return BookPrefs(volume_percent=vol, muted=bool(data.get("muted", False)))


@dataclass(slots=True)
class BookPrefsStore:
    """All books' prefs keyed by absolute path string."""

    entries: dict[str, BookPrefs] = field(default_factory=dict)


def get_prefs(store: BookPrefsStore, book_path: str) -> BookPrefs:
    """Return the prefs for ``book_path`` (a default when unset).

    Read-only: does not create an entry. Use :func:`set_volume` /
    :func:`set_muted` to persist a change.
    """
    return store.entries.get(book_path, BookPrefs())


def set_volume(store: BookPrefsStore, book_path: str, volume_percent: int) -> bool:
    """Remember the volume for this book (clamped 0-100). True when changed."""
    entry = store.entries.setdefault(book_path, BookPrefs())
    clamped = max(0, min(100, int(volume_percent)))
    if entry.volume_percent == clamped:
        return False
    entry.volume_percent = clamped
    return True


def set_muted(store: BookPrefsStore, book_path: str, muted: bool) -> None:
    """Remember the mute state for this book."""
    entry = store.entries.setdefault(book_path, BookPrefs())
    entry.muted = bool(muted)


def _store_path(data_dir: Path) -> Path:
    return data_dir / _FILE_NAME


def load_prefs(data_dir: Path) -> BookPrefsStore:
    """Read the store (an absent or broken file reads as empty)."""
    try:
        raw = json.loads(_store_path(data_dir).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return BookPrefsStore()
    if not isinstance(raw, dict):
        return BookPrefsStore()
    entries_raw = raw.get("entries")
    store = BookPrefsStore()
    if isinstance(entries_raw, dict):
        for key, val in entries_raw.items():
            store.entries[str(key)] = BookPrefs.from_dict(val)
    return store


def save_prefs(data_dir: Path, store: BookPrefsStore) -> None:
    """Persist the store atomically (temp file + ``os.replace``)."""
    write_json_atomic(
        _store_path(data_dir),
        {"entries": {k: v.to_dict() for k, v in store.entries.items()}},
    )