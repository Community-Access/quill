"""Hard line breaks: the thing QUILL's Markdown could not express (#1488).

A blind novelist wrote scene breaks as lines that follow one another with no
gap. In Word that is a hard return inside one paragraph. Opened in QUILL they
came back with blank lines between them and nothing removed them; he lost two
days and ended up with an HTML tag he correctly expected to break.

Three separate defects, and this file covers the vocabulary plus the renderer:

1. **The renderer implemented no hard break at all.** Two trailing spaces, a
   backslash and a literal ``<br>`` all failed -- every line of a paragraph was
   joined with a space, so there was no way to write one.
2. **Every line was rstripped** before anything looked at it, which destroyed
   the two-space spelling before it could be acted on. That is why his own
   attempt did nothing.
3. **The Word reader merged every paragraph into one** and lost hard returns
   entirely, which ``test_docx_scene_breaks`` covers.

The rule the tests encode: **read both spellings, write one.** Being strict
about input would fail documents that are correct; being loose about output
would mean QUILL writing the invisible spelling to a blind author's file.
"""

from __future__ import annotations

import pytest

from quill.core.browser_preview import render_preview_body
from quill.core.markdown_breaks import (
    HARD_BREAK_LABELS,
    HARD_BREAK_STYLES,
    add_hard_break,
    hard_break_suffix,
    line_ends_with_hard_break,
    normalise_hard_break_style,
    strip_hard_break,
)

SPACES = "  "
BACKSLASH = chr(92)
NEWLINE = chr(10)


# --------------------------------------------------------------------- #
# Reading both spellings


@pytest.mark.parametrize(
    "line",
    ["Illinois," + SPACES, "Illinois," + BACKSLASH, "Illinois,   ", "a" + SPACES],
)
def test_both_spellings_are_recognised(line: str) -> None:
    assert line_ends_with_hard_break(line)


@pytest.mark.parametrize(
    "line",
    [
        "Illinois,",
        "Illinois, ",  # one space is not a break
        "",
        "   ",  # a blank line with whitespace is a blank line
        "ends with an escaped backslash " + BACKSLASH * 2,
    ],
)
def test_what_is_not_a_hard_break(line: str) -> None:
    assert not line_ends_with_hard_break(line)


def test_a_line_of_only_spaces_is_blank_not_broken() -> None:
    """Otherwise every document with trailing whitespace on its blank lines --
    which is most of them -- grows stray breaks."""
    assert not line_ends_with_hard_break("    ")
    assert (
        render_preview_body("one" + NEWLINE + "   " + NEWLINE + "two", "markdown").count("<p>") == 2
    )


@pytest.mark.parametrize("marker", [SPACES, BACKSLASH])
def test_the_marker_is_removed_and_the_text_kept(marker: str) -> None:
    assert strip_hard_break("Illinois," + marker) == "Illinois,"


def test_stripping_leaves_an_ordinary_line_alone() -> None:
    assert strip_hard_break("Illinois,") == "Illinois,"


# --------------------------------------------------------------------- #
# Writing one spelling


def test_the_default_is_the_one_you_can_hear() -> None:
    """Two trailing spaces are invisible on screen, silent to a reader, and
    stripped by half the tools that touch a file. In an app written for people
    who cannot see the screen that is not a close call."""
    assert HARD_BREAK_STYLES[0] == "backslash"
    assert hard_break_suffix("backslash") == BACKSLASH
    assert hard_break_suffix("spaces") == SPACES


@pytest.mark.parametrize("junk", ["", None, "nonsense", "BACKSLASH ", 7])
def test_an_unknown_style_falls_back_rather_than_raising(junk: object) -> None:
    """A hand-edited settings file must not stop the editor writing a line."""
    assert normalise_hard_break_style(junk) == "backslash"


def test_every_style_has_a_label_for_a_chooser() -> None:
    assert set(HARD_BREAK_LABELS) == set(HARD_BREAK_STYLES)
    assert all(HARD_BREAK_LABELS[style].strip() for style in HARD_BREAK_STYLES)


@pytest.mark.parametrize("style", HARD_BREAK_STYLES)
def test_adding_a_break_is_idempotent(style: str) -> None:
    once = add_hard_break("Illinois,", style)
    assert add_hard_break(once, style) == once


def test_adding_a_break_converts_the_other_spelling_rather_than_doubling_it() -> None:
    """Which is what makes changing the setting safe to run over a document."""
    assert add_hard_break("Illinois," + SPACES, "backslash") == "Illinois," + BACKSLASH
    assert add_hard_break("Illinois," + BACKSLASH, "spaces") == "Illinois," + SPACES


# --------------------------------------------------------------------- #
# The renderer


def _scene(marker: str) -> str:
    return (
        "United States," + marker + NEWLINE + "Illinois," + marker + NEWLINE + "Chicago," + NEWLINE
    )


@pytest.mark.parametrize("marker", [SPACES, BACKSLASH])
def test_the_reported_scene_block_renders_as_three_lines(marker: str) -> None:
    """The exact shape from the report, in both spellings."""
    html = render_preview_body(_scene(marker), "markdown")
    assert html.count("<br>") == 2
    assert html.count("<p>") == 1
    assert BACKSLASH not in html  # the marker must not survive into the output


def test_a_soft_wrap_is_still_a_soft_wrap() -> None:
    """Markdown's own rule, and the reason a hard break needs a marker at all."""
    html = render_preview_body("United States," + NEWLINE + "Illinois," + NEWLINE, "markdown")
    assert "<br>" not in html
    assert "United States, Illinois," in html


def test_emphasis_still_spans_a_hard_break() -> None:
    """The lines are rendered as one string precisely so this keeps working; a
    per-line renderer would be the obvious implementation and would break it."""
    html = render_preview_body("this *spans" + SPACES + NEWLINE + "two lines* here", "markdown")
    assert "<em>spans<br>two lines</em>" in html


def test_a_blank_line_still_starts_a_paragraph() -> None:
    """The distinction the whole feature rests on: a break ends a line, a blank
    line ends a paragraph."""
    html = render_preview_body("one" + NEWLINE * 2 + "two", "markdown")
    assert html.count("<p>") == 2
    assert "<br>" not in html


def test_a_break_on_the_last_line_of_a_paragraph_adds_nothing() -> None:
    """There is no next line to break to, and a trailing <br> is a blank line
    the author did not write."""
    html = render_preview_body("only line" + SPACES + NEWLINE + NEWLINE + "next", "markdown")
    assert "<br>" not in html


def test_the_editor_text_and_the_render_agree_about_blank_lines() -> None:
    """The reporter's actual complaint, stated as a test: "the editor should not
    be showing me blank lines where blank lines will later just magically
    disappear"."""
    source = _scene(BACKSLASH)
    assert NEWLINE * 2 not in source  # no blank lines in what the editor shows
    assert render_preview_body(source, "markdown").count("<p>") == 1  # and none in the render
