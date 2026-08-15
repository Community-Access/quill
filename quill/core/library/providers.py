"""Search + download facade over the library sources (plan xxx.md 4.2).

One entry point the UI calls: :func:`search` across enabled sources and
:func:`download` for a chosen book/format. The returned bytes are written to a
file and opened via ``quill.io.open_read.read_open_document`` -- so a plain-text
or EPUB book opens in QUILL's accessible reader with no new reader code.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from quill.core.library import (
    bard,
    googlebooks,
    gutendex,
    internet_archive_books,
    opds,
    openlibrary,
)
from quill.core.library.model import Book, LibraryError

# Format key -> file extension, so a downloaded book opens by suffix in
# quill.io.open_read.read_open_document (txt/epub/html/pdf all handled there).
_FORMAT_EXT = {"txt": ".txt", "epub": ".epub", "html": ".html", "pdf": ".pdf", "mobi": ".mobi"}

Fetch = Callable[[str], bytes]

# Free, no-auth sources searchable by keyword today.
DEFAULT_SOURCES: tuple[str, ...] = ("gutenberg",)

#: Everything the hub can search without an account, in the order it is worth
#: searching: the sources that can hand you the book first, the ones that can
#: only tell you it exists last. Order is a ranking here -- results keep it
#: (see ``works.group``), so the openable answers arrive at the top of the list.
FREE_SOURCES: tuple[str, ...] = (
    "gutenberg",
    "standard-ebooks",
    "librivox",
    "openlibrary",
    "googlebooks",
    "archive",
    "bard",
)

# OPDS browse catalogues (public-domain libraries). Browsed via opds.catalog();
# large "all" feeds are for listing, then filtered locally by title.
OPDS_CATALOGS: dict[str, str] = {
    "standard-ebooks": "https://standardebooks.org/feeds/opds/all",
    "feedbooks": "https://catalog.feedbooks.com/catalog/public_domain.atom",
}


def _as_post_fetch(fetch: Fetch | None) -> bard.Fetch | None:
    """Adapt the shared GET-style ``fetch`` (URL-only, used by tests) to BARD's
    ``(url, body)`` signature by ignoring the body. ``None`` in production lets
    BARD use its own default POST fetch."""
    if fetch is None:
        return None
    return lambda url, _body: fetch(url)


def _dedupe_key(book: Book) -> tuple[str, str]:
    """A title+first-author identity for merging the same book across sources."""
    author = book.authors[0].strip().lower() if book.authors else ""
    return (book.title.strip().lower(), author)


def _merge_formats(keep: Book, extra: Book) -> Book:
    """Fold ``extra``'s download formats into ``keep`` (kept source wins ties)."""
    if not extra.formats:
        return keep
    merged = {**extra.formats, **keep.formats}  # keep's URLs take precedence
    if merged == dict(keep.formats):
        return keep
    return replace(keep, formats=merged)


def dedupe_books(books: list[Book]) -> list[Book]:
    """Merge duplicate titles across sources, unioning their download formats.

    The first occurrence sets identity/metadata; later duplicates only contribute
    any download formats the first lacked. Order is otherwise preserved.
    """
    seen: dict[tuple[str, str], int] = {}
    out: list[Book] = []
    for book in books:
        key = _dedupe_key(book)
        if key in seen:
            out[seen[key]] = _merge_formats(out[seen[key]], book)
        else:
            seen[key] = len(out)
            out.append(book)
    return out


