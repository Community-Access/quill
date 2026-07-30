"""Project Gutenberg search via the Gutendex API (plan xxx.md 4.1).

Gutendex is a free JSON API (no key) over Project Gutenberg's ~75k public-domain
books; each result lists download URLs per MIME type -- plain text, EPUB, HTML --
all of which open natively in QUILL's reader. Parsing is separated from fetching
so it is unit-testable with fixture JSON.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from urllib.parse import quote

from quill.core.library.http import fetch_bytes
from quill.core.library.model import Book, LibraryParseError

Fetch = Callable[[str], bytes]

_MIME_TO_FMT = {
    "text/plain": "txt",
    "application/epub+zip": "epub",
    "text/html": "html",
    "application/x-mobipocket-ebook": "mobi",
    "application/pdf": "pdf",
}


def _fmt_for(mime: str) -> str | None:
    base = mime.split(";", 1)[0].strip().lower()
    return _MIME_TO_FMT.get(base)


def _book_from_result(result: dict) -> Book:
    formats: dict[str, str] = {}
    for mime, url in (result.get("formats") or {}).items():
        fmt = _fmt_for(str(mime))
        # Skip archive bundles; keep the first readable URL per format.
        if fmt and url and not str(url).endswith(".zip"):
            formats.setdefault(fmt, str(url))
    authors = tuple(a.get("name", "") for a in (result.get("authors") or []) if a.get("name"))
    languages = result.get("languages") or []
    return Book(
        book_id=f"gutenberg:{result.get('id')}",
        title=result.get("title") or "(untitled)",
        authors=authors,
        source="gutenberg",
        language=languages[0] if languages else "",
        site_url=formats.get("html", ""),
        subjects=tuple(result.get("subjects") or [])[:8],
        formats=formats,
    )


def parse_search(raw: bytes) -> list[Book]:
    """Parse a Gutendex ``/books`` JSON response into books."""
    try:
        data = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise LibraryParseError(f"Gutendex response was not JSON: {exc}") from exc
    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list):
        return []
    return [_book_from_result(r) for r in results if isinstance(r, dict)]


def search(
    query: str,
    *,
    fetch: Fetch | None = None,
    limit: int = 20,
    safe_mode: bool = False,
) -> list[Book]:
    """Search Project Gutenberg for ``query`` and return up to ``limit`` books."""
    do_fetch = fetch or (lambda u: fetch_bytes(u, safe_mode=safe_mode))
    url = f"https://gutendex.com/books?search={quote(query)}"
    books = parse_search(do_fetch(url))
    return books[:limit] if limit else books
