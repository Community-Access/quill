"""Tests for the opt-in article/heading combining (ACB-style) in text_polish."""

from __future__ import annotations

from quill.core.speech.text_polish import DocumentSection, combine_heading_only_sections


def test_heading_only_section_folds_into_next_body() -> None:
    sections = [
        DocumentSection("Part One", ""),  # heading, no body
        DocumentSection("Chapter 1", "The story begins."),
    ]
    out = combine_heading_only_sections(sections)
    assert len(out) == 1
    assert out[0].title == "Part One: Chapter 1"
    assert out[0].text == "The story begins."


def test_consecutive_headings_combine() -> None:
    sections = [
        DocumentSection("Book", ""),
        DocumentSection("Part", ""),
        DocumentSection("Chapter", "Body text here."),
    ]
    out = combine_heading_only_sections(sections)
    assert out == [DocumentSection("Book: Part: Chapter", "Body text here.")]


def test_sections_with_body_are_untouched() -> None:
    sections = [
        DocumentSection("", "lead in"),
        DocumentSection("A", "alpha"),
        DocumentSection("B", "bravo"),
    ]
    assert combine_heading_only_sections(sections) == sections


def test_trailing_bodyless_headings_become_one_section() -> None:
    sections = [
        DocumentSection("A", "alpha"),
        DocumentSection("Appendix", ""),
        DocumentSection("Index", ""),
    ]
    out = combine_heading_only_sections(sections)
    assert out == [
        DocumentSection("A", "alpha"),
        DocumentSection("Appendix: Index", ""),
    ]


def test_extract_sections_combine_flag(tmp_path) -> None:
    from quill.core.speech.text_polish import extract_sections

    md = tmp_path / "doc.md"
    md.write_text("# Part One\n\n## Chapter 1\n\nThe body.\n", encoding="utf-8")
    # Default: each heading is its own section (Part One has no body of its own).
    default = extract_sections(md)
    assert [s.title for s in default] == ["Part One", "Chapter 1"]
    # Combine: the empty "Part One" folds into "Chapter 1".
    combined = extract_sections(md, combine_headings=True)
    assert [s.title for s in combined] == ["Part One: Chapter 1"]
    assert combined[0].text.strip() == "The body."
