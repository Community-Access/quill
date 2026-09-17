"""Heading N over a selection: every line, rewritten, in one edit (bad.md R3).

QUILL's Heading N *prepended*, so `### Notes` plus Heading 2 gave `## ### Notes`
and a five-line selection got one heading and four untouched lines. None of it
is audible -- the screen reader says "Heading 2" in every case -- so it survived
two years and surfaced only in published documents.
"""

from __future__ import annotations

from quill.core.heading_levels import (
    LevelResult,
    set_heading_level_over_lines,
)


def test_every_selected_line_becomes_a_heading() -> None:
    text = "one\ntwo\nthree"
    change = set_heading_level_over_lines(text, 0, len(text), 2)
    assert change.replacement == "## one\n## two\n## three"


def test_a_line_that_is_already_a_heading_is_rewritten_not_prepended() -> None:
    """The bug in one line: `### Notes` plus Heading 2 is `## Notes`."""
    text = "### Notes\nbody"
    change = set_heading_level_over_lines(text, 0, len(text), 2)
    assert change.replacement.splitlines()[0] == "## Notes"
    assert "###" not in change.replacement


def test_blank_lines_stay_blank() -> None:
    """An empty heading is not a heading; it is `## ` and a rendering problem."""
    text = "one\n\ntwo"
    change = set_heading_level_over_lines(text, 0, len(text), 1)
    assert change.replacement == "# one\n\n# two"


def test_level_zero_takes_the_markers_off_every_line() -> None:
    text = "# one\n## two\nplain"
    change = set_heading_level_over_lines(text, 0, len(text), 0)
    assert change.replacement == "one\ntwo\nplain"


def test_level_zero_on_a_block_with_no_headings_says_so() -> None:
    """So the caller can say "Already body text" rather than report a change
    that did not happen."""
    change = set_heading_level_over_lines("one\ntwo", 0, 7, 0)
    assert change.result is LevelResult.NOT_A_HEADING


def test_the_change_spans_whole_lines_even_from_a_partial_selection() -> None:
    """A selection that starts mid-word still heads the whole line: half a
    heading marker is not a thing anybody means."""
    text = "hello world\nsecond"
    change = set_heading_level_over_lines(text, 3, 8, 3)
    assert change.start == 0
    assert change.replacement == "### hello world"


def test_it_is_one_change_so_it_is_one_undo() -> None:
    """Five lines, one Replace. Five separate edits would take five presses of
    Ctrl+Z to walk back one action the person took once."""
    text = "a\nb\nc\nd\ne"
    change = set_heading_level_over_lines(text, 0, len(text), 4)
    assert (change.start, change.end) == (0, len(text))
    assert change.replacement.count("#### ") == 5


def test_html_headings_are_rewritten_too() -> None:
    text = "<h3>Notes</h3>\nbody"
    change = set_heading_level_over_lines(text, 0, len(text), 1, markup_kind="html")
    assert change.replacement.splitlines()[0] == "<h1>Notes</h1>"


def test_a_plain_document_refuses() -> None:
    change = set_heading_level_over_lines("one\ntwo", 0, 7, 2, markup_kind="plain")
    assert change.result is LevelResult.NO_MARKUP


def test_a_level_outside_one_to_six_refuses() -> None:
    assert set_heading_level_over_lines("one", 0, 3, 9).result is LevelResult.NO_MARKUP


def test_a_backwards_selection_works_the_same() -> None:
    """Selecting upward gives end < start, and it is still the same lines."""
    text = "one\ntwo"
    forward = set_heading_level_over_lines(text, 0, 7, 2)
    backward = set_heading_level_over_lines(text, 7, 0, 2)
    assert forward.replacement == backward.replacement
