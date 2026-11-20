"""The GitHub plain-language batch grammar (GitHub PRD 22.6, GH-R-086): no AI, no guesses.

Each sentence the PRD names reads to one exact search and one change, the
same every time; a word the grammar does not know is a sentence saying what
it does know, never a guess. The age is the one reading both Workbenches
share (``quill.core.workbench.plain_age``).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pytest

from quill.core.github.plain_batch import PlainError, order_items, parse_request
from quill.core.workbench.properties import FieldChange, ListDelta

TODAY = date(2026, 11, 19)


def test_close_every_issue_labelled_duplicate_older_than_90_days() -> None:
    request = parse_request("close every issue labelled duplicate older than 90 days", TODAY)
    assert request.query == "is:issue is:open label:duplicate created:<2026-08-21"
    assert request.changes() == [FieldChange("state", "State", None, "closed as completed")]
    assert request.changes_anything


def test_nobody_touched_means_updated_and_the_reason_is_kept() -> None:
    request = parse_request(
        "Close all issues labeled stale that nobody touched in 90 days as not planned.", TODAY
    )
    assert request.query == "is:issue is:open updated:<2026-08-21 label:stale"
    assert request.changes()[0].after == "closed as not planned"


def test_the_same_words_always_mean_the_same_search() -> None:
    sentence = "close every issue labelled duplicate older than 90 days"
    assert parse_request(sentence, TODAY) == parse_request(sentence, TODAY)


@pytest.mark.parametrize(
    ("sentence", "query", "after"),
    [
        (
            "reopen the closed issues labelled regression",
            "is:issue is:closed label:regression",
            "open",
        ),
        (
            "add label triage to every issue with no label",
            "is:issue is:open no:label",
            ListDelta(("triage",), ()),
        ),
        (
            "remove label wontfix from all closed issues",
            "is:issue is:closed",
            ListDelta((), ("wontfix",)),
        ),
        (
            "assign alice to every open issue labelled bug",
            "is:issue is:open label:bug",
            ListDelta(("alice",), ()),
        ),
        (
            "unassign bob from all pull requests by carol",
            "is:pr is:open author:carol",
            ListDelta((), ("bob",)),
        ),
        (
            'close every issue labelled "needs info" updated before March 2024',
            'is:issue is:open label:"needs info" updated:<2024-03-01',
            "closed as completed",
        ),
        (
            "close every issue without label keep in milestone 2027.1",
            "is:issue is:open -label:keep milestone:2027.1",
            "closed as completed",
        ),
        (
            "close all pull requests assigned to me",
            "is:pr is:open assignee:@me",
            "closed",
        ),
    ],
)
def test_each_shape_reads_to_one_search_and_one_change(sentence, query, after) -> None:
    request = parse_request(sentence, TODAY)
    assert request.query == query
    assert request.changes()[0].after == after


def test_questions_change_nothing_and_keep_their_order() -> None:
    request = parse_request("Which pull requests are waiting on me, oldest first?", TODAY)
    assert request.action == "list" and not request.changes_anything
    assert request.query == "is:pr is:open review-requested:@me"
    count = parse_request("how many issues are labelled bug?", TODAY)
    assert count.action == "count" and count.query == "is:issue is:open label:bug"


def test_order_items_sorts_by_the_date_the_sentence_names() -> None:
    @dataclass
    class Row:
        number: int
        created_at: str

    rows = [Row(1, "2026-03-01"), Row(2, "2025-01-01"), Row(3, "2026-01-01")]
    assert [r.number for r in order_items(rows, "created_asc")] == [2, 3, 1]
    assert [r.number for r in order_items(rows, "")] == [1, 2, 3]


@pytest.mark.parametrize(
    ("sentence", "says"),
    [
        ("frobnicate every issue", "Start with close, reopen"),
        ("close every issue labelled bug sometime", "does not read 'sometime'"),
        ("close every issue older than a fortnight", "as an age"),
        ("close every issue as duplicate", "needs the issue each one duplicates"),
        ("close every closed issue", "already closed"),
        ("reopen every open issue", "already open"),
        ("close everything", "Say issues or pull requests"),
        ("", "Say what to change"),
    ],
)
def test_a_word_it_does_not_know_is_said_never_guessed(sentence, says) -> None:
    with pytest.raises(PlainError) as caught:
        parse_request(sentence, TODAY)
    assert says in caught.value.plain
    assert caught.value.code == "QUILL-GITHUB-WORKBENCH-PHRASE"
