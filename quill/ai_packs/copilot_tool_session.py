"""The Copilot tool session: QUILL's family tools over the Copilot SDK (Phase 4a).

:meth:`quill.ai_packs.copilot.CopilotHarness.start_tool_session` builds one of
these. It never imports the SDK itself: the harness hands it a
``client_factory`` and the SDK classes it needs (:class:`SdkParts`), so tests
drive the real code path with a fake SDK.

How a task runs (codex.md 5.2, 5.3, 8; SDK 1.0.28 read from source):

- **Thread.** :meth:`CopilotToolSession.run` blocks on a worker thread and
  owns a private asyncio loop there -- never the UI thread's. Tool handlers
  and the permission callback are coroutines that move the blocking registry
  work to a worker thread with ``asyncio.to_thread``, so a pending approval
  never stalls the loop and Stop can still abort.
- **Only our tools.** ``tools`` is the registry's tools as ``Tool`` objects
  (not ``skip_permission``); ``available_tools`` is exactly their wire names
  (never empty, CLI issue #5306).
- **Permissions.** A ``custom-tool`` request for one of our names is approved
  only after :meth:`FamilyToolRegistry.authorize` (the broker, then the
  approver) says yes. Every other kind -- shell, write, read, url, mcp,
  memory, hook, ... -- is rejected with feedback and logged as a defect.
- **Streaming.** ``streaming=True``; ``assistant.message_delta`` becomes an
  ``AGENT_TEXT_DELTA`` event; ``assistant.message`` is the turn's answer;
  ``session.idle`` ends the turn; ``assistant.usage`` feeds ``on_usage``.
- **Stop (G4).** :meth:`CopilotToolSession.cancel` releases a pending
  approval (the approver's ``cancel()``), then on the loop:
  ``session.abort()``, ``session.disconnect()``, ``client.stop()``, and
  ``client.force_stop()`` if stopping overruns. Each step has its own
  deadline inside :data:`STOP_SECONDS` for the turn and
  :data:`CLOSE_SECONDS` for the child.
- **Local data (decision 4).** The per-app folders are swept at start,
  and cleared when the task ends -- however it ends.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from quill.core.ai.agent_workdir import AgentFolders
from quill.core.ai.approvals import Approver
from quill.core.ai.events import AgentEvent, AgentEventKind
from quill.core.ai.family_tools import FamilyToolRegistry, to_copilot_tools
from quill.core.ai.harness import AgentSpec, AIContext, HarnessResult, TurnUsage
from quill.core.ai.tool_gateway import Emit

__all__ = [
    "SdkParts",
    "CopilotToolSession",
    "RefusedToolSession",
    "STOP_SECONDS",
    "CLOSE_SECONDS",
    "REFUSAL_FEEDBACK",
]

_log = logging.getLogger(__name__)

#: Stop must end the turn within this long (G4).
STOP_SECONDS = 1.0
#: Closing must have the child gone within this long (G4).
CLOSE_SECONDS = 2.0

REFUSAL_FEEDBACK = "QUILL offers only its own tools; this request is not allowed."


@dataclass(frozen=True, slots=True)
class SdkParts:
    """The SDK classes the session needs, resolved lazily by the harness."""

    tool_cls: Any
    result_cls: Any
    binary_cls: Any
    reject_cls: Any
    approve_cls: Any


def _event_type(event: Any) -> str:
    kind = getattr(event, "type", "")
    return str(getattr(kind, "value", kind))


class RefusedToolSession:
    """A session that will not start (Safe Mode, SDK missing): says why."""

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


class CopilotToolSession:
    """One agent task on Copilot, over the family tools. See the module doc."""

    def __init__(
        self,
        *,
        agent: AgentSpec,
        ctx: AIContext,
        tools: FamilyToolRegistry,
        approver: Approver,
        emit: Emit,
        sdk: SdkParts,
        client_factory: Callable[[AgentFolders], Any],
        folders: AgentFolders,
        session_options: dict[str, Any],
        keep_open: bool = False,
        on_usage: Callable[[TurnUsage], None] | None = None,
        display_name: str = "GitHub Copilot",
        stop_seconds: float = STOP_SECONDS,
        close_seconds: float = CLOSE_SECONDS,
    ) -> None:
        self._id = uuid.uuid4().hex
        self._agent = agent
        self._ctx = ctx
        self._tools = tools
        self._approver = approver
        self._emit = emit
        self._sdk = sdk
        self._client_factory = client_factory
        self._folders = folders
        self._session_options = dict(session_options)
        self._keep_open = keep_open
        self._on_usage = on_usage
        self._name = display_name
        self._stop_seconds = stop_seconds
        self._close_seconds = close_seconds

        self._queue: deque[str] = deque()
        self._cancelled = False
        self._ended = False
        self._started = False
        self._lock = threading.Lock()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._cancel_event: asyncio.Event | None = None
        self._wake: asyncio.Event | None = None
        self._turn_done: asyncio.Event | None = None
        self._turn_error = ""
        self._answer = ""
        self._recorded_tools: list[str] = []

    # -- public, any thread -------------------------------------------------

    @property
    def session_id(self) -> str:
        return self._id

    @property
    def recorded_tool_names(self) -> list[str]:
        """The tool names offered to the engine (G3 checks they are all ours)."""
        return list(self._recorded_tools)

    def send(self, follow_up: str) -> None:
        text = follow_up.strip()
        if not text:
            return
        self._queue.append(text)
        self._poke("_wake")

    def end(self) -> None:
        self._ended = True
        self._poke("_wake")

    def cancel(self) -> None:
        self._cancelled = True
        release = getattr(self._approver, "cancel", None)
        if callable(release):
            release()  # a pending approval answers "Don't allow" now
        self._poke("_cancel_event")
        self._poke("_wake")

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
        loop = asyncio.new_event_loop()
        self._cancel_event = asyncio.Event()
        self._wake = asyncio.Event()
        self._loop = loop
        self._tools.set_emit(self._emit)
        self._tools.gate.begin_task(self._approver)
        try:
            self._folders.prepare()
            return loop.run_until_complete(self._main())
        except Exception as exc:  # noqa: BLE001 - an engine failure is a result
            _log.warning("Copilot tool session failed: %s", type(exc).__name__)
            self._emit(AgentEvent(AgentEventKind.ERROR, f"{self._name} could not complete."))
            return HarnessResult(status="error", error=str(exc))
        finally:
            self._tools.gate.end_task()
            self._folders.clear()
            self._loop = None
            loop.close()

    async def _main(self) -> HarnessResult:
        self._emit(AgentEvent(AgentEventKind.AGENT_STARTED, f"{self._name} started."))
        client = self._client_factory(self._folders)
        session: Any = None
        try:
            await client.start()
            if self._cancelled:
                return self._cancelled_result()
            session = await client.create_session(**self._create_kwargs())
            session.on(self._on_event)
            prompt: str | None = f"{self._ctx.prompt}\n\n{self._ctx.context_text}".strip()
            while prompt is not None:
                self._turn_done = asyncio.Event()
                self._turn_error = ""
                await session.send(prompt)
                await self._wait_turn()
                if self._cancelled:
                    await self._quietly(session.abort(), self._stop_seconds / 2)
                    return self._cancelled_result()
                if self._turn_error:
                    self._emit(AgentEvent(AgentEventKind.ERROR, self._turn_error))
                    return HarnessResult(status="error", error=self._turn_error)
                prompt = await self._next_prompt()
            if self._cancelled:
                return self._cancelled_result()
            self._emit(AgentEvent(AgentEventKind.AGENT_COMPLETED, f"{self._name} finished."))
            return HarnessResult(status="completed", final_text=self._answer)
        finally:
            await self._shutdown(client, session)

    def _create_kwargs(self) -> dict[str, Any]:
        from quill.ai_packs.copilot import available_tools_for, system_message_for

        sdk_tools = to_copilot_tools(
            self._tools,
            tool_cls=self._sdk.tool_cls,
            result_cls=self._sdk.result_cls,
            binary_cls=self._sdk.binary_cls,
        )
        names = available_tools_for(self._tools.wire_names())
        self._recorded_tools = list(names)
        kwargs: dict[str, Any] = dict(self._session_options)
        kwargs.update({
            "tools": sdk_tools,
            "available_tools": names,
            "on_permission_request": self._on_permission,
            "streaming": True,
            "working_directory": str(self._folders.work),
        })
        system_message = system_message_for(self._agent.system_prompt)
        if system_message is not None:
            kwargs["system_message"] = system_message
        return kwargs

    # -- engine callbacks ---------------------------------------------------

    async def _on_permission(self, request: Any, invocation: Any) -> Any:
        kind = str(getattr(request, "kind", ""))
        if kind == "custom-tool":
            name = str(getattr(request, "tool_name", ""))
            if name in self._tools.wire_names():
                args = getattr(request, "args", None)
                call_id = str(getattr(request, "tool_call_id", "") or "")
                ok, reason = await asyncio.to_thread(
                    self._tools.authorize, name, args if isinstance(args, dict) else {}, call_id
                )
                if ok:
                    return self._sdk.approve_cls()
                return self._sdk.reject_cls(feedback=reason or REFUSAL_FEEDBACK)
            self._tools.record_defect(f"Copilot asked to run a tool QUILL does not offer: {name}.")
        else:
            self._tools.record_defect(
                f"Copilot asked for a {kind or 'unknown'} permission; refused."
            )
        return self._sdk.reject_cls(feedback=REFUSAL_FEEDBACK)

    def _on_event(self, event: Any) -> None:
        kind = _event_type(event)
        data = getattr(event, "data", None)
        if kind == "assistant.message_delta":
            delta = str(getattr(data, "delta_content", "") or "")
            if delta:
                self._emit(AgentEvent(AgentEventKind.AGENT_TEXT_DELTA, delta, {"stream": "delta"}))
        elif kind == "assistant.message":
            content = getattr(data, "content", "")
            if isinstance(content, str) and content:
                self._answer = content
        elif kind == "assistant.usage":
            if self._on_usage is not None:
                self._on_usage(
                    TurnUsage(
                        engine="copilot",
                        model=str(getattr(data, "model", "") or ""),
                        input_tokens=int(getattr(data, "input_tokens", 0) or 0),
                        output_tokens=int(getattr(data, "output_tokens", 0) or 0),
                    )
                )
        elif kind == "session.idle":
            self._poke("_turn_done")
        elif kind == "session.error":
            self._turn_error = str(getattr(data, "message", "") or "The engine reported an error.")
            self._poke("_turn_done")

    # -- loop helpers -------------------------------------------------------

    def _poke(self, attr: str) -> None:
        """Set one of the loop's events from any thread."""
        loop = self._loop
        event = getattr(self, attr)
        if loop is None or event is None:
            return
        try:
            loop.call_soon_threadsafe(event.set)
        except RuntimeError:  # the loop already closed
            pass

    async def _wait_turn(self) -> None:
        assert self._turn_done is not None and self._cancel_event is not None
        waiters = {
            asyncio.ensure_future(self._turn_done.wait()),
            asyncio.ensure_future(self._cancel_event.wait()),
        }
        _done, pending = await asyncio.wait(waiters, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()

    async def _next_prompt(self) -> str | None:
        assert self._wake is not None
        while True:
            self._wake.clear()
            if self._cancelled:
                return None
            if self._queue:
                return self._queue.popleft()
            if not self._keep_open or self._ended:
                return None
            await self._wake.wait()

    @staticmethod
    async def _quietly(awaitable: Any, seconds: float) -> bool:
        """Await with a deadline; True when it finished cleanly."""
        try:
            await asyncio.wait_for(awaitable, timeout=seconds)
            return True
        except Exception:  # noqa: BLE001 - shutdown is best effort, then forced
            return False

    async def _shutdown(self, client: Any, session: Any) -> None:
        budget = self._close_seconds
        if session is not None:
            await self._quietly(session.disconnect(), budget / 4)
        if not await self._quietly(client.stop(), budget / 4):
            await self._quietly(client.force_stop(), budget / 2)

    def _cancelled_result(self) -> HarnessResult:
        self._emit(AgentEvent(AgentEventKind.AGENT_CANCELLED, f"{self._name} stopped."))
        return HarnessResult(status="cancelled")
