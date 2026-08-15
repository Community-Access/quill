"""Accessible book libraries (plan xxx.md Part 4).

A small, shared provider layer for free/accessible ebook sources -- Project
Gutenberg (via the Gutendex API) and OPDS catalogues (Standard Ebooks, Feedbooks)
today, with additional eligibility-gated sources able to plug in behind
the same shapes later. It is pure domain logic (no wx): search returns
:class:`Book` records, and ``download`` returns bytes the caller writes to a file
and opens through ``quill.io.open_read.read_open_document`` -- so a downloaded
plain-text, EPUB, or DAISY book opens in QUILL's accessible reader directly.

Both the main-app Library feature and the social app's OPDS browse bridge consume
this one layer (the "build the multiplier once" decision, §4.4).
"""

from __future__ import annotations

from quill.core.library.model import (
    Book,
    LibraryError,
    LibraryHTTPError,
    LibraryParseError,
)
from quill.core.library.providers import (
    DEFAULT_SOURCES,
    FREE_SOURCES,
    download,
    download_to_path,
    search,
)
from quill.core.library.works import Work, group

__all__ = [
    "DEFAULT_SOURCES",
    "FREE_SOURCES",
    "Book",
    "LibraryError",
    "LibraryHTTPError",
    "LibraryParseError",
    "Work",
    "download",
    "download_to_path",
    "group",
    "search",
]
