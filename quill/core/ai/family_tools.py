"""The family tool registry (codex.md 5.1a, 5.2) -- one tool list, every engine.

A :class:`FamilyTool` is written once and every agent engine translates from
it: :func:`to_copilot_tools` builds ``copilot.tools.Tool`` objects whose
handler calls back into the registry, and :func:`to_codex_dynamic_tools`
builds the Codex ``dynamicTools`` JSON (Phase 4b). Neither adapter defines a
tool of its own.

**Editor tools behave exactly as under Native.** :func:`editor_tools` wraps
:data:`quill.core.ai.agent_tools.TOOL_DESCRIPTORS` and calls
:func:`~quill.core.ai.agent_tools.execute_tool` against the session's
:class:`~quill.core.ai.tool_gateway.SafeEditorToolGateway`, so the broker,
the ``ActivityLog`` entry and the diff review all happen where they always
have. The gateway's "ask" reaches the :class:`~quill.core.ai.approvals.Approver`
because the gateway is built over an
:class:`~quill.core.ai.approvals.ApprovingEditorHost` (see
:func:`quill.core.ai.document_task.build_document_tools`).

**Other apps' tools** (Phase 4c: ``studio.*``, ``radio.*`` ...) register with
:meth:`FamilyToolRegistry.register_app`. For those the registry itself asks
the broker, writes the ``ActivityLog`` entry and emits the events; a handler
only does its one job and returns text or a :class:`ToolImage`.

**Names.** A tool's ``name`` is namespaced with a dot (``doc.read_outline``).
Copilot accepts only ``^[a-zA-Z0-9_-]+$``, so engines see :attr:`FamilyTool.wire_name`
(``doc_read_outline``); the registry maps both back. Namespacing also keeps a
QUILL tool from ever sharing a name with a vendor built-in (``apply_patch``).
"""

from __future__ import annotations

import asyncio
import base64
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

from quill.core.ai.activity_log import ActivityEntry, ActivityLog
from quill.core.ai.agent import SAFE_TOOL_IDS
from quill.core.ai.agent_tools import MUTATING_TOOL_NAMES, TOOL_DESCRIPTORS, execute_tool
from quill.core.ai.approvals import ApprovalGate
from quill.core.ai.events import AgentEvent, AgentEventKind
from quill.core.ai.permissions import (
    Decision,
    PermissionBroker,
    PermissionCategory,
    PermissionRequest,
    PermissionResult,
    RiskLevel,
)
from quill.core.ai.tool_gateway import AgentIdentity, Emit, SafeEditorToolGateway, ToolError
from quill.core.error_codes import CodedError

__all__ = [
    "ToolImage",
    "ToolOutput",
    "ToolCallResult",
    "ToolCallRecord",
    "FamilyTool",
    "FamilyToolError",
    "FamilyToolRegistry",
    "EDITOR_APP",
    "EDITOR_TOOL_CATEGORIES",
    "editor_tools",
    "to_copilot_tools",
    "to_codex_dynamic_tools",
    "codex_tool_response",
]

#: The editors' namespace (QUILL and QUILL Lite share it).
EDITOR_APP = "doc"

_WIRE_NAME = re.compile(r"^[a-zA-Z0-9_-]+$")


class FamilyToolError(CodedError):
    """A tool could not be registered (bad or duplicate name)."""

    code = "QUILL-AI-FAMILYTOOL-INVALID"


@dataclass(frozen=True, slots=True)
class ToolImage:
    """A picture a tool hands the model (G6: Copilot and Codex both take one)."""

    data: bytes
    mime_type: str = "image/png"
    description: str = ""

    def base64(self) -> str:
        return base64.b64encode(self.data).decode("ascii")


ToolOutput = str | ToolImage
ToolHandler = Callable[[dict[str, Any]], ToolOutput]


@dataclass(frozen=True, slots=True)
class ToolCallResult:
    """What a tool call gave back: text for the model, maybe a picture, and success."""

    text: str
    ok: bool = True
    image: ToolImage | None = None


