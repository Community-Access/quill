"""Claude through the Agent SDK, on the person's own key, with QUILL's tools (code.md 3.3).

**Own key only.** Anthropic does not allow a third-party product to offer
claude.ai sign-in, so this is My own key's Claude, billed per token to the
person. Branding follows the SDK's rules: "Claude" or "Claude Agent", never
"Claude Code".

**QUILL's tools, not Claude Code's** (decision 4):

- The registry's tools become an in-process MCP server (``quill``), and only
  their names are in ``allowed_tools``; each handler is
  :meth:`FamilyToolRegistry.call`, so the broker, the approval question and the
  review apply exactly as under Copilot.
- Every Claude Code built-in is named in ``disallowed_tools`` -- named, not
  ``"*"``, because a deny rule beats everything and ``"*"`` would deny QUILL's
  own MCP tools too. A built-in the person turned on for this project
  (:mod:`quill.core.ai.vendor_tools`) is left out of that list, and
  ``can_use_tool`` asks the person before each use.
- ``permission_mode="default"``, so anything else that slips through asks
  ``can_use_tool``, which refuses it and records a defect.

The SDK is the optional ``quill[ai-claude]`` extra and is imported only when a
task starts; the module is passed in for tests. Blocking :meth:`run` on a
worker, with :meth:`cancel` safe from any thread.
"""

from __future__ import annotations

import asyncio
import queue
import threading
import uuid
from typing import Any

from quill.core.ai.events import AgentEvent, AgentEventKind
from quill.core.ai.harness import AgentSpec, AIContext, HarnessCapabilities, HarnessResult

__all__ = ["CLAUDE_BUILTINS", "ClaudeToolHarness", "ClaudeToolSession", "session_options"]

#: Claude Code's built-in tools, each denied by name unless the person turned it on.
CLAUDE_BUILTINS: tuple[str, ...] = (
    "Bash",
    "BashOutput",
    "KillShell",
    "Read",
    "Write",
    "Edit",
    "MultiEdit",
    "NotebookEdit",
    "Glob",
    "Grep",
    "WebFetch",
    "WebSearch",
    "Task",
    "TodoWrite",
    "SlashCommand",
    "ExitPlanMode",
)

#: Which built-ins one opted-in vendor tool id lets through (vendor_tools.py).
_VENDOR_TO_BUILTINS: dict[str, tuple[str, ...]] = {
    "Read": ("Read",),
    "Grep": ("Grep",),
    "Glob": ("Glob",),
    "Edit": ("Edit", "MultiEdit", "Write"),
    "Bash": ("Bash", "BashOutput", "KillShell"),
    "WebFetch": ("WebFetch",),
}
_BUILTIN_KINDS: dict[str, str] = {
    "Read": "read",
    "Grep": "read",
    "Glob": "read",
    "Edit": "write",
    "MultiEdit": "write",
    "Write": "write",
    "Bash": "shell",
    "BashOutput": "shell",
    "KillShell": "shell",
    "WebFetch": "url",
}
_SERVER = "quill"


def session_options(registry: Any, system_prompt: str) -> dict[str, Any]:
    """The ``ClaudeAgentOptions`` keywords, without the MCP server and callback."""
    vendor = set(getattr(registry, "vendor_tools", frozenset()))
    let_through = {name for v in vendor for name in _VENDOR_TO_BUILTINS.get(v, ())}
    options: dict[str, Any] = {
        "allowed_tools": [f"mcp__{_SERVER}__{name}" for name in registry.wire_names()],
        "disallowed_tools": [name for name in CLAUDE_BUILTINS if name not in let_through],
        "permission_mode": "default",
    }
    if system_prompt.strip():
        options["system_prompt"] = system_prompt.strip()
    if getattr(registry, "vendor_cwd", ""):
        options["cwd"] = registry.vendor_cwd
    return options


