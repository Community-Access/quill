"""Choose Your AI, as :class:`quill.ui.hosted_ai_service.AiService` sees it (codex.md 10A).

Mixed into the one service both editors share, so QUILL and QUILL Lite route
the same way (rule 10). Where the silent precedence used to decide on every
request -- a ChatGPT sign-in, else a key, else the free AI -- the route is now
the **stored choice**, ``ai_connection``, migrated once from that precedence
so nobody's behaviour changes on upgrade
(:func:`quill.core.ai.connection_choice.migrate_choice`).

Every request asks :meth:`request_allowed` before it leaves, which says no,
with the specific sentence of 10A.5, when:

* the connection in use is not ready -- signed out by OpenAI or GitHub, signed
  out by the person (decision 15: "No AI is in use. Choose one."), or not
  available in this build (no GitHub registration, or no engine). There is no
  fall-through;
* it cannot do what the request needs (GATE-CAPS,
  :func:`quill.core.ai.connection_caps.require`);
* the route changed under the listener and they said No (the route guard).

The words and the rules live in wx-free modules (``connection_caps``,
``connection_choice``, ``connection_usage``); this mixin only reads live state
into them, so the window (Phase 1b) shows sentences it did not compose.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.ai.connection_caps import (
    CHATGPT,
    CODEX,
    CONNECTIONS,
    COPILOT,
    FREE,
    OWN_KEY,
    CapabilityMissing,
    ConnectionRecord,
    SwitchOffer,
    can,
    needs_label,
    record_for,
    require,
    switch_offer,
)
from quill.core.ai.connection_choice import (
    ConnectionFacts,
    ConnectionRow,
    in_use,
    limit_sentence,
    migrate_choice,
    not_ready_sentence,
    ready,
    request_route,
    revoked_sentence,
    row_states,
)

__all__ = ["ConnectionRouteMixin", "plain_sentence"]


def plain_sentence(error: BaseException) -> str:
    """A finished sentence for a person, from whatever went wrong.

    A coded error already carries one, plus a hint saying what to do next --
    both are worth speaking, and the hint is usually the more useful half.
    Anything else gets a generic sentence rather than a traceback.
    """
    from quill.core.ai.gateway_errors import GatewayError
    from quill.core.error_codes import CodedError

    if isinstance(error, (GatewayError, CodedError)):
        # The sentence first and the code last: str(error) leads with the code,
        # which a screen reader spells out before the person hears what happened.
        message = str(error.args[0]) if error.args else ""
        hint = getattr(error, "user_hint", "")
        code = getattr(error, "code", "")
        parts = [message, hint, f"Error code {code}." if code else ""]
        return " ".join(part.strip() for part in parts if part and part.strip())
    return "The AI service is not answering right now. Try again in a moment. Nothing was used."


class ConnectionRouteMixin:
    """The stored choice, its readiness, its capabilities and its sentences."""

    _app: Any
    _limits: Any
    chatgpt: Any
    own_key_ready: bool
    own_key_provider: str
    own_key_model: str
    signed_in: bool
    # route_chosen() and route_allowed() come from RouteGuardMixin, later in the MRO.

    # -- the stored choice ------------------------------------------------- #

    def _settings(self) -> Any:
        return getattr(self._app, "settings", None)

    def _save_settings(self) -> None:
        save = getattr(self._app, "save_settings", None)
        if callable(save):
            save()

    def _chatgpt_signed_in(self) -> bool:
        try:
            return bool(self.chatgpt.signed_in)
        except Exception:  # noqa: BLE001 - an unreadable store is "not signed in"
            return False

    @property
    def connection(self) -> str:
        """The stored choice (``free``, ``chatgpt``, ``copilot``, ``codex``, ``own_key``)."""
        return migrate_choice(
            self._settings(),
            chatgpt_signed_in=self._chatgpt_signed_in,
            own_key_ready=lambda: bool(self.own_key_ready),
            save=self._save_settings,
        )

    def connection_facts(self) -> ConnectionFacts:
        """Everything known about every connection, read locally (no network call)."""
        signed_in = self._chatgpt_signed_in()
        try:
            ended = bool(getattr(self.chatgpt, "ended_by_openai", False)) and not signed_in
        except Exception:  # noqa: BLE001 - as above
            ended = False
        return ConnectionFacts(
            stored=self.connection,
            free_connected=bool(self.signed_in),
            chatgpt_signed_in=signed_in,
            chatgpt_ended=ended,
            own_key_ready=bool(self.own_key_ready),
            own_key_provider=self.own_key_provider or "openai",
            **self._engine_facts(),
        )

    def _engine_facts(self) -> dict[str, bool]:
        """Copilot's and Codex's fields; :class:`CopilotRouteMixin` reads them."""
        return {}

    @property
    def connection_in_use(self) -> str:
        """The connection in use, or "" when none is."""
        return in_use(self.connection_facts())

    @property
    def route(self) -> str:
        """Which way a single request travels: the stored choice, with Codex's
        single requests on the ChatGPT plan's direct route (decision 21)."""
        return request_route(self.connection)

    @property
    def chatgpt_active(self) -> bool:
        """Whether requests go to OpenAI on the person's ChatGPT plan."""
        return self.route == CHATGPT

    @property
    def direct(self) -> bool:
        """Whether requests skip QUILL's service, and with it every QUILL limit."""
        return self.route != FREE

    def connection_model(self, connection: str = "") -> str:
        """The model *connection* (default: the stored one) answers with, or ""."""
        chosen = connection or self.connection
        settings = self._settings()
        if chosen == CHATGPT:
            return str(getattr(self.chatgpt, "model", "") or "")
        if chosen == OWN_KEY:
            return self.own_key_model
        if chosen == COPILOT:
            return str(getattr(settings, "ai_copilot_model", "") or "")
        if chosen == CODEX:
            return str(getattr(settings, "ai_codex_model", "") or "")
        return ""

    # -- choosing ---------------------------------------------------------- #

    def choose(self, connection: str) -> bool:
        """Make *connection* the one in use (Use This, or a sign-in: signing in is
        choosing). False, and nothing changes, when it is not ready."""
        settings = self._settings()
        if connection not in CONNECTIONS or not hasattr(settings, "ai_connection"):
            return False
        if not ready(self.connection_facts(), connection):
            return False
        settings.ai_connection = connection
        self._save_settings()
        self.route_chosen()
        return True

    @staticmethod
    def _set_up(facts: ConnectionFacts, connection: str) -> bool:
        return facts.free_connected if connection == FREE else ready(facts, connection)

    def note_readiness(self) -> None:
        """Remember which connections are set up, before a sign-in window opens."""
        facts = self.connection_facts()
        self._ready_before = {c: self._set_up(facts, c) for c in CONNECTIONS}

    def connection_changed(self, connection: str) -> None:
        """A window signed *connection* in or out, or saved or removed its key.

        A connection that became set up is chosen (signing in is choosing,
        10A.5). One that stopped being set up changes nothing about the stored
        choice: if it was in use, no AI is in use until the person chooses
        (decision 15). Either way the route guard hears it was a choice.
        """
        before: dict[str, bool] = getattr(self, "_ready_before", {})
        was = before.pop(connection, None)
        now = self._set_up(self.connection_facts(), connection)
        if now and was is False:
            self.choose(connection)
        self.route_chosen()

    # -- what the window and Ctrl+8 read ----------------------------------- #

    def connection_rows(self) -> list[ConnectionRow]:
        """Choose Your AI's five rows, each with its state (10A.3)."""
        return row_states(self.connection_facts())

    def capability_record(self, connection: str = "") -> ConnectionRecord:
        """The capability record for *connection* (default: the stored one)."""
        chosen = connection or self.connection
        limits = getattr(self, "_limits", None)
        return record_for(
            chosen,
            own_key_provider=self.own_key_provider or "openai",
            web_search_enabled=bool(getattr(limits, "web_search_enabled", False)),
            model=self.connection_model(chosen),
            available=self.connection_facts().available(chosen) if chosen else None,
        )

    def can_do(self, capability: str) -> bool:
        """Whether the connection in use can do *capability* now."""
        active = self.connection_in_use
        return bool(active) and can(self.capability_record(active), capability)

    def needs_label(self, capability: str) -> str:
        """The menu-label suffix for a command needing *capability*, or "" (10A.8)."""
        return "" if self.can_do(capability) else needs_label(capability)

    def capability_offer(self, capability: str) -> SwitchOffer:
        """The one-key switch sentence for *capability* (10A.8)."""
        facts = self.connection_facts()
        set_up = [c for c in CONNECTIONS if c != FREE and ready(facts, c)]
        if facts.free_connected:
            set_up.insert(0, FREE)
        limits = getattr(self, "_limits", None)
        return switch_offer(
            capability,
            set_up=set_up,
            in_use=in_use(facts),
            own_key_provider=facts.own_key_provider,
            web_search_enabled=bool(getattr(limits, "web_search_enabled", False)),
        )

    def _usage_inputs(self, free_quota: Any) -> dict[str, Any]:
        from quill.core.ai.chatgpt_usage import local_count
        from quill.core.ai.connection_usage import last_rate_limits

        account = self.chatgpt
        return {
            "app_name": str(getattr(self._app, "ai_agent_name", "") or "QUILL"),
            "free_quota": free_quota,
            "chatgpt_count": local_count(self._app.data_dir, str(getattr(account, "slug", ""))),
            "own_key_limits": last_rate_limits(self.own_key_provider or "openai"),
        }

    def usage_rows(self, free_quota: Any = None) -> list[Any]:
        """The one Usage view's rows (:class:`~quill.core.ai.connection_usage.UsageRow`)."""
        from quill.core.ai.connection_usage import usage_rows

        return usage_rows(self.connection_facts(), **self._usage_inputs(free_quota))

    def which_ai(self, free_quota: Any = None) -> str:
        """What Which AI Am I Using (Ctrl+8) speaks: connection, model, one usage clause."""
        from quill.core.ai.connection_usage import which_ai_sentence

        return which_ai_sentence(
            self.connection_facts(),
            model=self.connection_model(),
            **self._usage_inputs(free_quota),
        )

    def status_cell(self) -> str:
        """The AI status-bar cell's text (decision 19)."""
        from quill.core.ai.connection_usage import status_cell_text

        return status_cell_text(self.connection_facts(), model=self.connection_model())

    # -- the check every request makes ------------------------------------- #

    def request_allowed(self, requires: tuple[str, ...], on_error: Callable[[str], None]) -> bool:
        """Whether a request needing *requires* may leave now; on no, tells *on_error*
        once, with the sentence that says why, and nothing is sent."""
        problem = not_ready_sentence(self.connection_facts())
        if problem:
            on_error(problem)
            return False
        try:
            require(self.capability_record(), *requires)
        except CapabilityMissing as missing:
            on_error(str(missing.args[0]))
            return False
        return self.route_allowed(on_error)

    def _failure_sentence(self, error: BaseException) -> str:
        """The sentence for a failed request, with 10A.5's cases on the plan.

        A 401 forgets the sign-in and marks it ended by OpenAI; the plan's own
        limit, and usage that stayed unavailable through the bounded retry, say
        the limit sentence once. Nothing here retries or switches.
        """
        from quill.core.ai.chatgpt_errors import (
            ChatGptBusyError,
            ChatGptLimitError,
            ChatGptSignedOutError,
            ChatGptUsageUnavailableError,
        )
        from quill.core.ai.copilot_chat_parts import CopilotChatError

        if isinstance(error, CopilotChatError):
            return error.sentence  # said once; CopilotChat already marked the row
        connection = self.connection
        if connection in (CHATGPT, CODEX):
            if isinstance(error, ChatGptSignedOutError):
                try:
                    self.chatgpt.mark_ended_by_openai()
                except Exception:  # noqa: BLE001 - the sentence still holds
                    pass
                return revoked_sentence(CHATGPT)
            limited = isinstance(error, ChatGptLimitError) and not isinstance(
                error, ChatGptBusyError
            )
            if limited or isinstance(error, ChatGptUsageUnavailableError):
                agent = str(getattr(self._app, "ai_agent_name", "") or "QUILL")
                return limit_sentence(connection, agent)
        return plain_sentence(error)
