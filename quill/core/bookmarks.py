"""Named bookmark helpers (wx-free domain logic).

Kept as a separate module so the pure dict operations can be unit-tested
without importing wx. The UI layer (MainFrame) owns the bookmark dict
and calls these helpers directly.

#300: a small BookmarkVault persistence wrapper lets the editor
survive a restart with named jump points intact. The vault stores
bookmarks in app_data_dir() / "bookmarks.json" so the data stays
out of the documents folder; atomic writes via core.storage keep
the file consistent under sudden shutdown. The vault is intentionally
tiny and stateless beyond its on-disk file so it can be instantiated
per editor or shared across editors.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

DEFAULT_VAULT_FILENAME = "bookmarks.json"
DOCUMENT_MEMORY_FILENAME = "document_memory.json"


@dataclass(slots=True)
class BookmarkVault:
    """Persistent named-jump-point store.

    The vault wraps the name -> caret position mapping in a tiny
    object that can read and write itself to disk via core.storage.
    load is forgiving: a missing file or a malformed JSON file
    yields an empty vault instead of raising, so the editor can always
    start. Writes are atomic via write_json_atomic.

    Parameters
    ----------
    path:
        Filesystem location of the bookmark file. Defaults to
        app_data_dir() / "bookmarks.json" so user data lives in
        the standard application data directory.
    """

    path: Path = field(default_factory=lambda: app_data_dir() / DEFAULT_VAULT_FILENAME)
    bookmarks: dict[str, int] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | None = None) -> BookmarkVault:
        """Read the vault from disk and return a populated instance.

        Missing or malformed files yield an empty vault so the editor
        can always start (#300). The caller decides whether to surface
        a status message about the reset.
        """
        target = path if path is not None else app_data_dir() / DEFAULT_VAULT_FILENAME
        # Forgiving load: a missing file or a malformed JSON file
        # yields an empty vault instead of raising, so the editor can
        # always start (#300).
        try:
            raw = read_json(target, default={})
        except (OSError, ValueError):
            raw = {}
        bookmarks: dict[str, int] = {}
        if isinstance(raw, dict):
            for name, position in raw.items():
                if not isinstance(name, str) or not isinstance(position, int):
                    continue
                normalized = name.strip()
                if not normalized:
                    continue
                bookmarks[normalized] = max(0, position)
        return cls(path=target, bookmarks=bookmarks)

    def save(self) -> None:
        """Persist the vault to disk atomically (#300)."""
        ordered = {name: self.bookmarks[name] for name in sorted(self.bookmarks)}
        write_json_atomic(self.path, ordered)

    def set(self, name: str, position: int) -> None:
        normalized = name.strip()
        if not normalized:
            return
        self.bookmarks[normalized] = max(0, int(position))
        self.save()

    def remove(self, name: str) -> bool:
        if name in self.bookmarks:
            del self.bookmarks[name]
            self.save()
            return True
        return False

    def clear(self) -> None:
        if not self.bookmarks:
            return
        self.bookmarks.clear()
        self.save()

    def names(self) -> list[str]:
        return sorted(self.bookmarks.keys(), key=lambda value: value.lower())

    def position(self, name: str) -> int | None:
        return self.bookmarks.get(name)


@dataclass(slots=True)
class DocumentMemory:
    """Per-document bookmarks and last-cursor-position, persisted across sessions.

    Unlike :class:`BookmarkVault` (a single flat name->position map), this keys
    everything by the document's normalized absolute path, so each file remembers
    its own named jump points and where the cursor last was. Untitled documents
    (no path) get ``key_for() is None`` and are simply never persisted — the caller
    keeps those in memory for the session only.

    On-disk shape (``app_data_dir()/document_memory.json``)::

        {"<doc-key>": {"bookmarks": {"intro": 0, ...}, "last_position": 1234}}

    Forgiving load (missing/malformed -> empty), atomic save via core.storage.
    """

    path: Path = field(default_factory=lambda: app_data_dir() / DOCUMENT_MEMORY_FILENAME)
    documents: dict[str, dict] = field(default_factory=dict)

    @staticmethod
    def key_for(doc_path: object) -> str | None:
        """Normalized key for a document path, or None for an unsaved document."""
        if not doc_path:
            return None
        try:
            return os.path.normcase(os.path.abspath(str(doc_path)))
        except (OSError, ValueError):
            return None

    @classmethod
    def load(cls, path: Path | None = None) -> DocumentMemory:
        target = path if path is not None else app_data_dir() / DOCUMENT_MEMORY_FILENAME
        try:
            raw = read_json(target, default={})
        except (OSError, ValueError):
            raw = {}
        documents: dict[str, dict] = {}
        if isinstance(raw, dict):
            for key, entry in raw.items():
                if not isinstance(key, str) or not isinstance(entry, dict):
                    continue
                marks: dict[str, int] = {}
                for name, pos in (entry.get("bookmarks") or {}).items():
                    if isinstance(name, str) and isinstance(pos, int) and name.strip():
                        marks[name.strip()] = max(0, pos)
                last = entry.get("last_position")
                clean: dict[str, object] = {"bookmarks": marks}
                if isinstance(last, int):
                    clean["last_position"] = max(0, last)
                documents[key] = clean
        return cls(path=target, documents=documents)

    def save(self) -> None:
        ordered = {key: self.documents[key] for key in sorted(self.documents)}
        write_json_atomic(self.path, ordered)

    def _entry(self, key: str) -> dict:
        return self.documents.setdefault(key, {"bookmarks": {}})

    def bookmarks_for(self, key: str | None) -> dict[str, int]:
        if not key:
            return {}
        return dict(self.documents.get(key, {}).get("bookmarks", {}))

    def set_bookmarks(self, key: str | None, bookmarks: dict[str, int]) -> None:
        if not key:
            return
        self._entry(key)["bookmarks"] = {n: max(0, int(p)) for n, p in bookmarks.items()}
        self.save()

    def last_position(self, key: str | None) -> int | None:
        if not key:
            return None
        value = self.documents.get(key, {}).get("last_position")
        return value if isinstance(value, int) else None

    def set_last_position(self, key: str | None, position: int) -> None:
        if not key:
            return
        self._entry(key)["last_position"] = max(0, int(position))
        self.save()


def set_bookmark(bookmarks: dict[str, int], name: str, position: int) -> dict[str, int]:
    normalized_name = name.strip()
    if not normalized_name:
        return bookmarks
    updated = dict(bookmarks)
    updated[normalized_name] = max(0, position)
    return updated


def bookmark_names(bookmarks: dict[str, int]) -> list[str]:
    return sorted(bookmarks.keys(), key=lambda value: value.lower())


def bookmark_position(bookmarks: dict[str, int], name: str) -> int | None:
    return bookmarks.get(name)


def quick_slot_name(slot: int) -> str:
    """Reserved bookmark name for numbered quick-bookmark slot 0-9.

    Quick bookmarks are not a parallel storage system -- they are named
    bookmarks with a generated, centralized name, so they get persistence,
    save/load, and crash-safety for free from the existing bookmark store.
    """
    return f"Quick {slot}"
