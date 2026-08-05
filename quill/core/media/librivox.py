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
