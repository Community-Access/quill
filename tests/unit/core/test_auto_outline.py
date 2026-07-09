"""Tests for Accessible AutoOutline (#894): literal-text heading numbering."""

from __future__ import annotations

from quill.core.auto_outline import (
    OutlineStyle,
    apply_auto_outline,
    remove_outline_numbers,
    strip_outline_number,
)


def test_numeric_style_numbers_nested_headings() -> None:
    text = "# Intro\n## Background\n## Scope\n# Methods\n## Data\n"
    result = apply_auto_outline(text, OutlineStyle.NUMERIC)
    assert result == (
        "# 1. Intro\n"
        "## 1.1. Background\n"
        "## 1.2. Scope\n"
        "# 2. Methods\n"
        "## 2.1. Data\n"
    )


def test_numbering_resets_on_shallower_heading() -> None:
    text = "# One\n## One One\n### One One One\n# Two\n"
    result = apply_auto_outline(text)
    assert "# 2. Two" in result
    assert "1.1.1" in result
    # The second top-level heading has no leftover 1.1.1-style children.
    lines = result.splitlines()
    assert lines[-1] == "# 2. Two"


def test_legal_style_uses_roman_alpha_then_numeric() -> None:
    text = "# First\n## Sub\n### SubSub\n"
    result = apply_auto_outline(text, OutlineStyle.LEGAL)
    assert "# I. First" in result
    assert "## I.A. Sub" in result
    assert "### I.A.1. SubSub" in result


def test_second_top_level_legal_heading_is_II() -> None:
    text = "# First\n# Second\n"
    result = apply_auto_outline(text, OutlineStyle.LEGAL)
    assert "# II. Second" in result


def test_applying_twice_is_idempotent() -> None:
    text = "# Intro\n## Background\n"
    once = apply_auto_outline(text)
    twice = apply_auto_outline(once)
    assert once == twice


def test_reapplying_with_a_different_style_replaces_not_stacks() -> None:
    text = "# Intro\n## Background\n"
    numeric = apply_auto_outline(text, OutlineStyle.NUMERIC)
    legal = apply_auto_outline(numeric, OutlineStyle.LEGAL)
    assert legal == "# I. Intro\n## I.A. Background\n"


def test_heading_attributes_are_preserved() -> None:
    text = "# Intro {#intro}\n"
    result = apply_auto_outline(text)
    assert result == "# 1. Intro {#intro}\n"


def test_no_headings_returns_text_unchanged() -> None:
    text = "Just a paragraph, no headings here.\n"
    assert apply_auto_outline(text) == text


def test_fenced_code_block_headings_are_ignored() -> None:
    text = "# Real Heading\n```\n# not a heading\n```\n## Real Sub\n"
    result = apply_auto_outline(text)
    assert "# 1. Real Heading" in result
    assert "## 1.1. Real Sub" in result
    assert "# not a heading" in result  # untouched, inside the fence


def test_strip_outline_number_removes_numeric_prefix() -> None:
    assert strip_outline_number("1.2.3. My Heading") == "My Heading"


def test_strip_outline_number_removes_legal_prefix() -> None:
    assert strip_outline_number("I.A.1. My Heading") == "My Heading"


def test_strip_outline_number_leaves_unnumbered_title_untouched() -> None:
    assert strip_outline_number("My Heading") == "My Heading"


def test_remove_outline_numbers_reverts_a_numbered_document() -> None:
    text = "# Intro\n## Background\n"
    numbered = apply_auto_outline(text)
    reverted = remove_outline_numbers(numbered)
    assert reverted == text


def test_remove_outline_numbers_is_a_no_op_on_unnumbered_text() -> None:
    text = "# Intro\n## Background\n"
    assert remove_outline_numbers(text) == text


def test_skipped_heading_level_fills_a_zero_placeholder() -> None:
    # Level jumps from 1 straight to 3 with no intervening level 2.
    text = "# Top\n### Deep\n"
    result = apply_auto_outline(text)
    assert "# 1. Top" in result
    assert "### 1.0.1. Deep" in result
