"""The four-category rule: what can you actually do with this result?

A search across Gutenberg, Standard Ebooks, Open Library and the BARD catalogue
returns rows that look identical and behave completely differently. The category
is what removes the guesswork, so it has to be right for the awkward case: the
same provider returning both a full text and a record it can only point at.
"""

from __future__ import annotations

from quill.core.library.availability import (
    ACCOUNT_REQUIRED,
    CATALOG_RECORD,
    CATEGORY_LABELS,
    CATEGORY_SENTENCES,
    OPEN_NOW,
    PARTNER_REQUIRED,
    can_open_here,
    category,
    describe,
    label,
    summarise,
)
from quill.core.library.model import Book


def _book(source: str, **formats: str) -> Book:
    return Book(book_id="1", title="A Book", source=source, formats=dict(formats))


def test_a_record_with_a_download_is_open_now() -> None:
    assert category(_book("gutenberg", txt="u")) == OPEN_NOW
    assert can_open_here(_book("gutenberg", txt="u")) is True


def test_one_provider_can_return_both_kinds() -> None:
    # Open Library holds public-domain texts QUILL can fetch and records it can
    # only point at. A rule keyed on the source name gets one of those wrong
    # every single time, which is why the category reads the record instead.
    assert category(_book("openlibrary", txt="u")) == OPEN_NOW
    assert category(_book("openlibrary")) == CATALOG_RECORD


def test_bard_is_account_required_however_complete_the_record_looks() -> None:
    assert category(_book("bard")) == ACCOUNT_REQUIRED
    assert "does not sign in for you" in describe(_book("bard"))


def test_every_category_has_a_short_label_and_a_full_sentence() -> None:
    for key in (OPEN_NOW, CATALOG_RECORD, ACCOUNT_REQUIRED, PARTNER_REQUIRED):
        assert CATEGORY_LABELS[key].strip()
        assert CATEGORY_SENTENCES[key].endswith(".")


def test_the_label_is_the_phrase_a_row_speaks() -> None:
    assert label(_book("gutenberg", epub="u")) == "open now"
    assert label(_book("openlibrary")) == "catalog record"


def test_a_summary_counts_by_category_rather_than_totalling() -> None:
    said = summarise([_book("gutenberg", txt="u"), _book("bard"), _book("openlibrary")])
    assert said.startswith("3 results:")
    assert "1 open now" in said
    assert "1 account required" in said
    assert summarise([]) == "Nothing found."
