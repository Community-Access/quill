"""Tests for moving a document between plain text, Markdown, HTML and RTF.

The bug these are written against: the switcher converted once and relabelled
the result, so "convert to HTML" produced Markdown wearing an HTML label and
"convert to plain text" produced Markdown wearing a plain one. Every test here
asserts on the *text*, never on the label, because the label was never the part
that was wrong.
"""

from __future__ import annotations

import pytest

from quill.core.format_transitions import (
    FORMATS,
    PlainStyle,
    convert_text,
    has_markdown_markup,
    plan_transition,
)

MARKDOWN = "# Heading 1\n\nThis is **bold** and *italic*.\n\n- one\n- two\n"


# -- the matrix ------------------------------------------------------------- #


@pytest.mark.parametrize("source", FORMATS)
@pytest.mark.parametrize("target", FORMATS)
def test_every_direction_converts_without_raising(source: str, target: str) -> None:
    """All sixteen cells, the four no-ops included. A format switch may never
    be the thing that breaks the document."""
    start = convert_text(MARKDOWN, "markdown", source)
    assert isinstance(convert_text(start, source, target), str)


def test_markdown_to_html_produces_actual_html() -> None:
    """The headline failure: this used to answer '# Heading 1'."""
    html = convert_text(MARKDOWN, "markdown", "html")
    assert "<h1" in html.lower()
    assert "# Heading 1" not in html


def test_rtf_to_html_produces_actual_html() -> None:
    """Leaving rich text for HTML went through Markdown and stopped there."""
    rtf = convert_text(MARKDOWN, "markdown", "rtf")
    html = convert_text(rtf, "rtf", "html")
    assert "<h1" in html.lower()
    assert "# Heading 1" not in html


def test_markdown_to_rtf_produces_actual_rtf() -> None:
    assert convert_text(MARKDOWN, "markdown", "rtf").startswith("{\\rtf")


def test_html_to_markdown_recovers_the_markers() -> None:
    html = convert_text(MARKDOWN, "markdown", "html")
    assert "# Heading 1" in convert_text(html, "html", "markdown")


# -- plain text is strictly plain ------------------------------------------- #


def test_plain_strips_the_markers_by_default() -> None:
    """Jeff's report: switching to plain text kept the Markdown. The default is
    STRIP precisely so a caller that forgets to ask still produces plain text
    that really is plain."""
    plain = convert_text(MARKDOWN, "markdown", "plain")
    assert "Heading 1" in plain
    assert "#" not in plain
    assert "**" not in plain


def test_plain_keeps_the_markers_when_that_is_what_was_asked() -> None:
    """The other honest answer: a .txt file may hold a '#', and some people keep
    their notes exactly that way."""
    plain = convert_text(MARKDOWN, "markdown", "plain", plain_style=PlainStyle.KEEP)
    assert "# Heading 1" in plain


def test_rtf_to_plain_is_plain_not_markdown() -> None:
    """The exact path in the report: rich text to plain text used to answer
    Markdown, because leaving rich always produced Markdown and stopped."""
    rtf = convert_text(MARKDOWN, "markdown", "rtf")
    plain = convert_text(rtf, "rtf", "plain")
    assert "Heading 1" in plain
    assert "#" not in plain


# -- the question, asked only when there is something to ask ---------------- #


def test_plain_target_with_markdown_asks() -> None:
    plan = plan_transition(MARKDOWN, "markdown", "plain")
    assert plan.asks_plain_style is True
    assert plan.needs_prompt is True


def test_plain_target_without_markdown_does_not_ask() -> None:
    """A dialog raised when nothing is at stake is how people learn to dismiss
    dialogs without reading them."""
    plan = plan_transition("Just some ordinary prose.\n", "markdown", "plain")
    assert plan.asks_plain_style is False
    assert plan.needs_prompt is False


def test_leaving_rich_always_warns() -> None:
    plan = plan_transition(MARKDOWN, "rtf", "markdown")
    assert plan.warns_lossy is True
    assert plan.summary


def test_rtf_to_plain_both_warns_and_asks() -> None:
    plan = plan_transition(MARKDOWN, "rtf", "plain")
    assert plan.warns_lossy is True
    assert plan.asks_plain_style is True


