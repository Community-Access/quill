"""Open Library: the catalogue that knows a book exists.

The one thing this must not get wrong is the rights call. Open Library serves
public-domain scans and borrowable modern books through the same field shapes,
and treating a borrowable scan as a free full text would be QUILL claiming a
right nobody granted.
"""

from __future__ import annotations

import json

import pytest

from quill.core.library.model import LibraryParseError
from quill.core.library.openlibrary import parse_results, search, search_url

_PAYLOAD = json.dumps({
    "docs": [
        {
            "key": "/works/OL1234W",
            "title": "Middlemarch",
            "author_name": ["George Eliot"],
            "language": ["eng"],
            "subject": ["Fiction", "England"],
            "ia": ["middlemarch00elio"],
            "public_scan_b": True,
        },
        {
            "key": "/works/OL999W",
            "title": "A Borrowable Modern Novel",
            "author_name": ["Someone Living"],
            "ia": ["borrowable00some"],
            "public_scan_b": False,
            "ebook_access": "borrowable",
        },
        {"title": "No key, so no record"},
    ]
})


def test_a_public_domain_scan_becomes_something_QUILL_can_open() -> None:
    book = parse_results(_PAYLOAD)[0]
    assert book.title == "Middlemarch"
    assert book.formats["txt"].endswith("middlemarch00elio_djvu.txt")
    assert book.site_url == "https://openlibrary.org/works/OL1234W"


def test_a_borrowable_book_is_a_record_and_not_a_download() -> None:
    # Reproducing controlled digital lending here would be a worse version of
    # their own site with more ways to fail -- and offering the scan as a free
    # text would be worse than that.
    book = parse_results(_PAYLOAD)[1]
    assert book.formats == {}
    assert book.site_url


def test_a_record_with_no_key_is_dropped_rather_than_half_built() -> None:
    assert len(parse_results(_PAYLOAD)) == 2


def test_the_request_asks_only_for_the_fields_it_uses() -> None:
    # The default record is very large, and asking for all of it on every search
    # is a cost somebody else pays for.
    url = search_url("middlemarch", limit=5)
    assert "fields=" in url and "public_scan_b" in url
    assert "limit=5" in url
    assert url.startswith("https://openlibrary.org/search.json?")


@pytest.mark.parametrize("junk", ["", "not json", "[]", "{}", '{"docs": "nope"}'])
def test_a_broken_response_is_empty_or_a_named_error(junk: str) -> None:
    try:
        assert parse_results(junk) == []
    except LibraryParseError:
        pass  # named, coded, and speakable -- also acceptable


def test_an_empty_query_never_reaches_the_network() -> None:
    calls: list[str] = []
    assert search("  ", fetch=lambda url: calls.append(url) or b"{}") == []
    assert calls == []
