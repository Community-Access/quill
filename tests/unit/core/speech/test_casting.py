"""Tests for explicit voice casting (rules, matching, precedence)."""

from __future__ import annotations

from quill.core.speech.casting import cast_voices, normalize_rules, voice_for_section


def test_normalize_drops_blank_halves_and_keeps_order() -> None:
    rules = normalize_rules([(" Chapter * ", " af_bella "), ("", "x"), ("#2", ""), ("#3", "v3")])
    assert rules == [("Chapter *", "af_bella"), ("#3", "v3")]


def test_number_pattern_matches_exactly_one_section() -> None:
    rules = [("#1", "opener_voice")]
    assert voice_for_section(rules, 1, "Anything") == "opener_voice"
    assert voice_for_section(rules, 2, "Anything") == ""
    assert voice_for_section([("#x", "v")], 1, "Anything") == ""  # junk number: no match


def test_title_glob_is_case_insensitive_and_first_match_wins() -> None:
    rules = [("*interview*", "guest"), ("chapter *", "narrator")]
    assert voice_for_section(rules, 5, "Chapter 5: The Interview") == "guest"
    assert voice_for_section(rules, 4, "CHAPTER 4") == "narrator"
    assert voice_for_section(rules, 9, "Epilogue") == ""


def test_exact_title_pattern() -> None:
    assert voice_for_section([("Epilogue", "quiet")], 9, "  epilogue ") == "quiet"


def test_cast_voices_distinct_in_first_use_order() -> None:
    rules = [("#1", "a"), ("#2", "b"), ("#3", "a")]
    assert cast_voices(rules) == ["a", "b"]
