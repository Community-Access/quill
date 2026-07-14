"""Unit tests for the combined translation + TTS cost estimate (roadmap §7)."""

from __future__ import annotations

from quill.core.speech.cost_estimate import (
    AI_TRANSLATION_USD_PER_MILLION_CHARS,
    CostEstimate,
    estimate_combined,
    estimate_translation_usd,
    estimate_tts_usd,
)


def test_libretranslate_and_local_ai_are_free() -> None:
    assert estimate_translation_usd("libretranslate", 1_000_000) == 0.0
    assert estimate_translation_usd("ai_assistant", 1_000_000, ai_metered=False) == 0.0


def test_cloud_ai_translation_uses_blended_rate() -> None:
    cost = estimate_translation_usd("ai_assistant", 1_000_000, languages=2)
    assert cost == 2 * AI_TRANSLATION_USD_PER_MILLION_CHARS


def test_unknown_translation_provider_is_none() -> None:
    assert estimate_translation_usd("mystery", 1000) is None


def test_tts_sums_known_and_skips_unknown() -> None:
    # OpenAI tts-1 has a known per-char rate; an unknown model contributes nothing.
    known = estimate_tts_usd([("openai", "tts-1")], 1_000_000)
    assert known is not None and known > 0
    assert estimate_tts_usd([("openai", "no-such-model")], 1_000_000) is None


def test_combined_total_and_summary() -> None:
    est = estimate_combined(
        translation_provider="ai_assistant",
        cloud_tts_targets=[("openai", "tts-1")],
        char_count=1_000_000,
        languages=1,
    )
    assert est.translation_usd == AI_TRANSLATION_USD_PER_MILLION_CHARS
    assert est.tts_usd is not None and est.tts_usd > 0
    assert est.total_usd == est.translation_usd + est.tts_usd
    assert est.is_metered
    s = est.summary()
    assert "translation" in s and "speech" in s and "$" in s


def test_estimate_none_when_nothing_known() -> None:
    est = CostEstimate(translation_usd=None, tts_usd=None)
    assert est.total_usd is None and not est.is_metered
    assert est.summary() == "Estimated cloud cost: unavailable"
