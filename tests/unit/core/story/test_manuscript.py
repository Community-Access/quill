from __future__ import annotations

from quill.core.story.manuscript import Heading, iter_headings


def test_no_headings_returns_empty() -> None:
    assert iter_headings("Just a paragraph.\nAnd another.\n") == []


def test_levels_titles_and_offsets() -> None:
    text = "# Part One\n\nIntro.\n\n## Chapter 1\n\nText.\n### Scene A\n"
    headings = iter_headings(text)
    assert headings == [
        Heading(level=1, title="Part One", offset=0),
        Heading(level=2, title="Chapter 1", offset=text.index("## Chapter 1")),
        Heading(level=3, title="Scene A", offset=text.index("### Scene A")),
    ]


def test_trailing_hashes_and_extra_spaces_are_trimmed() -> None:
    headings = iter_headings("##   Chapter Two   ##\n")
    assert headings == [Heading(level=2, title="Chapter Two", offset=0)]


def test_hash_without_space_is_not_a_heading() -> None:
    # "#notatag" is not an ATX heading (needs a space); "#" channels in prose
    # must not be mistaken for structure.
    assert iter_headings("#nothashtag\nplain # in the middle\n") == []


def test_indented_up_to_three_spaces_still_counts() -> None:
    headings = iter_headings("   ## Indented\n")
    assert headings == [Heading(level=2, title="Indented", offset=0)]
