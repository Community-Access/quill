"""Golden tests for the plain-language explain engine.

Each syntax element must surface as a recognizable spoken phrase, and every
common mistake must come back as a sentence that names the character position
-- the whole point of the engine is that nothing regex-shaped reaches the ear.
"""

from __future__ import annotations

import pytest

from quill.core.regex_helper import explain_pattern


def _joined(pattern: str) -> str:
    result = explain_pattern(pattern)
    assert result.ok, f"{pattern!r} unexpectedly failed: {result.error}"
    assert result.steps, pattern
    assert result.error == ""
    assert result.error_position is None
    # Case-insensitive comparison surface: the engine capitalizes each spoken
    # step ("Any character."), and the goldens assert the phrase, not the case.
    return " ".join(result.steps).lower()


# -- literals and the dot -----------------------------------------------------


def test_literal_run_reads_as_text() -> None:
    assert "the text 'cat'" in _joined("cat")


def test_single_literal_character() -> None:
    assert "the character 'a'" in _joined("a")


def test_dot_is_any_character() -> None:
    assert "any character" in _joined(".")


# -- escapes ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("pattern", "phrase"),
    [
        (r"\d", "a digit"),
        (r"\D", "not a digit"),
        (r"\w", "word character"),
        (r"\W", "not a word character"),
        (r"\s", "whitespace character"),
        (r"\S", "not whitespace"),
        (r"\b", "word boundary"),
        (r"\B", "inside a word"),
        (r"\n", "newline character"),
        (r"\t", "tab character"),
        (r"\r", "carriage-return character"),
        (r"\\", "a backslash"),
        (r"\.", "a period"),
        (r"\?", "a question mark"),
    ],
)
def test_escapes(pattern: str, phrase: str) -> None:
    assert phrase in _joined(pattern).lower()


def test_backreference_by_number() -> None:
    assert "same text as group 1" in _joined(r"(\w+) \1")


# -- anchors ------------------------------------------------------------------


def test_caret_is_start_of_line() -> None:
    assert "start of a line" in _joined("^abc").lower()


def test_dollar_is_end_of_line() -> None:
    assert "end of a line" in _joined("abc$").lower()


def test_absolute_anchors() -> None:
    assert "very start of the text" in _joined(r"\Aabc").lower()
    assert "very end of the text" in _joined(r"abc\Z").lower()


# -- character classes --------------------------------------------------------


def test_simple_class() -> None:
    text = _joined("[abc]")
    assert "any of" in text
    assert "'a'" in text and "'b'" in text and "'c'" in text


def test_negated_class() -> None:
    assert "not any of" in _joined("[^abc]")


def test_class_range() -> None:
    assert "'a' through 'z'" in _joined("[a-z]")


def test_class_with_shorthand_and_escapes() -> None:
    text = _joined(r"[\d.-]")
    assert "a digit" in text
    assert "a period" in text
    assert "a hyphen" in text


# -- quantifiers --------------------------------------------------------------


def test_star_is_zero_or_more() -> None:
    assert "zero or more digits" in _joined(r"\d*").lower()


def test_plus_is_one_or_more() -> None:
    assert "one or more digits" in _joined(r"\d+").lower()


def test_question_mark_is_optionally() -> None:
    assert "optionally" in _joined(r"\d?").lower()


def test_exact_count() -> None:
    assert "exactly three" in _joined("a{3}").lower()


def test_open_ended_count() -> None:
    assert "two or more" in _joined("a{2,}").lower()


def test_bounded_count() -> None:
    assert "between two and five" in _joined("a{2,5}").lower()


def test_lazy_quantifier_reads_as_few_as_possible() -> None:
    assert "as few as possible" in _joined(r"\d+?").lower()


def test_quantified_literal_reads_naturally() -> None:
    # In "ca+t" only the 'a' repeats; the merge must not swallow it.
    text = _joined("ca+t").lower()
    assert "one or more" in text
    assert "'a'" in text


# -- groups and lookaround ----------------------------------------------------


def test_capture_group_is_numbered() -> None:
    assert "capture group 1" in _joined(r"(\d+)").lower()


def test_non_capturing_group_is_transparent() -> None:
    assert "the text 'abc'" in _joined("(?:abc)")


def test_named_group() -> None:
    assert "named 'year'" in _joined(r"(?P<year>\d{4})").lower()


def test_lookahead() -> None:
    assert "what comes next is" in _joined(r"(?=\d)").lower()


def test_negative_lookahead() -> None:
    assert "what comes next is not" in _joined(r"(?!\d)").lower()


def test_lookbehind() -> None:
    assert "just before" in _joined(r"(?<=\d)x").lower()


def test_negative_lookbehind() -> None:
    text = _joined(r"(?<!\d)x").lower()
    assert "just before" in text
    assert "not" in text


def test_named_backreference_is_honestly_advanced() -> None:
    text = _joined(r"(?P<word>\w+) (?P=word)")
    assert "same text as group 'word'" in text


def test_conditional_group_gets_generic_honest_step() -> None:
    assert "advanced" in _joined(r"(a)(?(1)b|c)").lower()


# -- alternation --------------------------------------------------------------


def test_alternation_reads_either_or() -> None:
    result = explain_pattern("cat|dog")
    assert result.ok
    assert result.steps[0].startswith("1. Either")
    assert result.steps[1].startswith("2. Or")
    assert "'cat'" in result.steps[0]
    assert "'dog'" in result.steps[1]


# -- inline flags -------------------------------------------------------------


def test_ignorecase_flag() -> None:
    assert "capital and small letters" in _joined("(?i)cat").lower()


def test_multiline_flag() -> None:
    assert "each line" in _joined("(?m)^a").lower()


def test_dotall_flag() -> None:
    assert "dot also matches newline" in _joined("(?s)a.b").lower()


def test_combined_flags() -> None:
    text = _joined("(?im)^cat").lower()
    assert "capital and small letters" in text
    assert "each line" in text


# -- the spec's worked example ------------------------------------------------


def test_price_pattern_reads_like_the_spec_example() -> None:
    text = _joined(r"^\d+(?:\.\d{2})?").lower()
    assert "start of a line" in text
    assert "one or more digits" in text
    assert "optionally" in text
    assert "a period" in text
    assert "exactly two digits" in text


def test_steps_are_numbered() -> None:
    result = explain_pattern(r"^\d+$")
    assert [step.split(".")[0] for step in result.steps] == ["1", "2", "3"]


def test_empty_pattern_is_explained() -> None:
    result = explain_pattern("")
    assert result.ok
    assert "empty pattern" in result.steps[0].lower()


# -- invalid patterns ---------------------------------------------------------


def _expect_error(pattern: str) -> tuple[str, int | None]:
    result = explain_pattern(pattern)
    assert not result.ok
    assert result.steps == ()
    assert result.error
    assert "character" in result.error, result.error
    return result.error, result.error_position


def test_unclosed_group() -> None:
    error, position = _expect_error("(abc")
    assert "Unclosed group" in error
    assert "character 1" in error
    assert position == 0


def test_unclosed_class() -> None:
    error, position = _expect_error("[abc")
    assert "Unclosed character class" in error
    assert "character 1" in error
    assert position == 0


def test_dangling_quantifier() -> None:
    error, position = _expect_error("*abc")
    assert "Dangling quantifier" in error
    assert "'*'" in error
    assert position == 0


def test_trailing_backslash() -> None:
    error, position = _expect_error("abc\\")
    assert "Trailing backslash" in error
    assert position is not None


def test_impossible_repeat_range() -> None:
    error, position = _expect_error("a{3,1}")
    assert "minimum is larger than the maximum" in error
    assert position is not None
