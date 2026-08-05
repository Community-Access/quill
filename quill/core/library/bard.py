"""NLS BARD public catalogue search (plan xxx.md Part 4).

The National Library Service for the Blind and Print Disabled (NLS), part of the
Library of Congress, publishes a free, no-key public API over the metadata of the
BARD collection. This provider issues a keyword search and maps each catalogue
record to a :class:`Book`.

BARD results are **metadata only** — they carry no in-app download. Obtaining a
title requires an eligible BARD patron account and is done on the BARD website, so
each result instead links to its official BARD / Library of Congress landing page
via ``site_url`` (a stable ``hdl.loc.gov`` handle). The Library dialog surfaces an
"Open in BARD" action for that link. No key or credential is ever sent.

The search endpoint is an HTTP ``POST`` with a JSON body, so parsing is separated
from fetching (unit-testable with fixture JSON) and the injected fetch takes the
request body alongside the URL.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable

from quill.core.library.http import fetch_bytes
from quill.core.library.model import Book, LibraryParseError

# BARD search POSTs a JSON body, so the injected fetch takes (url, body) rather
# than the URL-only ``Callable[[str], bytes]`` the GET-based providers use.
Fetch = Callable[[str, bytes], bytes]

_SEARCH_URL = "https://api.nlsbard.loc.gov/search/"
_HANDLE_PREFIX = "http://hdl.loc.gov/loc.nls/"
_ID_RE = re.compile(r"^([A-Za-z]+)(\d+)$")


def _query_body(query: str, limit: int) -> bytes:
    """Build the BARD ``POST /search/`` JSON body for a keyword search."""
    payload = {
        "terms": [{"field": "searchText", "term": [query]}],
        "pagination": {"count": limit if limit else 50, "offset": 0},
        "resultFormat": "normal",
    }
    return json.dumps(payload).encode("utf-8")


def _texts(value: object) -> list[str]:
    """Flatten a BARD metadata field into a list of plain strings.

    BARD text fields are often language-tagged objects such as
    ``{"value": "Sunset pass", "language": "en"}`` where ``value`` may itself be
    a string or a list of strings; other fields are plain strings or lists.
    Normalize them all to a flat list of non-empty strings.
    """
    out: list[str] = []
    items = value if isinstance(value, list) else [value]
    for item in items:
        inner = item.get("value") if isinstance(item, dict) else item
        if isinstance(inner, list):
            out.extend(str(x) for x in inner if x)
        elif inner:
            out.append(str(inner))
    return out


def _first(value: object) -> str:
    texts = _texts(value)
    return texts[0] if texts else ""


def _site_url(details: dict, book_id: str) -> str:
    """The stable BARD / Library of Congress landing page for a title.

    Prefer the record's own persistent handle URL; otherwise construct it from
    the book number (e.g. ``DB55555`` -> ``.../loc.nls/db.55555``).
    """
    urls = _texts(details.get("urls"))
    if urls:
        return urls[0]
    match = _ID_RE.match(book_id)
    if match:
        return f"{_HANDLE_PREFIX}{match.group(1).lower()}.{match.group(2)}"
    return ""


def _book_from_result(result: dict) -> Book:
    book_id = str(result.get("id") or "")
    raw_details = result.get("details")
    details: dict = raw_details if isinstance(raw_details, dict) else {}
    title = (
        _first(details.get("titles"))
        or str(details.get("titleFull") or "")
        or str(details.get("titleShort") or "")
        or "(untitled)"
    )
    language = str(details.get("primaryLanguageCode") or "")
    if not language:
        langs = _texts(details.get("languages"))
        language = langs[0] if langs else ""
    return Book(
        book_id=f"bard:{book_id}",
        title=title,
        authors=tuple(_texts(details.get("authors"))),
        source="bard",
        language=language,
        site_url=_site_url(details, book_id),
        subjects=tuple(_texts(details.get("subjects"))[:8]),
        formats={},  # metadata only: obtain from BARD via site_url (sign-in required)
    )


def parse_search(raw: bytes) -> list[Book]:
    """Parse a BARD ``POST /search/`` JSON response into books."""
    try:
        data = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise LibraryParseError(f"BARD response was not JSON: {exc}") from exc
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
    """Search the NLS BARD public catalogue for ``query`` (metadata only)."""
    do_fetch = fetch or (
        lambda u, b: fetch_bytes(
            u,
            body=b,
            content_type="application/json",
            accept="application/json",
            safe_mode=safe_mode,
        )
    )
    books = parse_search(do_fetch(_SEARCH_URL, _query_body(query, limit)))
    return books[:limit] if limit else books