class ClaudeToolSession:
    """One task: a Claude SDK client, QUILL's tools, follow-ups and Stop."""

    def __init__(
        self,
        sdk: Any,
        agent: AgentSpec,
        ctx: AIContext,
        registry: Any,
        approver: Any,
        emit: Any,
        *,
        keep_open: bool = False,
        extra: dict[str, Any] | None = None,
        model: str = "",
    ) -> None:
        self._sdk = sdk
        self._extra = dict(extra or {})
        if model:
            self._extra["model"] = model
        self._agent = agent
        self._ctx = ctx
        self._registry = registry
        self._approver = approver
        self._emit = emit
        self._keep_open = keep_open
        self._id = uuid.uuid4().hex
        self._follow_ups: queue.Queue[str | None] = queue.Queue()
        self._cancelled = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._client: Any = None

    @property
    def session_id(self) -> str:
        return self._id

    def send(self, follow_up: str) -> None:
        if follow_up.strip():
            self._follow_ups.put(follow_up)

    def end(self) -> None:
        self._follow_ups.put(None)

    def cancel(self) -> None:
        self._cancelled.set()
        self._follow_ups.put(None)
        loop, client = self._loop, self._client
        if loop is not None and client is not None and hasattr(client, "interrupt"):
            loop.call_soon_threadsafe(lambda: asyncio.ensure_future(client.interrupt()))

    def run(self) -> HarnessResult:
        self._registry.gate.begin_task(self._approver)
        try:
            return asyncio.run(self._run())
        except Exception as error:  # noqa: BLE001 - the engine's failure, said plainly
            said = str(error) or "Claude could not finish the task."
            self._emit(AgentEvent(AgentEventKind.ERROR, said))
            return HarnessResult(status="error", error=said)
        finally:
            self._registry.gate.end_task()

    # -- inside --------------------------------------------------------------- #

    def _server(self) -> Any:
        sdk = self._sdk
        tools = []
        for family_tool in self._registry.tools():
            wire = family_tool.wire_name

            async def handler(args: dict[str, Any], _wire: str = wire) -> dict[str, Any]:
                result = await asyncio.to_thread(self._registry.call, _wire, dict(args or {}))
                return {
                    "content": [{"type": "text", "text": result.text}],
                    "is_error": not result.ok,
                }

            tools.append(sdk.tool(wire, family_tool.description, family_tool.parameters)(handler))
        return sdk.create_sdk_mcp_server(name=_SERVER, version="1.0.0", tools=tools)

    async def _can_use_tool(self, name: str, tool_input: dict[str, Any], _context: Any) -> Any:
        sdk = self._sdk
        if name.startswith(f"mcp__{_SERVER}__"):
            return sdk.PermissionResultAllow()  # its own handler asks, through the registry
        kind = _BUILTIN_KINDS.get(name, "")
        if kind:
            detail = str(tool_input.get("command") or tool_input.get("file_path") or "")
            allowed = await asyncio.to_thread(self._registry.authorize_vendor, kind, detail)
            if allowed:
                return sdk.PermissionResultAllow()
        else:
            self._registry.record_defect(f"Claude asked for {name}, which QUILL never offers.")
        return sdk.PermissionResultDeny(message="The person keeps this for QUILL's own tools.")

    async def _run(self) -> HarnessResult:
        sdk = self._sdk
        self._loop = asyncio.get_running_loop()
        options = sdk.ClaudeAgentOptions(
            mcp_servers={_SERVER: self._server()},
            can_use_tool=self._can_use_tool,
            **session_options(self._registry, self._agent.system_prompt),
            **self._extra,  # the person's own key, only in the child's environment
        )
        answer = ""
        async with sdk.ClaudeSDKClient(options=options) as client:
            self._client = client
            prompt: str | None = f"{self._ctx.prompt}\n\n{self._ctx.context_text}".strip()
            while prompt is not None:
                if self._cancelled.is_set():
                    break
                await client.query(prompt)
                async for message in client.receive_response():
                    if isinstance(message, sdk.AssistantMessage):
                        for block in getattr(message, "content", []):
                            if isinstance(block, sdk.TextBlock) and block.text:
                                answer = block.text
                                self._emit(AgentEvent(AgentEventKind.AGENT_TEXT_DELTA, block.text))
                prompt = await asyncio.to_thread(self._next)
        if self._cancelled.is_set():
            self._emit(AgentEvent(AgentEventKind.AGENT_CANCELLED, "Claude stopped."))
            return HarnessResult(status="cancelled")
        self._emit(AgentEvent(AgentEventKind.AGENT_COMPLETED, "Claude finished."))
        return HarnessResult(status="completed", final_text=answer)

    def _next(self) -> str | None:
        if not self._keep_open:
            try:
                return self._follow_ups.get_nowait()
            except queue.Empty:
                return None
        return self._follow_ups.get()


class ClaudeToolHarness:
    """The Claude engine for agent tasks, on My own key."""

    def __init__(self, api_key: str = "", model: str = "", sdk: Any = None) -> None:
        self._api_key = api_key
        self._model = model
        self._sdk = sdk

    @property
    def id(self) -> str:
        return "claude"

    @property
    def display_name(self) -> str:
        return "Claude Agent"

    def capabilities(self) -> HarnessCapabilities:
        return HarnessCapabilities(requires_api_key=True, mcp=True, app_tools=True)

    def _module(self) -> Any:
        if self._sdk is None:
            import claude_agent_sdk  # type: ignore[import-not-found]

            self._sdk = claude_agent_sdk
        return self._sdk

    def start_tool_session(
        self,
        agent: AgentSpec,
        ctx: AIContext,
        tools: Any,
        approver: Any,
        emit: Any,
        *,
        keep_open: bool = False,
        on_usage: Any = None,
    ) -> ClaudeToolSession:
        tools.set_emit(emit)
        return ClaudeToolSession(
            self._module(),
            agent,
            ctx,
            tools,
            approver,
            emit,
            keep_open=keep_open,
            extra={"env": {"ANTHROPIC_API_KEY": self._api_key}} if self._api_key else {},
            model=self._model,
        )
