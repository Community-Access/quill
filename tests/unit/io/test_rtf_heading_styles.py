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
from quill.io.rtf_styles import heading_stylesheet


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
    heading_line = next(line for line in rtf.split("\n") if "Title" in line)
    assert heading_line.endswith("\\b0\\fs24\\par")


def test_the_stylesheet_does_not_disturb_the_round_trip() -> None:
    source = "# Title\nbody text\n## Two\n"
    assert rtf_to_markdown(markdown_to_rtf(source)) == source


def test_body_paragraphs_are_left_exactly_as_they_were() -> None:
    rtf = markdown_to_rtf("just a paragraph\n")
    assert "\\pard just a paragraph\\par" in rtf
    assert "\\s1" not in rtf.split("\\stylesheet", 1)[1].split("}\n", 1)[-1]
