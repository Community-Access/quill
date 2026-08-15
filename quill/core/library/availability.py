"""What can you actually do with this result? The four-category rule.

The Accessible Libraries programme's guiding rule, and the reason a hub that
searches several catalogues at once is usable at all: **every result lands in one
of four unmistakable categories, and says which.**

1. **Open now** -- QUILL can stream, read or download it directly.
2. **Public catalog record** -- QUILL can search it but must hand off access.
3. **Account required** -- you authenticate with the provider yourself.
4. **Partner integration required** -- QUILL would need an organizational
   agreement, which it does not have.

Why this matters more here than in most result lists: a search across Gutenberg,
Standard Ebooks, Open Library and the BARD catalogue returns rows that look
identical and behave completely differently. Pressing Enter on one opens a book;
on another it opens a web page; on a third it can do nothing at all. Sighted
users discover that difference by trying. **Announcing the category on the row
is what removes the guesswork**, and it is why the category is computed here --
from what the record actually carries -- rather than being a label a provider
adapter remembers to set.

Category 4 exists so that a closed collection can be *named and refused* rather
than silently omitted: "Learning Ally -- partner integration required" tells
somebody where the book is. Nothing in QUILL pursues those agreements, and no
category-4 source is searched today; the category is here so adding one later
cannot quietly present it as something it is not.

wx-free, strict-typed, pure.
"""

from __future__ import annotations

from quill.core.library.model import Book

OPEN_NOW = 1
CATALOG_RECORD = 2
ACCOUNT_REQUIRED = 3
PARTNER_REQUIRED = 4

#: The short phrase spoken on every row, after the title and author.
CATEGORY_LABELS: dict[int, str] = {
    OPEN_NOW: "open now",
    CATALOG_RECORD: "catalog record",
    ACCOUNT_REQUIRED: "account required",
    PARTNER_REQUIRED: "partner integration required",
}

#: The fuller sentence, for the details pane and the status line.
CATEGORY_SENTENCES: dict[int, str] = {
    OPEN_NOW: "QUILL can open this here.",
    CATALOG_RECORD: (
        "QUILL found this record but cannot open the book itself. "
        "Open in Browser goes to the library's own page for it."
    ),
    ACCOUNT_REQUIRED: (
        "This needs an account with the library that holds it. "
        "QUILL does not sign in for you; Open in Browser goes to their page."
    ),
    PARTNER_REQUIRED: (
        "This collection needs an agreement between QUILL and the organization "
        "that runs it, which does not exist. The record is shown so you know "
        "where the book is."
    ),
}

#: Sources whose records are metadata only, however complete they look. BARD's
#: public API searches the whole collection and downloads none of it: obtaining a
#: title needs an eligible patron account on their own site.
ACCOUNT_SOURCES: frozenset[str] = frozenset({"bard"})

#: Sources that would need an organizational agreement. Empty today, and
#: deliberately present: see the module docstring.
PARTNER_SOURCES: frozenset[str] = frozenset()


def category(book: Book) -> int:
    """Which of the four *book* is in.

    Decided by what the record carries, not by what its provider usually
    returns: Open Library holds both public-domain texts QUILL can fetch and
    records it can only point at, and a rule keyed on the source name would get
    one of those two wrong every time.
    """
    source = (book.source or "").strip().lower()
    if source in PARTNER_SOURCES:
        return PARTNER_REQUIRED
    if book.formats:
        return OPEN_NOW
    if source in ACCOUNT_SOURCES:
        return ACCOUNT_REQUIRED
    return CATALOG_RECORD


def label(book: Book) -> str:
    """The phrase for the row: "open now", "catalog record"..."""
    return CATEGORY_LABELS.get(category(book), CATEGORY_LABELS[CATALOG_RECORD])


def describe(book: Book) -> str:
    """The sentence for the details pane."""
    return CATEGORY_SENTENCES.get(category(book), CATEGORY_SENTENCES[CATALOG_RECORD])


def can_open_here(book: Book) -> bool:
    """Whether the Open button should do anything at all for *book*."""
    return category(book) == OPEN_NOW


def summarise(books: list[Book]) -> str:
    """One sentence over a whole result set, so a search says what it found.

    Counted by category rather than totalled, because "40 results" of which two
    are openable is a worse answer than the truth.
    """
    if not books:
        return "Nothing found."
    counts: dict[int, int] = {}
    for book in books:
        counts[category(book)] = counts.get(category(book), 0) + 1
    parts = [f"{counts[key]} {CATEGORY_LABELS[key]}" for key in sorted(counts) if counts.get(key)]
    total = len(books)
    return f"{total} result{'' if total == 1 else 's'}: {', '.join(parts)}."
