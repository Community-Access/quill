"""Provider catalog metadata for the AI assistant.

Pure, wx-free helpers describing each supported assistant provider: default
hosts and models, whether an API key is required, human-facing key labels and
help text, and recommended model lists/guidance. Extracted from
``assistant_ai`` to keep that module under the GATE-11 size budget (CQ-1) and to
give the provider catalog a single cohesive home.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.ai.model_manager import total_ram_gb


@dataclass(slots=True)
class ModelRecommendation:
    model: str
    framing: str
    reason: str


# The canonical, ordered set of provider ids the catalog knows about. "off"
# (AI disabled) and "ollama" (local) need no key; the rest are keyed providers.
ALL_PROVIDERS: tuple[str, ...] = (
    "off",
    "ollama",
    "ollama_cloud",
    "openai",
    "claude",
    "openrouter",
    "gemini",
    "custom",
)


def allowed_providers(policy: object | None = None) -> list[str]:
    """Return the provider ids selectable under an optional admin policy (§15).

    With no policy (the default), every catalog provider is returned. With an
    :class:`~quill.core.ai.admin_policy.AdminPolicy`, the org allow/block lists are
    applied; ``"off"`` is always selectable so AI can never be policy-locked on.
    """
    if policy is None:
        return list(ALL_PROVIDERS)
    from quill.core.ai.admin_policy import AdminPolicy, is_provider_allowed

    if not isinstance(policy, AdminPolicy):
        return list(ALL_PROVIDERS)
    return [p for p in ALL_PROVIDERS if is_provider_allowed(policy, p)]


def default_host_for_provider(provider: str) -> str:
    normalized = provider.strip().lower()
    if normalized == "openai":
        return "https://api.openai.com"
    if normalized == "claude":
        return "https://api.anthropic.com"
    if normalized == "openrouter":
        return "https://openrouter.ai/api"
    if normalized == "gemini":
        return "https://generativelanguage.googleapis.com"
    if normalized == "ollama_cloud":
        return "https://ollama.com"
    if normalized == "custom":
        return "https://api.openai.com"
    if normalized == "off":
        return ""
    return "http://localhost:11434"


def default_model_for_provider(provider: str) -> str:
    normalized = provider.strip().lower()
    if normalized == "openai":
        return "gpt-4o-mini"
    if normalized == "claude":
        return "claude-haiku-4-5-20251001"
    if normalized == "openrouter":
        return "openrouter/auto"
    if normalized == "gemini":
        return "gemini-2.5-flash"
    if normalized == "ollama_cloud":
        # A real, listed cloud model id (bare "qwen3" 404s on ollama.com). gemma3
        # is a non-reasoning instruction follower, so its OpenAI-compatible
        # `content` is always populated — reasoning models (e.g. gpt-oss) return
        # empty content on long tool prompts. See providers/regression learnings.
        return "gemma3:12b"
    if normalized == "custom":
        return "gpt-4o-mini"
    if normalized == "off":
        return ""
    return "llama3.2:1b-instruct-q4_K_M"


def provider_requires_api_key(provider: str) -> bool:
    normalized = provider.strip().lower()
    return normalized in {
        "ollama_cloud",
        "openai",
        "claude",
        "openrouter",
        "gemini",
        "custom",
    }


def provider_display_name(provider: str) -> str:
    """Return a friendly, human-facing name for a provider id."""
    normalized = provider.strip().lower()
    names = {
        "off": "Off",
        "ollama": "Ollama (local)",
        "ollama_cloud": "Ollama Cloud",
        "openai": "OpenAI",
        "claude": "Claude",
        "openrouter": "OpenRouter",
        "gemini": "Google Gemini",
        "custom": "Custom OpenAI-compatible endpoint",
    }
    return names.get(normalized, provider.strip() or "the selected provider")


def provider_api_key_label(provider: str) -> str:
    normalized = provider.strip().lower()
    if normalized == "openai":
        return "OpenAI API key"
    if normalized == "claude":
        return "Claude API key"
    if normalized == "openrouter":
        return "OpenRouter API key"
    if normalized == "gemini":
        return "Google Gemini API key"
    if normalized == "ollama_cloud":
        return "Ollama Cloud API key"
    if normalized == "custom":
        return "API key (OpenAI-compatible endpoint)"
    return "API key (optional)"


def provider_api_key_storage_hint() -> str:
    """Plain-language reassurance about where the API key is kept.

    Intentionally free of implementation jargon ("Credential Manager", "DPAPI",
    "encrypted fallback") and platform-specific wording, so it reads well on any
    OS and when spoken by a screen reader. Use it as hint/help text near the key
    field, not as the field's accessible name (#122).
    """
    return "Your key is stored securely on this device and never shared."


def provider_help_text(provider: str) -> str:
    normalized = provider.strip().lower()
    if normalized == "ollama":
        return "Local Ollama: no key required. Best for private on-device workflows."
    if normalized == "openai":
        return "OpenAI: default host is prefilled. Add key and list models."
    if normalized == "claude":
        return "Claude: default host is prefilled and model discovery is supported."
    if normalized == "openrouter":
        return "OpenRouter: broad model routing with a single key."
    if normalized == "gemini":
        return "Gemini: default Google API endpoint is prefilled."
    if normalized == "ollama_cloud":
        return "Ollama Cloud: add your cloud key to discover hosted models."
    if normalized == "custom":
        return "Advanced OpenAI-compatible endpoint: override host/model as needed."
    return "AI provider is off."


def recommended_models_for_provider(provider: str) -> list[str]:
    normalized = provider.strip().lower()
    if normalized == "openai":
        return ["gpt-4o-mini", "gpt-4.1-mini", "gpt-4.1"]
    if normalized == "claude":
        return ["claude-haiku-4-5-20251001", "claude-sonnet-4-6"]
    if normalized == "openrouter":
        from quill.core.ai.free_models import best_free_writing_model

        free_default = (
            best_free_writing_model("openrouter") or "meta-llama/llama-3.3-70b-instruct:free"
        )
        return [
            free_default,
            "openai/gpt-4o-mini",
            "openrouter/auto",
            "anthropic/claude-sonnet-4-6",
        ]
    if normalized == "gemini":
        return ["gemini-2.5-flash", "gemini-2.5-pro"]
    if normalized == "ollama_cloud":
        # Real, listed cloud model ids (bare "qwen3"/"gemma3" 404). gemma3:12b
        # leads as a reliable non-reasoning default; the gpt-oss reasoning models
        # follow for users who want them (their reasoning channel is handled in
        # parse_chat_response).
        return ["gemma3:12b", "gpt-oss:120b", "gpt-oss:20b"]
    if normalized == "ollama":
        if total_ram_gb() < 8.0:
            return [
                "llama3.2:1b-instruct-q4_K_M",
                "qwen2.5:1.5b-instruct-q4_K_M",
                "qwen2.5:3b-instruct-q4_K_M",
                "moondream:1.8b",
            ]
        return [
            "qwen2.5:7b-instruct-q4_K_M",
            "llama3.1:8b-instruct-q4_K_M",
            "qwen2.5:3b-instruct-q4_K_M",
            "llava:7b",
        ]
    return ["gpt-4o-mini", "claude-sonnet-4-6", "gemini-2.5-flash"]


def recommended_model_guidance(provider: str) -> list[ModelRecommendation]:
    normalized = provider.strip().lower()
    if normalized == "ollama":
        if total_ram_gb() < 8.0:
            return [
                ModelRecommendation(
                    model="llama3.2:1b-instruct-q4_K_M",
                    framing="Fast local drafting",
                    reason="Best fit for lower-memory devices.",
                ),
                ModelRecommendation(
                    model="qwen2.5:1.5b-instruct-q4_K_M",
                    framing="Balanced local writing",
                    reason="Slightly stronger output with modest resource use.",
                ),
                ModelRecommendation(
                    model="moondream:1.8b",
                    framing="Vision (image description)",
                    reason=(
                        "A multimodal model -- required for Describe Image / AI image "
                        "description. Text-only models such as llama3.2 cannot read images."
                    ),
                ),
            ]
        return [
            ModelRecommendation(
                model="qwen2.5:7b-instruct-q4_K_M",
                framing="Quality-focused local editing",
                reason="Higher quality while staying practical for local runs.",
            ),
            ModelRecommendation(
                model="llama3.1:8b-instruct-q4_K_M",
                framing="General local assistant",
                reason="Reliable for rewriting, summarizing, and grammar tasks.",
            ),
            ModelRecommendation(
                model="llava:7b",
                framing="Vision (image description)",
                reason=(
                    "A multimodal model -- required for Describe Image / AI image "
                    "description. Text-only models such as llama3.2 cannot read images."
                ),
            ),
        ]
    if normalized == "openai":
        return [
            ModelRecommendation(
                model="gpt-4o-mini",
                framing="Cost-aware daily use",
                reason=(
                    "Fast and inexpensive, and handles the great majority of writing tasks "
                    "well — rewriting, summarizing, grammar, and quick questions. The best "
                    "starting point for most people."
                ),
            ),
            ModelRecommendation(
                model="gpt-4.1",
                framing="High-quality reasoning",
                reason=(
                    "Noticeably stronger on complex transformations, nuanced editing, and "
                    "longer documents, at higher cost and slightly slower responses. Choose "
                    "it when quality matters more than speed or price."
                ),
            ),
        ]
    if normalized == "claude":
        return [
            ModelRecommendation(
                model="claude-haiku-4-5-20251001",
                framing="Speed-first drafting",
                reason=(
                    "Anthropic's fast, low-cost model — very responsive for rapid back-and-"
                    "forth, drafting, and everyday edits. A great, affordable default."
                ),
            ),
            ModelRecommendation(
                model="claude-sonnet-4-6",
                framing="Deep writing review",
                reason=(
                    "Stronger reasoning and careful long-form revision, better for nuanced "
                    "rewrites and structured documents, at higher cost. Pick it when you "
                    "want the most thoughtful output."
                ),
            ),
        ]
    if normalized == "openrouter":
        from quill.core.ai.free_models import best_free_writing_model

        free_default = (
            best_free_writing_model("openrouter") or "meta-llama/llama-3.3-70b-instruct:free"
        )
        return [
            ModelRecommendation(
                model=free_default,
                framing="Free and strong (recommended)",
                reason=(
                    "A capable free writing model that costs nothing — the best starting "
                    "point if you don't want to pay. It uses your own free daily quota, so "
                    "there's no shared limit. Free hosted models may log or train on what "
                    "you send, so keep confidential text on the on-device option."
                ),
            ),
            ModelRecommendation(
                model="openai/gpt-4o-mini",
                framing="Predictable speed and cost",
                reason=(
                    "A specific fast, low-cost paid model for stable, repeatable behavior — "
                    "pennies per use when you want more consistency than the free tier."
                ),
            ),
            ModelRecommendation(
                model="openrouter/auto",
                framing="Automatic routing",
                reason=(
                    "Lets OpenRouter pick a capable model for each request. Convenient, but "
                    "it can route to paid models, so it is not a guaranteed-free choice."
                ),
            ),
        ]
    if normalized == "gemini":
        return [
            ModelRecommendation(
                model="gemini-2.5-flash",
                framing="Fast cloud drafting",
                reason=(
                    "Google's fast model with a generous free tier — low latency for "
                    "everyday writing help, and an easy, low-cost default."
                ),
            ),
            ModelRecommendation(
                model="gemini-2.5-pro",
                framing="Long-context analysis",
                reason=(
                    "Handles very large prompts and deeper synthesis better, at higher cost "
                    "and latency. Choose it for big documents or research-style tasks."
                ),
            ),
        ]
    if normalized == "ollama_cloud":
        return [
            ModelRecommendation(
                model="gemma3:12b",
                framing="Reliable hosted default",
                reason=(
                    "A dependable, hosted open model that follows instructions well and "
                    "always returns usable text — the safest Ollama Cloud starting point."
                ),
            ),
            ModelRecommendation(
                model="gpt-oss:120b",
                framing="Largest hosted open model",
                reason=(
                    "More capable on harder tasks but heavier and slower; a reasoning model, "
                    "so responses may pause to think before answering."
                ),
            ),
            ModelRecommendation(
                model="gpt-oss:20b",
                framing="Lighter hosted open model",
                reason=(
                    "A smaller, quicker reasoning model — a middle ground between gemma3 and "
                    "the 120b when you want more capability without the largest cost."
                ),
            ),
        ]
    return [
        ModelRecommendation(
            model=name,
            framing="General recommendation",
            reason="Suggested model for this provider.",
        )
        for name in recommended_models_for_provider(provider)
    ]
