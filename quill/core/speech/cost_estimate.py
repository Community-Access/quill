"""Combined translation + TTS cost estimate for cloud runs (roadmap §7).

Translated audio export can meter twice for cloud providers: once to translate the
text (when the configured AI provider is a paid cloud model) and once to synthesize
it (OpenAI / Gemini / ElevenLabs). This module produces a single, honest *estimate*
the UI shows before a run so the cost is never a surprise.

It is deliberately conservative and clearly approximate:

* **TTS** is priced precisely per provider/model via :mod:`quill.core.ai.cloud_tts`.
* **Translation** is free for LibreTranslate (local/self-hosted) and for a local AI
  model; for a paid cloud AI it is estimated from a blended per-character rate,
  since the exact price depends on the chosen model.

``wx``-free and strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass

# A blended, model-agnostic rate for cloud-LLM translation, per million source
# characters. Translation reads the source and writes a similar-length output; at
# ~4 chars/token that is on the order of half a million tokens per million chars
# round-trip. Intentionally conservative — guidance, not a quote.
AI_TRANSLATION_USD_PER_MILLION_CHARS = 12.0


@dataclass(frozen=True, slots=True)
class CostEstimate:
    """An approximate USD cost split into its translation and speech parts.

    A ``None`` part means "no known price" (e.g. a local model, or a TTS
    provider/model without a published rate) — distinct from a known ``0.0``.
    """

    translation_usd: float | None
    tts_usd: float | None

    @property
    def total_usd(self) -> float | None:
        parts = [c for c in (self.translation_usd, self.tts_usd) if c is not None]
        return sum(parts) if parts else None

    @property
    def is_metered(self) -> bool:
        """True when any part is a known, non-zero cost worth surfacing."""
        total = self.total_usd
        return total is not None and total > 0.0

    def summary(self) -> str:
        """A one-line human estimate, e.g. ``~$0.1234 (translation ~$0.05, speech ~$0.07)``."""
        total = self.total_usd
        if total is None:
            return "Estimated cloud cost: unavailable"
        bits: list[str] = []
        if self.translation_usd is not None:
            bits.append(f"translation ~${self.translation_usd:.4f}")
        if self.tts_usd is not None:
            bits.append(f"speech ~${self.tts_usd:.4f}")
        detail = f" ({', '.join(bits)})" if bits else ""
        return f"Estimated cloud cost: ~${total:.4f}{detail} (approximate)"


def estimate_translation_usd(
    provider: str, char_count: int, *, languages: int = 1, ai_metered: bool = True
) -> float | None:
    """Estimate translation cost for *char_count* chars across *languages* targets.

    LibreTranslate and a local AI model are free (``0.0``); a paid cloud AI provider
    is estimated from :data:`AI_TRANSLATION_USD_PER_MILLION_CHARS`. An unknown
    provider returns ``None``.
    """
    chars = max(0, int(char_count)) * max(1, int(languages))
    backend = provider.strip().lower()
    if backend == "libretranslate":
        return 0.0
    if backend == "ai_assistant":
        if not ai_metered:
            return 0.0
        return (chars / 1_000_000.0) * AI_TRANSLATION_USD_PER_MILLION_CHARS
    return None


def estimate_tts_usd(targets: list[tuple[str, str]], char_count: int) -> float | None:
    """Sum the TTS cost over cloud *targets* (``(provider, model)``) for *char_count*.

    Returns ``None`` when no target has a known price (so the UI can omit the line
    rather than imply free); a target without a published rate is skipped.
    """
    from quill.core.ai import cloud_tts

    total = 0.0
    any_known = False
    for provider, model in targets:
        cost = cloud_tts.estimate_cost_usd(provider, model, char_count)
        if cost is not None:
            total += cost
            any_known = True
    return total if any_known else None


def estimate_combined(
    *,
    translation_provider: str,
    cloud_tts_targets: list[tuple[str, str]],
    char_count: int,
    languages: int = 1,
    ai_metered: bool = True,
) -> CostEstimate:
    """Build the combined estimate for a translated cloud run.

    *cloud_tts_targets* are the ``(provider, model)`` pairs of the **cloud** voices
    only (local engines cost nothing). *char_count* is the per-language character
    count of the document; TTS is charged per language, so the total TTS cost scales
    with the number of cloud targets via *cloud_tts_targets*.
    """
    translation = estimate_translation_usd(
        translation_provider, char_count, languages=languages, ai_metered=ai_metered
    )
    tts = estimate_tts_usd(cloud_tts_targets, char_count)
    return CostEstimate(translation_usd=translation, tts_usd=tts)
