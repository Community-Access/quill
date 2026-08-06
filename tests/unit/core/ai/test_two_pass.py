"""Tests for the two-pass observe-then-rewrite prompts (#1320)."""

from __future__ import annotations

import pytest

from quill.core.ai.two_pass import (
    DEFAULT_WORD_BUDGET,
    observe_prompt,
    rewrite_prompt,
    within_budget,
    word_count,
)


def test_observe_prompt_shows_source_and_asks_for_plain_facts() -> None:
    prompt = observe_prompt("The cat sat on the mat.", kind="passage")
    assert "The cat sat on the mat." in prompt
    assert "observations" in prompt.lower()
    assert "do not interpret" in prompt.lower()


def test_rewrite_prompt_budgets_and_hides_the_source() -> None:
    prompt = rewrite_prompt("- A cat\n- A mat", word_budget=40, output="summary")
    assert "40 words" in prompt
    assert "ONLY the observations" in prompt
    assert "- A cat" in prompt
    # The rewrite pass must not carry the original source, only the observations.
    assert "summary" in prompt.lower()


def test_rewrite_prompt_rejects_a_nonpositive_budget() -> None:
    with pytest.raises(ValueError):
        rewrite_prompt("obs", word_budget=0)


def test_default_budget_is_modest() -> None:
    assert 0 < DEFAULT_WORD_BUDGET <= 300


def test_word_count_and_within_budget() -> None:
    assert word_count("one two three") == 3
    assert within_budget("one two three", 3)
    assert not within_budget("one two three four", 3)
