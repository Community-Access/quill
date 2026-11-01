"""The Codex engine: QUILL's family tools on the person's ChatGPT plan (Phase 4b).

:class:`CodexHarness` is the harness the engine registry lists; its
:meth:`~CodexHarness.start_tool_session` returns a :class:`CodexToolSession`,
which drives one :class:`~quill.core.ai.codex_app_server.CodexAppServer` child
for one task. Mirrors :mod:`quill.ai_packs.copilot_tool_session`, with plain
threads instead of asyncio because app-server is a JSON-RPC child, not an SDK.

How a task runs (codex.md 2, 5.2, 5.3, 5.4, 8, decisions 4 and 21):

- **Token.** This app's own ChatGPT sign-in (its agent name), read when the
  task starts and again before every turn. A different token means the
  account renewed it: the child restarts with the new one and the thread is
  resumed (``thread/resume``), serialized, so the conversation carries on
  (G2). An ``unauthorized`` turn gets one renewal and one retry, never a loop.
- **Only our tools (G3).** ``thread/start`` carries the registry's
  ``dynamicTools`` and nothing else; the launch switches and the ``config``
  map turn Codex's own tools off; ``sandbox`` is ``read-only`` and
  ``approvalPolicy`` is ``untrusted``, so anything that slipped through has to
  ask -- and every built-in approval is declined and logged as a defect.
- **Tool calls.** ``item/tool/call`` goes to :meth:`FamilyToolRegistry.call`,
  one at a time; the broker, the approver and the diff review decide there.
- **Stop (G4).** :meth:`CodexToolSession.cancel` releases a pending approval,
  the run thread sends ``turn/interrupt`` at once, and the child is closed
  (killed if it lingers) within :data:`CLOSE_SECONDS`.
- **Local data (decision 4).** ``CODEX_HOME`` is swept at start, kept through
  a renewal, and cleared when the task ends, however it ends.
- **Single requests (decision 21)** never start a child: they go to the plan's
  direct route, so :meth:`CodexHarness.start_session` says so and does nothing.

wx-free, strict-typed.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
import uuid
from collections import deque
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from quill.core.ai.agent_workdir import AgentFolders, agent_folders
from quill.core.ai.codex_app_server import (
    CLOSE_SECONDS,
    STOP_SECONDS,
    CodexAppServer,
    CodexProtocolError,
    CodexRpcError,
    NotificationHandler,
    RequestHandler,
    thread_config,
)
from quill.core.ai.codex_binary import find_codex_app_server
from quill.core.ai.copilot_auth import DEFAULT_AGENT_NAME
from quill.core.ai.events import AgentEvent, AgentEventKind
from quill.core.ai.family_tools import ToolCallResult, codex_tool_response, to_codex_dynamic_tools
from quill.core.ai.harness import (
    AgentSpec,
    AIContext,
    HarnessCapabilities,
    HarnessResult,
    TurnUsage,
)
from quill.core.error_codes import CodedError
from quill.stability.safe_mode import should_enable_safe_mode

if TYPE_CHECKING:
    from pathlib import Path

    from quill.core.ai.approvals import Approver
    from quill.core.ai.family_tools import FamilyToolRegistry
    from quill.core.ai.permissions import PermissionBroker
    from quill.core.ai.tool_gateway import Emit, SafeEditorToolGateway

__all__ = [
    "CodexHarness",
    "CodexToolSession",
    "ServerFactory",
    "SINGLE_REQUEST_SENTENCE",
    "LIMIT_SENTENCE",
]

_log = logging.getLogger(__name__)

SINGLE_REQUEST_SENTENCE = "Codex, on your ChatGPT plan. Single requests go to the plan directly."
LIMIT_SENTENCE = (
    "Your ChatGPT plan's usage limit is reached. It resets on its own; "
    "Manage usage in ChatGPT shows when."
)
_SIGNED_OUT = "Your ChatGPT sign-in has ended. Sign in again in Choose Your AI."

#: ``(folders, token, on_notification, on_request) -> CodexAppServer`` (not started).
ServerFactory = Callable[[AgentFolders, str, NotificationHandler, RequestHandler], CodexAppServer]

#: Built-in approvals: each is declined and logged as a defect (5.3).
_DECLINE_ANSWERS: dict[str, dict[str, Any]] = {
    "item/commandExecution/requestApproval": {"decision": "decline"},
    "item/fileChange/requestApproval": {"decision": "decline"},
    "execCommandApproval": {"decision": "denied"},
    "applyPatchApproval": {"decision": "denied"},
    "mcpServer/elicitation/request": {"action": "decline"},
}


class _RefusedSession:
    """A session that will not start (Safe Mode, no engine, single request)."""

    def __init__(self, reason: str, emit: Emit) -> None:
        self._id = uuid.uuid4().hex
        self._reason = reason
        self._emit = emit

    @property
    def session_id(self) -> str:
        return self._id

    def run(self) -> HarnessResult:
        self._emit(AgentEvent(AgentEventKind.ERROR, self._reason))
        return HarnessResult(status="error", error=self._reason)

    def cancel(self) -> None:
        return None

    def send(self, follow_up: str) -> None:
        return None

    def end(self) -> None:
        return None


def _plain(exc: BaseException) -> str:
    """A coded error's own sentence, without the ``[QUILL-...]`` prefix."""
    if isinstance(exc, CodedError) and exc.args:
        return str(exc.args[0])
    return "The Codex engine could not complete."


