"""Runner safety and reporting: bounds, zero-width loops, and spoken locations."""

from __future__ import annotations

import re

from quill.core.regex_helper import preview_replace, run_pattern

# -- bounds -------------------------------------------------------------------


def test_max_matches_truncates_and_flags() -> None:
    result = run_pattern(r"\d", "1" * 50, max_matches=10)
    assert result.ok
    assert len(result.matches) == 10
    assert result.truncated


def test_under_the_match_limit_is_not_truncated() -> None:
    result = run_pattern(r"\d", "123", max_matches=10)
    assert result.ok
    assert len(result.matches) == 3
    assert not result.truncated


def test_oversized_text_is_truncated_and_flagged() -> None:
    result = run_pattern("x", "x" * 100, max_text_chars=10)
    assert result.ok
    assert result.truncated
    assert len(result.matches) == 10


# -- zero-width safety --------------------------------------------------------


def test_zero_width_pattern_terminates() -> None:
    result = run_pattern("a*", "bbb")
    assert result.ok
    # One empty match at each position, including the end of the text.
    assert len(result.matches) == 4
    assert all(match.text == "" for match in result.matches)


def test_zero_width_alternating_with_real_matches() -> None:
    result = run_pattern("a*", "ba")
    assert result.ok
    assert [match.text for match in result.matches] == ["", "a", ""]


# -- locations and groups -----------------------------------------------------


def test_line_and_column_are_one_based() -> None:
    text = "alpha\nbeta gamma\nbeta"
    result = run_pattern("beta", text)
    assert result.ok
    first, second = result.matches
    assert (first.line, first.column) == (2, 1)
    assert (second.line, second.column) == (3, 1)


def test_column_counts_within_the_line() -> None:
    result = run_pattern("gamma", "alpha\nbeta gamma\n")
    assert result.ok
    match = result.matches[0]
    assert (match.line, match.column) == (2, 6)
    assert (match.start, match.end) == (11, 16)


def test_groups_are_captured() -> None:
    result = run_pattern(r"(\d+)-(\d+)", "pages 10-20 and 30-40")
    assert result.ok
    assert result.matches[0].groups == ("10", "20")
    assert result.matches[1].groups == ("30", "40")


def test_optional_group_reports_none() -> None:
    result = run_pattern(r"(\d+)(\.\d+)?", "7 then 2.5")
    assert result.ok
    assert result.matches[0].groups == ("7", None)
    assert result.matches[1].groups == ("2", ".5")


def test_flags_are_honoured() -> None:
    result = run_pattern("beta", "BETA", flags=re.IGNORECASE)
    assert result.ok
    assert result.matches[0].text == "BETA"


# -- errors never raise -------------------------------------------------------


def test_invalid_pattern_reports_plain_language_error() -> None:
    result = run_pattern("(abc", "text")
    assert not result.ok
    assert result.matches == ()
    assert "Unclosed group" in result.error
    assert "character 1" in result.error


def test_invalid_class_reports_plain_language_error() -> None:
    result = run_pattern("[abc", "text")
    assert not result.ok
    assert "Unclosed character class" in result.error


# -- preview_replace ----------------------------------------------------------


def test_preview_lines_read_as_sentences() -> None:
    text = "\n" * 11 + "the colour here"
    lines = preview_replace("colour", "color", text)
    assert lines == ("'colour' to 'color' at line 12",)


def test_preview_respects_count() -> None:
    lines = preview_replace(r"\d", "N", "1 2 3 4", count=2)
    assert len(lines) == 2
    assert lines[0] == "'1' to 'N' at line 1"


def test_preview_expands_group_references() -> None:
    lines = preview_replace(r"(\w+)-(\w+)", r"\2-\1", "well-known")
    assert lines == ("'well-known' to 'known-well' at line 1",)


def test_preview_invalid_group_reference_is_plain_words() -> None:
    lines = preview_replace(r"(a)", r"\2", "abc")
    assert len(lines) == 1
    assert "group" in lines[0]
    assert "does not define" in lines[0]


def test_preview_invalid_pattern_is_plain_words() -> None:
    lines = preview_replace("(abc", "x", "text")
    assert len(lines) == 1
    assert "could not be used" in lines[0]
    assert "Unclosed group" in lines[0]


def test_preview_zero_width_terminates() -> None:
    lines = preview_replace("a*", "-", "bbb", count=10)
    assert len(lines) == 4
