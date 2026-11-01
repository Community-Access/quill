"""Multi-step document tasks: the first agent feature (codex.md 6.2, decision 3).

"Fix the heading levels, then build a table of contents, then list broken
links." The person gives one instruction; an agent engine (Copilot first,
Codex in Phase 4b) works through it with the editor's own tools -- read the
outline, read a section, apply a reviewed patch, audit accessibility, run a
safe command -- and the task ends with a plain-text summary of what changed
(decision 13). Every edit is still reviewed as text in the diff review and
undoable with one Control Z, because the tools are the
:class:`~quill.core.ai.tool_gateway.SafeEditorToolGateway`'s.

This module is wx-free. **The API the agent window calls** (QUILL and QUILL
Lite reach it through the same shared code; neither builds its own):

1. ``runner = DocumentTaskRunner(harness, host, approver, broker=...,
   activity=..., agent=spec, emit=..., keep_open=True)`` -- ``harness`` is any
   :class:`~quill.core.ai.harness.ToolHarness` (``supports_app_tools``);
   ``host`` is the editor's ``EditorHost`` (its ``preview_diff`` and
   ``announce`` marshal to the UI thread, e.g. with
   :class:`~quill.core.ai.approvals.UiThreadBridge`); ``approver`` is the
   approval dialog (:class:`~quill.core.ai.approvals.UiApprovalBridge`).
2. ``session = runner.start(instruction)`` on the UI thread (cheap; no
   launch), then ``outcome = runner.finish(session.run())`` on a
   ``QuillTaskManager`` worker. Or ``runner.run(instruction)`` on the worker
   for both at once.
3. While it runs: ``runner.send(text)`` for a follow-up, ``runner.end()``
   when the person is done (``keep_open`` sessions), ``runner.cancel()`` for
   Stop. Events arrive through ``emit`` (text deltas, tool calls, patches).
4. ``outcome.summary`` is the closing sentence(s) to show, speak and braille;
   ``outcome.changes`` lists each applied change in words.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace

from quill.core.ai.activity_log import ActivityLog
from quill.core.ai.approvals import Approver, ApprovingEditorHost
from quill.core.ai.context_builder import ContextScope
from quill.core.ai.family_tools import EDITOR_APP, FamilyToolRegistry, editor_tools
from quill.core.ai.harness import (
    AgentSpec,
    AIContext,
    HarnessResult,
    ToolHarness,
    ToolSession,
    TurnUsage,
)
from quill.core.ai.permissions import PermissionBroker, RiskLevel
from quill.core.ai.tool_gateway import AgentIdentity, EditorHost, Emit, SafeEditorToolGateway

__all__ = [
    "DOCUMENT_TASK_TOOLS",
    "DOCUMENT_TASK_INSTRUCTIONS",
    "DocumentTaskOutcome",
    "DocumentTaskRunner",
    "build_document_tools",
    "default_document_agent",
    "summarize_outcome",
]

#: The editor tools a document task may use. ``read_document`` is included
#: because ``apply_patch`` needs the full original text it replaces; the web
#: tools are not (they reach the network and need their own consent).
DOCUMENT_TASK_TOOLS: tuple[str, ...] = (
    "read_outline",
    "read_section",
    "read_document",
    "read_selection",
    "apply_patch",
    "audit_accessibility",
    "run_command",
)

#: Appended to the agent spec's own instructions for every document task.
DOCUMENT_TASK_INSTRUCTIONS = (
    "You are working in a document open in a QUILL editor, for a person who "
    "may be using a screen reader. Use only the tools you are given. Read "
    "before you change anything. To change the document, call doc_apply_patch "
    "with the full original text from doc_read_document and the full new "
    "text; the person reviews every change before it is applied, and may "
    "decline it. doc_run_command accepts only the listed command ids. Work "
    "through the steps in order. Never draw charts, graphs, diagrams or "
    "pictures, in text art or otherwise. Finish with a short plain-text "
    "summary of what you changed and anything you could not do."
)


def default_document_agent() -> AgentSpec:
    """The agent used when the window has not picked a catalog spec."""
    return AgentSpec(
        id="document-task",
        display_name="Document task",
        system_prompt="",
        description="Carries out a multi-step change to the open document.",
        risk=RiskLevel.LOW,
        default_scope=ContextScope.FULL_DOCUMENT,
        needs_tool_use=True,
    )


def build_document_tools(
    host: EditorHost,
    broker: PermissionBroker,
    activity: ActivityLog,
    identity: AgentIdentity,
    emit: Emit | None = None,
    *,
    names: Sequence[str] = DOCUMENT_TASK_TOOLS,
    web: object | None = None,
) -> tuple[FamilyToolRegistry, SafeEditorToolGateway]:
    """The registry and gateway for one document task, wired together.

    The gateway is built over an :class:`ApprovingEditorHost` on the
    registry's gate, so the broker's "ask" inside any editor tool reaches the
    task's approver, with the task's grants.
    """
    registry = FamilyToolRegistry(broker, activity, identity, emit, app_scope=EDITOR_APP)
    gateway = SafeEditorToolGateway(
        ApprovingEditorHost(host, registry.gate),  # type: ignore[arg-type]
        broker,
        activity,
        identity,
        emit,
        web=web,
    )
    registry.register_app(EDITOR_APP, editor_tools(gateway, names=names))
    return registry, gateway


@dataclass(frozen=True, slots=True)
class DocumentTaskOutcome:
    """How a task ended, in words."""

    status: str  # "completed" | "cancelled" | "error"
    summary: str
    answer: str = ""
    changes: tuple[str, ...] = ()
    declined: int = 0
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "completed"


def _change_sentence(name: str) -> str:
    bare = name.split(".", 1)[-1]
    return {
        "apply_patch": "Changed the document",
        "replace_selection": "Replaced the selection",
        "insert": "Inserted text",
        "run_command": "Ran a command",
    }.get(bare, f"Used {bare}")


def summarize_outcome(result: HarnessResult, registry: FamilyToolRegistry) -> DocumentTaskOutcome:
    """The closing text summary (decision 13), from what actually happened.

    Built from the registry's record of calls, not from the model's claims;
    the model's own summary follows as ``answer``.
    """
    changes = tuple(_change_sentence(r.name) for r in registry.calls if r.mutating and r.ok)
    declined = sum(1 for r in registry.calls if r.mutating and not r.ok)
    if result.status == "cancelled":
        lead = "Stopped."
    elif result.status == "error":
        lead = "The task could not finish."
    else:
        lead = "Done."
    if changes:
        count = len(changes)
        what = f"{count} change applied" if count == 1 else f"{count} changes applied"
        body = f" {what}: {'; '.join(changes)}. Each can be undone with Control Z."
    else:
        body = " No changes were made to the document."
    if declined:
        body += (
            " 1 proposed change was not applied."
            if declined == 1
            else f" {declined} proposed changes were not applied."
        )
    return DocumentTaskOutcome(
        status=result.status,
        summary=(lead + body).strip(),
        answer=result.final_text.strip(),
        changes=changes,
        declined=declined,
        error=result.error,
    )


@dataclass
class DocumentTaskRunner:
    """Runs document tasks on one editor through one tool harness."""

    harness: ToolHarness
    host: EditorHost
    approver: Approver
    broker: PermissionBroker
    activity: ActivityLog
    agent: AgentSpec = field(default_factory=default_document_agent)
    emit: Emit = field(default=lambda _event: None)
    keep_open: bool = False
    on_usage: Callable[[TurnUsage], None] | None = None
    file_type: str = ""
    web: object | None = None
    _session: ToolSession | None = field(default=None, init=False, repr=False)
    _registry: FamilyToolRegistry | None = field(default=None, init=False, repr=False)

    @property
    def registry(self) -> FamilyToolRegistry | None:
        """The current (or last) task's registry, for its record of calls."""
        return self._registry

    def start(self, instruction: str, context_text: str = "") -> ToolSession:
        """Build the task's tools and session. Does not launch anything."""
        identity = AgentIdentity(self.agent.id, self.agent.risk, harness=self.harness.id)
        registry, _gateway = build_document_tools(
            self.host, self.broker, self.activity, identity, self.emit, web=self.web
        )
        spec = replace(
            self.agent,
            system_prompt=f"{self.agent.system_prompt.strip()}\n\n{DOCUMENT_TASK_INSTRUCTIONS}".strip(),
        )
        ctx = AIContext(prompt=instruction, context_text=context_text, file_type=self.file_type)
        session = self.harness.start_tool_session(
            spec,
            ctx,
            registry,
            self.approver,
            self.emit,
            keep_open=self.keep_open,
            on_usage=self.on_usage,
        )
        self._registry = registry
        self._session = session
        return session

    def finish(self, result: HarnessResult) -> DocumentTaskOutcome:
        """Turn the session's result into the closing summary."""
        registry = self._registry
        if registry is None:
            return DocumentTaskOutcome(status=result.status, summary="No task was started.")
        return summarize_outcome(result, registry)

    def run(self, instruction: str, context_text: str = "") -> DocumentTaskOutcome:
        """Start and run one task, blocking. Call on a worker thread."""
        session = self.start(instruction, context_text)
        return self.finish(session.run())

    def send(self, follow_up: str) -> None:
        if self._session is not None:
            self._session.send(follow_up)

    def end(self) -> None:
        if self._session is not None:
            self._session.end()

    def cancel(self) -> None:
        if self._session is not None:
            self._session.cancel()
