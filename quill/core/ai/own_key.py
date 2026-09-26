"""AI help with the user's own OpenAI key: no allowance, no QUILL server.

The five AI help commands normally go through QUILL's free service, which keeps
an allowance per person and a size limit per request. Somebody with their own
OpenAI account can switch that off: the same five commands then go **straight
from this computer to OpenAI**, billed to their account, with no QUILL server in
between and none of the free tier's limits.

Three things make it the same feature rather than a second one:

* **The same instructions.** :data:`INSTRUCTIONS` are the gateway's own
  templates (``quill-ai-gateway/app/prompts.py``), sent as the system message so
  a summary is the same summary whichever way it travels.
  ``tests/unit/core/ai/test_own_key.py`` fails if the two drift.
* **The same key store as QUILL.** The key lives where QUILL's AI Hub keeps its
  OpenAI key (Windows Credential Manager, or an encrypted file in a portable
  copy), so a key entered in either program works in both.
* **The same client.** :func:`quill.core.assistant_ai.generate_assistant_response`
  -- QUILL's own provider code, plain HTTPS, certificate-checked, with retries.

wx-free.
"""

from __future__ import annotations

from typing import Any

from quill.core.ai.gateway_client import GatewayLimits
from quill.core.error_codes import CodedError

__all__ = [
    "INSTRUCTIONS",
    "OWN_KEY_LIMITS",
    "OWN_KEY_PROVIDER",
    "OwnKeyError",
    "ask_with_own_key",
    "default_model",
    "has_own_key",
    "load_settings_fields",
    "own_key_active",
    "request_for",
]

OWN_KEY_PROVIDER = "openai"

#: The instruction half of each gateway template, sent as the system message.
#: Must match ``quill-ai-gateway/app/prompts.py`` word for word.
INSTRUCTIONS: dict[str, str] = {
    "summarize": (
        "Summarize the following text in a few clear sentences, in plain "
        "language suitable for a screen reader to read aloud. Preserve the "
        "key facts; do not add information that isn't in the text. Return "
        "only the summary, with no preamble."
    ),
    "rewrite": (
        "Rewrite the following text to be clearer and more concise, "
        "preserving its meaning and tone. Return only the rewritten text, "
        "with no preamble or explanation."
    ),
    "proofread": (
        "Correct the spelling, grammar and punctuation of the following "
        "text. Do not change the wording, the tone, or the meaning beyond "
        "what the corrections require, and do not rewrite for style. Return "
        "only the corrected text, with no preamble, no explanation and no "
        "list of what changed."
    ),
    "explain": (
        "Explain what the following passage means, in plain language "
        "suitable for a screen reader to read aloud. Be brief. Explain only "
        "what the passage says; do not judge it, and do not add information "
        "from outside it. Return only the explanation, with no "
        "preamble."
    ),
    "document_qna": (
        "You are answering a question about excerpts from the user's own "
        "document. Answer only from the excerpts provided; if they do not "
        "contain the answer, say so plainly rather than guessing. Keep the "
        "answer concise and in plain language suitable for a screen reader "
        "to read aloud."
    ),
}

#: What the pad is told the limits are with an own key: every feature on, and
#: sizes that are the model's rather than an allowance's. The pad still warns
#: before sending something enormous, because a person paying per token should
#: know before a whole book goes.
OWN_KEY_LIMITS = GatewayLimits(
    max_input_tokens=100_000,
    max_output_tokens=4_000,
    max_chunks_per_request=8,
    hosted_ai_enabled=True,
    feature_flags={feature: True for feature in INSTRUCTIONS},
)


class OwnKeyError(CodedError):
    """A request with the user's own key did not produce an answer."""

    code = "QUILL-AI-OWN-KEY-FAILED"
    user_hint = (
        "Check the key and the model in Use My Own OpenAI Key, and that your "
        "OpenAI account has credit. Or switch back to QUILL's free AI there."
    )


def default_model() -> str:
    from quill.core.assistant_ai import default_model_for_provider

    return default_model_for_provider(OWN_KEY_PROVIDER)


def has_own_key() -> bool:
    """Whether an OpenAI key is stored (or set in the environment)."""
    from quill.core.assistant_ai import load_provider_api_key

    try:
        return bool(load_provider_api_key(OWN_KEY_PROVIDER))
    except Exception:  # noqa: BLE001 - an unreadable store is "no key"
        return False


def own_key_active(settings: Any = None) -> bool:
    """Whether AI help uses the user's key: whenever one is saved.

    There is deliberately no separate switch. A saved key lifts every limit;
    removing it (Use My Own OpenAI Key, Remove the Saved Key) is how a person
    goes back to the free service. *settings* is accepted for the callers'
    convenience and not consulted.
    """
    del settings
    return has_own_key()


def load_settings_fields(data: Any) -> dict[str, Any]:
    """The own-key setting from saved JSON, for QUILL's settings loader."""
    return {"ai_own_key_model": str(data.get("ai_own_key_model", "") or "")}


def request_for(feature: str, prompt: str, chunks: list[str] | None = None) -> tuple[str, str]:
    """``(system, user)`` messages for *feature* -- the gateway's, split in two."""
    instructions = INSTRUCTIONS.get(feature)
    if instructions is None:
        raise OwnKeyError(f"{feature.replace('_', ' ').capitalize()} is not available.")
    if feature == "document_qna":
        context = "\n\n---\n\n".join(chunks or [])
        return instructions, f"Excerpts:\n{context}\n\nQuestion: {prompt}"
    return instructions, prompt


def ask_with_own_key(
    feature: str, prompt: str, chunks: list[str] | None = None, *, model: str = ""
) -> str:
    """Send one AI help request to OpenAI with the user's key. Blocking.

    Raises :class:`OwnKeyError` with a sentence written for a person.
    """
    from quill.core.assistant_ai import (
        AssistantConnectionSettings,
        default_host_for_provider,
        generate_assistant_response,
        load_provider_api_key,
    )

    key = load_provider_api_key(OWN_KEY_PROVIDER)
    if not key:
        raise OwnKeyError("No OpenAI key is stored on this computer.")
    system, user = request_for(feature, prompt, chunks)
    connection = AssistantConnectionSettings(
        provider=OWN_KEY_PROVIDER,
        host=default_host_for_provider(OWN_KEY_PROVIDER),
        model=model.strip() or default_model(),
    )
    text, error = generate_assistant_response(
        connection,
        key,
        user,
        max_tokens=OWN_KEY_LIMITS.max_output_tokens,
        system_prompt=system,
    )
    if error or not text:
        raise OwnKeyError(f"OpenAI did not answer: {error or 'the answer was empty'}.")
    return text.strip()
