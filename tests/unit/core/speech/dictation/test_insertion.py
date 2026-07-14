from __future__ import annotations

from quill.core.speech.dictation.insertion import normalize_for_insertion


def test_trims_surrounding_whitespace() -> None:
    assert normalize_for_insertion("  hello world  ") == "hello world "


def test_empty_or_whitespace_only_yields_empty() -> None:
    assert normalize_for_insertion("   ") == ""
    assert normalize_for_insertion("") == ""


def test_joining_space_added_after_word_char() -> None:
    # Caret sits right after "the": dictating "cat" should not glue to "thecat".
    out = normalize_for_insertion("cat", prefix_char="e", suffix_char="")
    assert out == " cat "


def test_no_joining_space_after_open_bracket_or_space() -> None:
    assert normalize_for_insertion("cat", prefix_char="(", suffix_char="").startswith("cat")
    assert normalize_for_insertion("cat", prefix_char=" ", suffix_char="").startswith("cat")


def test_no_leading_space_before_punctuation() -> None:
    out = normalize_for_insertion(".", prefix_char="d", suffix_char="")
    assert out.startswith(".")  # never " ." after a word


def test_no_trailing_space_before_existing_text() -> None:
    out = normalize_for_insertion("cat", prefix_char=" ", suffix_char="s")
    assert out == "cat"  # butting against more letters: no trailing space


def test_trailing_space_when_followed_by_whitespace() -> None:
    assert normalize_for_insertion("cat", prefix_char=" ", suffix_char=" ") == "cat "


def test_intelligent_spacing_off_only_trims() -> None:
    out = normalize_for_insertion(
        "  cat  ", prefix_char="e", suffix_char="s", intelligent_spacing=False
    )
    assert out == "cat"