@dataclass(frozen=True, slots=True)
class ToolCallRecord:
    """One call, for the task's closing summary (decision 13)."""

    name: str
    ok: bool
    mutating: bool
    text: str


@dataclass(frozen=True, slots=True)
class FamilyTool:
    """One tool any engine may call.

    ``parameters`` is a JSON schema (``{"type": "object", ...}``). ``app`` is
    the scope: reads inside the running app's own scope are allowed without
    a question (5.3). ``via_gateway`` marks an editor tool whose permission,
    log and diff review happen inside the gateway rather than here.
    """

    name: str
    description: str
    handler: ToolHandler
    parameters: dict[str, Any] = field(default_factory=lambda: _schema({}, ()))
    category: PermissionCategory = PermissionCategory.READ_DOCUMENT
    risk: RiskLevel = RiskLevel.LOW
    app: str = EDITOR_APP
    mutating: bool = False
    via_gateway: bool = False
    summarize: Callable[[dict[str, Any]], str] | None = None

    @property
    def wire_name(self) -> str:
        return self.name.replace(".", "_")

    def summary_for(self, args: dict[str, Any]) -> str:
        """One plain sentence on what this call will do, for the approval."""
        if self.summarize is not None:
            try:
                return self.summarize(args)
            except Exception:  # noqa: BLE001 - a bad summary never blocks the ask
                pass
        return self.description


