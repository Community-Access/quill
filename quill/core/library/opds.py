"""OPDS catalogue browsing (Standard Ebooks, Feedbooks) -- plan xxx.md 4.2.

OPDS is an Atom-based catalogue format many free libraries expose. One parser
covers several sources and doubles as the social app's "OPDS catalogs as browse
sources" bridge (§4.0). Parsing is separated from fetching and is XXE/DTD-guarded.
"""

from __future__ import annotations

from collections.abc import Callable
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

from quill.core import safe_xml
from quill.core.library.http import fetch_bytes
from quill.core.library.model import Book, LibraryParseError

Fetch = Callable[[str], bytes]

_ACQUISITION = "acquisition"  # opds acquisition link rel substring
_MIME_TO_FMT = {
    "application/epub+zip": "epub",
    "application/x-mobipocket-ebook": "mobi",
    "application/pdf": "pdf",
    "text/plain": "txt",
    "text/html": "html",
}


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _fmt_for(mime: str) -> str | None:
    return _MIME_TO_FMT.get(mime.split(";", 1)[0].strip().lower())


def _reject_dtd(raw: bytes) -> None:
    head = raw[:4096].lower()
    if b"<!doctype" in head or b"<!entity" in head:
        raise LibraryParseError("OPDS declares a DTD/entity; refused")


def _author_names(entry: ET.Element) -> tuple[str, ...]:
    names: list[str] = []
    for child in entry:
        if _local(child.tag) != "author":
            continue
        for sub in child:
            text = (sub.text or "").strip()
            if _local(sub.tag) == "name" and text:
                names.append(text)
    return tuple(names)


def _entry_to_book(entry: ET.Element, base_url: str) -> Book | None:
    title = ""
    book_id = ""
    language = ""
    site_url = ""
    formats: dict[str, str] = {}
    for child in entry:
        name = _local(child.tag)
        if name == "title":
            title = (child.text or "").strip()
        elif name == "id":
            book_id = (child.text or "").strip()
        elif name == "language":
            language = (child.text or "").strip()
        elif name == "link":
            rel = child.attrib.get("rel", "")
            href = child.attrib.get("href", "")
            mime = child.attrib.get("type", "")
            if not href:
                continue
            full = urljoin(base_url, href)
            if _ACQUISITION in rel:
                fmt = _fmt_for(mime)
                if fmt:
                    formats.setdefault(fmt, full)
            elif rel == "alternate" and not site_url:
                site_url = full
    if not title:
        return None
    return Book(
        book_id=book_id or f"opds:{title}",
        title=title,
        authors=_author_names(entry),
        source="opds",
        language=language,
        site_url=site_url,
        formats=formats,
    )


def parse_catalog(raw: bytes, *, base_url: str = "") -> list[Book]:
    """Parse an OPDS catalogue feed into books (relative links resolved)."""
    if not raw:
        return []
    _reject_dtd(raw)
    try:
        root = safe_xml.fromstring(raw)
    except ET.ParseError as exc:
        raise LibraryParseError(f"OPDS is not well-formed XML: {exc}") from exc
    out: list[Book] = []
    for entry in root:
        if _local(entry.tag) != "entry":
            continue
        book = _entry_to_book(entry, base_url)
        if book is not None:
            out.append(book)
    return out


def catalog(url: str, *, fetch: Fetch | None = None, safe_mode: bool = False) -> list[Book]:
    """Fetch and parse an OPDS catalogue URL into books."""
    do_fetch = fetch or (lambda u: fetch_bytes(u, safe_mode=safe_mode))
    return parse_catalog(do_fetch(url), base_url=url)
