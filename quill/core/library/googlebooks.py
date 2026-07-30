"""Google Books search via the public Books API (plan xxx.md 4.2).

The Books API is a free JSON endpoint (no key for basic keyword search) over
Google's very large catalogue. Most results are metadata-only, but public-domain
volumes expose EPUB/PDF download links in ``accessInfo`` -- both open natively in
QUILL's reader. Parsing is separated from fetching so it is unit-testable with
fixture JSON, and every network call funnels through the library's single egress
site (``http.fetch_bytes``) so no new outbound site is introduced (GATE-9).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from urllib.parse import quote

from quill.core.library.http import fetch_bytes
from quill.core.library.model import Book, LibraryParseError

Fetch = Callable[[str], bytes]

_API = "https://www.googleapis.com/books/v1/volumes"


def _download_formats(access: dict) -> dict[str, str]:
    """EPUB/PDF download links from an ``accessInfo`` block (public-domain only).

    A format is only offered when the API marks it available *and* gives a direct
    ``downloadLink``; otherwise the volume is metadata-only (still searchable, not
    downloadable).
    """
    formats: dict[str, str] = {}
    for key in ("epub", "pdf"):
        block = access.get(key)
        if isinstance(block, dict) and block.get("isAvailable"):
            link = block.get("downloadLink")
            if isinstance(link, str) and link.startswith("https://"):
                formats[key] = link
    return formats


def _book_from_item(item: dict) -> Book:
    info = item.get("volumeInfo") or {}
    access = item.get("accessInfo") or {}
    authors = tuple(a for a in (info.get("authors") or []) if isinstance(a, str) and a)
    return Book(
        book_id=f"googlebooks:{item.get('id', '')}",
        title=str(info.get("title") or "(untitled)"),
        authors=authors,
        source="googlebooks",
        language=str(info.get("language") or ""),
        site_url=str(info.get("infoLink") or info.get("previewLink") or ""),
        subjects=tuple(c for c in (info.get("categories") or []) if isinstance(c, str))[:8],
        formats=_download_formats(access if isinstance(access, dict) else {}),
    )


def parse_search(raw: bytes) -> list[Book]:
    """Parse a Books API ``/volumes`` JSON response into books."""
    try:
        data = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise LibraryParseError(f"Google Books response was not JSON: {exc}") from exc
    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    return [_book_from_item(it) for it in items if isinstance(it, dict)]


def search(
    query: str,
    *,
    fetch: Fetch | None = None,
    limit: int = 20,
    safe_mode: bool = False,
    free_only: bool = False,
) -> list[Book]:
    """Search Google Books for ``query`` and return up to ``limit`` books.

    ``free_only`` restricts to free ebooks (the ``filter=free-ebooks`` facet), so
    the results are the ones actually downloadable and readable in QUILL.
    """
    do_fetch = fetch or (lambda u: fetch_bytes(u, safe_mode=safe_mode))
    max_results = min(max(limit, 1), 40) if limit else 20
    url = f"{_API}?q={quote(query)}&maxResults={max_results}&country=US"
    if free_only:
        url += "&filter=free-ebooks"
    books = parse_search(do_fetch(url))
    return books[:limit] if limit else books
