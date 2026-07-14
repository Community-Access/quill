"""AIBackend that routes generation to the user's configured provider (AI-13).

When the user has configured an AI connection (OpenAI, Claude, Gemini, Azure
OpenAI, OpenRouter, a custom OpenAI-compatible endpoint, or local/cloud Ollama),
this backend makes that provider actually produce the response, instead of
generation silently falling back to the bundled local model. It is a thin
adapter over ``quill.core.assistant_ai.generate_assistant_response`` so the
provider request building, endpoint-security check, verified TLS, retry, and
error taxonomy all live in one place.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.ai.backend import AIBackend
from quill.core.assistant_ai import (
    AssistantConnectionSettings,
    generate_assistant_response,
    generate_assistant_response_stream,
    load_assistant_api_key,
    load_assistant_connection_settings,
    load_provider_api_key,
    provider_requires_api_key,
)


class ProviderChatBackend(AIBackend):
    """Generate via the configured cloud or Ollama provider."""

    name = "provider"

    def __init__(
        self,
        settings: AssistantConnectionSettings | None = None,
        api_key: str | None = None,
    ) -> None:
        self._settings = settings or load_assistant_connection_settings()
        if api_key is not None:
            self._api_key = api_key
        else:
            # Prefer the active provider's own key. The legacy active-key store is shared
            # across providers, so after a provider switch it can hold a *different*
            # provider's key (-> 401 "authentication failed") or be empty (-> "no key
            # configured"). The per-provider key is unambiguous; fall back to the active
            # store only for older installs that have just the one key.
            provider = self._settings.provider.strip().lower()
            self._api_key = load_provider_api_key(provider) or load_assistant_api_key()

    @property
    def settings(self) -> AssistantConnectionSettings:
        return self._settings

    def is_available(self) -> tuple[bool, str | None]:
        provider = self._settings.provider.strip().lower()
        if provider == "off":
            return False, "The AI provider is set to Off."
        if provider_requires_api_key(provider) and not self._api_key.strip():
            return False, "No API key is configured for this provider. Add one in AI settings."
        return True, None

    def respond(self, prompt: str) -> str:
        available, reason = self.is_available()
        if not available:
            raise RuntimeError(reason or "The AI provider is not available.")
        text, error = generate_assistant_response(self._settings, self._api_key, prompt)
        if error is not None:
            raise RuntimeError(error)
        return text or ""

    def respond_stream(self, prompt: str, on_delta: Callable[[str], None]) -> str:
        """Stream tokens from the configured provider with accessible cadence (AI-14).

        Delivers each fragment to ``on_delta`` as the model produces it. If the
        provider request fails before any token arrives, it falls back to the
        blocking request so a transient streaming hiccup still yields an answer.
        """
        available, reason = self.is_available()
        if not available:
            raise RuntimeError(reason or "The AI provider is not available.")
        emitted = False

        def track(fragment: str) -> None:
            nonlocal emitted
            emitted = True
            on_delta(fragment)

        text, error = generate_assistant_response_stream(
            self._settings, self._api_key, prompt, track
        )
        if error is not None:
            if emitted:
                # Tokens already reached the user; surface the interruption
                # rather than re-running and duplicating the partial reply.
                raise RuntimeError(error)
            # Nothing streamed yet: degrade cleanly to one blocking request.
            text, error = generate_assistant_response(self._settings, self._api_key, prompt)
            if error is not None:
                raise RuntimeError(error)
            if text:
                on_delta(text)
        return text or ""


class SimpleChatBackend(AIBackend):
    """AIBackend backed by the simple ai_chat.send_prompt path.

    Uses settings.ai_chat_default_provider / ai_chat_default_model rather than
    the AI-13 connection file, so the two config paths share the same Assistant.
    """

    name = "simple_chat"

    def __init__(self, provider_id: str, model_id: str) -> None:
        self._provider_id = provider_id
        self._model_id = model_id

    def _load_key(self) -> str:
        from quill.core.ai_chat import PROVIDERS
        from quill.platform.windows.credential_store import load_secret

        pdef = PROVIDERS.get(self._provider_id, {})
        cred = pdef.get("credential_name")
        return load_secret(cred) if cred else ""

    def is_available(self) -> tuple[bool, str | None]:
        if not self._provider_id or not self._model_id:
            return False, "No provider or model configured."
        from quill.core.ai_chat import PROVIDERS

        pdef = PROVIDERS.get(self._provider_id)
        if pdef is None:
            return False, f"Unknown provider: {self._provider_id}"
        if pdef.get("needs_key") and not self._load_key().strip():
            return False, f"No API key configured for {pdef['label']}."
        return True, None

    def respond(self, prompt: str) -> str:
        from quill.core.ai_chat import send_prompt

        return send_prompt(self._provider_id, self._model_id, prompt, api_key=self._load_key())

    def respond_stream(self, prompt: str, on_delta: Callable[[str], None]) -> str:
        # send_prompt does not stream; deliver the full response as a single delta.
        text = self.respond(prompt)
        if text:
            on_delta(text)
        return text
