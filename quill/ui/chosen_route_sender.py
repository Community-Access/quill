"""QUILL's sender for the AI chosen in Choose Your AI (:mod:`quill.core.ai.chosen_route`).

Every advanced AI command reaches a provider through
``generate_assistant_response``; in QUILL their settings name
:data:`~quill.core.ai.chosen_route.ROUTE_PROVIDER`, and the request arrives
here. It goes the way every AI-menu request goes:

1. **The shared route decides** (:meth:`ConnectionRouteMixin.request_connection`),
   on the UI thread: the same refusal when the chosen AI is not ready or cannot
   do it, the same "Send to a Different AI?" before another company is used,
   and the same sentence naming Auto's pick before anything is sent.
2. **The request goes to that connection** and nowhere else: an own key's
   provider with its own key, the ChatGPT plan, GitHub Copilot, or QUILL's free
   AI service.

A refusal is raised as :class:`~quill.core.ai.chosen_route.ChosenRouteError`
with its sentence, which each feature reports as it reports any AI error.
"""

from __future__ import annotations

import threading
from typing import Any

from quill.core.ai.chosen_route import ChosenRouteError

__all__ = ["ChosenRouteSender", "install"]

_TEXT = ("text",)
_PICTURES = ("text", "pictures")


def _on_ui_thread() -> bool:
    try:
        import wx

        return bool(wx.IsMainThread())
    except Exception:  # noqa: BLE001 - no wx: treat the caller as the UI thread
        return True


class ChosenRouteSender:
    """Sends one prompt on the connection the shared route allows."""

    def __init__(self, frame: Any) -> None:
        self._frame = frame
        self._bridge: Any = None

    def _service(self) -> Any:
        return self._frame._ai_service()

    def _on_ui(self, work: Any, default: Any) -> Any:
        """Run *work* on the UI thread and wait for it (directly when already there)."""
        if _on_ui_thread():
            return work()
        if self._bridge is None:
            import wx

            from quill.core.ai.approvals import UiThreadBridge

            self._bridge = UiThreadBridge(wx.CallAfter)
        return self._bridge.call(work, default=default)

    def connection(self, requires: tuple[str, ...] = _TEXT) -> str:
        """The connection this request may use, or raise with the reason why none.

        A picture also needs the connection's first-picture consent (10B.4):
        No, the default, sends nothing.
        """
        said: list[str] = []

        def decide() -> str:
            # AI help switched on, and the free AI's agreement when that is the
            # route: the same consent every AI-menu command asks for.
            if not self._frame._ai_ready():
                said.append("Nothing was sent.")
                return ""
            chosen = str(self._service().request_connection(requires, said.append) or "")
            if chosen and "pictures" in requires:
                from quill.ui.hosted_ai_picture_consent import ask_picture_consent

                if not ask_picture_consent(self._frame, chosen):
                    said.append("Nothing was sent.")
                    return ""
            return chosen

        connection = str(self._on_ui(decide, "") or "")
        if not connection:
            raise ChosenRouteError(said[0] if said else "Nothing was sent.")
        return connection

    def picture(self, path: Any, prompt: str) -> str:
        """Ask the chosen AI about the picture at *path*; the answer, or raise."""
        connection = self.connection(_PICTURES)
        service = self._service()
        try:
            return picture_on(service, connection, path, prompt)
        except ChosenRouteError:
            raise
        except Exception as error:  # noqa: BLE001 - the route's own sentence
            raise ChosenRouteError(service._failure_sentence(error, connection)) from error

    def describe(self) -> str:
        """The AI in use, as the status bar says it: "My own key, OpenAI, gpt-4o"."""
        return str(self._service().status_cell())

    def choose(self) -> None:
        """Open Choose Your AI."""
        self._frame._ai_open_choose()

    def __call__(self, prompt: str, system_prompt: str = "") -> str:
        connection = self.connection()
        service = self._service()
        try:
            return send_on(service, connection, prompt, system_prompt)
        except ChosenRouteError:
            raise
        except Exception as error:  # noqa: BLE001 - the route's own sentence
            raise ChosenRouteError(service._failure_sentence(error, connection)) from error


