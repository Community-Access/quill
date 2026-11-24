"""The AI setup wizard's connection check for a provider and key.

Moved out of :mod:`quill.ui.ai_setup_wizard` (GATE-11) unchanged. It runs on
the wizard's worker thread and never raises.
"""

from __future__ import annotations


def _probe_provider(provider: str, api_key: str) -> tuple[bool, str]:
    """Quick, contained connection check for a provider + key. Never raises."""
    try:
        import dataclasses

        from quill.core.ai.provider_backend import ProviderChatBackend
        from quill.core.ai.providers import default_host_for_provider, default_model_for_provider
        from quill.core.assistant_ai import AssistantConnectionSettings

        settings = AssistantConnectionSettings(
            provider=provider,
            host=default_host_for_provider(provider),
            model=default_model_for_provider(provider),
        )
        backend = ProviderChatBackend(settings=dataclasses.replace(settings), api_key=api_key)
        try:
            reply = backend.respond("Reply with exactly one word: ok")
            if reply and reply.strip():
                return (True, "")
        except Exception as chat_exc:  # noqa: BLE001 - probe error handled below
            # A *valid* key can still fail this chat probe when the default probe model
            # is unavailable to the account — e.g. Gemini returns HTTP 404 "model ... is
            # no longer available to new users" (#1231). Don't reject a good key over one
            # model: fall back to listing the account's models, which only needs the key.
            # A bad key lists nothing, so this stays a real key check.
            from quill.core.assistant_ai import list_assistant_models

            models, list_error = list_assistant_models(settings, api_key)
            if models:
                return (True, "")
            return (False, list_error or str(chat_exc))
        # Chat succeeded but returned nothing usable: confirm via the model list before
        # rejecting, so an empty completion doesn't masquerade as a bad key.
        from quill.core.assistant_ai import list_assistant_models

        models, _list_error = list_assistant_models(settings, api_key)
        if models:
            return (True, "")
        return (False, "The provider returned no response to a test prompt.")
    except Exception as exc:  # noqa: BLE001 - report the reason, never crash the UI
        return (False, str(exc))
