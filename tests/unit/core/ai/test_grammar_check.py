"""Unit tests for quill.core.ai.grammar_check."""

from __future__ import annotations

import json

import pytest

from quill.core.ai.grammar_check import (
    CATEGORIES,
    GrammarCheckAuthError,
    GrammarCheckError,
    GrammarCheckParseError,
    GrammarIssue,
    _chunk_document,
    _parse_issues,
    apply_grammar_fixes,
)

# ---------------------------------------------------------------------------
# CATEGORIES
# ---------------------------------------------------------------------------


def test_categories_contains_expected_keys() -> None:
    assert "grammar" in CATEGORIES
    assert "punctuation" in CATEGORIES
    assert "clarity" in CATEGORIES
    assert "style" in CATEGORIES
    assert "word_choice" in CATEGORIES


# ---------------------------------------------------------------------------
# GrammarIssue
# ---------------------------------------------------------------------------


def test_grammar_issue_frozen() -> None:
    issue = GrammarIssue("grammar", "is", "are", "verb agreement", "he is here")
    with pytest.raises((AttributeError, TypeError)):
        issue.original = "other"  # type: ignore[misc]


def test_grammar_issue_category_label() -> None:
    issue = GrammarIssue("word_choice", "big", "large", "formality", "big word")
    assert issue.category_label == "Word Choice"


def test_grammar_issue_unknown_category_label() -> None:
    issue = GrammarIssue("custom_cat", "a", "b", "reason", "context")
    assert issue.category_label == "Custom Cat"


# ---------------------------------------------------------------------------
# _chunk_document
# ---------------------------------------------------------------------------


def test_chunk_document_short_text_no_split() -> None:
    text = "Short text."
    chunks = _chunk_document(text)
    assert chunks == [text]


def test_chunk_document_splits_on_paragraph() -> None:
    text = "\n\n".join(["Paragraph one."] * 5)
    chunks = _chunk_document(
        text,
    )
    # With default max, should be one chunk; test with a small override
    from quill.core.ai import grammar_check as gc

    orig = gc._MAX_CHUNK_CHARS
    gc._MAX_CHUNK_CHARS = 30
    try:
        chunks = _chunk_document(text)
        assert len(chunks) > 1
        assert all(c.strip() for c in chunks)
    finally:
        gc._MAX_CHUNK_CHARS = orig


def test_chunk_document_no_empty_chunks() -> None:
    text = "A.\n\nB.\n\n\n\nC."
    from quill.core.ai import grammar_check as gc

    orig = gc._MAX_CHUNK_CHARS
    gc._MAX_CHUNK_CHARS = 5
    try:
        chunks = _chunk_document(text)
        assert all(c.strip() for c in chunks)
    finally:
        gc._MAX_CHUNK_CHARS = orig


# ---------------------------------------------------------------------------
# _parse_issues
# ---------------------------------------------------------------------------


def test_parse_issues_valid_json() -> None:
    source = "He go to the store every day."
    data = [
        {
            "category": "grammar",
            "original": "He go",
            "suggestion": "He goes",
            "explanation": "Subject-verb agreement.",
            "context": "He go to the store",
        }
    ]
    issues = _parse_issues(json.dumps(data), source)
    assert len(issues) == 1
    assert issues[0].original == "He go"
    assert issues[0].suggestion == "He goes"
    assert issues[0].category == "grammar"


def test_parse_issues_strips_markdown_fences() -> None:
    source = "He go to the store."
    raw = (
        '```json\n[{"category":"grammar","original":"He go","suggestion":"He goes",'
        '"explanation":"Agreement","context":"He go to"}]\n```'
    )
    issues = _parse_issues(raw, source)
    assert len(issues) == 1


def test_parse_issues_skips_item_not_in_source() -> None:
    source = "The cat sat."
    data = [
        {
            "category": "grammar",
            "original": "xyz not in source",
            "suggestion": "abc",
            "explanation": "x",
            "context": "xyz",
        }
    ]
    issues = _parse_issues(json.dumps(data), source)
    assert issues == []


def test_parse_issues_skips_missing_original_or_suggestion() -> None:
    source = "Hello there."
    data = [
        {
            "category": "grammar",
            "original": "",
            "suggestion": "X",
            "explanation": "e",
            "context": "c",
        }
    ]
    issues = _parse_issues(json.dumps(data), source)
    assert issues == []


def test_parse_issues_invalid_json_raises() -> None:
    with pytest.raises(GrammarCheckParseError):
        _parse_issues("not json", "some text")


def test_parse_issues_non_array_raises() -> None:
    with pytest.raises(GrammarCheckParseError):
        _parse_issues('{"key": "val"}', "some text")


def test_parse_issues_unknown_category_defaults_to_grammar() -> None:
    source = "He go to the store."
    data = [
        {
            "category": "unknown_cat",
            "original": "He go",
            "suggestion": "He goes",
            "explanation": "x",
            "context": "He go to",
        }
    ]
    issues = _parse_issues(json.dumps(data), source)
    assert len(issues) == 1
    assert issues[0].category == "grammar"


# ---------------------------------------------------------------------------
# apply_grammar_fixes
# ---------------------------------------------------------------------------


def test_apply_grammar_fixes_no_accepted() -> None:
    text = "He go to the store."
    issues = [GrammarIssue("grammar", "He go", "He goes", "agreement", "He go to")]
    result, count = apply_grammar_fixes(text, issues, accepted=set())
    assert result == text
    assert count == 0


def test_apply_grammar_fixes_accepted() -> None:
    text = "He go to the store."
    issues = [GrammarIssue("grammar", "He go", "He goes", "agreement", "He go to")]
    result, count = apply_grammar_fixes(text, issues, accepted={0})
    assert "He goes" in result
    assert count == 1


def test_apply_grammar_fixes_out_of_range_index_ignored() -> None:
    text = "Fine."
    issues: list[GrammarIssue] = []
    result, count = apply_grammar_fixes(text, issues, accepted={99})
    assert result == text
    assert count == 0


def test_apply_grammar_fixes_multiple_accepted() -> None:
    text = "He go to there store."
    issues = [
        GrammarIssue("grammar", "He go", "He goes", "agreement", "He go to"),
        GrammarIssue("grammar", "there store", "the store", "word choice", "to there store"),
    ]
    result, count = apply_grammar_fixes(text, issues, accepted={0, 1})
    assert count == 2
    assert "He goes" in result
    assert "the store" in result
    # Original misspelled phrases are fully replaced
    assert "there store" not in result


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


def test_auth_error_is_grammar_error() -> None:
    assert issubclass(GrammarCheckAuthError, GrammarCheckError)


def test_parse_error_is_grammar_error() -> None:
    assert issubclass(GrammarCheckParseError, GrammarCheckError)
