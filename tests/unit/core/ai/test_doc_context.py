"""Large-document context: chunking, section slicing, structured summary."""

from __future__ import annotations

from quill.core.ai.compaction import estimate_tokens
from quill.core.ai.doc_context import chunk_text, section_text, structured_summary
from quill.core.outline import OutlineEntry, extract_outline_entries


def test_chunk_empty() -> None:
    assert chunk_text("") == []
    assert chunk_text("   \n  ") == []


def test_chunk_keeps_small_document_in_one_chunk() -> None:
    text = "Para one.\n\nPara two.\n\nPara three."
    assert chunk_text(text, max_tokens=2000) == [text]


def test_chunk_respects_token_budget() -> None:
    paras = "\n\n".join(f"Paragraph number {i} with a few words here." for i in range(20))
    chunks = chunk_text(paras, max_tokens=30)
    assert len(chunks) > 1
    for chunk in chunks:
        assert estimate_tokens(chunk) <= 30 or "\n\n" not in chunk  # whole-block exception


def test_chunk_hard_splits_oversized_paragraph() -> None:
    big = "word " * 500  # one huge paragraph
    chunks = chunk_text(big, max_tokens=20)
    assert len(chunks) > 1
    for chunk in chunks:
        assert estimate_tokens(chunk) <= 25  # near the budget


def test_chunk_preserves_content() -> None:
    text = "Alpha beta.\n\nGamma delta.\n\nEpsilon zeta."
    joined = " ".join(chunk_text(text, max_tokens=8))
    for token in ["Alpha", "Gamma", "Epsilon", "zeta"]:
        assert token in joined


def test_section_text_extracts_between_headings() -> None:
    doc = "# A\n\nAlpha body.\n\n# B\n\nBeta body.\n\n# C\n\nGamma body."
    outline = extract_outline_entries(doc, "markdown")
    assert len(outline) == 3
    sec0 = section_text(doc, outline, 0)
    assert "Alpha body" in sec0
    assert "Beta body" not in sec0
    sec2 = section_text(doc, outline, 2)
    assert "Gamma body" in sec2


def test_section_text_last_section_runs_to_end() -> None:
    doc = "# Only\n\nThe whole tail."
    outline = extract_outline_entries(doc, "markdown")
    assert "whole tail" in section_text(doc, outline, 0)


def test_section_text_bad_index() -> None:
    outline = [OutlineEntry(level=1, title="A", position=0)]
    try:
        section_text("# A", outline, 5)
    except IndexError:
        pass
    else:
        raise AssertionError("expected IndexError")


def test_structured_summary_includes_headings_and_fits_budget() -> None:
    text = "\n\n".join(f"Section {i} opening sentence with detail." for i in range(50))
    summary = structured_summary(text, max_tokens=80, outline_titles=["Intro", "Body", "End"])
    assert "Headings: Intro; Body; End" in summary
    assert estimate_tokens(summary) <= 100  # near budget
    assert len(summary) < len(text)


def test_structured_summary_never_larger_than_source() -> None:
    text = "short doc"
    summary = structured_summary(text, max_tokens=10000)
    assert len(summary) <= len(text)
