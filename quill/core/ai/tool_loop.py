"""Native multi-step tool-calling loop (PRD §8.1, §10, §14).

The base Native harness does a single generate-and-apply pass. This module adds
the real agent loop: the model takes multiple steps, each either a **tool call**
(read selection, read document, replace selection, apply a patch, run a command)
or a **final** answer. Every tool call goes through the
:class:`~quill.core.ai.tool_gateway.SafeEditorToolGateway`, so the broker's
permission checks, the diff preview, undo checkpoints, and the audit log all apply
to every step; every step emits normalized :class:`AgentEvent`s.

The loop is provider-neutral and fully testable because the model is abstracted
behind :class:`ToolPlanner`: ``next_step`` returns the next :class:`ToolStep`
given the agent, context, and the transcript so far. A real planner wraps a
function-calling model; tests use a scripted planner. The loop never references
wx.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from quill.core.ai.agent_tools import MUTATING_TOOL_NAMES
from quill.core.ai.events import AgentEvent, AgentEventKind
from quill.core.ai.harness import AgentSpec, AIContext, HarnessResult
from quill.core.ai.tool_gateway import Emit, PermissionDeniedError, SafeEditorToolGateway

__all__ = [
    "ToolStep",
    "ToolResult",
    "ToolPlanner",
    "run_tool_loop",
    "MAX_STEPS",
]

MAX_STEPS = 8


@dataclass(frozen=True, slots=True)
class ToolStep:
    """One planner decision: a tool call, or the final answer.

    ``kind`` is ``"tool"`` or ``"final"``. For a tool step, ``tool`` is the tool
    name and ``args`` its string arguments (e.g. ``{"text": ...}``,
    ``{"proposed": ..., "original": ...}``, ``{"command_id": ...}``). For a final
    step, ``final_text`` is the answer.
    """

    kind: str
    tool: str = ""
    args: dict[str, str] = field(default_factory=dict)
    final_text: str = ""


@dataclass(frozen=True, slots=True)
class ToolResult:
    """The recorded outcome of a tool step, fed back to the planner."""

    tool: str
    ok: bool
    output: str


class ToolPlanner(Protocol):
    """Decides the next step given the running transcript."""

    def next_step(
        self, agent: AgentSpec, ctx: AIContext, transcript: tuple[ToolResult, ...]
    ) -> ToolStep: ...


def _dispatch(gateway: SafeEditorToolGateway, step: ToolStep) -> str:
    """Run one tool step against the gateway via the shared tool surface."""
    from quill.core.ai.agent_tools import execute_tool

    return execute_tool(gateway, step.tool, step.args)


def _completion_text(transcript: list[ToolResult], applied_edit: bool) -> str:
    """A human answer when the model ran out of steps without a ``final``.

    After an applied edit, confirm the change (so the chat never surfaces a raw
    ``"True"``). Otherwise fall back to the most recent readable tool output.
    """
    if applied_edit:
        return "Done. I applied the change to your document."
    for result in reversed(transcript):
        if result.ok and result.tool not in MUTATING_TOOL_NAMES and result.output:
            return result.output
    return ""


def run_tool_loop(
    planner: ToolPlanner,
    agent: AgentSpec,
    ctx: AIContext,
    gateway: SafeEditorToolGateway,
    emit: Emit,
    *,
    max_steps: int = MAX_STEPS,
) -> HarnessResult:
    """Drive the planner against the gateway until a final answer or the cap.

    A denied permission is *not* fatal: it is recorded in the transcript so the
    planner can choose another path. An unknown tool or a gateway exception ends
    the run with an error result. Reaching ``max_steps`` ends the run cleanly with
    whatever final text is available.
    """
    emit(AgentEvent(AgentEventKind.AGENT_STARTED, f"{agent.display_name} started."))
    transcript: list[ToolResult] = []
    applied_edit = False

    for _ in range(max_steps):
        step = planner.next_step(agent, ctx, tuple(transcript))

        if step.kind == "final":
            emit(AgentEvent(AgentEventKind.AGENT_COMPLETED, f"{agent.display_name} finished."))
            return HarnessResult(status="completed", final_text=step.final_text)

        # One edit per turn: once a change has landed, a further edit request means
        # the model is looping instead of finishing (it never emitted a final). Stop
        # cleanly with what we have rather than re-applying / duplicating the edit.
        if applied_edit and step.tool in MUTATING_TOOL_NAMES:
            emit(AgentEvent(AgentEventKind.AGENT_COMPLETED, f"{agent.display_name} finished."))
            return HarnessResult(
                status="completed", final_text=_completion_text(transcript, applied_edit)
            )

        emit(AgentEvent(AgentEventKind.TOOL_CALL_REQUESTED, f"{agent.display_name}: {step.tool}"))
        try:
            output = _dispatch(gateway, step)
        except PermissionDeniedError as exc:
            # Recoverable: tell the planner and let it adapt.
            transcript.append(ToolResult(step.tool, ok=False, output=str(exc)))
            emit(AgentEvent(AgentEventKind.TOOL_CALL_DENIED, f"{step.tool} denied."))
            continue
        except Exception as exc:  # unknown tool / gateway failure: end the run
            emit(AgentEvent(AgentEventKind.ERROR, f"{step.tool} failed."))
            return HarnessResult(status="error", error=str(exc))

        transcript.append(ToolResult(step.tool, ok=True, output=output))
        emit(AgentEvent(AgentEventKind.TOOL_CALL_COMPLETED, f"{step.tool} done."))
        if step.tool in MUTATING_TOOL_NAMES and output == "True":
            applied_edit = True

    emit(AgentEvent(AgentEventKind.WARNING, "Agent reached the step limit."))
    return HarnessResult(status="completed", final_text=_completion_text(transcript, applied_edit))
