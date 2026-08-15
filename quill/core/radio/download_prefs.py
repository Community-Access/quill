"""Where a download goes, and what it is called when it gets there.

A downloads folder full of ``ch01.mp3``, ``ch01.mp3 (2)``, ``00412.ogg`` is a
folder nobody can use -- and it is exactly what you get from saving files under
whatever the server called them. So Quill Radio decides the shape, and the shape
is the feature:

* **A podcast goes under its show.** ``Podcasts/The Rest Is History/Rome.mp3``.
  A podcast is a series you follow, and a folder per show is how anybody would
  file one by hand.
* **A book goes in a folder of its own**, because a book *is* a folder -- forty
  chapters that are one thing. ``Books/Middlemarch/Chapter 04.mp3``.
* **And when you have more than one book by somebody, the author gets a folder
  too.** ``Books/George Eliot/Middlemarch/…``. Not before then: a single book
  filed two levels deep is two keystrokes of navigation to reach one thing, and
  an author folder holding exactly one book is a folder that exists to be
  opened and immediately left.

That last rule is the one worth stating, because it is the one a simpler design
gets wrong in both directions -- always nesting by author, or never doing it.
The right answer depends on what is already on disk, which is why
:func:`plan_destination` is given the library it is filing into.

Everything else is a preference with a sensible default: one root folder, and a
switch per rule for anybody whose filing habits differ.

wx-free, strict-typed. Nothing here writes a file; it decides paths.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from quill.core.storage import write_json_atomic

_FILENAME = "radio_downloads.json"

#: What each kind of thing is filed under, inside the root.
FOLDER_BOOKS = "Books"
FOLDER_PODCASTS = "Podcasts"
FOLDER_MUSIC = "Music"
FOLDER_OTHER = "Recordings"

#: Sources that are books, podcasts, or music, for filing purposes. A source not
#: named here files under "Recordings", which is honest rather than clever.
_BOOK_SOURCES = frozenset({"LibriVox", "Project Gutenberg"})
_PODCAST_SOURCES = frozenset({"Podcasts (Apple)", "Podcast"})
_MUSIC_SOURCES = frozenset({"ccMixter", "Audius"})

_UNSAFE = re.compile(r"[^\w\-. ]+")
#: Windows reserves these whatever the extension, so a book called "Con" or a
#: podcast called "Aux" would produce a folder that cannot be created.
_RESERVED = frozenset({
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{n}" for n in range(1, 10)),
    *(f"lpt{n}" for n in range(1, 10)),
})


def safe_segment(text: str, *, fallback: str = "Untitled") -> str:
    """One path segment: no separators, no reserved names, not endless.

    Trailing dots and spaces are stripped because Windows silently drops them,
    which turns two differently-named books into one folder.
    """
    cleaned = _UNSAFE.sub("", str(text or "")).strip()
    cleaned = " ".join(cleaned.split())[:80].rstrip(". ")
    if not cleaned:
        return fallback
    if cleaned.lower() in _RESERVED:
        return f"{cleaned} file"
    return cleaned


@dataclass(slots=True)
class DownloadPrefs:
    """Where downloads go, and how they are arranged when they get there."""

    #: "" means the default: a Quill Radio folder under the user's Downloads.
    root: str = ""
    #: A folder per podcast show. Off means everything lands in Podcasts/.
    folder_per_show: bool = True
    #: A folder per book. Off means chapters land beside each other, which is
    #: only sane for single-file books.
    folder_per_book: bool = True
    #: Group books under their author *once there is more than one*. Off files
    #: every book directly under Books/.
    group_books_by_author: bool = True
    #: Keep the queue running when the window is closed to the tray.
    keep_going_in_background: bool = True
    #: Ask where to put each download instead of filing it automatically.
    always_ask: bool = False

    def describe(self) -> str:
        """The settings line: what will happen to the next thing you save."""
        if self.always_ask:
            return "Quill Radio asks where to put each download."
        where = self.root or "your Downloads folder"
        shape = "Books and podcasts each get their own folder."
        if not (self.folder_per_book or self.folder_per_show):
            shape = "Everything is saved side by side."
        return f"Downloads go to {where}. {shape}"

    def to_dict(self) -> dict[str, object]:
        return {
            "root": self.root,
            "folder_per_show": self.folder_per_show,
            "folder_per_book": self.folder_per_book,
            "group_books_by_author": self.group_books_by_author,
            "keep_going_in_background": self.keep_going_in_background,
            "always_ask": self.always_ask,
        }

    @classmethod
    def from_dict(cls, data: object) -> DownloadPrefs:
        if not isinstance(data, dict):
            return cls()
        return cls(
            root=str(data.get("root", "")),
            folder_per_show=bool(data.get("folder_per_show", True)),
            folder_per_book=bool(data.get("folder_per_book", True)),
            group_books_by_author=bool(data.get("group_books_by_author", True)),
            keep_going_in_background=bool(data.get("keep_going_in_background", True)),
            always_ask=bool(data.get("always_ask", False)),
        )


def default_root() -> Path:
    """The Downloads folder everybody already has, with our own folder inside."""
    return Path.home() / "Downloads" / "Quill Radio"


def resolved_root(prefs: DownloadPrefs) -> Path:
    return Path(prefs.root) if prefs.root.strip() else default_root()


def kind_of(source: str) -> str:
    """Which shelf a source's downloads belong on."""
    name = str(source or "").strip()
    if name in _BOOK_SOURCES:
        return FOLDER_BOOKS
    if name in _PODCAST_SOURCES:
        return FOLDER_PODCASTS
    if name in _MUSIC_SOURCES:
        return FOLDER_MUSIC
    return FOLDER_OTHER


def plan_destination(
    prefs: DownloadPrefs,
    *,
    source: str,
    work: str = "",
    author: str = "",
    existing_authors: dict[str, int] | None = None,
) -> Path:
    """The folder one download belongs in.

    *work* is the book or show it is part of, *author* whoever made it, and
    *existing_authors* maps an author to how many of their works are already
    filed -- which is what decides whether this author has earned a folder. An
    author folder holding exactly one book is a folder you open and immediately
    leave; two or more is a shelf.
    """
    root = resolved_root(prefs)
    kind = kind_of(source)
    base = root / kind

    if kind == FOLDER_PODCASTS:
        if prefs.folder_per_show and work:
            return base / safe_segment(work, fallback="Podcast")
        return base

    if kind == FOLDER_BOOKS:
        parts: list[str] = []
        if prefs.group_books_by_author and author:
            counted = (existing_authors or {}).get(author.strip(), 0)
            # "More than one" counts this book too: filing the second book by
            # somebody should move to an author folder, not wait for a third.
            if counted >= 1:
                parts.append(safe_segment(author, fallback="Unknown author"))
        if prefs.folder_per_book and work:
            parts.append(safe_segment(work, fallback="Book"))
        return base.joinpath(*parts) if parts else base

    return base


def config_path(data_dir: Path | str) -> Path:
    return Path(data_dir) / _FILENAME


def load(data_dir: Path | str) -> DownloadPrefs:
    """This machine's download preferences. A damaged file reads as defaults."""
    try:
        return DownloadPrefs.from_dict(
            json.loads(config_path(data_dir).read_text(encoding="utf-8"))
        )
    except (OSError, ValueError):
        return DownloadPrefs()


def save(data_dir: Path | str, prefs: DownloadPrefs) -> None:
    write_json_atomic(config_path(data_dir), prefs.to_dict())
