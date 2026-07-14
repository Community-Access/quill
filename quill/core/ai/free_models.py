"""Free / low-cost model catalog and classification (writing-first).

Pure, ``wx``-free helpers that classify provider models into cost tiers
(``free`` / ``low`` / ``flagship``), rank them for writing quality, and flag
whether a model is dependable for multi-step tool use (agents). This is the data
layer behind the "Use free AI (recommended)" onboarding path and the AI Hub
"Free" filter.

Design notes:

- **Free is derived, not hardcoded.** A model is free when the provider reports
  zero prompt+completion pricing, or (for OpenRouter) when its id ends in the
  documented ``:free`` suffix. The suffix is the durable signal, so the classifier
  keeps working as OpenRouter rotates its free line-up. A tiny curated allowlist
  only provides sensible *offline* defaults and writing-quality ordering.
- **Writing quality** is a coarse rank (bigger, stronger instruct models sort
  first) so the best available free model can be chosen without a benchmark.
- **Tool use** is conservative: very small models (<= 3B) are marked unreliable
  for the agent tool loop, which drives the graceful single-shot fallback.

This module builds on :mod:`quill.core.ai.model_manager` (local GGUF registry)
and reuses the already-audited ``ai_chat`` network helpers for live discovery.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

# Cost tiers. Ordered from cheapest to most capable/expensive.
TIER_FREE = "free"
TIER_LOW = "low"
TIER_FLAGSHIP = "flagship"

COST_TIERS: tuple[str, ...] = (TIER_FREE, TIER_LOW, TIER_FLAGSHIP)

# A model whose per-token prompt price is at or below this (USD/token) is treated
# as "low" cost rather than flagship. 1e-6 USD/token ~= $1 per million tokens,
# which covers the small/fast cloud models (gpt-4o-mini, haiku, flash).
_LOW_COST_MAX_USD_PER_TOKEN = 1e-6


@dataclass(frozen=True, slots=True)
class ModelInfo:
    """Classification of a single model for the free/low-cost catalog."""

    id: str
    provider: str
    cost_tier: str
    writing_quality: int
    tool_use: bool
    display_name: str = ""

    @property
    def is_free(self) -> bool:
        return self.cost_tier == TIER_FREE


# Curated, offline-safe defaults: known-good free OpenRouter writing models, best
# first. These may rotate over time; the ``:free`` suffix heuristic is what keeps
# live classification correct regardless of this list. Kept intentionally small.
PREFERRED_FREE_MODELS: dict[str, tuple[str, ...]] = {
    "openrouter": (
        "meta-llama/llama-3.3-70b-instruct:free",
        "qwen/qwen-2.5-72b-instruct:free",
        "google/gemma-2-9b-it:free",
        "mistralai/mistral-7b-instruct:free",
    ),
}

# Known flagship / low-cost cloud model ids by substring, used when pricing
# metadata is unavailable (e.g. the OpenAI/Anthropic/Gemini native endpoints,
# which do not expose OpenRouter-style pricing on /models).
_FLAGSHIP_HINTS: tuple[str, ...] = (
    "gpt-4.1",
    "gpt-4o",  # note: gpt-4o-mini is caught by _LOW_HINTS first
    "claude-sonnet",
    "claude-opus",
    "gemini-2.5-pro",
    "o1",
    "o3",
)
_LOW_HINTS: tuple[str, ...] = (
    "gpt-4o-mini",
    "gpt-4.1-mini",
    "haiku",
    "flash",
    "-mini",
)

# Parameter-size tokens like "70b", "7b", "1.5b", "405b".
_SIZE_RE = re.compile(r"(\d+(?:\.\d+)?)\s*b\b", re.IGNORECASE)


def _to_float(value: object) -> float | None:
    """Best-effort parse of a pricing value (OpenRouter uses strings like "0")."""
    if value is None:
        return None
    if isinstance(value, bool):  # guard: bool is an int subclass
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    return None


def is_free_pricing(pricing: Mapping[str, object] | None) -> bool:
    """True when both prompt and completion prices are present and zero."""
    if not pricing:
        return False
    prompt = _to_float(pricing.get("prompt"))
    completion = _to_float(pricing.get("completion"))
    if prompt is None or completion is None:
        return False
    return prompt == 0.0 and completion == 0.0


def has_free_suffix(model_id: str) -> bool:
    """True for the documented OpenRouter ``:free`` model-id convention."""
    return model_id.strip().lower().endswith(":free")


def is_free_model(
    model_id: str,
    pricing: Mapping[str, object] | None = None,
    provider: str = "",
) -> bool:
    """Classify a model as free via the ``:free`` suffix or zero pricing."""
    return has_free_suffix(model_id) or is_free_pricing(pricing)


def _largest_size_b(model_id: str) -> float:
    sizes = [float(m) for m in _SIZE_RE.findall(model_id)]
    return max(sizes) if sizes else 0.0


def supports_tool_use(model_id: str) -> bool:
    """Whether a model is dependable for the multi-step agent tool loop.

    Conservative by design: models at or below 3B parameters are judged
    unreliable (they drive the single-shot agent fallback). Unknown-size models
    default to ``True`` so we do not needlessly downgrade capable cloud models.
    """
    size = _largest_size_b(model_id.strip().lower())
    if size and size <= 3.0:
        return False
    return True


def writing_quality(model_id: str) -> int:
    """Coarse writing-quality rank (higher is better) for ordering.

    Driven mostly by parameter count, with a nudge for known-strong families.
    Meant only to sort candidates, not to benchmark them.
    """
    lowered = model_id.strip().lower()
    size = _largest_size_b(lowered)
    if size >= 60:
        score = 90
    elif size >= 30:
        score = 75
    elif size >= 12:
        score = 60
    elif size >= 7:
        score = 45
    elif size >= 4:
        score = 30
    elif size > 0:
        score = 15
    else:
        score = 50  # unknown size: assume a capable hosted model
    if any(hint in lowered for hint in ("llama-3.3", "qwen-2.5", "qwen2.5", "mistral-large")):
        score += 5
    return score


def cost_tier_for(
    model_id: str,
    pricing: Mapping[str, object] | None = None,
    provider: str = "",
) -> str:
    """Classify a model into ``free`` / ``low`` / ``flagship``."""
    if is_free_model(model_id, pricing, provider):
        return TIER_FREE
    prompt = _to_float(pricing.get("prompt")) if pricing else None
    if prompt is not None:
        return TIER_LOW if prompt <= _LOW_COST_MAX_USD_PER_TOKEN else TIER_FLAGSHIP
    lowered = model_id.strip().lower()
    if any(hint in lowered for hint in _LOW_HINTS):
        return TIER_LOW
    if any(hint in lowered for hint in _FLAGSHIP_HINTS):
        return TIER_FLAGSHIP
    return TIER_FLAGSHIP


def classify_model(
    model_id: str,
    provider: str,
    pricing: Mapping[str, object] | None = None,
    display_name: str = "",
) -> ModelInfo:
    """Build a :class:`ModelInfo` from an id, provider, and optional pricing."""
    return ModelInfo(
        id=model_id,
        provider=provider,
        cost_tier=cost_tier_for(model_id, pricing, provider),
        writing_quality=writing_quality(model_id),
        tool_use=supports_tool_use(model_id),
        display_name=display_name or model_id,
    )


def _rank_key(info: ModelInfo) -> tuple[int, int, str]:
    # Free first (tier index), then higher writing quality, then id for stability.
    tier_index = COST_TIERS.index(info.cost_tier) if info.cost_tier in COST_TIERS else 99
    return (tier_index, -info.writing_quality, info.id)


def rank_models(models: Sequence[ModelInfo]) -> list[ModelInfo]:
    """Sort models so the best free writing model comes first."""
    return sorted(models, key=_rank_key)


def free_models(models: Sequence[ModelInfo]) -> list[ModelInfo]:
    """The free subset of ``models``, ranked best-first."""
    return rank_models([m for m in models if m.is_free])


def best_free_writing_model(
    provider: str,
    available: Sequence[str] | None = None,
) -> str | None:
    """Pick the best free writing model id for ``provider``.

    With a live ``available`` id list, prefer a curated model that is actually
    offered, else the best-ranked ``:free`` model on offer. With no list, fall
    back to the first curated default so onboarding still has a sensible pick
    while offline.
    """
    normalized = provider.strip().lower()
    preferred = PREFERRED_FREE_MODELS.get(normalized, ())
    if available is None:
        return preferred[0] if preferred else None
    available_set = {a.strip() for a in available}
    for candidate in preferred:
        if candidate in available_set:
            return candidate
    free_ids = [a for a in available if is_free_model(a, provider=normalized)]
    if not free_ids:
        return None
    ranked = rank_models([classify_model(a, normalized) for a in free_ids])
    return ranked[0].id if ranked else None


@dataclass(frozen=True, slots=True)
class FreePathAdvice:
    """A strongly-advised free path, with an honest risk note and good default."""

    rank: int
    title: str
    summary: str
    risk_note: str
    provider: str
    model: str
    needs_key: bool


def recommended_free_paths() -> list[FreePathAdvice]:
    """The strongly-advised free options, best-results first, with risk notes.

    Two dependable, zero-cost paths are always offered so onboarding can direct
    firmly instead of leaving people to guess:

    1. **Best quality (free):** OpenRouter with the user's own free key, defaulted
       to a strong free writing model. Rate limited to *their own* free quota, so
       there is no cost or shared-quota risk to anyone else.
    2. **Most private (free):** fully on-device local model — nothing leaves the
       computer, no account, works offline; quality is more modest.

    The honest non-risk guidance is explicit: free hosted endpoints may retain or
    train on prompts under their terms, so the copy advises against sending
    confidential text there and points privacy-sensitive users at the local path.
    """
    best_free = best_free_writing_model("openrouter") or "meta-llama/llama-3.3-70b-instruct:free"
    quality = FreePathAdvice(
        rank=1,
        title="Best quality, free",
        summary=(
            "Use OpenRouter with your own free key and a strong free writing model. "
            "Much better output than a small on-device model, and still costs nothing."
        ),
        risk_note=(
            "Uses your own free daily quota, so there is no shared limit or cost to "
            "anyone else. Free hosted models may log or train on what you send, so "
            "keep confidential text on the private on-device option below."
        ),
        provider="openrouter",
        model=best_free,
        needs_key=True,
    )
    private = FreePathAdvice(
        rank=2,
        title="Most private, free",
        summary=(
            "Run a model on your own computer. No account, works offline, and your "
            "writing never leaves the device. Quality is more modest than the cloud "
            "free models."
        ),
        risk_note="Nothing leaves your computer. No key, no quota, no cost.",
        provider="ollama",
        model="",
        needs_key=False,
    )
    return [quality, private]


def _build_free_path_guidance() -> str:
    """Short, warm, honest advice for the best zero-cost paths, with a good default.

    Kept deliberately tight — two lines and a privacy note — so the wizard's connect
    step stays magical rather than a wall of text. The named free model comes from
    :func:`best_free_writing_model`, so the copy stays in sync with the catalog.
    """
    free_model = best_free_writing_model("openrouter") or "a strong free model"
    return (
        "Prefer AI at no cost? Two great free paths:\n"
        f"- Best quality: pick OpenRouter, tap Get API key for a free key, and QUILL "
        f"preselects a strong free model ({free_model}) for you.\n"
        "- Most private: pick Ollama to run on your own computer — no key, works "
        "offline, nothing leaves your device.\n"
        "Free cloud models may use what you send, so keep private writing on the "
        "on-device option."
    )


# Strong free-path guidance, built once at import for the wizard's connect step.
FREE_PATH_GUIDANCE: str = _build_free_path_guidance()


def stronger_model_hint(needs_tool_use: bool, model: str) -> str:
    """A soft, non-blocking note when a tool-loop agent runs on a small model.

    Returns an empty string when there's nothing to say (the agent is single-shot,
    or the model is capable). Never blocks — this is only a spoken cue that the
    result may be better on a stronger model.
    """
    if needs_tool_use and model and not supports_tool_use(model):
        return "This agent works best with a stronger model; a small model may do less here."
    return ""


def resolve_model_for_task(
    task_verb: str,
    configured: Sequence[ModelInfo] | None = None,
) -> ModelInfo | None:
    """Pick the cheapest configured model capable of a writing task.

    Light verbs (rewrite, shorten, proofread, summarize, continue, translate, tone)
    run well on free models, so the cheapest free/low model wins. Heavier verbs
    (agentic, multi-step, long-document reasoning) prefer a tool-use-capable model.
    Returns ``None`` when ``configured`` is empty. This is advisory routing — the
    caller may still honor an explicit user choice.
    """
    if not configured:
        return None
    ranked = rank_models(configured)
    heavy = task_verb.strip().lower() in _HEAVY_TASK_VERBS
    if heavy:
        capable = [m for m in ranked if m.tool_use]
        if capable:
            # Cheapest capable model: free first, then by quality (rank order).
            return capable[0]
    return ranked[0]


# Writing verbs that need multi-step reasoning or tool use; everything else is
# "light" and runs fine on a free model.
_HEAVY_TASK_VERBS: frozenset[str] = frozenset({
    "agent",
    "research",
    "qa",
    "accessibility",
    "outline",
    "toc",
    "publish",
})


def fetch_classified_models(
    provider_id: str,
    api_key: str = "",
    base_url: str = "",
) -> list[ModelInfo]:
    """Fetch and classify a provider's models, preserving pricing when present.

    Reuses the audited ``ai_chat`` network helpers (no new egress site). Returns
    a best-first ranked list. Raises the underlying ``ai_chat`` errors on failure
    so callers can surface a speakable message.
    """
    from quill.core import ai_chat

    raw = ai_chat.list_models_raw(provider_id, api_key=api_key, base_url=base_url)
    classified = [
        classify_model(
            item.get("id", ""),
            provider_id,
            pricing=item.get("pricing") if isinstance(item.get("pricing"), Mapping) else None,
            display_name=str(item.get("name") or item.get("id") or ""),
        )
        for item in raw
        if item.get("id")
    ]
    return rank_models(classified)
