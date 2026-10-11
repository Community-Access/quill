"""User-facing descriptions of the active hosted-AI route.

The service decides where a request travels and waits for it; this mixin says
what that route means in the pad and conversation window. Keeping those
sentences together avoids duplicating provider and billing rules in callers.
"""

from __future__ import annotations

from typing import Any

__all__ = ["RouteWords"]


class RouteWords:
    """Mixed into :class:`quill.ui.hosted_ai_service.AiService`."""

    chatgpt_active: bool
    own_key_active: bool
    own_key_provider: str
    own_key_model: str
    chatgpt: Any
    direct: bool
    free_limits: Any

    @property
    def route_label(self) -> str:
        """The active direct route as a person hears it."""
        if self.chatgpt_active:
            return "your ChatGPT subscription"
        from quill.core.ai.own_key import provider_name

        return f"your own {provider_name(self.own_key_provider)} key"

    @property
    def direct_model(self) -> str:
        """The model a direct route answers with, or an empty string."""
        if self.chatgpt_active:
            return str(self.chatgpt.model or "")
        return self.own_key_model

    def size_note(self, text: str) -> str:
        """What sending *text* on the active direct route means."""
        if not self.direct:
            return ""
        free_tokens = self.free_limits.max_input_tokens
        if self.chatgpt_active:
            from quill.core.ai.chatgpt_ai_help import size_note

            return size_note(text, self.direct_model, free_limit_tokens=free_tokens)
        from quill.core.ai.own_key import size_warning

        return size_warning(
            text,
            self.own_key_model,
            free_limit_tokens=free_tokens,
            provider=self.own_key_provider,
        )

    def conversation_note(self) -> str:
        """What a conversation costs on the active route."""
        if self.chatgpt_active:
            return (
                "This conversation uses your ChatGPT subscription: no QUILL limit, and "
                "each message counts toward your plan's own usage. The whole "
                "conversation goes with each message."
            )
        if self.own_key_active:
            from quill.core.ai.own_key import conversation_note

            return conversation_note(self.own_key_provider)
        return (
            "Each message uses one of your free requests. The conversation so far "
            "goes with it as far as the free size limit allows, so a long "
            "conversation gradually forgets its beginning; this window says when "
            "that starts."
        )