def _outcome(turn: dict[str, Any]) -> tuple[str, str]:
    """``(outcome, message)`` for a ``turn/completed`` turn."""
    status = str(turn.get("status", ""))
    if status == "completed":
        return "completed", ""
    error = turn.get("error")
    raw = json.dumps(error).lower() if error is not None else ""
    if "usagelimitexceeded" in raw or "usage_limit_exceeded" in raw:
        return "limit", LIMIT_SENTENCE
    if "unauthorized" in raw or "401" in raw:
        return "unauthorized", _SIGNED_OUT
    message = error.get("message") if isinstance(error, dict) else None
    return status or "failed", str(message or "The Codex engine reported an error.")


class CodexToolSession:
    """One agent task on Codex, over the family tools. See the module doc."""

    def __init__(
        self,
        *,
        agent: AgentSpec,
        ctx: AIContext,
        tools: FamilyToolRegistry,
        approver: Approver,
        emit: Emit,
        token_provider: Callable[[], str],
        server_factory: ServerFactory,
        folders: AgentFolders,
        keep_open: bool = False,
        on_usage: Callable[[TurnUsage], None] | None = None,
        model: str | None = None,
        display_name: str = "Codex",
        stop_seconds: float = STOP_SECONDS,
        close_seconds: float = CLOSE_SECONDS,
        turn_timeout: float = 900.0,
    ) -> None:
        self._id = uuid.uuid4().hex
        self._agent = agent
        self._ctx = ctx
        self._tools = tools
        self._approver = approver
        self._emit = emit
        self._token_provider = token_provider
        self._factory = server_factory
        self._folders = folders
        self._keep_open = keep_open
        self._on_usage = on_usage
        self._model = model
        self._name = display_name
        self._stop_seconds = stop_seconds
        self._close_seconds = close_seconds
        self._turn_timeout = turn_timeout

        self._queue: deque[str] = deque()
        self._cancelled = False
        self._ended = False
        self._started = False
        self._lock = threading.Lock()
        self._refresh_lock = threading.Lock()
        self._tool_lock = threading.Lock()
        self._wake = threading.Event()
        self._turn_done = threading.Event()
        self._turn_outcome = ""
        self._turn_message = ""
        self._answer = ""
        self._token = ""
        self._server: CodexAppServer | None = None
        self._thread_id = ""
        self._thread_params: dict[str, Any] = {}
        self.rate_limits: dict[str, Any] | None = None
        self.restarts = 0

    # -- public, any thread -------------------------------------------------

    @property
    def session_id(self) -> str:
        return self._id

    @property
    def recorded_thread_params(self) -> dict[str, Any]:
        """The ``thread/start`` params sent (G3 checks the tools are all ours)."""
        return dict(self._thread_params)

    @property
    def recorded_tool_names(self) -> list[str]:
        return [str(t.get("name", "")) for t in self._thread_params.get("dynamicTools", [])]

    @property
    def thread_id(self) -> str:
        return self._thread_id

    def send(self, follow_up: str) -> None:
        text = follow_up.strip()
        if text:
            self._queue.append(text)
            self._wake.set()

    def end(self) -> None:
        self._ended = True
        self._wake.set()

    def cancel(self) -> None:
        self._cancelled = True
        release = getattr(self._approver, "cancel", None)
        if callable(release):
            release()  # a pending approval answers "Don't allow" now
        self._turn_done.set()
        self._wake.set()

    # -- run, worker thread -------------------------------------------------

    def run(self) -> HarnessResult:
        with self._lock:
            if self._started:
                return HarnessResult(status="error", error="This session has already run.")
            self._started = True
        if self._cancelled:
            return self._cancelled_result()
        reset = getattr(self._approver, "reset", None)
        if callable(reset):
            reset()
        self._tools.set_emit(self._emit)
        self._tools.gate.begin_task(self._approver)
        try:
            self._folders.prepare()
            return self._main()
        except Exception as exc:  # noqa: BLE001 - an engine failure is a result
            _log.warning("Codex tool session failed: %s", type(exc).__name__)
            message = _plain(exc)
            self._emit(AgentEvent(AgentEventKind.ERROR, message))
            return HarnessResult(status="error", error=message)
        finally:
            self._tools.gate.end_task()
            self._close_server()
            self._folders.clear()

    def _main(self) -> HarnessResult:
        self._emit(AgentEvent(AgentEventKind.AGENT_STARTED, f"{self._name} started."))
        self._token = self._token_provider()
        self._server = self._launch(self._token)
        if self._cancelled:
            return self._cancelled_result()
        self._thread_params = self._build_thread_params()
        self._thread_id = self._server.thread_start(self._thread_params)
        if not self._thread_id:
            raise CodexProtocolError("The Codex engine did not start a conversation.")
        self.rate_limits = self._server.read_rate_limits(timeout=2.0)
        prompt: str | None = f"{self._ctx.prompt}\n\n{self._ctx.context_text}".strip()
        while prompt is not None:
            self._refresh(only_if_renewed=True)
            outcome = self._run_turn(prompt)
            if outcome == "unauthorized" and not self._cancelled and self._refresh():
                outcome = self._run_turn(prompt)
            if self._cancelled:
                return self._cancelled_result()
            if outcome != "completed":
                self._emit(AgentEvent(AgentEventKind.ERROR, self._turn_message))
                return HarnessResult(status="error", error=self._turn_message)
            prompt = self._next_prompt()
        if self._cancelled:
            return self._cancelled_result()
        self._emit(AgentEvent(AgentEventKind.AGENT_COMPLETED, f"{self._name} finished."))
        return HarnessResult(status="completed", final_text=self._answer)

    def _build_thread_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {
            "cwd": str(self._folders.work),
            "approvalPolicy": "untrusted",
            "sandbox": "read-only",
            "ephemeral": False,  # kept for the task so a renewal can resume (decision 4)
            "config": thread_config(),
            "dynamicTools": to_codex_dynamic_tools(self._tools),
        }
        if self._agent.system_prompt.strip():
            # Developer instructions, not base: the vendor's own stay in place.
            params["developerInstructions"] = self._agent.system_prompt.strip()
        if self._model:
            params["model"] = self._model
        return params

    def _launch(self, token: str) -> CodexAppServer:
        server = self._factory(self._folders, token, self._on_notification, self._on_request)
        server.start()
        return server

    def _run_turn(self, prompt: str) -> str:
        server = self._server
        assert server is not None
        self._turn_done.clear()
        self._turn_outcome = ""
        self._turn_message = ""
        if self._cancelled:
            return "cancelled"
        turn_id = server.turn_start(self._thread_id, prompt)
        deadline = time.monotonic() + self._turn_timeout
        while not self._turn_done.wait(0.25):
            if not server.running:
                self._turn_message = "The Codex engine stopped unexpectedly."
                return "failed"
            if time.monotonic() > deadline:
                self._turn_message = "The Codex engine took too long to answer."
                server.turn_interrupt(self._thread_id, turn_id, timeout=self._stop_seconds / 2)
                return "failed"
        if self._cancelled:
            server.turn_interrupt(self._thread_id, turn_id, timeout=self._stop_seconds / 2)
            return "cancelled"
        return self._turn_outcome or "failed"

    def _refresh(self, *, only_if_renewed: bool = False) -> bool:
        """Restart with a renewed token and resume the thread (G2), serialized.

        True when the child now runs on a different token than before.
        """
        with self._refresh_lock:
            token = self._token_provider()
            if not token or token == self._token:
                if not only_if_renewed:
                    self._turn_message = _SIGNED_OUT
                return False
            self._close_server()
            self._token = token
            self._server = self._launch(token)
            self._thread_id = self._server.thread_resume(self._thread_id)
            self.restarts += 1
            return True

    def _next_prompt(self) -> str | None:
        while True:
            self._wake.clear()
            if self._cancelled:
                return None
            if self._queue:
                return self._queue.popleft()
            if not self._keep_open or self._ended:
                return None
            self._wake.wait()

    def _close_server(self) -> None:
        server, self._server = self._server, None
        if server is not None:
            server.close(self._close_seconds)

    def _cancelled_result(self) -> HarnessResult:
        self._emit(AgentEvent(AgentEventKind.AGENT_CANCELLED, f"{self._name} stopped."))
        return HarnessResult(status="cancelled")

    # -- engine callbacks (reader and request threads) ----------------------

    def _on_notification(self, method: str, params: dict[str, Any]) -> None:
        if method == "item/agentMessage/delta":
            delta = str(params.get("delta", "") or "")
            if delta:
                self._emit(AgentEvent(AgentEventKind.AGENT_TEXT_DELTA, delta, {"stream": "delta"}))
        elif method == "item/completed":
            item = params.get("item")
            if isinstance(item, dict) and item.get("type") == "agentMessage":
                text = item.get("text")
                if isinstance(text, str) and text:
                    self._answer = text
        elif method == "turn/completed":
            turn = params.get("turn")
            self._turn_outcome, self._turn_message = _outcome(
                turn if isinstance(turn, dict) else {}
            )
            self._turn_done.set()
        elif method == "thread/tokenUsage/updated":
            self._usage(params)
        elif method == "account/rateLimits/updated":
            self.rate_limits = params

    def _usage(self, params: dict[str, Any]) -> None:
        usage = params.get("tokenUsage")
        last = usage.get("last") if isinstance(usage, dict) else None
        if self._on_usage is None or not isinstance(last, dict):
            return
        self._on_usage(
            TurnUsage(
                engine="codex",
                model=self._model or "",
                input_tokens=int(last.get("inputTokens", 0) or 0),
                output_tokens=int(last.get("outputTokens", 0) or 0),
            )
        )

    def _on_request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method == "item/tool/call":
            return self._tool_call(params)
        self._tools.record_defect(f"Codex sent {method}, which QUILL never allows; declined.")
        answer = _DECLINE_ANSWERS.get(method)
        if answer is not None:
            return dict(answer)
        raise CodexRpcError("QUILL does not offer this.", rpc_code=-32601)

    def _tool_call(self, params: dict[str, Any]) -> dict[str, Any]:
        name = str(params.get("tool", "") or "")
        args = params.get("arguments")
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except ValueError:
                args = {}
        call_id = str(params.get("callId", "") or "")
        if self._cancelled:
            return codex_tool_response(ToolCallResult(text="The task was stopped.", ok=False))
        if self._tools.get(name) is None:
            self._tools.record_defect(f"Codex asked to run a tool QUILL does not offer: {name}.")
        with self._tool_lock:
            result = self._tools.call(name, args if isinstance(args, dict) else {}, call_id)
        return codex_tool_response(result)