def _schema(props: dict[str, Any], required: Sequence[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": props,
        "required": list(required),
        "additionalProperties": False,
    }


class FamilyToolRegistry:
    """The tools one agent task may call, and the one place they are called.

    Built per task: it carries the agent's identity for the broker and the
    log, and owns the task's :class:`ApprovalGate`. An engine calls
    :meth:`call` (by namespaced or wire name); Copilot's permission callback
    calls :meth:`authorize` first.
    """

    def __init__(
        self,
        broker: PermissionBroker,
        activity: ActivityLog,
        identity: AgentIdentity,
        emit: Emit | None = None,
        *,
        app_scope: str = EDITOR_APP,
    ) -> None:
        self._broker = broker
        self._activity = activity
        self._who = identity
        self._emit: Emit = emit or (lambda _event: None)
        self.gate = ApprovalGate(app_scope=app_scope)
        self._tools: dict[str, FamilyTool] = {}
        self._wire: dict[str, str] = {}
        self.calls: list[ToolCallRecord] = []

    @property
    def identity(self) -> AgentIdentity:
        return self._who

    def set_emit(self, emit: Emit) -> None:
        """Point events at a session's ``emit`` (the engine adapter does this)."""
        self._emit = emit

    # -- registering --------------------------------------------------------

    def register(self, tool: FamilyTool) -> None:
        if not _WIRE_NAME.match(tool.wire_name):
            raise FamilyToolError(f"Tool name {tool.name!r} is not a valid engine name.")
        if tool.name in self._tools or tool.wire_name in self._wire:
            raise FamilyToolError(f"Tool {tool.name!r} is already registered.")
        self._tools[tool.name] = tool
        self._wire[tool.wire_name] = tool.name

    def register_app(self, app: str, tools: Iterable[FamilyTool]) -> None:
        """Register one app's tools; each must sit in ``app.``'s namespace."""
        for tool in tools:
            if tool.app != app or not tool.name.startswith(f"{app}."):
                raise FamilyToolError(f"Tool {tool.name!r} is not in the {app!r} namespace.")
            self.register(tool)

    # -- looking up ---------------------------------------------------------

    def tools(self, app: str | None = None) -> list[FamilyTool]:
        return [t for t in self._tools.values() if app is None or t.app == app]

    def names(self) -> list[str]:
        return list(self._tools)

    def wire_names(self) -> list[str]:
        return [t.wire_name for t in self._tools.values()]

    def get(self, name: str) -> FamilyTool | None:
        """By namespaced name or wire name."""
        if name in self._tools:
            return self._tools[name]
        full = self._wire.get(name)
        return self._tools.get(full) if full else None

    def record_defect(self, summary: str) -> None:
        """Log an engine request that should never arrive (5.3): a defect."""
        self._activity.append(
            ActivityEntry.now(
                kind="engine_defect",
                agent_id=self._who.agent_id,
                harness=self._who.harness,
                summary=summary,
                detail={"category": "defect"},
            )
        )
        self._emit(AgentEvent(AgentEventKind.WARNING, summary))

    def mutated(self) -> bool:
        """True when any successful call this task changed something."""
        return any(record.ok and record.mutating for record in self.calls)

    # -- deciding and calling -----------------------------------------------

    def authorize(self, name: str, args: dict[str, Any], call_id: str = "") -> tuple[bool, str]:
        """Decide a call before an engine makes it: ``(allowed, reason)``.

        The broker decides first; a deny is final. Its "ask" goes to the
        approver (once, for this task, or no) and a yes leaves one pass for
        this call so the handler does not ask again. A preview-required
        edit is allowed here because its diff review, inside the handler, is
        the question.
        """
        tool = self.get(name)
        if tool is None:
            return False, f"{name!r} is not a QUILL tool."
        verdict = self._resolve(tool, args)
        if verdict.blocked:
            self._log("tool_call_denied", tool, f"Denied {tool.name}: {verdict.reason}")
            return False, verdict.reason
        if verdict.decision is Decision.ASK and not self.gate.authorize_ahead(
            tool, tool.summary_for(args), call_id
        ):
            self._log("tool_call_denied", tool, f"Declined {tool.name}.")
            return False, "The person did not allow this."
        return True, verdict.reason

    def call(
        self, name: str, args: dict[str, Any] | None = None, call_id: str = ""
    ) -> ToolCallResult:
        """Run one tool. Never raises: a failure is a result the model can read."""
        args = dict(args or {})
        tool = self.get(name)
        if tool is None:
            return ToolCallResult(text=f"There is no QUILL tool named {name!r}.", ok=False)
        self._emit(AgentEvent(AgentEventKind.TOOL_CALL_REQUESTED, f"{tool.name} requested."))
        self.gate.set_current(tool, call_id)
        try:
            result = self._call(tool, args)
        except ToolError as exc:
            result = ToolCallResult(text=_plain(exc), ok=False)
        except Exception:  # noqa: BLE001 - a tool failure is reported, never raised
            self._log("tool_call_denied", tool, f"{tool.name} failed.")
            result = ToolCallResult(text=f"The tool {tool.name} could not run.", ok=False)
        finally:
            self.gate.set_current(None)
        self.calls.append(ToolCallRecord(tool.name, result.ok, tool.mutating, result.text))
        return result

    def _call(self, tool: FamilyTool, args: dict[str, Any]) -> ToolCallResult:
        if tool.via_gateway:
            # The gateway does the broker, the log, the events and the review.
            return _gateway_result(tool, tool.handler(args))
        verdict = self._resolve(tool, args)
        if verdict.blocked:
            self._log("tool_call_denied", tool, f"Denied {tool.name}: {verdict.reason}")
            self._emit(AgentEvent(AgentEventKind.TOOL_CALL_DENIED, f"Denied: {tool.name}."))
            return ToolCallResult(text=f"Not permitted: {verdict.reason}", ok=False)
        if verdict.decision is not Decision.ALLOW:
            self._emit(AgentEvent(AgentEventKind.PERMISSION_REQUIRED, tool.summary_for(args)))
            if not self.gate.check(tool, tool.summary_for(args)):
                self._log("tool_call_denied", tool, f"Declined {tool.name}.")
                self._emit(AgentEvent(AgentEventKind.TOOL_CALL_DENIED, f"Declined: {tool.name}."))
                return ToolCallResult(text="The person did not allow this.", ok=False)
        output = tool.handler(args)
        self._log("tool_call_completed", tool, f"Ran {tool.name}.")
        self._emit(AgentEvent(AgentEventKind.TOOL_CALL_COMPLETED, f"{tool.name} done."))
        if isinstance(output, ToolImage):
            return ToolCallResult(text=output.description or "A picture.", image=output)
        return ToolCallResult(text=output)

    def _resolve(self, tool: FamilyTool, args: dict[str, Any]) -> PermissionResult:
        command_id = None
        if tool.category is PermissionCategory.RUN_COMMAND:
            command_id = str(args.get("command_id", ""))
        return self._broker.resolve(
            PermissionRequest(
                category=tool.category,
                agent_id=self._who.agent_id,
                agent_risk=self._who.risk,
                command_id=command_id,
            )
        )

    def _log(self, kind: str, tool: FamilyTool, summary: str) -> None:
        self._activity.append(
            ActivityEntry.now(
                kind=kind,
                agent_id=self._who.agent_id,
                harness=self._who.harness,
                summary=summary,
                detail={"tool": tool.name, "category": tool.category.value},
            )
        )


def _plain(exc: Exception) -> str:
    """The message without the ``[QUILL-...]`` code prefix, for the model."""
    text = str(exc)
    return re.sub(r"^\[QUILL-[A-Z0-9-]+\]\s*", "", text)


def _gateway_result(tool: FamilyTool, output: ToolOutput) -> ToolCallResult:
    if isinstance(output, ToolImage):
        return ToolCallResult(text=output.description or "A picture.", image=output)
    if tool.mutating and output in ("True", "False"):
        if output == "True":
            return ToolCallResult(text="Done. The change was applied and can be undone.")
        return ToolCallResult(
            text="Not applied: the person declined or it was not permitted.", ok=False
        )
    return ToolCallResult(text=output)


# -- the editor tools ------------------------------------------------------

#: The permission category each editor tool is gated by inside the gateway.
EDITOR_TOOL_CATEGORIES: dict[str, PermissionCategory] = {
    "read_selection": PermissionCategory.READ_SELECTION,
    "read_document": PermissionCategory.READ_DOCUMENT,
    "read_outline": PermissionCategory.READ_SELECTION,
    "replace_selection": PermissionCategory.MODIFY_SELECTION,
    "insert": PermissionCategory.MODIFY_SELECTION,
    "apply_patch": PermissionCategory.MODIFY_DOCUMENT,
    "run_command": PermissionCategory.RUN_COMMAND,
    "read_section": PermissionCategory.READ_DOCUMENT,
    "read_app_state": PermissionCategory.READ_SELECTION,
    "audit_accessibility": PermissionCategory.READ_DOCUMENT,
    "web_search": PermissionCategory.WEB,
    "web_fetch": PermissionCategory.WEB,
}

_EDITOR_RISK: dict[str, RiskLevel] = {
    "replace_selection": RiskLevel.MEDIUM,
    "insert": RiskLevel.MEDIUM,
    "apply_patch": RiskLevel.HIGH,
    "run_command": RiskLevel.MEDIUM,
    "web_search": RiskLevel.MEDIUM,
    "web_fetch": RiskLevel.MEDIUM,
}

_OPTIONAL_ARGS = frozenset({"scope", "label"})

#: Off unless asked for: they reach the network and need their own consent.
_DEFAULT_EXCLUDED = frozenset({"web_search", "web_fetch"})

_SUMMARIES: dict[str, Callable[[dict[str, Any]], str]] = {
    "replace_selection": lambda a: "Replace the selected text with the agent's version.",
    "insert": lambda a: "Insert the agent's text at the cursor.",
    "apply_patch": lambda a: "Replace the document with the reviewed text.",
    "run_command": lambda a: f"Run the QUILL command {a.get('command_id', '')}.",
    "web_search": lambda a: f"Search the web for {a.get('query', '')}.",
    "web_fetch": lambda a: f"Fetch the web page {a.get('url', '')}.",
}


def _editor_parameters(name: str, params: dict[str, str]) -> dict[str, Any]:
    props: dict[str, Any] = {
        arg: {"type": "string", "description": text} for arg, text in params.items()
    }
    if name == "run_command":
        props["command_id"]["enum"] = list(SAFE_TOOL_IDS)
    required = [arg for arg in params if arg not in _OPTIONAL_ARGS]
    return _schema(props, required)


def editor_tools(
    gateway: SafeEditorToolGateway,
    *,
    names: Iterable[str] | None = None,
    app: str = EDITOR_APP,
) -> list[FamilyTool]:
    """The editor tools as family tools over ``gateway``.

    ``names`` picks a subset by bare descriptor name (``read_outline``); by
    default every tool except the two web tools, which reach the network and
    need their own consent.
    """
    wanted = set(names) if names is not None else None
    tools: list[FamilyTool] = []
    for descriptor in TOOL_DESCRIPTORS:
        bare = descriptor.name
        if wanted is not None and bare not in wanted:
            continue
        if wanted is None and bare in _DEFAULT_EXCLUDED:
            continue

        def _handler(args: dict[str, Any], _name: str = bare) -> ToolOutput:
            return execute_tool(gateway, _name, {k: str(v) for k, v in args.items()})

        tools.append(
            FamilyTool(
                name=f"{app}.{bare}",
                description=descriptor.description,
                handler=_handler,
                parameters=_editor_parameters(bare, descriptor.parameters),
                category=EDITOR_TOOL_CATEGORIES[bare],
                risk=_EDITOR_RISK.get(bare, RiskLevel.LOW),
                app=app,
                mutating=bare in MUTATING_TOOL_NAMES,
                via_gateway=True,
                summarize=_SUMMARIES.get(bare),
            )
        )
    return tools


# -- serializers -----------------------------------------------------------


def to_copilot_tools(
    registry: FamilyToolRegistry,
    *,
    tool_cls: Any,
    result_cls: Any,
    binary_cls: Any,
) -> list[Any]:
    """``copilot.tools.Tool`` objects whose handlers call the registry.

    The SDK classes are passed in so core never imports the SDK. Handlers
    are coroutines that run the (possibly blocking) registry call in a
    worker thread, so a pending approval never stalls the session's event
    loop and Stop can still abort the turn. ``skip_permission`` stays
    False: every call is also asked about through the permission callback.
    """
    tools: list[Any] = []
    for tool in registry.tools():
        wire = tool.wire_name

        async def _handler(invocation: Any, _wire: str = wire) -> Any:
            args = getattr(invocation, "arguments", None)
            call_id = str(getattr(invocation, "tool_call_id", "") or "")
            result = await asyncio.to_thread(
                registry.call, _wire, args if isinstance(args, dict) else {}, call_id
            )
            return copilot_result(result, result_cls=result_cls, binary_cls=binary_cls)

        tools.append(
            tool_cls(
                name=wire,
                description=tool.description,
                handler=_handler,
                parameters=tool.parameters,
                skip_permission=False,
            )
        )
    return tools


def copilot_result(result: ToolCallResult, *, result_cls: Any, binary_cls: Any) -> Any:
    """A registry result as a Copilot ``ToolResult``."""
    binaries = None
    if result.image is not None:
        binaries = [
            binary_cls(
                data=result.image.base64(),
                mime_type=result.image.mime_type,
                type="image",
                description=result.image.description,
            )
        ]
    return result_cls(
        text_result_for_llm=result.text,
        result_type="success" if result.ok else "failure",
        binary_results_for_llm=binaries,
    )


def to_codex_dynamic_tools(registry: FamilyToolRegistry) -> list[dict[str, Any]]:
    """The Codex ``thread/start`` ``dynamicTools`` list (Phase 4b).

    Shape per ``codex-rs/protocol/src/dynamic_tools.rs``: ``name``,
    ``description``, ``inputSchema``. Phase 4b checks it against the
    generated schema of the pinned app-server.
    """
    return [
        {"name": t.wire_name, "description": t.description, "inputSchema": t.parameters}
        for t in registry.tools()
    ]


def codex_tool_response(result: ToolCallResult) -> dict[str, Any]:
    """The answer to an ``item/tool/call``: ``{contentItems, success}``."""
    items: list[dict[str, Any]] = [{"type": "inputText", "text": result.text}]
    if result.image is not None:
        items.append({
            "type": "inputImage",
            "imageUrl": f"data:{result.image.mime_type};base64,{result.image.base64()}",
        })
    return {"contentItems": items, "success": result.ok}