def send_on(service: Any, connection: str, prompt: str, system_prompt: str = "") -> str:
    """Send *prompt* on *connection* through *service*; the answer, or raise."""
    from quill.core.ai.connection_caps import CHATGPT, COPILOT, OWN_KEY

    whole = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
    if connection == OWN_KEY:
        from quill.core.ai.own_key_providers import host_for, needs_key
        from quill.core.assistant_ai import (
            AssistantConnectionSettings,
            generate_assistant_response,
            load_provider_api_key,
        )

        provider = str(service.own_key_provider)
        settings = AssistantConnectionSettings(
            provider=provider, host=host_for(provider), model=str(service.own_key_model)
        )
        key = load_provider_api_key(provider) if needs_key(provider) else ""
        text, error = generate_assistant_response(
            settings, key, prompt, system_prompt=system_prompt
        )
        if error is not None:
            raise ChosenRouteError(error)
        return text or ""
    if connection == CHATGPT:
        from quill.core.ai.chatgpt_ai_help import converse_with_chatgpt

        return str(converse_with_chatgpt(service.chatgpt, whole, None, []))
    if connection == COPILOT:
        work = service._copilot_converse_work(whole, None, [], threading.Event())
        return str(work()[0])
    reply = service.client().converse(whole, None, [])
    return str(reply[0])


#: Written once the older choice has been carried into Choose Your AI.
_MIGRATED_FILE = "assistant-connection-followed.json"

#: Said once, after the move, so nobody is surprised by where requests now go.
MOVED_SENTENCE = (
    "QUILL's other AI commands, such as spell check, translate and Ask Quill, now "
    "use the AI you choose in Choose Your AI."
)


def migrate_older_choice(settings: Any, save: Any) -> str:
    """Carry ``assistant-connection.json``'s provider and key into the shared choice, once.

    The older choice becomes the own-key row, when that row is not already set
    up: the provider, its model, its address and the key QUILL saved for it --
    never a key from the environment, which the person never gave QUILL. With no
    stored choice yet, the own-key row becomes the choice. Returns the sentence
    to say once, or "" when there was nothing to move.
    """
    from quill.core.ai import own_key_providers as providers
    from quill.core.ai.connection_caps import OWN_KEY
    from quill.core.ai.legacy_key_owner import belongs_to
    from quill.core.ai.own_key import own_key_active
    from quill.core.assistant_ai import (
        assistant_connection_path,
        load_assistant_connection_settings,
        save_provider_api_key,
        stored_assistant_api_key,
        stored_provider_api_key,
    )
    from quill.core.storage import write_json_atomic

    older = assistant_connection_path()
    marker = older.parent / _MIGRATED_FILE
    if marker.exists() or not older.exists():
        return ""
    conn = load_assistant_connection_settings()
    provider = conn.provider.strip().lower()
    kept = ""
    if provider in providers.PROVIDERS and not own_key_active(settings):
        key = ""
        if providers.needs_key(provider):
            key = stored_provider_api_key(provider) or (
                stored_assistant_api_key() if belongs_to(provider) else ""
            )
        if key or not providers.needs_key(provider):
            if key and not stored_provider_api_key(provider):
                save_provider_api_key(provider, key)
            settings.ai_own_key_provider = provider
            settings.ai_own_key_model = conn.model
            if provider in providers.HOST_PROVIDERS:
                providers.save_host(provider, conn.host)
            providers.mark_set_up(provider)
            if not str(getattr(settings, "ai_connection", "") or ""):
                settings.ai_connection = OWN_KEY
            save()
            name = providers.PROVIDER_NAMES[provider]
            kept = f" Your {name} setup was moved to My own key in Choose Your AI."
    write_json_atomic(marker, {"schema_version": 1, "followed": True})
    return MOVED_SENTENCE + kept + " Press Ctrl+8 to hear which AI is in use."


def picture_on(service: Any, connection: str, path: Any, prompt: str) -> str:
    """Ask *connection* about the picture at *path* through *service*."""
    from quill.core.ai.connection_caps import CHATGPT, COPILOT

    if connection == CHATGPT:
        from quill.core.ai.chatgpt_ai_help import describe_image_with_chatgpt

        return str(describe_image_with_chatgpt(service.chatgpt, path, prompt))
    if connection == COPILOT:
        return str(service._copilot_image_work(path, prompt)())
    from quill.core.ai.own_key import describe_image_with_own_key

    return str(
        describe_image_with_own_key(
            path, prompt, provider=service.own_key_provider, model=service.own_key_model
        )
    )


def install(frame: Any) -> None:
    """Make *frame*'s chosen AI the route for QUILL's advanced AI commands.

    Run once the window is up: the older choice is carried over first (and
    said once), then every advanced request goes the shared route.
    """
    from quill.core.ai import chosen_route

    host = frame._ai_host()
    try:
        said = migrate_older_choice(host.settings, host.save_settings)
    except Exception:  # noqa: BLE001 - a failed move must never stop QUILL starting
        said = ""
    chosen_route.set_sender(ChosenRouteSender(frame))
    if said:
        frame._announce(said)
