"""Linked documents: the links in show notes or a post that Scribe can take (PRD 8.6, 8.8).

QUILL Cast ("Convert Linked Document with Scribe for Documents..." on an
episode) and QUILL Social (the same on a post) both ask one question: which of
these links point straight at a file of one of the 23 types Scribe takes
(3.1)? A link to a web page, or one with no telling extension, is left out:
Scribe takes direct file links only, and a page behind a sign-in never works.

The rows are written for a list a screen reader reads (accessibility review,
2026-11-21): the link's own words first, so first-letter navigation works,
then the file and where it is; a link with no words of its own, or words that
only repeat the address or the file name, reads "Notes.pdf on example.org";
two rows that would read alike gain their file name.

wx-free.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from urllib.parse import unquote, urlsplit

from quill.core.scribe.inputs import ACCEPTED_EXTENSIONS
from quill.core.text_links import Link, links_in_html, links_in_text


@dataclass(frozen=True, slots=True)
class LinkedDocument:
    """A link that points straight at a file Scribe takes."""

    url: str
    text: str = ""

    @property
    def file_name(self) -> str:
        return unquote(PurePosixPath(urlsplit(self.url).path).name) or self.url

    @property
    def host(self) -> str:
        host = urlsplit(self.url).hostname or ""
        return host.removeprefix("www.")

    @property
    def plain(self) -> str:
        """``Notes.pdf on example.org``."""
        return f"{self.file_name} on {self.host}" if self.host else self.file_name


def is_document_link(url: str) -> bool:
    """True for an http(s) address whose path ends in a type Scribe takes."""
    parts = urlsplit(url or "")
    if parts.scheme.lower() not in ("http", "https") or not parts.hostname:
        return False
    return PurePosixPath(unquote(parts.path)).suffix.lower() in ACCEPTED_EXTENSIONS


def _words(link: Link) -> str:
    return " ".join((link.text or "").split())


def document_links(links: list[Link]) -> list[LinkedDocument]:
    """The links in *links* that Scribe can take, once each, in order."""
    seen: set[str] = set()
    found: list[LinkedDocument] = []
    for link in links:
        url = link.url.strip()
        key = url.rstrip("/").lower()
        if key in seen or not is_document_link(url):
            continue
        seen.add(key)
        found.append(LinkedDocument(url=url, text=_words(link)))
    return found


def documents_in_html(html: str) -> list[LinkedDocument]:
    """Show notes (HTML or text): the links Scribe can take."""
    return document_links(links_in_html(html or ""))


def documents_in_text(text: str, *extra: str) -> list[LinkedDocument]:
    """A post's text, plus any further addresses (its link, its media)."""
    links = links_in_text(text or "")
    links += [Link(url=url) for url in extra if url]
    return document_links(links)


def row_labels(documents: list[LinkedDocument]) -> list[str]:
    """One row per document, words first, alike rows told apart."""
    rows: list[str] = []
    for document in documents:
        words = document.text
        lowered = words.lower()
        if (
            not words
            or lowered.startswith(("http://", "https://", "www."))
            or lowered == document.file_name.lower()
        ):
            rows.append(document.plain)
        else:
            rows.append(f"{words} ({document.host})" if document.host else words)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row] = counts.get(row, 0) + 1
    result: list[str] = []
    for row, document in zip(rows, documents, strict=True):
        if counts[row] > 1 and document.plain != row:
            row = f"{row}, {document.file_name}"
        result.append(row)
    return result


def list_label(count: int, where: str) -> str:
    """The choice list's label, with its count: ``Linked documents in this post, 3:``."""
    return f"Linked documents in {where}, {count}:"


def none_sentence(subject: str, *, verb: str = "links") -> str:
    """``This post links no documents Scribe for Documents can convert.``"""
    from quill.core.scribe import PRODUCT_NAME

    return f"{subject[0].upper()}{subject[1:]} {verb} no documents {PRODUCT_NAME} can convert."


__all__ = [
    "LinkedDocument",
    "document_links",
    "documents_in_html",
    "documents_in_text",
    "is_document_link",
    "list_label",
    "none_sentence",
    "row_labels",
]
