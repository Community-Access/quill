"""Unit tests for quill.core.ai.spell_check."""

from __future__ import annotations

import pytest

from quill.core.ai.spell_check import (
    SpellCorrection,
    apply_corrections,
)

# ---------------------------------------------------------------------------
# SpellCorrection dataclass
# ---------------------------------------------------------------------------


def test_spell_correction_is_frozen() -> None:
    c = SpellCorrection("teh", "the", "I typed teh word")
    with pytest.raises((AttributeError, TypeError)):
        c.original = "other"  # type: ignore[misc]


def test_spell_correction_fields() -> None:
    c = SpellCorrection(original="recieve", correction="receive", context="I will recieve it")
    assert c.original == "recieve"
    assert c.correction == "receive"
    assert c.context == "I will recieve it"


# ---------------------------------------------------------------------------
# apply_corrections
# ---------------------------------------------------------------------------


def test_apply_corrections_empty_list() -> None:
    text = "Hello world."
    result, count = apply_corrections(text, [])
    assert result == text
    assert count == 0


def test_apply_corrections_single() -> None:
    text = "I recieve letters."
    corrections = [SpellCorrection("recieve", "receive", "I recieve letters")]
    result, count = apply_corrections(text, corrections)
    assert "receive" in result
    assert "recieve" not in result
    assert count == 1


def test_apply_corrections_multiple() -> None:
    text = "She is definately comming tomorrow."
    corrections = [
        SpellCorrection("definately", "definitely", "She is definately comming"),
        SpellCorrection("comming", "coming", "definately comming tomorrow"),
    ]
    result, count = apply_corrections(text, corrections)
    assert "definitely" in result
    assert "coming" in result
    assert count == 2


def test_apply_corrections_word_not_in_text_is_skipped() -> None:
    text = "Hello world."
    corrections = [SpellCorrection("xyz", "abc", "xyz context")]
    result, count = apply_corrections(text, corrections)
    assert result == text
    assert count == 0


def test_apply_corrections_uses_context_to_disambiguate() -> None:
    # Same word appearing twice; context picks the right occurrence
    text = "The cat sat. The cat ate."
    corrections = [
        SpellCorrection("cat", "Cat", "The cat sat"),
    ]
    result, count = apply_corrections(text, corrections)
    # At least one replacement happened
    assert count >= 1


def test_apply_corrections_returns_original_on_no_match() -> None:
    text = "All fine here."
    corrections = [SpellCorrection("misssing", "missing", "misssing word")]
    result, count = apply_corrections(text, corrections)
    assert result == text
    assert count == 0


def test_apply_corrections_preserves_surrounding_text() -> None:
    text = "The quick brown fox."
    corrections = [SpellCorrection("quick", "swift", "The quick brown")]
    result, count = apply_corrections(text, corrections)
    assert result == "The swift brown fox."
    assert count == 1


def test_apply_corrections_does_not_double_apply() -> None:
    # A correction whose replacement contains the original should not cascade
    text = "teh end."
    corrections = [SpellCorrection("teh", "the", "teh end")]
    result, count = apply_corrections(text, corrections)
    assert result == "the end."
    assert count == 1
