"""The three-stop ring a list key should be, over Markdown markers.

A toggle can only say yes or no, which is why QUILL Lite had bullets and no way
to make a numbered list at all (bad.md P1.5). What is being asserted here is the
ring itself, the scope, and the two things the obvious implementation gets
wrong: numbering that restarts at one and counts only the lines it numbers, and
a rewrite that never reaches outside the lines it was given.
"""

from __future__ import annotations

from quill.core.list_style import cycle_list_style, list_style_of


def test_the_styles_ring_in_order() -> None:
    text = "one\ntwo\n"
    text, style, _start, _end = cycle_list_style(text, 0, len(text))
    assert (style, text) == ("bullet", "- one\n- two\n")
    text, style, _start, _end = cycle_list_style(text, 0, len(text))
    assert (style, text) == ("numbered", "1. one\n2. two\n")
    text, style, _start, _end = cycle_list_style(text, 0, len(text))
    assert (style, text) == ("none", "one\ntwo\n")


def test_numbering_restarts_at_one_for_the_lines_it_marks() -> None:
    """A numbered list whose markers are all "1." is not a numbered list."""
    text, style, _start, _end = cycle_list_style("- a\n- b\n- c\n", 0, 11)
    assert (style, text) == ("numbered", "1. a\n2. b\n3. c\n")


def test_blank_lines_are_left_alone_and_not_counted() -> None:
    text, _style, _start, _end = cycle_list_style("one\n\ntwo\n", 0, 8)
    assert text == "- one\n\n- two\n"
    text, _style, _start, _end = cycle_list_style(text, 0, 12)
    assert text == "1. one\n\n2. two\n"


def test_indentation_survives_the_marker() -> None:
    text, _style, _start, _end = cycle_list_style("    deep\n", 0, 8)
    assert text == "    - deep\n"


def test_only_the_lines_in_the_span_are_touched() -> None:
    """QUILL's list-off ran over the whole buffer, so turning one list off
    removed every other list in the file (bad.md R2)."""
    text = "- keep\n\none\ntwo\n"
    updated, _style, _start, _end = cycle_list_style(text, 8, 15)
    assert updated == "- keep\n\n- one\n- two\n"


def test_a_caret_with_no_selection_acts_on_its_own_line() -> None:
    updated, _style, start, end = cycle_list_style("one\ntwo\n", 5, 5)
    assert updated == "one\n- two\n"
    assert updated[start:end] == "- two"


def test_a_half_marked_run_marks_the_rest_rather_than_unmarking() -> None:
    """Which is what somebody who has just typed a new item wants."""
    updated, style, _start, _end = cycle_list_style("- one\ntwo\n", 0, 9)
    assert (style, updated) == ("bullet", "- one\n- two\n")


def test_the_marker_styles_people_actually_type_are_recognised() -> None:
    assert list_style_of(["* one", "+ two", "- three"]) == "bullet"
    assert list_style_of(["1) one", "2. two"]) == "numbered"
    assert list_style_of(["one", "- two"]) == "none"
    assert list_style_of([]) == "none"
    assert list_style_of(["", "  "]) == "none"


def test_the_offsets_span_exactly_what_was_rewritten() -> None:
    text = "before\none\ntwo\nafter\n"
    updated, _style, start, end = cycle_list_style(text, 7, 13)
    assert updated[start:end] == "- one\n- two"
    assert updated[:start] == "before\n"


def test_an_empty_document_is_left_alone() -> None:
    updated, style, start, end = cycle_list_style("", 0, 0)
    assert (updated, style, start, end) == ("", "bullet", 0, 0)


# ---------------------------------------------------------------------------
# Turning one list off, and only that one (bad.md R2)
# ---------------------------------------------------------------------------


def test_only_the_list_at_the_caret_is_found() -> None:
    """QUILL's list-off used to run over the whole document, so switching one
    three-item list off silently unmade every other list in the file."""
    from quill.core.list_style import list_block_span

    text = "intro\n\n- a\n- b\n- c\n\npara\n\n- x\n- y"
    start, end = list_block_span(text, text.index("- b"), text.index("- b"))
    assert text[start:end] == "- a\n- b\n- c"


def test_a_caret_outside_any_list_finds_nothing() -> None:
    from quill.core.list_style import list_block_span

    assert list_block_span("intro\n\n- a\n- b", 0, 3) is None


def test_a_blank_line_between_two_items_keeps_one_list() -> None:
    """A loose list is still one list; the blank lines are part of it."""
    from quill.core.list_style import list_block_span

    text = "- a\n\n- b\n\n- c"
    assert list_block_span(text, 0, 0) == (0, len(text))


def test_a_blank_line_after_the_last_item_ends_the_list() -> None:
    from quill.core.list_style import list_block_span

    text = "- a\n- b\n\nafter"
    start, end = list_block_span(text, 0, 0)
    assert text[start:end] == "- a\n- b"


def test_strip_returns_the_span_the_text_and_the_count() -> None:
    """The count, because the caller must say it: "Bullet list removed, 3
    items" is the only way somebody who cannot see the markers go learns how
    much changed."""
    from quill.core.list_style import strip_list_block

    text = "intro\n- a\n- b\n- c"
    start, end, replacement, items = strip_list_block(text, text.index("- a"), text.index("- a"))
    assert replacement == "a\nb\nc"
    assert items == 3
    assert text[:start] == "intro\n"


def test_numbered_lists_strip_too() -> None:
    from quill.core.list_style import strip_list_block

    text = "1. one\n2. two"
    _, _, replacement, items = strip_list_block(text, 0, 0)
    assert replacement == "one\ntwo"
    assert items == 2


def test_indentation_survives_the_strip() -> None:
    """A nested list that loses its markers keeps its shape; the indent is the
    only thing left saying which item belonged under which."""
    from quill.core.list_style import strip_list_block

    text = "- top\n  - nested"
    _, _, replacement, _ = strip_list_block(text, 0, 0)
    assert replacement == "top\n  nested"
