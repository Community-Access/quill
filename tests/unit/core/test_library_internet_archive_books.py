"""The Internet Archive's text side, and the rights rule that makes it safe.

One Archive search returns public-domain scans, community uploads with no
declared rights at all, and borrow-controlled modern books -- and they look
identical in a result list. Everything here is about the rule that decides which
of those QUILL is willing to offer.
"""

from __future__ import annotations

import json

import pytest

from quill.core.library.internet_archive_books import (
    SAFE_COLLECTIONS,
    has_open_signal,
    is_borrow_restricted,
    is_safe,
    parse_results,
    search,
    search_url,
)
from quill.core.library.model import LibraryParseError


def _payload(*docs: dict) -> str:
    return json.dumps({"response": {"docs": list(docs)}})


_PUBLIC = {
    "identifier": "pd1",
    "title": "A Public Domain Book",
    "creator": "Dickens, Charles",
    "licenseurl": "http://creativecommons.org/publicdomain/mark/1.0/",
}
_BORROWED = {
    "identifier": "lent",
    "title": "A Borrowed Modern Book",
    "access-restricted-item": "true",
    "licenseurl": "http://creativecommons.org/publicdomain/mark/1.0/",
}
_UNSTATED = {"identifier": "anon", "title": "Community Upload With No Rights Stated"}
_COLLECTION = {"identifier": "coll", "title": "A Scan", "collection": ["americana", "texts"]}


def test_a_borrow_controlled_book_is_never_offered() -> None:
    # QUILL does not implement controlled digital lending and must not imply it
    # can. Not even as a catalog record: a row somebody has to be told they
    # cannot have is worse than a row that is not there.
    assert is_borrow_restricted(_BORROWED) is True
    assert parse_results(_payload(_BORROWED)) == []


def test_an_empty_rights_field_is_not_an_open_signal() -> None:
    # The Archive's middle ground -- community uploads with nothing declared --
    # is exactly where a permissive reading would go wrong.
    assert has_open_signal(_UNSTATED) is False
    assert parse_results(_payload(_UNSTATED)) == []


def test_a_declared_public_domain_mark_is_enough() -> None:
    assert is_safe(_PUBLIC) is True
    book = parse_results(_payload(_PUBLIC))[0]
    assert book.title == "A Public Domain Book"
    assert book.source == "archive"
    assert book.authors == ("Dickens, Charles",)


def test_membership_of_an_allowlisted_collection_is_enough() -> None:
    assert has_open_signal(_COLLECTION) is True
    assert len(parse_results(_payload(_COLLECTION))) == 1


def test_the_allowlist_stays_short_enough_to_mean_something() -> None:
    # Every entry is a claim this code makes on somebody's behalf, and a
    # collection added casually is how a rights rule stops meaning anything.
    assert len(SAFE_COLLECTIONS) <= 10


@pytest.mark.parametrize(
    "rights",
    [
        "Public Domain",
        "no known copyright",
        "CC0 1.0",
        "https://creativecommons.org/licenses/by/4.0/",
    ],
)
def test_every_shape_of_open_signal_is_recognised(rights: str) -> None:
    assert has_open_signal({"rights": rights}) is True


def test_the_search_is_pinned_to_texts() -> None:
    # A search that could return an audio item would be one this module's
    # rights rule was never written for.
    url = search_url("dickens")
    assert "mediatype%3Atexts" in url
    assert url.startswith("https://archive.org/advancedsearch.php?")


def test_the_text_derivative_is_what_is_offered() -> None:
    # Plain text rather than the PDF: it is what reads properly in a screen
    # reader.
    book = parse_results(_payload(_PUBLIC))[0]
    assert set(book.formats) == {"txt"}
    assert book.formats["txt"].endswith("/pd1/pd1_djvu.txt")
    assert book.site_url.endswith("/details/pd1")


def test_a_record_with_no_identifier_is_dropped() -> None:
    assert parse_results(_payload({"title": "Nameless"})) == []


@pytest.mark.parametrize("junk", ["", "not json", "{}", '{"response": "nope"}'])
def test_a_broken_response_is_empty_or_a_named_error(junk: str) -> None:
    try:
        assert parse_results(junk) == []
    except LibraryParseError:
        pass


def test_an_empty_query_never_reaches_the_network() -> None:
    calls: list[str] = []
    assert search("   ", fetch=lambda url: calls.append(url) or b"{}") == []
    assert calls == []
