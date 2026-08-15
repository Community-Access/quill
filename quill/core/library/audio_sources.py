"""The listening half of the hub: recordings as library results.

Quill Radio finds the LibriVox recording. The Library finds the Gutenberg text.
Until now those two never met, so *Middlemarch* was two searches in two places
and nothing in QUILL knew they were the same book.

This is the join. A :class:`~quill.core.media.librivox.LibriVoxBook` becomes an
ordinary :class:`~quill.core.library.model.Book` carrying one ``audio`` format,
which is all :mod:`quill.core.library.works` needs to group it with the text and
say **read or listen** on one row.

**One format, not one per chapter.** A LibriVox book is dozens of section files,
and a result list that offers dozens of links has buried the book. The record
carries the first section as its playable address and its own catalogue page as
``site_url``; playing the whole thing in order is Quill Radio's job, and it
already does it well.

**Nothing is re-hosted and nothing is re-encoded.** These are the publishers'
own URLs, fetched only when somebody asks.

wx-free, strict-typed, pure. The network lives in the provider modules this
converts *from*, never here.
"""

from __future__ import annotations

from quill.core.library.model import Book
from quill.core.media.librivox import LibriVoxBook

#: LibriVox publishes authors as one already-formatted string ("Eliot, George").
#: Split on the separator it actually uses rather than guessing at names.
_AUTHOR_SEPARATOR = ";"

_CATALOGUE_URL = "https://librivox.org/api/feed/audiobooks/?id={book_id}"


def _authors(raw: str) -> tuple[str, ...]:
    parts = [part.strip() for part in (raw or "").split(_AUTHOR_SEPARATOR)]
    return tuple(part for part in parts if part)


def from_librivox(book: LibriVoxBook) -> Book:
    """One LibriVox audiobook as a library result.

    A book with no playable section is still returned, as a catalogue record:
    LibriVox occasionally lists a work whose files have moved, and "we know this
    recording exists" is a better answer than dropping it silently.
    """
    formats: dict[str, str] = {}
    first = next((section for section in book.sections if section.url), None)
    if first is not None:
        formats["audio"] = first.url
    return Book(
        book_id=f"librivox:{book.book_id}",
        title=book.title,
        authors=_authors(book.authors),
        source="librivox",
        site_url=_CATALOGUE_URL.format(book_id=book.book_id),
        formats=formats,
    )


def from_librivox_books(books: list[LibriVoxBook]) -> list[Book]:
    """Every LibriVox result as a library result, in the order given."""
    return [from_librivox(book) for book in books]
