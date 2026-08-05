"""Library provider layer: Gutendex + OPDS parsing, search, download, safety."""

from __future__ import annotations

import json

import pytest

from quill.core.library import bard, googlebooks, gutendex, opds, providers
from quill.core.library.http import fetch_bytes, refuse_in_safe_mode
from quill.core.library.model import (
    Book,
    LibraryError,
    LibraryHTTPError,
    LibraryParseError,
)

GUTENDEX = json.dumps({
    "results": [
        {
            "id": 1342,
            "title": "Pride and Prejudice",
            "authors": [{"name": "Austen, Jane"}],
            "languages": ["en"],
            "subjects": ["Love stories"],
            "formats": {
                "text/plain; charset=utf-8": "https://www.gutenberg.org/files/1342/1342-0.txt",
                "application/epub+zip": "https://www.gutenberg.org/ebooks/1342.epub.images",
                "text/html": "https://www.gutenberg.org/ebooks/1342",
                "application/octet-stream": "https://www.gutenberg.org/files/1342/1342.zip",
            },
        }
    ]
}).encode("utf-8")

OPDS = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:dc="http://purl.org/dc/terms/">
  <title>Standard Ebooks</title>
  <entry>
    <title>Frankenstein</title>
    <id>url:frankenstein</id>
    <author><name>Mary Shelley</name></author>
    <dc:language>en</dc:language>
    <link rel="http://opds-spec.org/acquisition"
          type="application/epub+zip" href="/ebooks/frankenstein.epub"/>
    <link rel="alternate" type="text/html" href="https://standardebooks.org/ebooks/frankenstein"/>
  </entry>
