"""Tests for the deterministic output-quality filter (#1319)."""

from __future__ import annotations

from quill.core.ai.quality_filter import (
    NEGATIVE_EXAMPLE_PAIRS,
    find_quality_issues,
    negative_examples_block,
    retry_instruction,
)


def test_clean_text_has_no_issues() -> None:
    assert find_quality_issues("The results were positive. The deadline is Friday.") == []


def test_empty_and_blank_are_clean() -> None:
    assert find_quality_issues("") == []
    assert find_quality_issues("   \n ") == []


def test_detects_hedging_judgment_and_filler() -> None:
    text = (
        "In today's world, it seems the plan is clearly the best. "
        "It is important to note the risks."
    )
    issues = find_quality_issues(text)
    assert "in today's world" in issues
    assert "it seems" in issues
    assert "clearly" in issues
    assert "it is important to note" in issues


def test_matching_is_case_insensitive() -> None:
    assert "clearly" in find_quality_issues("CLEARLY this works.")
    assert "arguably" in find_quality_issues("Arguably the best.")


def test_word_boundary_avoids_false_positives() -> None:
    # "surely" must not fire inside "measurely"/"insurely"; "of course" needs the
    # whole phrase, not "course" alone.
    assert find_quality_issues("The measurement of the golf course was exact.") == []


def test_each_issue_reported_once_in_stable_order() -> None:
    text = "Clearly, clearly, it seems it seems."
    issues = find_quality_issues(text)
    assert issues.count("clearly") == 1
    assert issues.count("it seems") == 1
    # hedging group is scanned before the judgment group
    assert issues.index("it seems") < issues.index("clearly")


def test_retry_instruction_is_empty_without_issues() -> None:
    assert retry_instruction([]) == ""


def test_retry_instruction_names_each_issue() -> None:
    instruction = retry_instruction(["it seems", "clearly"])
    assert '"it seems"' in instruction
    assert '"clearly"' in instruction
    assert "revised text" in instruction.lower()


def test_negative_examples_block_carries_the_pairs() -> None:
    block = negative_examples_block()
    for weak, better in NEGATIVE_EXAMPLE_PAIRS:
        assert weak in block
        assert better in block
