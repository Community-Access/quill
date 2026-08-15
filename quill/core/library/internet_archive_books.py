"""The Internet Archive's text side, and the rule that makes it safe to search.

Quill Radio already browses the Archive for audio. Its *book* side is a very
different proposition, and the reason this was the last piece of the libraries
programme rather than the first: one search returns public-domain scans,
community uploads, borrow-controlled modern books under controlled digital
lending, and items whose rights fields say nothing at all -- and they look
identical in a result list.

So the rule here is deliberately narrow, and it is a rule about **rights**, not
about relevance:

1. **Texts only.** ``mediatype:texts``; the audio side is Quill Radio's and
   LibriVox's, and mixing them here would duplicate both.
2. **Nothing borrow-controlled, ever.** ``access-restricted-item`` marks an item
   lent one copy at a time through Archive's own reader. QUILL neither
   implements that nor pretends to, so such an item is not returned at all --
   not even as a catalog record, because a row somebody has to be told they
   cannot have is worse than a row that is not there.
3. **An explicit open signal is required.** A public-domain or Creative Commons
   ``licenseurl``, a ``rights`` field that says public domain, or membership of
   an allowlisted collection whose whole contents are public domain. Anything
   else -- including the enormous middle ground of community uploads with empty
   rights fields -- is skipped. **Never assume a downloadable-looking file may
   be redistributed.**

That rule throws away a great many real results. That is the intended trade: the
alternative is a list where some rows are lawful to download and some are not,
distinguishable only by reading a page on another site.

**On the download address.** Archive derives a plain-text version of a scanned
book at ``<identifier>_djvu.txt``, which is its own long-standing convention and
the same address Open Library links to. It is a convention rather than a
guarantee: an item without that derivative yields a failed download with a clear
message, never the wrong book. Plain text is offered rather than the PDF because
it is what reads properly in a screen reader.

Parsing is separated from fetching so it is unit-testable with fixture JSON, and
every call funnels through the library layer's single egress site
(:func:`quill.core.library.http.fetch_bytes`) -- no new outbound site (GATE-9).

wx-free, strict-typed.
"""

from __future__ import annotations

import json
import urllib.parse
from collections.abc import Callable

from quill.core.library.model import Book, LibraryParseError

Fetch = Callable[[str], bytes]

_SEARCH_URL = "https://archive.org/advancedsearch.php"
_DETAILS_URL = "https://archive.org/details/{identifier}"
_TEXT_URL = "https://archive.org/download/{identifier}/{identifier}_djvu.txt"

#: Collections whose entire contents are public domain or openly licensed, so
#: membership alone is a sufficient signal. Kept short on purpose: every entry
#: is a claim this code is making on somebody's behalf, and a collection added
#: casually is how a rights rule stops meaning anything.
SAFE_COLLECTIONS: frozenset[str] = frozenset({
    "gutenberg",  # Project Gutenberg's own mirror
    "opensource",  # uploader-declared open licences, always with a licenseurl
    "cdl",  # excluded below by access-restricted-item; listed so it is visible
    "americana",  # American Libraries: pre-1929 scans
    "toronto",  # University of Toronto: pre-1929 scans
    "JSTOR_ealy_journal_content",  # early journal content, public domain
})

#: ``access-restricted-item`` values that mean controlled digital lending.
_RESTRICTED_VALUES: frozenset[str] = frozenset({"true", "yes", "1"})

#: Substrings in ``licenseurl`` / ``rights`` that are an explicit open signal.
_OPEN_SIGNALS: tuple[str, ...] = (
    "creativecommons.org",
    "publicdomain",
    "public domain",
    "cc0",
    "no known copyright",
)

_FIELDS = (
    "identifier",
    "title",
    "creator",
    "year",
    "language",
    "subject",
    "licenseurl",
    "rights",
    "access-restricted-item",
    "collection",
)


def search_url(query: str, *, limit: int = 20) -> str:
    """The request this provider makes, exposed so tests can assert it.

    ``mediatype:texts`` is folded into the query rather than left to the caller:
    a search that could return an audio item would be a search that could return
    something this module's rights rule was never written for.
    """
    params = [("q", f"({query}) AND mediatype:texts"), ("output", "json")]
    params.extend(("fl[]", field) for field in _FIELDS)
    params.append(("rows", str(max(1, int(limit)))))
    params.append(("page", "1"))
    return f"{_SEARCH_URL}?{urllib.parse.urlencode(params)}"


def _first(value: object) -> str:
    """Archive returns some fields as a string and some as a list of one."""
    if isinstance(value, list):
        return str(value[0]).strip() if value else ""
    return str(value or "").strip()


def _all(value: object) -> tuple[str, ...]:
    if isinstance(value, list):
        return tuple(str(item).strip() for item in value if str(item).strip())
    text = str(value or "").strip()
    return (text,) if text else ()


def is_borrow_restricted(record: dict[str, object]) -> bool:
    """Whether this item is lent rather than given.

    Controlled digital lending: one copy, one reader, through Archive's own
    reader. QUILL does not implement that and must not imply it can.
    """
    return _first(record.get("access-restricted-item")).lower() in _RESTRICTED_VALUES


def has_open_signal(record: dict[str, object]) -> bool:
    """Whether the item *says* it is free to read, rather than merely looking it.

    An empty rights field is not an open signal. That is the whole rule: the
    Archive's middle ground of community uploads with no declared licence is
    exactly where a permissive reading would go wrong.
    """
    haystack = " ".join([
        _first(record.get("licenseurl")).lower(),
        _first(record.get("rights")).lower(),
    ])
    if any(signal in haystack for signal in _OPEN_SIGNALS):
        return True
    return bool(set(_all(record.get("collection"))) & SAFE_COLLECTIONS)


def is_safe(record: dict[str, object]) -> bool:
    """Whether QUILL may offer this item at all."""
    return not is_borrow_restricted(record) and has_open_signal(record)


def parse_results(json_text: str) -> list[Book]:
    """An advancedsearch payload as books QUILL may lawfully offer.

    Everything the rights rule rejects is dropped silently rather than returned
    as an unavailable row: a list where some entries exist only to be refused is
    a list that takes longer to read and helps less.
    """
    try:
        payload = json.loads(json_text)
    except (TypeError, ValueError) as error:
        raise LibraryParseError("The Internet Archive returned something unreadable.") from error
    response = payload.get("response") if isinstance(payload, dict) else None
    docs = response.get("docs") if isinstance(response, dict) else None
    if not isinstance(docs, list):
        return []

    books: list[Book] = []
    for record in docs:
        if not isinstance(record, dict):
            continue
        identifier = _first(record.get("identifier"))
        title = _first(record.get("title"))
        if not identifier or not title or not is_safe(record):
            continue
        books.append(
            Book(
                book_id=f"archive:{identifier}",
                title=title,
                authors=_all(record.get("creator")),
                source="archive",
                language=_first(record.get("language")),
                site_url=_DETAILS_URL.format(identifier=identifier),
                subjects=_all(record.get("subject"))[:8],
                formats={"txt": _TEXT_URL.format(identifier=identifier)},
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
    """Search the Archive's text side for *query*, rights rule applied."""
    text = str(query or "").strip()
    if not text:
        return []
    from quill.core.library.http import fetch_bytes

    do_fetch = fetch or (lambda url: fetch_bytes(url, safe_mode=safe_mode))
    raw = do_fetch(search_url(text, limit=limit))
    return parse_results(raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw)
