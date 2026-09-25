"""The computed inverse of expand_selection.

Added because QUILL's shrink was an *undo of the expansion stack*, which can
only retrace a path the user actually walked. Select a paragraph outright, ask
to shrink, and the stack has nothing to say -- even though "the line the cursor
is on" is an obvious and useful answer.

That failure is invisible to a sighted tester, who sees the selection simply not
change, and indistinguishable by ear from a broken command. So the answer is
computed from the text instead, and both QUILL and QUILL Lite use it.
"""

from __future__ import annotations

from quill.core.selection import expand_selection, shrink_selection

TEXT = "One two three. Four five six.\n\nSecond paragraph here.\nAnd a third line."


def test_shrinking_walks_the_ladder_inwards() -> None:
    start, end = 0, len(TEXT)
    scopes = []
    for _ in range(6):
        result = shrink_selection(TEXT, start, end)
        if result is None:
            break
        start, end, scope = result
        scopes.append(scope)
    assert scopes, "shrinking the whole document produced nothing"
    # Strictly inwards, never repeating a level.
    assert len(scopes) == len(set(scopes)), scopes
    assert scopes[-1] == "word"


def test_each_step_is_strictly_smaller() -> None:
    start, end = 0, len(TEXT)
    previous = end - start
    while (result := shrink_selection(TEXT, start, end)) is not None:
        start, end, _scope = result
        assert 0 < end - start < previous, (start, end, previous)
        previous = end - start


def test_a_single_word_has_nothing_smaller() -> None:
    """The bottom of the ladder answers None rather than looping."""
    assert shrink_selection(TEXT, 0, 3) is None


def test_an_empty_selection_has_nothing_to_shrink() -> None:
    assert shrink_selection(TEXT, 5, 5) is None


def test_it_works_without_any_expansion_having_happened() -> None:
    """The whole reason this exists, stated as a test.

    A stack-based shrink refuses here, because the caller never expanded. This
    one answers, because the answer is a property of the text.
    """
    paragraph_start = TEXT.index("Second")
    paragraph_end = len(TEXT)
    result = shrink_selection(TEXT, paragraph_start, paragraph_end)
    assert result is not None
    new_start, new_end, _scope = result
    assert (new_end - new_start) < (paragraph_end - paragraph_start)


def test_shrink_undoes_expand_from_a_word() -> None:
    """Expand then shrink returns to a span no larger than where it started."""
    start, end = 0, 3  # "One"
    grown = expand_selection(TEXT, start, end)
    assert grown is not None
    gs, ge, _ = grown
    back = shrink_selection(TEXT, gs, ge)
    assert back is not None
    bs, be, _ = back
    assert (be - bs) <= (ge - gs)


def test_reversed_bounds_are_accepted() -> None:
    """A caller may hand back a selection made by dragging upwards."""
    forward = shrink_selection(TEXT, 0, 29)
    backward = shrink_selection(TEXT, 29, 0)
    assert forward == backward


def test_out_of_range_bounds_are_clamped_not_raised() -> None:
    assert shrink_selection(TEXT, -50, len(TEXT) + 50) is not None
    assert shrink_selection("", 0, 10) is None