</feed>
"""


def test_gutendex_parse():
    books = gutendex.parse_search(GUTENDEX)
    assert len(books) == 1
    b = books[0]
    assert b.book_id == "gutenberg:1342"
    assert b.title == "Pride and Prejudice"
    assert b.authors == ("Austen, Jane",)
    assert b.language == "en"
    assert b.formats["txt"].endswith("1342-0.txt")
    assert b.formats["epub"].endswith(".epub.images")
    assert "zip" not in b.formats  # archive bundle skipped


def test_gutendex_search_uses_query():
    seen = {}

    def fake_fetch(url):
        seen["url"] = url
        return GUTENDEX

    books = gutendex.search("pride", fetch=fake_fetch)
    assert "gutendex.com/books?search=pride" in seen["url"]
    assert books[0].title == "Pride and Prejudice"


def test_opds_parse_and_resolve_relative():
    books = opds.parse_catalog(OPDS, base_url="https://standardebooks.org/feeds/opds/all")
    assert len(books) == 1
    b = books[0]
    assert b.title == "Frankenstein"
    assert b.authors == ("Mary Shelley",)
    # relative acquisition href resolved against the base URL
    assert b.formats["epub"] == "https://standardebooks.org/ebooks/frankenstein.epub"
    assert b.site_url == "https://standardebooks.org/ebooks/frankenstein"


def test_opds_rejects_dtd():
    hostile = b'<?xml version="1.0"?><!DOCTYPE feed [<!ENTITY x "y">]><feed></feed>'
    with pytest.raises(LibraryParseError):
        opds.parse_catalog(hostile)


GOOGLEBOOKS = json.dumps({
    "items": [
        {
            "id": "vol-1",
            "volumeInfo": {
                "title": "Moby-Dick",
                "authors": ["Herman Melville"],
                "language": "en",
                "infoLink": "https://books.google.com/books?id=vol-1",
                "categories": ["Fiction"],
            },
            "accessInfo": {
                "publicDomain": True,
                "epub": {
                    "isAvailable": True,
                    "downloadLink": "https://books.google.com/books/download/vol-1.epub",
                },
                "pdf": {"isAvailable": False},
            },
        },
        {
            "id": "vol-2",
            "volumeInfo": {"title": "In-Copyright Book", "authors": ["A. Writer"]},
            "accessInfo": {"epub": {"isAvailable": False}, "pdf": {"isAvailable": False}},
        },
    ]
}).encode("utf-8")


def test_googlebooks_parse_public_domain_and_metadata_only():
    books = googlebooks.parse_search(GOOGLEBOOKS)
    assert len(books) == 2
    pd, meta = books
    assert pd.book_id == "googlebooks:vol-1"
    assert pd.title == "Moby-Dick"
    assert pd.authors == ("Herman Melville",)
    assert pd.source == "googlebooks"
    assert pd.formats["epub"].endswith("vol-1.epub")  # downloadable
    assert "pdf" not in pd.formats  # not available
    # Metadata-only volume is still returned but has no download formats.
    assert meta.formats == {}


def test_googlebooks_search_builds_query_and_free_filter():
    seen = {}

    def fake_fetch(url):
        seen["url"] = url
        return GOOGLEBOOKS

    googlebooks.search("moby", fetch=fake_fetch, free_only=True)
    assert "googleapis.com/books/v1/volumes?q=moby" in seen["url"]
    assert "filter=free-ebooks" in seen["url"]


def test_provider_search_googlebooks():
    books = providers.search("moby", sources=("googlebooks",), fetch=lambda u: GOOGLEBOOKS)
    assert books and books[0].source == "googlebooks"


# NLS BARD public catalogue search: a POST /search/ response, metadata only.
BARD = json.dumps({
    "pagination": {"count": 2, "offset": 0, "totalResults": 2},
    "results": [
        {
            "id": "DB55555",
            "type": "book",
            "format": "audio",
            "details": {
                "titles": [{"value": "Sunset pass", "language": "en"}],
                "authors": [{"value": ["Grey, Zane"], "language": "en"}],
                "subjects": ["Romance", "Western Stories"],
                "primaryLanguageCode": "en",
                "urls": ["http://hdl.loc.gov/loc.nls/db.55555"],
            },
        },
        {
            "id": "BR12345",
            "type": "book",
            "format": "braille",
            "details": {
                "titles": [{"value": "A Braille Title", "language": "en"}],
                "authors": [{"value": ["Writer, A."], "language": "en"}],
                # no "urls" -> site_url is constructed from the book number
            },
        },
    ],
}).encode("utf-8")


def test_bard_parse():
    books = bard.parse_search(BARD)
    assert len(books) == 2
    audio, braille = books
    assert audio.book_id == "bard:DB55555"
    assert audio.title == "Sunset pass"
    assert audio.authors == ("Grey, Zane",)
    assert audio.source == "bard"
    assert audio.language == "en"
    assert audio.subjects == ("Romance", "Western Stories")
    assert audio.site_url == "http://hdl.loc.gov/loc.nls/db.55555"
    assert audio.formats == {}  # metadata only; obtained on the BARD site
    # When the record omits urls, site_url is built from the book number.
    assert braille.site_url == "http://hdl.loc.gov/loc.nls/br.12345"


def test_bard_search_posts_query_body():
    seen = {}

    def fake_fetch(url, body):
        seen["url"] = url
        seen["body"] = body
        return BARD

    books = bard.search("sunset", fetch=fake_fetch)
    assert seen["url"].endswith("/search/")
    payload = json.loads(seen["body"])
    assert payload["terms"][0]["field"] == "searchText"
    assert payload["terms"][0]["term"] == ["sunset"]
    assert books[0].title == "Sunset pass"


def test_provider_search_bard_metadata_only():
    books = providers.search("sunset", sources=("bard",), fetch=lambda u: BARD)
    assert books and books[0].source == "bard"
    assert books[0].formats == {}  # no in-app download; open on the BARD site
    assert books[0].site_url.startswith("http://hdl.loc.gov/loc.nls/")


def test_fetch_bytes_post_body_rejects_non_https_and_safe_mode():
    # BARD search POSTs a JSON body through fetch_bytes; the same guards apply.
    with pytest.raises(LibraryHTTPError):
        fetch_bytes("http://insecure.example/search", body=b"{}", content_type="application/json")
    with pytest.raises(LibraryHTTPError):
        fetch_bytes("https://api.nlsbard.loc.gov/search/", body=b"{}", safe_mode=True)


def test_feedbooks_catalog_registered():
    assert "feedbooks" in providers.OPDS_CATALOGS
    assert providers.OPDS_CATALOGS["feedbooks"].startswith("https://")


def test_dedupe_merges_same_title_across_sources():
    a = Book(
        book_id="gutenberg:1",
        title="Moby-Dick",
        authors=("Herman Melville",),
        source="gutenberg",
        formats={"txt": "https://g/1.txt"},
    )
    b = Book(
        book_id="googlebooks:x",
        title="moby-dick ",
        authors=("herman melville",),
        source="googlebooks",
        formats={"epub": "https://gb/x.epub"},
    )
    c = Book(book_id="gutenberg:2", title="Frankenstein", authors=("Mary Shelley",))
    merged = providers.dedupe_books([a, b, c])
    assert len(merged) == 2  # the two Moby-Dick rows collapsed
    moby = merged[0]
    assert moby.book_id == "gutenberg:1"  # first occurrence keeps identity
    # Formats from the duplicate were unioned in (txt from a, epub from b).
    assert moby.formats["txt"].endswith("1.txt")
    assert moby.formats["epub"].endswith("x.epub")


def test_search_dedupes_by_default():
    def fake_fetch(url):
        # gutendex and googlebooks both return "Moby-Dick" for the same query.
        return GUTENDEX if "gutendex" in url else GOOGLEBOOKS

    # Distinct titles here, but exercise the merged multi-source path + cap.
    books = providers.search("x", sources=("gutenberg", "googlebooks"), fetch=fake_fetch, limit=50)
    keys = [(b.title.lower(), b.authors) for b in books]
    assert len(keys) == len(set(keys))  # no duplicate title+author pairs survived


def test_provider_search_gutenberg():
    books = providers.search("pride", fetch=lambda u: GUTENDEX)
    assert books and books[0].source == "gutenberg"


def test_download_prefers_readable_format_and_returns_bytes():
    book = gutendex.parse_search(GUTENDEX)[0]
    captured = {}

    def fake_fetch(url):
        captured["url"] = url
        return b"BOOK TEXT"

    # Default preference picks plain text (opens natively in QUILL).
    data = providers.download(book, fetch=fake_fetch)
    assert data == b"BOOK TEXT"
    assert captured["url"].endswith("1342-0.txt")
    # Explicit epub preference overrides.
    providers.download(book, "epub", fetch=fake_fetch)
    assert captured["url"].endswith(".epub.images")


def test_download_without_any_format_raises():
    empty = Book(book_id="x", title="No formats")
    with pytest.raises(LibraryError):
        providers.download(empty, fetch=lambda u: b"")


def test_model_download_url_preference():
    b = Book(book_id="x", title="t", formats={"pdf": "p", "epub": "e", "txt": "t"})
    assert b.download_url() == "t"  # txt preferred
    assert b.download_url("pdf") == "p"  # explicit override
    assert b.authors_label == "Unknown author"


def test_http_rejects_non_https_and_safe_mode():
    with pytest.raises(LibraryHTTPError):
        fetch_bytes("http://insecure.example/book.txt")
    with pytest.raises(LibraryHTTPError):
        refuse_in_safe_mode(True)


def test_download_to_path_writes_file_with_correct_suffix(tmp_path):
    book = gutendex.parse_search(GUTENDEX)[0]
    path = providers.download_to_path(book, tmp_path, "epub", fetch=lambda u: b"EPUB BYTES")
    # Extension matches the format so read_open_document dispatches correctly.
    assert path.suffix == ".epub"
    assert path.read_bytes() == b"EPUB BYTES"
    assert path.parent == tmp_path
    # Default (no fmt) picks plain text.
    txt = providers.download_to_path(book, tmp_path, fetch=lambda u: b"PLAIN")
    assert txt.suffix == ".txt"


def test_resolve_returns_format_and_url():
    book = gutendex.parse_search(GUTENDEX)[0]
    fmt, url = book.resolve()
    assert fmt == "txt"
    assert url.endswith("1342-0.txt")


def test_error_codes_are_stamped():
    assert LibraryError.code.startswith("QUILL-LIBRARY")
    assert LibraryHTTPError.code == "QUILL-LIBRARY-HTTP"
    assert LibraryParseError.code == "QUILL-LIBRARY-PARSE"
    assert "[QUILL-LIBRARY-HTTP]" in str(LibraryHTTPError("boom"))
