"""Audio Studio library store (Phase 2 port-in).

The book library backing the standalone Studio's "Your books" tree (and
available to the embedded surface): a flat list of :class:`BookEntry` records
plus a set of nested ``"/"``-separated folder paths (the same shape Radio
uses for show favorites), persisted atomically as JSON.

The pinned views (Favorites / In Progress / Recently Played / Inbox) are
derived queries, not stored state. ``Inbox`` is the set of recently-opened
audiobook files (from :mod:`quill.core.recent`) that have not yet been added
to the library, mirroring how Radio surfaces fresh stream entries.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from quill.core.recent import recent_audiobook_files
from quill.core.storage import write_json_atomic

#: The fixed set of pinned views shown above the folder tree. Order matters:
#: it is the order the tree builder appends them as root children.
PINNED_VIEWS: tuple[str, ...] = ("Favorites", "In Progress", "Recently Played", "Inbox")

_FILE_NAME = "audio_studio_library.json"


@dataclass
class BookEntry:
    """One book in the library."""

    path: str
    title: str
    folder: str = ""
    favorite: bool = False
    last_played_at: float = 0.0
    added_at: float = 0.0


@dataclass
class LibraryState:
    """The whole library: its books and the known folder paths."""

    books: list[BookEntry] = field(default_factory=list)
    folders: list[str] = field(default_factory=list)


def _store_path(data_dir: Path) -> Path:
    return data_dir / _FILE_NAME


def load_library(data_dir: Path) -> LibraryState:
    """Load the library from ``data_dir``; an empty state when absent or invalid."""
    p = _store_path(data_dir)
    if not p.exists():
        return LibraryState()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return LibraryState()
    if not isinstance(data, dict):
        return LibraryState()
    books: list[BookEntry] = []
    for b in data.get("books", []):
        if isinstance(b, dict):
            books.append(
                BookEntry(
                    path=str(b.get("path", "")),
                    title=str(b.get("title", "")),
                    folder=str(b.get("folder", "") or ""),
                    favorite=bool(b.get("favorite", False)),
                    last_played_at=float(b.get("last_played_at", 0.0) or 0.0),
                    added_at=float(b.get("added_at", 0.0) or 0.0),
                )
            )
    folders = [str(f) for f in data.get("folders", []) if isinstance(f, str)]
    return LibraryState(books=books, folders=folders)


def save_library(data_dir: Path, state: LibraryState) -> None:
    """Persist the library atomically (temp file + ``os.replace``)."""
    write_json_atomic(
        _store_path(data_dir),
        {
            "books": [b.__dict__ for b in state.books],
            "folders": list(state.folders),
        },
    )


def _find(state: LibraryState, path: str) -> BookEntry | None:
    for b in state.books:
        if b.path == path:
            return b
    return None


def record_play(state: LibraryState, path: str, *, now: float) -> None:
    """Stamp ``last_played_at`` on the matching book; no-op when absent."""
    book = _find(state, path)
    if book is not None:
        book.last_played_at = now


def toggle_favorite(state: LibraryState, path: str) -> bool:
    """Flip the favorite flag on the matching book; return the new state.

    Returns ``False`` when the book is not in the library (so a caller can
    treat an unknown path as "not favorited" without an exception).
    """
    book = _find(state, path)
    if book is None:
        return False
    book.favorite = not book.favorite
    return book.favorite


def move_to_folder(state: LibraryState, path: str, folder: str) -> None:
    """Assign ``folder`` to the matching book and record the folder path.

    No-op (and no orphan folder created) when the book is not in the library.
    """
    book = _find(state, path)
    if book is None:
        return
    book.folder = folder
    if folder and folder not in state.folders:
        state.folders.append(folder)


def view_query(state: LibraryState, view: str) -> list[BookEntry]:
    """Return the books that belong to a pinned view.

    - ``Favorites``: books with ``favorite`` set.
    - ``In Progress``: books with a non-zero ``last_played_at`` (refined with a
      "not finished" marker by the UI wiring; the backing only knows "started").
    - ``Recently Played``: started books, newest first.
    - ``Inbox``: recently-opened audiobook files not yet added to the library.
    """
    if view == "Favorites":
        return [b for b in state.books if b.favorite]
    if view == "Recently Played":
        return sorted(
            [b for b in state.books if b.last_played_at],
            key=lambda b: b.last_played_at,
            reverse=True,
        )
    if view == "In Progress":
        return [b for b in state.books if 0 < b.last_played_at]
    if view == "Inbox":
        known = {b.path for b in state.books}
        return [
            BookEntry(path=str(p), title=p.stem)
            for p in recent_audiobook_files()
            if str(p) not in known
        ]
    return []