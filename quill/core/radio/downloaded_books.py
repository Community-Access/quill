"""A downloaded book, read back off the disk as chapters in order.

Downloading a forty-chapter novel is only half of a feature. The other half is
listening to it, and a folder of forty files is not a book unless something
knows they are *one thing, in order* -- which is exactly what the filing rules
already arranged for (``download_prefs``) and what nothing had yet read back.

So this reads the folder. It is the smallest possible bridge between "Quill
Radio can save a book" and "Quill Radio can play one", and it is deliberately
not a library: there is no database, no index, no scan on startup. The folder
**is** the record. Somebody who moves, renames or deletes a chapter by hand has
changed the book, and the next read simply agrees with them.

Two rules that make the order right:

* **Natural order, not string order.** ``Chapter 2`` comes before ``Chapter 10``,
  which is obvious to a person and wrong in every naive sort. A book that plays
  its tenth chapter second is worse than one that does not play at all.
* **Only audio.** The licence note written beside a Creative Commons track, a
  cover image, a stray text file -- none of them is a chapter, and playing one
  is a silence somebody has to diagnose.

wx-free, strict-typed, pure apart from reading directory entries.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

#: What counts as a chapter. Everything Quill Radio can actually play.
AUDIO_SUFFIXES: frozenset[str] = frozenset({
    ".mp3",
    ".m4a",
    ".m4b",
    ".ogg",
    ".oga",
    ".opus",
    ".flac",
    ".wav",
    ".aac",
    ".wma",
})

_NUMBERS = re.compile(r"(\d+)")


def natural_key(name: str) -> tuple:
    """Sort key where 2 comes before 10, as anybody would expect."""
    return tuple(
        int(part) if part.isdigit() else part.lower() for part in _NUMBERS.split(str(name))
    )


@dataclass(frozen=True, slots=True)
class Chapter:
    """One file of a book, and what to call it out loud."""

    path: Path
    index: int
    total: int

    @property
    def title(self) -> str:
        """The file's own name, cleaned up -- publishers name these well."""
        return self.path.stem.replace("_", " ").strip() or f"Chapter {self.index}"

    def spoken(self) -> str:
        """ "Chapter 4 of 40, The Dead Hand." -- position first, because that is
        what somebody moving through a book is tracking."""
        return f"{self.index} of {self.total}, {self.title}."


@dataclass(slots=True)
class DownloadedBook:
    """One folder that holds one book."""

    folder: Path
    chapters: list[Chapter] = field(default_factory=list)
    #: The author folder above it, when the filing rules made one.
    author: str = ""

    @property
    def title(self) -> str:
        return self.folder.name

    @property
    def is_empty(self) -> bool:
        return not self.chapters

    def row_label(self) -> str:
        """One row: the book, who wrote it, and how much of it is here."""
        count = len(self.chapters)
        parts = [self.title]
        if self.author:
            parts.append(f"by {self.author}")
        parts.append(f"{count} chapter{'' if count == 1 else 's'}")
        return ", ".join(parts)

    def chapter_at(self, index: int) -> Chapter | None:
        return self.chapters[index] if 0 <= index < len(self.chapters) else None

    def index_of(self, path: Path | str) -> int:
        """Where a file sits in this book, or -1. The basis of "next chapter"."""
        target = Path(path).resolve()
        for chapter in self.chapters:
            try:
                if chapter.path.resolve() == target:
                    return chapter.index - 1
            except OSError:
                continue
        return -1


def chapters_in(folder: Path | str) -> list[Chapter]:
    """Every playable file in *folder*, in natural order."""
    directory = Path(folder)
    try:
        files = [
            entry
            for entry in directory.iterdir()
            if entry.is_file() and entry.suffix.lower() in AUDIO_SUFFIXES
        ]
    except OSError:
        return []
    files.sort(key=lambda entry: natural_key(entry.name))
    total = len(files)
    return [Chapter(path=path, index=i, total=total) for i, path in enumerate(files, start=1)]


def read_book(folder: Path | str, *, author: str = "") -> DownloadedBook:
    """One folder as a book."""
    return DownloadedBook(folder=Path(folder), chapters=chapters_in(folder), author=author)


def find_books(books_root: Path | str) -> list[DownloadedBook]:
    """Every downloaded book under the Books folder, however it was filed.

    Handles both shapes the filing rules produce -- ``Books/Middlemarch/`` and
    ``Books/George Eliot/Middlemarch/`` -- by looking one level down when a
    folder holds only folders. That is the same question a person answers by
    glancing at it, and it means the reader does not need to be told which rule
    was in force when the book was saved.
    """
    root = Path(books_root)
    found: list[DownloadedBook] = []
    try:
        entries = sorted(
            (entry for entry in root.iterdir() if entry.is_dir()),
            key=lambda entry: natural_key(entry.name),
        )
    except OSError:
        return []
    for entry in entries:
        book = read_book(entry)
        if not book.is_empty:
            found.append(book)
            continue
        # No audio directly inside: treat it as an author folder.
        try:
            children = sorted(
                (child for child in entry.iterdir() if child.is_dir()),
                key=lambda child: natural_key(child.name),
            )
        except OSError:
            continue
        found.extend(
            book
            for book in (read_book(child, author=entry.name) for child in children)
            if not book.is_empty
        )
    return found


def next_chapter(book: DownloadedBook, current: Path | str) -> Chapter | None:
    """The chapter after *current*, or ``None`` at the end of the book."""
    position = book.index_of(current)
    if position < 0:
        return None
    return book.chapter_at(position + 1)


def book_for(path: Path | str, books_root: Path | str) -> DownloadedBook | None:
    """The book a playing file belongs to, if it is in the downloads folder.

    Asked of every finished track, so it reads the file's own folder rather than
    walking the whole library: a book is exactly the folder its chapters sit in,
    and that is one directory listing instead of a scan.
    """
    target = Path(path)
    try:
        root = Path(books_root).resolve()
        folder = target.parent.resolve()
        if root != folder and root not in folder.parents:
            return None
    except OSError:
        return None
    author = folder.parent.name if folder.parent != Path(books_root) else ""
    book = read_book(folder, author=author)
    return book if not book.is_empty else None
