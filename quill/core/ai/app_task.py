"""Agent tasks in the QuillVille apps (codex.md 6, Phase 4c) -- wx-free.

The editors' multi-step document task (:mod:`quill.core.ai.document_task`) has
one shape every app can share: the person says what they want, an agent engine
(My GitHub Copilot, or Codex on the ChatGPT plan) works through it with that
app's own tools, and the task ends with a plain-text summary of what was done,
built from the registry's record of calls rather than the model's claims
(decision 13). This module is that shape without the editor.

* :class:`AppTaskSpec` -- one app's task: its namespace (``radio``), the
  window's title, the instructions every engine gets, and the words that say
  what each changing tool did ("Scheduled a recording").
* :class:`AppTaskRunner` -- the runner the agent window drives, with the same
  calls as :class:`~quill.core.ai.document_task.DocumentTaskRunner`:
  ``start(instruction)``, ``finish(result)``, ``send``, ``end``, ``cancel`` and
  an ``emit`` attribute. ``tools`` builds the task's tools afresh for each
  task, so nothing a handler holds outlives it.
* :func:`summarize_app_outcome` -- the closing text summary.

**Every tool goes through the registry**: reads in the app's own scope run
without a question; anything that changes, records, schedules or sends a
picture asks the person (once, for this task, or no) through the task's
:class:`~quill.core.ai.approvals.Approver` (codex.md 5.3), and a write shows
its text first through the app's preview (``AppTaskHost.preview``).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

from quill.core.ai.activity_log import ActivityLog
from quill.core.ai.approvals import Approver
from quill.core.ai.context_builder import ContextScope
from quill.core.ai.document_task import DocumentTaskOutcome
from quill.core.ai.family_tools import FamilyTool, FamilyToolRegistry
from quill.core.ai.harness import (
    AgentSpec,
    AIContext,
    HarnessResult,
    ToolHarness,
    ToolSession,
    TurnUsage,
)
from quill.core.ai.permissions import PermissionBroker, RiskLevel
from quill.core.ai.tool_gateway import AgentIdentity, Emit

__all__ = [
    "AppTaskHost",
    "AppTaskRunner",
    "AppTaskSpec",
    "FAMILY_TASK_RULES",
    "summarize_app_outcome",
]

#: Every app task's instructions end with these (decision 13 and codex.md 5.3).
FAMILY_TASK_RULES = (
    "Use only the tools you are given. Read before you change anything. Every "
    "step that changes something asks the person first, and they may say no; "
    "if they do, carry on without it or stop. Never draw charts, graphs, "
    "diagrams or pictures, in text art or otherwise. Finish with a short "
    "plain-text summary of what was done and anything you could not do."
)


class AppTaskHost(Protocol):
    """What an app's tools may ask of the window, from a worker thread.

    ``preview`` shows a proposed change as text and answers whether the
    person applied it; ``on_ui`` runs a callable on the UI thread and returns
    its value (or *default* when the task was stopped); ``note`` adds a line
    to the task's transcript, silently.
    """

    def preview(self, title: str, text: str) -> bool: ...

    def on_ui(self, fn: Callable[[], Any], default: Any = None) -> Any: ...

    def note(self, text: str) -> None: ...


@dataclass(frozen=True, slots=True)
class AppTaskSpec:
    """One app's agent task."""

    #: The tool namespace and approval scope (``radio``).
    app: str
    #: The agent's id, for the activity log and the broker.
    agent_id: str
    #: The window's title ("Find and Record").
    title: str
    #: What the engine is told, before :data:`FAMILY_TASK_RULES`.
    instructions: str
    #: Tool name -> what it did, for the summary ("Scheduled a recording").
    done_words: Mapping[str, str] = field(default_factory=dict)
    #: What the summary calls a change ("change", "recording").
    noun: str = "change"

    def agent(self) -> AgentSpec:
        return AgentSpec(
            id=self.agent_id,
            display_name=self.title,
            system_prompt=f"{self.instructions.strip()}\n\n{FAMILY_TASK_RULES}",
            description=self.title,
            risk=RiskLevel.LOW,
            default_scope=ContextScope.PROMPT_ONLY,
            needs_tool_use=True,
        )


def _done(spec: AppTaskSpec, name: str) -> str:
    if name in spec.done_words:
        return spec.done_words[name]
    bare = name.split(".", 1)[-1].replace("_", " ")
    return f"Used {bare}"


def summarize_app_outcome(
    result: HarnessResult, registry: FamilyToolRegistry, spec: AppTaskSpec
) -> DocumentTaskOutcome:
    """The closing text summary (decision 13), from what actually happened."""
    done = tuple(_done(spec, r.name) for r in registry.calls if r.mutating and r.ok)
    declined = sum(1 for r in registry.calls if r.mutating and not r.ok)
    if result.status == "cancelled":
        lead = "Stopped."
    elif result.status == "error":
        lead = "The task could not finish."
    else:
        lead = "Done."
    if done:
        noun = spec.noun if len(done) == 1 else f"{spec.noun}s"
        body = f" {len(done)} {noun} made: {'; '.join(done)}."
    else:
        body = " Nothing was changed."
    if declined:
        body += (
            " 1 proposed step was not taken."
            if declined == 1
            else f" {declined} proposed steps were not taken."
        )
    return DocumentTaskOutcome(
        status=result.status,
        summary=(lead + body).strip(),
        answer=result.final_text.strip(),
        changes=done,
        declined=declined,
        error=result.error,
    )


@dataclass
class AppTaskRunner:
    """Runs one app's agent tasks through one tool harness."""

    harness: ToolHarness
    approver: Approver
    spec: AppTaskSpec
    tools: Callable[[], Sequence[FamilyTool]]
    broker: PermissionBroker = field(default_factory=PermissionBroker)
    activity: ActivityLog = field(default_factory=ActivityLog)
    emit: Emit = field(default=lambda _event: None)
    keep_open: bool = False
    on_usage: Callable[[TurnUsage], None] | None = None
    #: Facts sent with the first instruction (what is on screen, as text).
    context: Callable[[], str] | None = None
    _session: ToolSession | None = field(default=None, init=False, repr=False)
    _registry: FamilyToolRegistry | None = field(default=None, init=False, repr=False)

    @property
    def registry(self) -> FamilyToolRegistry | None:
        return self._registry

    def start(self, instruction: str, context_text: str = "") -> ToolSession:
        """Build the task's tools and session. Does not launch anything."""
        agent = self.spec.agent()
        identity = AgentIdentity(agent.id, agent.risk, harness=self.harness.id)
        registry = FamilyToolRegistry(
            self.broker, self.activity, identity, self.emit, app_scope=self.spec.app
        )
        registry.register_app(self.spec.app, self.tools())
        if not context_text and self.context is not None:
            try:
                context_text = self.context()
            except Exception:  # noqa: BLE001 - facts are a help, never a blocker
                context_text = ""
        session = self.harness.start_tool_session(
            agent,
            AIContext(prompt=instruction, context_text=context_text),
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
        registry = self._registry
        if registry is None:
            return DocumentTaskOutcome(status=result.status, summary="No task was started.")
        return summarize_app_outcome(result, registry, self.spec)

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
