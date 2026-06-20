"""Unit tests for quill.core.markdown_extensions (issue #257)."""

from __future__ import annotations

from quill.core.markdown_extensions import (
    apply_nl2br,
    check_heading_structure,
    extract_headings,
    generate_toc,
    insert_toc,
    slugify,
)


class TestSlugify:
    def test_lowercases_and_dashes(self) -> None:
        assert slugify("Hello, World!") == "hello-world"

    def test_empty_falls_back(self) -> None:
        assert slugify("   ") == "section"


class TestExtractHeadings:
    def test_extracts_levels_and_titles(self) -> None:
        text = "# Title\n\nIntro text.\n\n## Section One\n\nMore.\n"
        headings = extract_headings(text)
        assert [(h.level, h.title) for h in headings] == [(1, "Title"), (2, "Section One")]

    def test_duplicate_titles_get_unique_slugs(self) -> None:
        text = "# Intro\n\n## Notes\n\n## Notes\n"
        headings = extract_headings(text)
        assert [h.slug for h in headings] == ["intro", "notes", "notes-2"]

    def test_ignores_non_heading_hashes(self) -> None:
        assert extract_headings("not a # heading because no space\n") == []
        assert extract_headings("#NoSpace\n") == []


class TestCheckHeadingStructure:
    def test_no_headings_is_clean(self) -> None:
        assert check_heading_structure("just text\n") == []

    def test_flags_non_h1_start(self) -> None:
        diagnostics = check_heading_structure("## Section\n")
        assert any("level 2" in d.message for d in diagnostics)

    def test_flags_skipped_level(self) -> None:
        diagnostics = check_heading_structure("# Title\n\n#### Too Deep\n")
        assert any("skipped from 1 to 4" in d.message for d in diagnostics)

    def test_well_formed_document_has_no_warnings(self) -> None:
        text = "# Title\n\n## Section\n\n### Subsection\n"
        assert check_heading_structure(text) == []


class TestGenerateToc:
    def test_empty_when_no_headings(self) -> None:
        assert generate_toc("no headings here\n") == ""

    def test_builds_nested_links(self) -> None:
        text = "# Title\n\n## Section One\n\n## Section Two\n"
        toc = generate_toc(text)
        assert "- [Title](#title)" in toc
        assert "  - [Section One](#section-one)" in toc
        assert "  - [Section Two](#section-two)" in toc


class TestInsertToc:
    def test_replaces_marker(self) -> None:
        text = "# Title\n\n[TOC]\n\n## Section\n"
        updated, count = insert_toc(text)
        assert count == 2
        assert "[TOC]" not in updated
        assert "- [Title](#title)" in updated

    def test_inserts_after_first_heading_when_no_marker(self) -> None:
        text = "# Title\n\nBody text.\n\n## Section\n"
        updated, count = insert_toc(text)
        assert count == 2
        lines = updated.splitlines()
        assert lines[0] == "# Title"
        assert "[Section](#section)" in updated

    def test_no_headings_returns_unchanged(self) -> None:
        text = "just a paragraph\n"
        updated, count = insert_toc(text)
        assert updated == text
        assert count == 0


class TestApplyNl2br:
    def test_preserves_blank_line_paragraphs(self) -> None:
        text = "Paragraph one.\n\nParagraph two."
        assert apply_nl2br(text) == text

    def test_adds_hard_break_within_paragraph(self) -> None:
        text = "Line one\nLine two\n\nNext paragraph"
        result = apply_nl2br(text)
        assert "Line one  \nLine two" in result
        assert "Next paragraph" in result
        assert "Next paragraph  " not in result

    def test_skips_code_fences(self) -> None:
        text = "```\nline a\nline b\n```"
        assert apply_nl2br(text) == text

    def test_skips_tilde_fences(self) -> None:
        text = "~~~\nline a\nline b\n~~~"
        assert apply_nl2br(text) == text

    def test_four_backtick_fence_preserves_contents(self) -> None:
        text = "````\nline a\nline b\n````"
        assert apply_nl2br(text) == text

    def test_closing_fence_must_match_opener_character(self) -> None:
        # Tilde opener, backtick closer - the closer is ignored; backticks
        # inside are still treated as code content, and the backticks
        # themselves do not close the tilde fence.
        text = "~~~\n```\nstill inside\n```\n~~~\n"
        result = apply_nl2br(text)
        # Trailing blank line is collapsed by splitlines(); only the
        # structural equality matters here.
        assert result == text.rstrip("\n")
        assert "still inside" in result
        assert "\n~~~\n" not in result  # closing tilde fence did not gain a hard break

    def test_closing_fence_must_be_at_least_as_long(self) -> None:
        # Three backticks open, three tildes do NOT close (different char);
        # a shorter backtick run also does not close.
        text = "```\nline a\n~~\nstill inside\n```"
        assert apply_nl2br(text) == text
