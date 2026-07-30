"""Book records and coded errors for the library layer (plan xxx.md Part 4)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import ClassVar

from quill.core.error_codes import CodedError

# Normalized download-format keys. Order = default download preference: plain
# text and EPUB open natively and accessibly in QUILL's reader; PDF last.
FORMAT_PREFERENCE: tuple[str, ...] = ("txt", "epub", "html", "mobi", "pdf")


class LibraryError(CodedError):
    """A library operation failed."""

    code: ClassVar[str] = "QUILL-LIBRARY-GENERAL"


class LibraryHTTPError(LibraryError):
    """A library network fetch failed (unreachable, refused, bad status)."""

    code: ClassVar[str] = "QUILL-LIBRARY-HTTP"


class LibraryParseError(LibraryError):
    """A catalogue response could not be parsed."""

    code: ClassVar[str] = "QUILL-LIBRARY-PARSE"


@dataclass(frozen=True)
class Book:
    """One catalogue result and where to download each of its formats."""

    book_id: str
    title: str
    authors: tuple[str, ...] = ()
    source: str = ""  # gutenberg | standard-ebooks | feedbooks | ...
    language: str = ""
    site_url: str = ""
    subjects: tuple[str, ...] = ()
    formats: Mapping[str, str] = field(default_factory=dict)  # format key -> url

    @property
    def authors_label(self) -> str:
        return ", ".join(self.authors) if self.authors else "Unknown author"

    def resolve(self, *prefer: str) -> tuple[str, str] | None:
        """The best ``(format_key, url)`` honoring ``prefer`` then default order."""
        for fmt in (*prefer, *FORMAT_PREFERENCE):
            url = self.formats.get(fmt)
            if url:
                return fmt, url
        for fmt, url in self.formats.items():
            if url:
                return fmt, url
        return None

    def download_url(self, *prefer: str) -> str | None:
        """The best download URL, honoring ``prefer`` then the default order."""
        resolved = self.resolve(*prefer)
        return resolved[1] if resolved else None
