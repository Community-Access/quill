"""My GitHub Copilot and Codex, as :class:`quill.ui.hosted_ai_service.AiService` sees them.

Mixed into the one service both editors share, ahead of the route mixins, so
QUILL and QUILL Lite reach Copilot and Codex the same way (rule 10). It adds
what Phase 2 and Phase 4 need from the service and nothing else:

* **Readiness, read locally.** Whether this app has a GitHub registration, the
  engine and its own token (:func:`quill.core.ai.copilot_state.readiness`),
  and whether the bundled Codex app-server is here. These become
  :class:`~quill.core.ai.connection_choice.ConnectionFacts` fields, so the
  window's rows, Ctrl+8 and every request read one truth.
* **Requests on Copilot** (codex.md 10A.12): ask, a conversation turn and Ask
  About an Image go through :class:`~quill.core.ai.copilot_chat.CopilotChat`
  on a worker; the service's own request methods hand the answer back with
  ``wx.CallAfter``. A failure is said once with its ``sentence`` -- no retry,
  no switch (10A.5).
* **GitHub's count**, fetched on a worker and kept for this session, so the
  Usage list and Which AI Am I Using can say it without blocking the window.
* **The agent engine for the connection in use**: Copilot's tool harness, or
  Codex given this app's own ChatGPT access token -- never another app's
  (5.4, decision 21).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.ai.connection_caps import CODEX, COPILOT

__all__ = ["CopilotRouteMixin"]


class _ModelHarness:
    """A tool harness that starts every session on a chosen model."""

    def __init__(self, harness: Any, model: str) -> None:
        self._harness = harness
        self._model = model

    @property
    def id(self) -> str:
        return str(self._harness.id)

    @property
    def display_name(self) -> str:
        return str(getattr(self._harness, "display_name", self._harness.id))

    def capabilities(self) -> Any:
        return self._harness.capabilities()

    def start_tool_session(self, *args: Any, **kwargs: Any) -> Any:
        if self._model:
            kwargs.setdefault("model", self._model)
        return self._harness.start_tool_session(*args, **kwargs)


class CopilotRouteMixin:
    """Copilot's readiness, requests, models and count; the agent engine."""

    _app: Any
    chatgpt: Any
    data_dir: Any
    connection: str
    route: str

    # -- who this app is ----------------------------------------------------- #

    @property
    def agent_name(self) -> str:
        """The app's own name on GitHub's and OpenAI's pages: "QUILL", "QUILL Lite"."""
        return str(getattr(self._app, "ai_agent_name", "") or "QUILL")

    # -- readiness ------------------------------------------------------------ #

    def copilot_readiness(self) -> Any:
        from quill.core.ai.copilot_state import readiness

        return readiness(self.agent_name, data_dir=self.data_dir)

    @property
    def codex_available(self) -> bool:
        """Whether this build carries the Codex app-server (decision 1)."""
        try:
            from quill.core.ai.codex_binary import find_codex_app_server

            return find_codex_app_server() is not None
        except Exception:  # noqa: BLE001 - an unreadable folder is "not here"
            return False

    def _engine_facts(self) -> dict[str, bool]:
        """The Copilot and Codex fields of ``ConnectionFacts``, read locally."""
        try:
            state = self.copilot_readiness()
            fields = {
                "copilot_available": state.available,
                "copilot_signed_in": state.signed_in,
                "copilot_ended": state.marks.ended_by_github and not state.signed_in,
                "copilot_policy_off": state.marks.policy_off,
            }
        except Exception:  # noqa: BLE001 - an unreadable store is "not available"
            fields = {}
        fields["codex_available"] = self.codex_available
        return fields

    def engine_unavailable_about(self, connection: str) -> str:
        """Why the Copilot or Codex row reads "not available yet", in one sentence."""
        from quill.core.ai.connection_words import engine_unavailable_about

        registered = True
        if connection == COPILOT:
            from quill.core.ai.copilot_auth import is_configured

            registered = is_configured(self.agent_name)
        return engine_unavailable_about(connection, registered=registered, app_name=self.agent_name)

    # -- requests ---------------------------------------------------------------- #

    @property
    def copilot_active(self) -> bool:
        """Whether single requests go to GitHub Copilot."""
        return self.route == COPILOT

    def copilot_chat(self) -> Any:
        """A :class:`CopilotChat` on this app's own sign-in and chosen model."""
        from quill.core.ai.copilot_chat import CopilotChat

        model = str(getattr(getattr(self._app, "settings", None), "ai_copilot_model", "") or "")
        return CopilotChat(
            self.agent_name, app_name=self.agent_name, model=model, data_dir=self.data_dir
        )

    def _copilot_ask_work(
        self, feature: str, prompt: str, chunks: list[str] | None, language: str, stop: Any
    ) -> Callable[..., tuple[str, None]]:
        from quill.core.ai.copilot_ai_help import ask_with_copilot

        chat = self.copilot_chat()

        def work(**_kwargs: Any) -> tuple[str, None]:
            answer = ask_with_copilot(
                chat,
                feature,
                prompt,
                chunks,
                language=language or "English",
                on_delta=lambda _piece: None,
                stop=stop.is_set,
            )
            return answer, None

        return work

    def _copilot_converse_work(
        self, prompt: str, chunks: list[str] | None, history: list[dict[str, str]], stop: Any
    ) -> Callable[..., tuple[str, None, int]]:
        from quill.core.ai.copilot_ai_help import converse_with_copilot

        chat = self.copilot_chat()

        def work(**_kwargs: Any) -> tuple[str, None, int]:
            reply = converse_with_copilot(
                chat, prompt, chunks, history, on_delta=lambda _piece: None, stop=stop.is_set
            )
            return reply, None, 0

        return work

    def _copilot_image_work(self, path: Any, question: str) -> Callable[..., str]:
        from quill.core.ai.copilot_ai_help import describe_image_with_copilot

        chat = self.copilot_chat()
        return lambda **_kwargs: describe_image_with_copilot(chat, path, question)

    # -- models --------------------------------------------------------------- #

    def copilot_models(self) -> tuple[list[tuple[str, str]], str]:
        """``([(id, label), ...], error)`` from ``models.list``. Blocking; a worker calls it.

        Copilot Free's one Auto row comes back alone; the window shows it as the
        only choice (10A.4).
        """
        from quill.core.ai.copilot_chat import CopilotChatError

        try:
            listed = self.copilot_chat().list_models()
        except CopilotChatError as error:
            return [], error.sentence
        return [(model.id, model.name) for model in listed.models], ""

    # -- GitHub's count ---------------------------------------------------------- #

    @property
    def last_copilot_quota(self) -> Any:
        """GitHub's last count for this app's account, or None before one arrives."""
        return getattr(self, "_copilot_quota", None)

    def fetch_copilot_quota(
        self, *, on_done: Callable[[Any], None], on_error: Callable[[str], None]
    ) -> None:
        """Ask GitHub for this account's quota on a worker; answers on the UI thread."""
        from quill.ui.hosted_ai_service import _call_after, _submit

        chat = self.copilot_chat()

        def done(_name: str, quota: Any) -> None:
            self._copilot_quota = quota
            _call_after(on_done, quota)

        def failed(_name: str, error: BaseException) -> None:
            _call_after(on_error, str(getattr(error, "sentence", "") or error))

        _submit(
            "quill-ai-copilot-quota", lambda **_k: chat.quota(), on_success=done, on_failure=failed
        )

    def _usage_inputs(self, free_quota: Any) -> dict[str, Any]:
        inputs: dict[str, Any] = super()._usage_inputs(free_quota)  # type: ignore[misc]
        inputs["copilot_quota"] = self.last_copilot_quota
        return inputs

    def which_ai_later(self, say: Callable[[str], None]) -> None:
        """Which AI Am I Using, with GitHub's count when Copilot is in use.

        One line, said once. With a count already kept it is said at once and
        the count refreshed quietly for next time; with none yet, the line waits
        for GitHub's answer (or its failure), so the window never blocks.
        """
        which: Callable[[], str] = self.which_ai  # type: ignore[attr-defined]
        in_use = str(getattr(self, "connection_in_use", "") or "")
        if in_use != COPILOT:
            say(which())
            return
        if self.last_copilot_quota is not None:
            say(which())
            self.fetch_copilot_quota(on_done=lambda _q: None, on_error=lambda _m: None)
            return
        self.fetch_copilot_quota(on_done=lambda _q: say(which()), on_error=lambda _m: say(which()))

    # -- the words, on Copilot ------------------------------------------------------ #

    @property
    def route_label(self) -> str:
        if self.copilot_active:
            return "your GitHub Copilot"
        return str(super().route_label)  # type: ignore[misc]

    @property
    def direct_model(self) -> str:
        if self.copilot_active:
            settings = getattr(self._app, "settings", None)
            return str(getattr(settings, "ai_copilot_model", "") or "")
        return str(super().direct_model)  # type: ignore[misc]

    def size_note(self, text: str) -> str:
        if self.copilot_active:
            return ""  # Copilot reports no size QUILL can compare against
        return str(super().size_note(text))  # type: ignore[misc]

    def conversation_note(self) -> str:
        if self.copilot_active:
            return (
                "This conversation uses your GitHub Copilot: no QUILL limit, and each "
                "message counts toward your Copilot plan. The whole conversation goes "
                "with each message."
            )
        return str(super().conversation_note())  # type: ignore[misc]

    # -- the agent engine ------------------------------------------------------------ #

    def agent_harness(self, connection: str = "") -> Any:
        """The tool harness for *connection* (default: the one in use), or None.

        Copilot runs its tool harness on this app's own GitHub sign-in; Codex
        is given this app's own ChatGPT access token as its ``token_provider``.
        Each starts on the model chosen for it, when one is.
        """
        chosen = connection or str(getattr(self, "connection_in_use", "") or "")
        settings = getattr(self._app, "settings", None)
        if chosen == COPILOT:
            from quill.ai_packs.copilot import CopilotHarness

            model = str(getattr(settings, "ai_copilot_model", "") or "")
            return _ModelHarness(CopilotHarness(agent_name=self.agent_name), model)
        if chosen == CODEX:
            from quill.core.ai.harness.codex import CodexHarness

            model = str(getattr(settings, "ai_codex_model", "") or "")
            harness = CodexHarness(
                agent_name=self.agent_name, token_provider=self.chatgpt.access_token
            )
            return _ModelHarness(harness, model)
        return None
