"""LibriVox audiobook provider (PRD Section 5 / Section 9.12 unified library).

A small, wx-free provider that searches the free LibriVox public catalog and
returns audiobooks with their per-section audio URLs, so the player can stream or
download them. Network access goes through the already-reviewed library egress
chokepoint (:func:`quill.core.library.http.fetch_bytes`, GATE-9), and the HTTP
call is injectable so the parsing is unit-tested with no network.

LibriVox is a public-domain audiobook library that requires no account.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.parse import quote

from quill.core.media.errors import MediaError

_API = "https://librivox.org/api/feed/audiobooks"

Fetch = Callable[[str], bytes]


class LibriVoxError(MediaError):
    """Raised when a LibriVox search cannot be completed or parsed."""

    code = "QUILL-MEDIA-LIBRIVOX-FAILED"


@dataclass(frozen=True, slots=True)
class LibriVoxSection:
    """One playable section (track) of a LibriVox book."""

    index: int
    title: str
    url: str


@dataclass(frozen=True, slots=True)
class LibriVoxBook:
    """A LibriVox audiobook and its sections."""

    book_id: str
    title: str
    authors: str = ""
    total_time: str = ""
    sections: tuple[LibriVoxSection, ...] = field(default_factory=tuple)

    @property
    def has_audio(self) -> bool:
        return any(section.url for section in self.sections)


def _default_fetch(url: str) -> bytes:
    from quill.core.library.http import fetch_bytes

    return fetch_bytes(url, accept="application/json")


def search(query: str, *, limit: int = 20, fetch: Fetch | None = None) -> list[LibriVoxBook]:
    """Search LibriVox by title and return matching audiobooks with sections.

    Raises :class:`LibriVoxError` on a transport or parse failure.
    """
    query = query.strip()
    if not query:
        return []
    fetcher = fetch or _default_fetch
    url = f"{_API}/?title=^{quote(query)}&format=json&extended=1&limit={max(1, int(limit))}"
    try:
        raw = fetcher(url)
    except Exception as exc:  # noqa: BLE001 - normalized to a coded error
        raise LibriVoxError(f"LibriVox search failed: {exc}") from exc
    return _parse_books(raw)


def _parse_books(raw: bytes | str) -> list[LibriVoxBook]:
    try:
        data = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise LibriVoxError(f"LibriVox returned unreadable data: {exc}") from exc
    if not isinstance(data, dict):
        return []
    books_raw = data.get("books", [])
    if not isinstance(books_raw, list):
        return []
    books: list[LibriVoxBook] = []
    for entry in books_raw:
        if isinstance(entry, dict):
            books.append(_parse_book(entry))
    return books


def _parse_book(entry: dict[str, object]) -> LibriVoxBook:
    sections: list[LibriVoxSection] = []
    raw_sections = entry.get("sections", [])
    if isinstance(raw_sections, list):
        for index, sec in enumerate(raw_sections):
            if not isinstance(sec, dict):
                continue
            url = str(sec.get("listen_url", "") or "")
            if not url:
                continue
            title = str(sec.get("title", "") or f"Section {index + 1}")
            sections.append(LibriVoxSection(index=index, title=title, url=url))
    return LibriVoxBook(
        book_id=str(entry.get("id", "") or ""),
        title=str(entry.get("title", "") or "Untitled"),
        authors=_format_authors(entry.get("authors", [])),
        total_time=str(entry.get("totaltime", "") or ""),
        sections=tuple(sections),
    )


def _format_authors(raw: object) -> str:
    if not isinstance(raw, list):
        return ""
    names = []
    for author in raw:
        if not isinstance(author, dict):
            continue
        first = str(author.get("first_name", "") or "").strip()
        last = str(author.get("last_name", "") or "").strip()
        full = f"{first} {last}".strip()
        if full:
            names.append(full)
    return ", ".join(names)


__all__ = ["Fetch", "LibriVoxBook", "LibriVoxError", "LibriVoxSection", "search"]


# --------------------------------------------------------------------------- #
# Browse axes (Quill Radio 3.x)
#
# `search` answers "find the book I can name". These answer "show me what there
# is", which is the question a browse tree exists for. Every filter below was
# checked against the live API on 2026-08-13 -- including the one that does not
# exist: there is no working `title` filter in any form (query string or path,
# with or without a caret), while `author`, `genre` and `since` all work. A
# By Title axis would have to be a client-side sort over paged results, and is
# deliberately not offered rather than offered and quietly returning nothing.
# --------------------------------------------------------------------------- #

#: Recently Added looks back this far. LibriVox publishes a few titles a day, so
#: a month is a browsable list rather than a firehose or an empty folder.
RECENT_WINDOW_SECONDS = 45 * 24 * 3600

#: The genres LibriVox actually files books under, in the order a listener is
#: likely to want them. The API filters by genre name but publishes no genre
#: *list* endpoint, so this is a curated constant -- the same pattern
#: ``core/radio/networks.py`` uses for its catalog. Refresh by hand if LibriVox
#: adds one; an unknown genre simply returns no books rather than erroring.
BROWSE_GENRES: tuple[str, ...] = (
    "Action & Adventure Fiction",
    "Antiquity",
    "Art, Design & Architecture",
    "Biography & Autobiography",
    "Children's Fiction",
    "Classics (Antiquity)",
    "Comedy",
    "Cooking",
    "Crime & Mystery Fiction",
    "Detective Fiction",
    "Dramatic Readings",
    "Epistolary Fiction",
    "Essays & Short Works",
    "Fantasy Fiction",
    "General Fiction",
    "Gothic Fiction",
    "Historical Fiction",
    "History",
    "Horror & Supernatural Fiction",
    "Humorous Fiction",
    "Literary Fiction",
    "Modern (19th C)",
    "Modern (20th C)",
    "Music",
    "Myths, Legends & Fairy Tales",
    "Nature",
    "Nautical & Marine Fiction",
    "Philosophy",
    "Plays",
    "Poetry",
    "Politics",
    "Psychology",
    "Religion",
    "Romance",
    "Sagas",
    "Satire",
    "Science",
    "Science Fiction",
    "Short Stories",
    "Travel & Geography",
    "War & Military Fiction",
    "Westerns",
    "Writing & Linguistics",
)

_AUTHORS_API = "https://librivox.org/api/feed/authors"


@dataclass(frozen=True, slots=True)
class LibriVoxAuthor:
    """One author from the catalog's author feed."""

    author_id: str
    first_name: str = ""
    last_name: str = ""

    @property
    def display_name(self) -> str:
        """ "Twain, Mark" -- surname first, because the browse list sorts by it."""
        if self.last_name and self.first_name:
            return f"{self.last_name}, {self.first_name}"
        return self.last_name or self.first_name or "Unknown"


