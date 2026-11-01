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
    route: str

    @property
    def own_key_ready(self) -> bool:
        """Whether a key is saved for the provider the listener chose: the row is set up."""
        from quill.core.ai.own_key import own_key_active

        return own_key_active(getattr(self._app, "settings", None))

    @property
    def own_key_active(self) -> bool:
        """Whether requests go to the provider with the user's own key: it is the
        connection in use (``ai_connection``) and its key is saved.

        Then there is no QUILL server, no sign-in and no allowance: the same
        five commands, billed to the user's account (:mod:`quill.core.ai.own_key`).
        """
        return self.route == "own_key" and self.own_key_ready

    @property
    def own_key_provider(self) -> str:
        """The provider the listener chose for their key (``own_key_providers.PROVIDERS``)."""
        from quill.core.ai.own_key import chosen_provider

        return chosen_provider(getattr(self._app, "settings", None))

    @property
    def own_key_model(self) -> str:
        """The model own-key requests use: the chosen one, or the provider's default."""
        from quill.core.ai.own_key import default_model

        chosen = getattr(getattr(self._app, "settings", None), "ai_own_key_model", "")
        return str(chosen or "").strip() or default_model(self.own_key_provider)

    @property
    def own_key_can_see(self) -> bool:
        """Whether the own key's provider reads pictures, from the capability registry:
        Gemini does, an Ollama model does when its ``/api/show`` says so, and the
        rest are text only on this route (GATE-CAPS)."""
        if not self.own_key_active:
            return False
        from quill.core.ai.connection_caps import OWN_KEY, PICTURES, record_for

        record = record_for(
            OWN_KEY, own_key_provider=self.own_key_provider, model=self.own_key_model
        )
        return record.claim(PICTURES).supported

    def own_key_sign_out(self) -> None:
        """Sign out of My own key: forget the chosen provider's key. Ollama on this
        computer has none to forget, so it stops being the choice instead."""
        from quill.core.ai.own_key_providers import OPENAI, needs_key
        from quill.core.assistant_ai import clear_provider_api_key

        provider = self.own_key_provider or OPENAI
        if needs_key(provider):
            clear_provider_api_key(provider)
            return
        settings = getattr(self._app, "settings", None)
        if settings is not None:
            settings.ai_own_key_provider = OPENAI
            save = getattr(self._app, "save_settings", None)
            if callable(save):
                save()


__all__ = ["OwnKeyRouteMixin"]
