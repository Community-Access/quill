"""Find and replace across every open document (QUILLVille, Chris Nova, Oct 2026)."""

from __future__ import annotations

from quill.core.find_model import FindQuery
from quill.core.open_documents_search import (
    OpenDoc,
    find_across,
    find_all_across,
    line_text,
    plan_replace,
)

DOCS = [
    OpenDoc("One.txt", "alpha cat\nbeta"),
    OpenDoc("Two.txt", "no match here"),
    OpenDoc("Untitled", "a cat and a cat"),  # never saved: still searched
]
CAT = FindQuery("cat")


def test_the_rest_of_this_document_comes_first() -> None:
    hit = find_across(DOCS, CAT, current=2, position=0)
    assert (hit.doc, hit.match.start, hit.moved, hit.wrapped) == (2, 2, False, False)


def test_the_next_document_with_a_match_is_next_and_says_it_moved() -> None:
    hit = find_across(DOCS, CAT, current=0, position=9)  # past One's only cat
    assert (hit.doc, hit.match.start, hit.moved, hit.wrapped) == (2, 2, True, False)


def test_it_comes_back_round_to_where_it_started() -> None:
    hit = find_across(DOCS, CAT, current=2, position=15)  # past both cats
    assert (hit.doc, hit.moved, hit.wrapped) == (0, True, True)


def test_the_skipped_part_of_the_first_document_is_the_last_place_looked() -> None:
    docs = [OpenDoc("A", "cat x cat"), OpenDoc("B", "nothing")]
    hit = find_across(docs, CAT, current=0, position=9)
    assert (hit.doc, hit.match.start, hit.wrapped) == (0, 0, True)


def test_no_wrap_stops_at_the_last_document() -> None:
    assert find_across(DOCS, FindQuery("cat", wrap=False), current=2, position=15) is None


def test_backwards_goes_to_the_previous_document_last_match() -> None:
    hit = find_across(DOCS, CAT, current=2, position=0, backwards=True)
    assert (hit.doc, hit.match.start, hit.moved) == (0, 6, True)


def test_nothing_anywhere_is_none() -> None:
    assert find_across(DOCS, FindQuery("zebra"), current=0, position=0) is None
    assert find_across([], CAT, current=0, position=0) is None


def test_find_all_lists_every_match_in_document_order() -> None:
    hits, truncated = find_all_across(DOCS, CAT)
    assert [(doc, m.start) for doc, m in hits] == [(0, 6), (2, 2), (2, 12)]
    assert truncated is False


def test_find_all_says_when_it_stopped_early() -> None:
    hits, truncated = find_all_across(DOCS, CAT, max_matches=2)
    assert len(hits) == 2 and truncated is True


def test_replace_is_planned_before_anything_changes_and_read_only_is_left_alone() -> None:
    docs = [*DOCS, OpenDoc("Report", "cat cat cat", editable=False)]
    plan = plan_replace(docs, CAT, "dog")
    assert [(i, count) for i, _text, count in plan.changes] == [(0, 1), (2, 2)]
    assert plan.changes[1][1] == "a dog and a dog"
    assert (plan.total, plan.documents, plan.skipped, plan.skipped_matches) == (3, 2, 1, 3)
    assert docs[2].text == "a cat and a cat"  # nothing was changed


def test_the_modes_mean_what_they_mean_in_one_document() -> None:
    docs = [OpenDoc("A", "Cat cat category")]
    assert len(find_all_across(docs, FindQuery("cat", case_sensitive=True))[0]) == 2
    assert len(find_all_across(docs, FindQuery("cat", whole_word=True))[0]) == 2
    assert len(find_all_across(docs, FindQuery("c.t", mode="regex"))[0]) == 3


def test_a_line_is_shown_trimmed() -> None:
    hits, _ = find_all_across(DOCS, CAT)
    assert line_text(DOCS[0].text, hits[0][1]) == "alpha cat"
