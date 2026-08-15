"""One book, several libraries -- and what the row says about it.

The failure this prevents is specific to listening: *Middlemarch* found in four
catalogues used to be four near-identical rows, each read out in full, differing
only in a source name near the end. Grouping is what makes the list navigable,
and the four-category label is what makes a mixed list safe to press Enter in.
"""

from __future__ import annotations

import pytest

from quill.core.library import availability
from quill.core.library.model import Book
from quill.core.library.works import (
    FILTERS,
    RECOMMENDED_NOTE,
    apply_filter,
    describe,
    group,
    normalise_author,
    normalise_title,
    source_name,
    summarise,
)


def _book(title: str, author: str, source: str, **formats: str) -> Book:
    return Book(
        book_id=f"{source}:{title}",
        title=title,
        authors=(author,),
        source=source,
        formats=dict(formats),
        site_url=f"https://{source}.example/{title}",
    )


_EDITIONS = [
    _book(
        "Middlemarch: A Study of Provincial Life", "Eliot, George", "gutenberg", txt="t", epub="e"
    ),
    _book("Middlemarch", "George Eliot", "standard-ebooks", epub="e2"),
    _book("Middlemarch", "Eliot, George, 1819-1880", "librivox", audio="a"),
    _book("Adam Bede", "George Eliot", "bard"),
]


def test_the_same_book_from_four_libraries_is_one_row() -> None:
    works = group(_EDITIONS)
    assert [work.title for work in works] == ["Middlemarch", "Adam Bede"]
    assert len(works[0].editions) == 3


def test_the_plainest_title_wins() -> None:
    # A row should read as the book's name, not as one catalogue's subtitle.
    assert group(_EDITIONS)[0].title == "Middlemarch"


def test_one_author_written_three_ways_is_one_author() -> None:
    assert normalise_author(("George Eliot",)) == "eliot"
    assert normalise_author(("Eliot, George",)) == "eliot"
    assert normalise_author(("Eliot, George, 1819-1880",)) == "eliot"


def test_a_subtitle_does_not_make_a_different_book() -> None:
    assert normalise_title("Middlemarch: A Study of Provincial Life") == "middlemarch"
    assert normalise_title("The Mill on the Floss") == "mill on the floss"


def test_the_row_says_what_you_can_do_and_where_it_came_from() -> None:
    row = group(_EDITIONS)[0].row_label()
    assert row.startswith("Middlemarch, by ")
    assert "read or listen" in row
    assert "open now" in row
    assert "Project Gutenberg" in row and "LibriVox" in row
    assert RECOMMENDED_NOTE in row


def test_a_catalog_only_row_says_so_rather_than_looking_openable() -> None:
    row = group(_EDITIONS)[1].row_label()
    assert "account required" in row
    assert "the BARD catalog" in row
    assert "read" not in row  # nothing to read here; saying so would be a lie


def test_audio_and_text_are_equals_and_the_row_joins_them() -> None:
    work = group(_EDITIONS)[0]
    assert work.has_audio and work.has_text


def test_the_recommended_edition_is_the_one_enter_acts_on() -> None:
    # Not a judgement about Gutenberg: a proofread, semantically marked EPUB is
    # materially better with a screen reader, which is worth acting on by default.
    best = group(_EDITIONS)[0].best_edition
    assert best is not None
    assert best.source == "standard-ebooks"


def test_a_work_with_nothing_openable_still_has_something_to_do() -> None:
    best = group(_EDITIONS)[1].best_edition
    assert best is not None
    assert best.site_url  # the library's own page
    assert group(_EDITIONS)[1].category == availability.ACCOUNT_REQUIRED


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("all", ["Middlemarch", "Adam Bede"]),
        ("open", ["Middlemarch"]),
        ("read", ["Middlemarch"]),
        ("listen", ["Middlemarch"]),
        ("nonsense", ["Middlemarch", "Adam Bede"]),
    ],
)
def test_the_filter_narrows_what_is_already_here(mode: str, expected: list[str]) -> None:
    # Local to the results already fetched: re-searching would make "show me
    # only the ones I can open" cost a second wait for an answer already in hand.
    assert [work.title for work in apply_filter(group(_EDITIONS), mode)] == expected


def test_every_filter_has_a_label_somebody_would_recognise() -> None:
    assert [key for key, _label in FILTERS] == ["all", "open", "read", "listen"]
    assert all(label and label[0].isupper() for _key, label in FILTERS)


def test_the_summary_counts_by_what_can_be_done() -> None:
    # "40 results" of which two are openable is a worse answer than the truth.
    said = summarise(group(_EDITIONS))
    assert "2 books found" in said
    assert "1 you can open here" in said
    assert summarise([]) == "Nothing found. Try different words."


def test_a_search_with_no_openable_result_says_so_outright() -> None:
    said = summarise(group([_EDITIONS[3]]))
    assert "catalog records" in said


def test_a_library_is_named_the_way_a_person_would_say_it() -> None:
    assert source_name("standard-ebooks") == "Standard Ebooks"
    assert source_name("bard") == "the BARD catalog"
    assert source_name("") == "an unnamed source"


def test_the_details_pane_lists_every_edition_and_its_formats() -> None:
    text = describe(group(_EDITIONS)[0])
    assert "Project Gutenberg: epub, txt" in text
    assert "LibriVox: audio" in text
    assert "read and to listen" in text
