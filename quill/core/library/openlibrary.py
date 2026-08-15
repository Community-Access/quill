"""Open Library search: the catalogue that knows what a book *is*.

Open Library is the bibliographic layer the rest of this hub was missing. The
other sources each know their own holdings; Open Library knows the work -- its
editions, its ISBNs, its subjects, and often that a public-domain full text
exists at all. That makes it useful for two jobs neither Gutenberg nor Standard
Ebooks can do:

* **Finding out that a book exists**, when the free sources have nothing under
  the title you typed.
* **Enriching a thin record** -- an author's full name, a first publication year,
  subjects -- for a result that arrived from somewhere with sparser metadata.

**No borrowing inside QUILL.** Open Library lends scanned modern books through a
controlled-digital-lending system with accounts, waitlists and DRM. Reproducing
any of that here would be building a worse version of their own site with more
ways to fail, so a lendable record is a **catalog record**
(:mod:`quill.core.library.availability`) and *Open in Browser* goes to their
page. Where a record is genuinely public domain and Internet Archive holds the
text, the record carries the archive identifier so the hub can say so.

**Cached and gentle.** Open Library asks for reasonable request volumes, so this
is a search-on-Enter provider -- never per keystroke -- and it asks for exactly
the fields it uses rather than the whole record.

Parsing is separated from fetching, so it is unit-testable with fixture JSON, and
every call funnels through the library layer's single egress site
(:func:`quill.core.library.http.fetch_bytes`) -- no new outbound site (GATE-9).

wx-free, strict-typed.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from urllib.parse import quote_plus

from quill.core.library.model import Book, LibraryParseError

Fetch = Callable[[str], bytes]

_SEARCH = "https://openlibrary.org/search.json"
_WORK_URL = "https://openlibrary.org{key}"

#: Only what is used. Open Library's default record is very large, and asking
#: for the whole thing on every search is a cost somebody else pays for.
_FIELDS = (
    "key",
    "title",
    "author_name",
    "first_publish_year",
    "language",
    "subject",
    "ia",
    "public_scan_b",
    "ebook_access",
)


def search_url(query: str, *, limit: int = 20) -> str:
    """The request this provider would make, exposed so tests can assert it."""
    fields = ",".join(_FIELDS)
    return f"{_SEARCH}?q={quote_plus(query)}&fields={fields}&limit={max(1, int(limit))}"


def _first_language(raw: object) -> str:
    if isinstance(raw, list) and raw:
        return str(raw[0])
    return str(raw or "")


def _is_public_domain(record: dict[str, object]) -> bool:
    """Whether Open Library says the full text is freely readable.

    ``public_scan_b`` is the honest signal; ``ebook_access`` of ``"public"``
    says the same thing in the newer field. Anything else -- borrowable,
    printdisabled, no ebook -- is **not** public domain, and treating a
    borrowable scan as one would be QUILL claiming a right nobody granted.
    """
    if bool(record.get("public_scan_b")):
        return True
    return str(record.get("ebook_access", "")).strip().lower() == "public"


def parse_results(json_text: str) -> list[Book]:
    """Open Library's ``search.json`` payload as :class:`Book` records.

    A record with no downloadable format is still returned: knowing a book
    exists, and where, is the job this provider is here for. It becomes a
    *catalog record* rather than being dropped.
    """
    try:
        payload = json.loads(json_text)
    except (TypeError, ValueError) as error:
        raise LibraryParseError("Open Library returned something unreadable.") from error
    docs = payload.get("docs") if isinstance(payload, dict) else None
    if not isinstance(docs, list):
        return []

    books: list[Book] = []
    for entry in docs:
        if not isinstance(entry, dict):
            continue
        title = str(entry.get("title", "")).strip()
        key = str(entry.get("key", "")).strip()
        if not title or not key:
            continue
        authors = tuple(
            str(name).strip() for name in (entry.get("author_name") or []) if str(name).strip()
        )
        subjects = tuple(
            str(subject).strip()
            for subject in (entry.get("subject") or [])[:8]
            if str(subject).strip()
        )
        formats: dict[str, str] = {}
        archive_ids = entry.get("ia")
        if _is_public_domain(entry) and isinstance(archive_ids, list) and archive_ids:
            # A public-domain scan the Internet Archive serves as full text.
            # Offered as one format rather than a shelf of derivatives: the
            # plain text is the one that reads well in a screen reader.
            identifier = str(archive_ids[0]).strip()
            if identifier:
                formats["txt"] = f"https://archive.org/download/{identifier}/{identifier}_djvu.txt"
        books.append(
            Book(
                book_id=key,
                title=title,
                authors=authors,
                source="openlibrary",
                language=_first_language(entry.get("language")),
                site_url=_WORK_URL.format(key=key),
                subjects=subjects,
                formats=formats,
            )
        )
    return books


def search(
    query: str,
    *,
    fetch: Fetch | None = None,
    limit: int = 20,
    safe_mode: bool = False,
) -> list[Book]:
    """Search Open Library for *query*."""
    text = str(query or "").strip()
    if not text:
        return []
    from quill.core.library.http import fetch_bytes

    do_fetch = fetch or (lambda url: fetch_bytes(url, safe_mode=safe_mode))
    raw = do_fetch(search_url(text, limit=limit))
    return parse_results(raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw)