def search(
    query: str,
    *,
    sources: tuple[str, ...] = DEFAULT_SOURCES,
    fetch: Fetch | None = None,
    limit: int = 20,
    safe_mode: bool = False,
    dedupe: bool = True,
    catalogs: dict[str, str] | None = None,
) -> list[Book]:
    """Search the enabled sources for ``query``; merge, dedupe, and cap results.

    *catalogs* is ``{id: url}`` for the OPDS catalogues to consider, which is how
    a catalogue somebody added themselves (``catalogs.py``) becomes searchable
    without this module knowing it exists. Omitted, only the built-ins are known.
    """
    catalog_urls = {**OPDS_CATALOGS, **(catalogs or {})}
    results: list[Book] = []
    for source in sources:
        if source == "gutenberg":
            results.extend(gutendex.search(query, fetch=fetch, limit=limit, safe_mode=safe_mode))
        elif source == "googlebooks":
            results.extend(googlebooks.search(query, fetch=fetch, limit=limit, safe_mode=safe_mode))
        elif source == "openlibrary":
            # The bibliographic layer: it knows a book exists even when none of
            # the free libraries hold it, and its public-domain records carry a
            # real full text.
            results.extend(openlibrary.search(query, fetch=fetch, limit=limit, safe_mode=safe_mode))
        elif source == "archive":
            # Last, and narrowest: the Archive's text side mixes public-domain
            # scans with borrow-controlled books, so its rights rule throws away
            # a great many real results on purpose (internet_archive_books.py).
            results.extend(
                internet_archive_books.search(query, fetch=fetch, limit=limit, safe_mode=safe_mode)
            )
        elif source == "librivox":
            results.extend(_librivox_books(query, fetch=fetch, limit=limit, safe_mode=safe_mode))
        elif source == "bard":
            # NLS BARD public catalogue (metadata only; POST search endpoint).
            results.extend(
                bard.search(query, fetch=_as_post_fetch(fetch), limit=limit, safe_mode=safe_mode)
            )
        elif source in catalog_urls:
            # OPDS "all" feeds have no server-side search; filter titles locally.
            books = opds.catalog(catalog_urls[source], fetch=fetch, safe_mode=safe_mode)
            q = query.lower()
            results.extend(b for b in books if q in b.title.lower())
    if dedupe:
        results = dedupe_books(results)
    return results[:limit] if limit else results


def _librivox_books(query: str, *, fetch: Fetch | None, limit: int, safe_mode: bool) -> list[Book]:
    """LibriVox recordings as library results -- the listening half of the hub.

    A failure here is *no recordings*, not a failed search: LibriVox being slow
    must not cost somebody the Gutenberg text that was found alongside it.
    """
    from quill.core.library import audio_sources
    from quill.core.library.http import refuse_in_safe_mode
    from quill.core.media import librivox

    refuse_in_safe_mode(safe_mode)
    try:
        found = librivox.search(query, limit=limit, fetch=fetch)
    except Exception:  # noqa: BLE001 - one slow catalogue must not fail the search
        return []
    return audio_sources.from_librivox_books(found)


def download(
    book: Book,
    fmt: str = "",
    *,
    fetch: Fetch | None = None,
    safe_mode: bool = False,
) -> bytes:
    """Download a book's chosen (or best-available) format as bytes."""
    from quill.core.library.http import fetch_bytes

    resolved = book.resolve(fmt) if fmt else book.resolve()
    if resolved is None:
        raise LibraryError(f"No downloadable format for {book.title!r}.")
    do_fetch = fetch or (lambda u: fetch_bytes(u, safe_mode=safe_mode))
    return do_fetch(resolved[1])


def _safe_filename(title: str) -> str:
    name = re.sub(r"[^\w\- ]+", "", title).strip() or "book"
    return name[:80]


def download_to_path(
    book: Book,
    dest_dir: Path | str,
    fmt: str = "",
    *,
    fetch: Fetch | None = None,
    safe_mode: bool = False,
) -> Path:
    """Download a book into ``dest_dir`` and return the file path.

    The extension matches the downloaded format, so the caller can hand the path
    straight to ``quill.io.open_read.read_open_document`` and the book opens in
    QUILL's accessible reader (plain text and EPUB natively).
    """
    from quill.core.library.http import fetch_bytes

    resolved = book.resolve(fmt) if fmt else book.resolve()
    if resolved is None:
        raise LibraryError(f"No downloadable format for {book.title!r}.")
    fmt_key, url = resolved
    do_fetch = fetch or (lambda u: fetch_bytes(u, safe_mode=safe_mode))
    data = do_fetch(url)
    directory = Path(dest_dir)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{_safe_filename(book.title)}{_FORMAT_EXT.get(fmt_key, '.txt')}"
    path.write_bytes(data)
    return path
