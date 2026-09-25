"""Promoting and demoting a heading, and the four ways it can refuse.

The rule was two regexes and four branches inline in ``main_frame.py`` until
2026-09-09 -- the shape that gets copied rather than called the second time
somebody needs it, and QUILL Lite was the second time. It is here now, and both
products' Alt+Shift+Left / Right run it.

The refusals carry as much weight as the change. Nothing about this operation
makes a sound or moves the caret, so "you are not on a heading", "this is
already Heading 1" and "that key is not bound to anything" are indistinguishable
to a listener unless each is named -- which is why the return value is a reason
rather than a bool.
"""

from __future__ import annotations

from quill.core.heading_levels import LevelResult, adjust_heading_level


def _apply(text: str, caret: int, delta: int, kind: str = "markdown") -> str:
    change = adjust_heading_level(text, caret, delta, markup_kind=kind)
    assert change.changed, change.result
    return text[: change.start] + change.replacement + text[change.end :]


def test_promote_removes_a_hash_and_demote_adds_one() -> None:
    text = "## Installing\nbody\n"

    assert _apply(text, 4, -1) == "# Installing\nbody\n"
    assert _apply(text, 4, +1) == "### Installing\nbody\n"


def test_the_line_is_found_from_anywhere_on_it() -> None:
    """The caret is wherever the user left it, not on the hashes."""
    text = "intro\n### Deep heading\ntail\n"
    caret = text.index("heading")

    assert _apply(text, caret, -1) == "intro\n## Deep heading\ntail\n"


def test_a_heading_one_refuses_to_be_promoted_into_nothing() -> None:
    """Clamped rather than wrapped, and named rather than silent.

    Wrapping would turn "promote past the top" into "demote to the bottom" --
    a restructuring nobody asked for and one that is very hard to notice by ear.
    """
    change = adjust_heading_level("# Title\n", 3, -1)

    assert change.result is LevelResult.AT_TOP
    assert change.replacement == ""


def test_a_heading_six_refuses_to_be_demoted_further() -> None:
    change = adjust_heading_level("###### Deepest\n", 3, +1)

    assert change.result is LevelResult.AT_BOTTOM


def test_an_ordinary_line_is_not_a_heading() -> None:
    change = adjust_heading_level("just a paragraph\n", 4, -1)

    assert change.result is LevelResult.NOT_A_HEADING


def test_a_hash_with_no_space_is_not_a_heading() -> None:
    """``#tag`` is a word somebody wrote, not a heading, and Markdown agrees."""
    assert adjust_heading_level("#hashtag\n", 3, +1).result is LevelResult.NOT_A_HEADING


def test_a_document_with_no_markup_at_all_says_so() -> None:
    """Distinct from "not on a heading": there is nowhere to put one."""
    change = adjust_heading_level("# Title\n", 3, -1, markup_kind="plain")

    assert change.result is LevelResult.NO_MARKUP


def test_html_headings_move_too() -> None:
    text = "<h3>Installing</h3>\n"

    assert _apply(text, 6, -1, "html") == "<h2>Installing</h2>\n"


def test_an_html_heading_keeps_its_attributes() -> None:
    """An ``id=`` on a heading is usually the anchor somebody's link points at.

    Dropping it while "adjusting a level" would break that link silently, which
    is a much larger edit than the one that was asked for.
    """
    text = '<h2 id="install" class="x">Installing</h2>\n'

    moved = _apply(text, 30, +1, "html")

    assert moved == '<h3 id="install" class="x">Installing</h3>\n'


def test_the_new_level_is_reported_so_the_caller_can_say_it() -> None:
    """ "Adjusted heading level" does not say which way it went."""
    change = adjust_heading_level("### Deep\n", 5, -1)

    assert (change.old_level, change.new_level) == (3, 2)


def test_a_caret_past_the_end_is_clamped_rather_than_raising() -> None:
    text = "# Title"

    assert _apply(text, 9_999, +1) == "## Title"