class CodexHarness:
    """The Codex engine in the registry: app tools on, one-shot work refused.

    ``token_provider`` should be the app's own ``ChatGptAccount.access_token``
    (the account the app already holds); without one, an account for
    ``agent_name`` is built at task start. Never another app's account (5.4).
    """

    def __init__(
        self,
        *,
        agent_name: str = DEFAULT_AGENT_NAME,
        token_provider: Callable[[], str] | None = None,
        server_factory: ServerFactory | None = None,
        binary_resolver: Callable[[], Path | None] = find_codex_app_server,
    ) -> None:
        self.agent_name = agent_name
        self._token_provider = token_provider
        self._server_factory = server_factory
        self._binary_resolver = binary_resolver

    @property
    def id(self) -> str:
        return "codex"

    @property
    def display_name(self) -> str:
        return "Codex"

    def is_available(self) -> tuple[bool, str | None]:
        if self._binary_resolver() is None:
            return False, "This build does not include the Codex engine."
        return True, None

    def capabilities(self) -> HarnessCapabilities:
        return HarnessCapabilities(
            chat=True,
            streaming=True,
            tool_calling=True,
            patch_generation=True,
            mcp=False,
            audio=False,
            images=True,
            requires_oauth=True,
            app_tools=True,
        )

    def start_session(
        self,
        agent: AgentSpec,
        ctx: AIContext,
        gateway: SafeEditorToolGateway,
        broker: PermissionBroker,
        emit: Emit,
    ) -> _RefusedSession:
        """Single requests take the plan's direct route (decision 21), never a child."""
        return _RefusedSession(SINGLE_REQUEST_SENTENCE, emit)

    def _default_token_provider(self) -> Callable[[], str]:
        from quill.core.ai.chatgpt_account import ChatGptAccount
        from quill.core.paths import app_data_dir

        return ChatGptAccount(app_data_dir(), agent_name=self.agent_name).access_token

    def _default_factory(self) -> ServerFactory:
        agent_name = self.agent_name

        def _factory(
            folders: AgentFolders,
            token: str,
            on_notification: NotificationHandler,
            on_request: RequestHandler,
        ) -> CodexAppServer:
            return CodexAppServer(
                agent_name=agent_name,
                folders=folders,
                token=token,
                on_notification=on_notification,
                on_request=on_request,
            )

        return _factory

    def start_tool_session(
        self,
        agent: AgentSpec,
        ctx: AIContext,
        tools: FamilyToolRegistry,
        approver: Approver,
        emit: Emit,
        *,
        keep_open: bool = False,
        on_usage: Callable[[TurnUsage], None] | None = None,
        model: str | None = None,
        folders: AgentFolders | None = None,
    ) -> CodexToolSession | _RefusedSession:
        """A multi-turn task over the family tools; refused in Safe Mode (G4)."""
        if should_enable_safe_mode(sys.argv, os.environ):
            return _RefusedSession("Safe Mode is on, so AI agents are off.", emit)
        available, reason = self.is_available()
        if not available:
            return _RefusedSession(reason or "Codex is not available.", emit)
        return CodexToolSession(
            agent=agent,
            ctx=ctx,
            tools=tools,
            approver=approver,
            emit=emit,
            token_provider=self._token_provider or self._default_token_provider(),
            server_factory=self._server_factory or self._default_factory(),
            folders=folders or agent_folders("codex", self.agent_name),
            keep_open=keep_open,
            on_usage=on_usage,
            model=model,
        )
