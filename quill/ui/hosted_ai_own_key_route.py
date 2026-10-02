"""The own-key half of :class:`quill.ui.hosted_ai_service.AiService` (GATE-11 split).

Four questions about the listener's own key, answered from the live settings
every time so nothing here can go stale: whether a key is saved for the
provider they chose, which provider that is, which model, and whether that
provider reads pictures. The choice of provider is explicit -- the Provider
list in Use My Own AI Key -- and nothing here infers one from a key that
happens to exist (qc.md X-07).
"""

from __future__ import annotations

from typing import Any


class OwnKeyRouteMixin:
    """Mixed into ``AiService``; reads ``self._app.settings``."""

    _app: Any

    @property
    def own_key_active(self) -> bool:
        """Whether requests go to OpenAI with the user's own key instead.

        Then there is no QUILL server, no sign-in and no allowance: the same
        five commands, billed to the user's OpenAI account
        (:mod:`quill.core.ai.own_key`).
        """
        from quill.core.ai.own_key import own_key_active

        return own_key_active(getattr(self._app, "settings", None))

    @property
    def own_key_provider(self) -> str:
        """``"openai"`` or ``"gemini"``: the provider the listener chose for their key."""
        from quill.core.ai.own_key import provider_for

        return provider_for(getattr(self._app, "settings", None))

    @property
    def own_key_model(self) -> str:
        """The model own-key requests use: the chosen one, or the provider's default."""
        from quill.core.ai.own_key import default_model

        chosen = getattr(getattr(self._app, "settings", None), "ai_own_key_model", "")
        return str(chosen or "").strip() or default_model(self.own_key_provider)

    @property
    def own_key_can_see(self) -> bool:
        """Whether the own key's provider reads pictures (Gemini does; OpenAI's own-key
        route here is text only)."""
        return self.own_key_active and self.own_key_provider == "gemini"


__all__ = ["OwnKeyRouteMixin"]