@pytest.mark.parametrize(
    "text",
    [
        "# Heading\n",
        "Some **bold** words.\n",
        "- a list item\n",
        "1. a numbered item\n",
        "See [the docs](https://example.com).\n",
        "```\ncode\n```\n",
        "> quoted\n",
        "~~struck~~\n",
    ],
)
def test_markdown_markers_are_recognised(text: str) -> None:
    assert has_markdown_markup(text) is True


@pytest.mark.parametrize(
    "text",
    ["", "Ordinary prose with no markers.\n", "A * lonely asterisk.\n", "2 + 2 = 4\n"],
)
def test_prose_is_not_mistaken_for_markdown(text: str) -> None:
    assert has_markdown_markup(text) is False


# -- switches that must change nothing -------------------------------------- #


@pytest.mark.parametrize("fmt", FORMATS)
def test_switching_to_the_format_you_are_already_in_is_a_no_op(fmt: str) -> None:
    """A no-op switch must never rewrite the buffer -- doing so would mark a
    clean document dirty and, through the pivot, could subtly reflow it."""
    assert convert_text(MARKDOWN, fmt, fmt) == MARKDOWN
    assert plan_transition(MARKDOWN, fmt, fmt).needs_prompt is False


def test_an_unknown_format_leaves_the_text_alone() -> None:
    assert convert_text(MARKDOWN, "markdown", "klingon") == MARKDOWN
    assert convert_text(MARKDOWN, "klingon", "markdown") == MARKDOWN


# -- round trips ------------------------------------------------------------ #


def test_markdown_html_markdown_round_trips_exactly() -> None:
    """It did not: ``markdown_to_html`` writes a <title>, and the reader emitted
    it as body text, so every switch out and back *grew a line* -- and because
    the line is the document's own name it reads as something the author wrote
    rather than as damage.
    """
    html = convert_text(MARKDOWN, "markdown", "html", title="MyNotes")
    assert convert_text(html, "html", "markdown") == MARKDOWN


def test_repeated_round_trips_stay_stable() -> None:
    """Switching back and forth all afternoon must converge, not accumulate."""
    text = MARKDOWN
    for _ in range(3):
        text = convert_text(
            convert_text(text, "markdown", "html", title="MyNotes"), "html", "markdown"
        )
    assert text == MARKDOWN


def test_the_document_title_never_becomes_body_text() -> None:
    html = convert_text(MARKDOWN, "markdown", "html", title="Quarterly Report")
    assert "Quarterly Report" in html  # it is in the <head>
    assert "Quarterly Report" not in convert_text(html, "html", "markdown")


# -- emphasis survives the journey ------------------------------------------ #

EMPHASIS = "Normal, **bold**, *italic*, <u>underline</u>, ~~strike~~.\n"


def test_underline_reaches_rich_text_as_real_underline() -> None:
    """Markdown has no underline syntax, so Insert Tag writes ``<u>``. The RTF
    writer had no rule for it and emitted the tag as four literal characters in
    the paragraph -- the words arrived, the underline did not, and nothing said
    so."""
    rtf = convert_text(EMPHASIS, "markdown", "rtf")
    assert "\\ul" in rtf
    assert "<u>" not in rtf


def test_strikethrough_reaches_rich_text_as_real_strikethrough() -> None:
    rtf = convert_text(EMPHASIS, "markdown", "rtf")
    assert "\\strike" in rtf
    assert "~~" not in rtf


def test_plain_text_keeps_no_tags_and_no_tildes() -> None:
    """ "Strictly plain" has to mean it: a .txt file promising no markup must not
    contain ``<u>`` or ``~~``."""
    plain = convert_text(EMPHASIS, "markdown", "plain")
    assert "underline" in plain and "strike" in plain
    for marker in ("<u>", "</u>", "~~", "**", "*"):
        assert marker not in plain


def test_emphasis_survives_a_round_trip_through_rich_text() -> None:
    """Not byte-identical -- underline comes back as QUILL's canonical span --
    but the *formatting* survives, which is what was being lost."""
    back = convert_text(convert_text(EMPHASIS, "markdown", "rtf"), "rtf", "markdown")
    assert "**bold**" in back
    assert "{underline}" in back
    assert "{strike}" in back


def test_code_spans_keep_their_literal_tags_everywhere() -> None:
    """Somebody writing *about* ``<u>`` keeps their example, in every direction."""
    source = "Use `<u>text</u>` for underline.\n"
    assert "<u>text</u>" in convert_text(source, "markdown", "plain")
    assert "<u>text</u>" in convert_text(source, "markdown", "rtf")