def _books_url(**params: object) -> str:
    """A books-feed URL. ``extended=1`` is always on: without it a book arrives
    with no sections, and a book with no sections has nothing to play."""
    parts = ["format=json", "extended=1"]
    parts += [
        f"{key}={quote(str(value))}" for key, value in params.items() if value not in ("", None)
    ]
    return f"{_API}/?{'&'.join(parts)}"


def _fetch_books(url: str, fetch: Fetch | None) -> list[LibriVoxBook]:
    fetcher = fetch or _default_fetch
    try:
        raw = fetcher(url)
    except Exception as exc:  # noqa: BLE001 - normalized to a coded error
        raise LibriVoxError(f"LibriVox request failed: {exc}") from exc
    return _parse_books(raw)


def recent_books(*, limit: int = 60, fetch: Fetch | None = None) -> list[LibriVoxBook]:
    """Books added in the last few weeks, newest first."""
    import time

    since = int(time.time()) - RECENT_WINDOW_SECONDS
    return _fetch_books(_books_url(since=since, limit=max(1, int(limit))), fetch)


def books_by_genre(
    genre: str, *, limit: int = 60, fetch: Fetch | None = None
) -> list[LibriVoxBook]:
    """Books filed under *genre*."""
    if not genre.strip():
        return []
    return _fetch_books(_books_url(genre=genre.strip(), limit=max(1, int(limit))), fetch)


def books_by_author(
    author: str, *, limit: int = 60, fetch: Fetch | None = None
) -> list[LibriVoxBook]:
    """Books by *author* -- a surname, which is what the API matches on."""
    if not author.strip():
        return []
    return _fetch_books(_books_url(author=author.strip(), limit=max(1, int(limit))), fetch)


def parse_authors(raw: bytes | str) -> list[LibriVoxAuthor]:
    """Parse the author feed (pure). Authors with no name at all are dropped."""
    try:
        data = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise LibriVoxError(f"LibriVox returned unreadable data: {exc}") from exc
    rows = data.get("authors") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return []
    authors: list[LibriVoxAuthor] = []
    for entry in rows:
        if not isinstance(entry, dict):
            continue
        author = LibriVoxAuthor(
            author_id=str(entry.get("id", "") or ""),
            first_name=str(entry.get("first_name", "") or "").strip(),
            last_name=str(entry.get("last_name", "") or "").strip(),
        )
        if author.last_name or author.first_name:
            authors.append(author)
    return authors


def list_authors(*, limit: int = 2000, fetch: Fetch | None = None) -> list[LibriVoxAuthor]:
    """Every author in the catalog, surname-sorted.

    Around 7,200 of them, which is why the browse tree groups them A-Z rather
    than listing them flat.
    """
    fetcher = fetch or _default_fetch
    url = f"{_AUTHORS_API}/?format=json&limit={max(1, int(limit))}"
    try:
        raw = fetcher(url)
    except Exception as exc:  # noqa: BLE001
        raise LibriVoxError(f"LibriVox author list failed: {exc}") from exc
    authors = parse_authors(raw)
    authors.sort(key=lambda a: (a.last_name.casefold(), a.first_name.casefold()))
    return authors
