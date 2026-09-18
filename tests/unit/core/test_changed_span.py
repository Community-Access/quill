"""The narrowest edit that turns one string into another (bad.md C2, N3).

Both editors had a helper that replaced the **whole document** for any change
at all, and on the rich surface that is not merely wasteful -- it is
destructive. Writing over a selection makes the new text adopt the format at
the selection's start, so selecting all and writing turns every run into
whatever position 0 was.

Confirmed live on 2026-09-17 by ``scripts/probe_rich_edits.py``: a document
with one Heading 1 and two body lines came back with ``all_headings()``
reporting **five** headings -- every line promoted. The row predicted the
formatting would be *lost*; it actually *spreads*, which is worse, and is why
the obvious check ("is my heading still there?") answers yes and misses it.
"""

from __future__ import annotations

import pytest

from quill.core.selection import changed_span


def _apply(before: str, span: tuple[int, int, str]) -> str:
    start, end, replacement = span
    return before[:start] + replacement + before[end:]


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ("", ""),
        ("abc", "abc"),
        ("one\ntwo\nthree", "one\nTWO\nthree"),
        ("one\ntwo", "one\ntwo\nthree"),
        ("one\ntwo\nthree", "one\nthree"),
        ("abc", ""),
        ("", "abc"),
        ("aaa", "aa"),
        ("aa", "aaa"),
        ("alpha beta", "beta alpha"),
        ("x" * 500, "x" * 250 + "y" + "x" * 250),
    ],
)
def test_the_span_always_reproduces_the_new_text(before: str, after: str) -> None:
    """The only property that must hold without exception: applying the span to
    *before* gives *after*. A narrowing that is wrong is worse than no
    narrowing, because it corrupts rather than wastes."""
    assert _apply(before, changed_span(before, after)) == after


def test_an_unchanged_document_is_an_empty_span() -> None:
    """Distinguishable from "changed to nothing", which is what every no-op
    announcement depends on -- QUILL's line tools announced their past tense
    even when nothing had changed (bad.md N2)."""
    assert changed_span("same", "same") == (0, 0, "")


def test_changed_to_nothing_is_not_the_same_as_unchanged() -> None:
    assert changed_span("gone", "") == (0, 4, "")


def test_a_one_line_edit_touches_one_line() -> None:
    """The point of the whole exercise. Appending a line must not rewrite the
    lines above it, because on the rich surface rewriting them re-formats them.
    """
    before = "Chapter One\nBody text.\nMore body."
    after = before + "\nInserted line."

    start, end, replacement = changed_span(before, after)

    assert (start, end) == (len(before), len(before))
    assert replacement == "\nInserted line."
    assert start > len("Chapter One"), "the heading line must be outside the span"


def test_a_change_in_the_middle_leaves_both_ends_alone() -> None:
    before = "keep this\nCHANGE ME\nand keep this"
    after = before.replace("CHANGE ME", "changed")

    start, end, replacement = changed_span(before, after)

    assert before[:start] == "keep this\n"
    assert before[end:] == "\nand keep this"
    assert replacement == "changed"


def test_the_suffix_never_runs_back_past_the_prefix() -> None:
    """The arithmetic that is easy to get wrong: with repeated characters the
    common prefix and the common suffix can otherwise overlap and produce a
    span with end < start, which applies as a corruption rather than an edit."""
    for before, after in (("aaaa", "aa"), ("aa", "aaaa"), ("abab", "ab"), ("", "aaa")):
        start, end, _replacement = changed_span(before, after)
        assert start <= end, f"{before!r} -> {after!r} gave start={start} end={end}"
        assert _apply(before, changed_span(before, after)) == after
