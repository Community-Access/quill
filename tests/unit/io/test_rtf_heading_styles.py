"""A heading saved to RTF must be a real heading, not big bold text.

Before this, ``markdown_to_rtf`` emitted ``\\b`` and an outline level and nothing
else. The file opened in Word with "Normal" in the style box, an empty navigation
pane, and -- the part that bit inside QUILL's own editor -- no point size at all,
so every heading came back through the rich-mode ladder as a Heading 4, whatever
level it went out as. The editor could still find its headings in *markup* mode
because it re-read the hashes, which is why the round trip looked fine.
"""

from __future__ import annotations

import pytest

from quill.core.heading_ladder import HEADING_POINT_SIZES, heading_level_for_font
from quill.io.rtf import markdown_to_rtf, rtf_to_markdown
from quill.io.rtf_styles import DEFAULT_HALF_POINTS, heading_stylesheet


def test_the_document_declares_a_stylesheet() -> None:
    assert "\\stylesheet" in markdown_to_rtf("# Title\n")


@pytest.mark.parametrize("level", [1, 2, 3, 4, 5, 6])
def test_every_level_is_declared_with_words_own_style_name(level: int) -> None:
    # Lower case: "heading 1" is Word's built-in style, "Heading 1" would be a
    # new user-defined style that Word treats as unrelated to its own.
    assert f"heading {level};" in heading_stylesheet()


@pytest.mark.parametrize("level", [1, 2, 3, 4, 5, 6])
def test_a_heading_paragraph_references_its_style(level: int) -> None:
    rtf = markdown_to_rtf(f"{'#' * level} Title\n")
    assert f"\\s{level}\\outlinelevel{level - 1}" in rtf


@pytest.mark.parametrize("level", [1, 2, 3, 4, 5, 6])
def test_the_written_point_size_is_the_editors_own_ladder(level: int) -> None:
    """The round trip that was silently broken.

    Rich mode recognises a heading by its point size and weight. A file written
    with any other size reopens at the wrong level, so the writer and the
    control must read the same table -- which is the whole reason the ladder
    moved to ``quill.core.heading_ladder``.
    """
    rtf = markdown_to_rtf(f"{'#' * level} Title\n")
    half_points = int(round(HEADING_POINT_SIZES[level] * 2))
    assert f"\\fs{half_points} Title" in rtf
    assert heading_level_for_font(half_points / 2, bold=True) == level


def test_a_heading_does_not_enlarge_the_paragraph_after_it() -> None:
    # \pard resets the paragraph, not the font. Without an explicit reset the
    # body text following a Heading 1 would render at 20 point.
    rtf = markdown_to_rtf("# Title\nbody text\n")
    # The heading's own paragraph, not merely the first line mentioning "Title".
    # The stylesheet declares Word's built-in ``Title`` style by name, so the
    # header line contains the word too -- and being first, it is what a plain
    # "in line" search finds. The heading is the paragraph line: it ends in
    # \par and carries the Heading 1 style.
    heading_line = next(
        line for line in rtf.split("\n") if "Title" in line and line.endswith("\\par")
    )
    assert heading_line.endswith(f"\\b0\\fs{DEFAULT_HALF_POINTS}\\par")


def test_the_stylesheet_does_not_disturb_the_round_trip() -> None:
    source = "# Title\nbody text\n## Two\n"
    assert rtf_to_markdown(markdown_to_rtf(source)) == source


def test_body_paragraphs_are_left_exactly_as_they_were() -> None:
    rtf = markdown_to_rtf("just a paragraph\n")
    assert "\\pard just a paragraph\\par" in rtf
    # The preamble is one line -- tables, stylesheet and the body size -- so
    # everything after the first newline is the document itself.
    assert "\\s1" not in rtf.split("\n", 1)[1]


def test_body_text_is_written_at_the_ladders_body_size() -> None:
    """Body text must not be the size of a heading.

    Reported from QUILL Lite: bold a line and it was announced as "heading
    level 4" by a user who had pressed Ctrl+B and nothing else. A rich
    heading *is* its point size plus bold, Heading 4 is twelve point, and
    twelve point is what RTF gives a paragraph that names no size -- so body
    text in every file QUILL wrote was a Heading 4 waiting for somebody to
    embolden it. The writer states the ladder's own body size instead.
    """
    rtf = markdown_to_rtf("just a paragraph\n")
    preamble = rtf.split("\n", 1)[0]
    assert f"\\fs{DEFAULT_HALF_POINTS}" in preamble
    assert heading_level_for_font(DEFAULT_HALF_POINTS / 2, bold=True) is None
