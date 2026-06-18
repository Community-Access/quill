"""Agentic task session for QUILL.

Runs a multi-step agent loop:
  plan -> generate -> (optionally iterate) -> return AgentResult

The loop is intentionally simple: one AI call per step, no branching tool calls.
Each step may optionally emit a progress callback so the UI can update a gauge.
All calls are blocking; run on a background thread with a stop event to cancel.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from quill.core.ai.custom_instructions import split_instruction
from quill.core.assistant_ai import generate_assistant_response

if TYPE_CHECKING:
    from quill.core.assistant_agents import AgentPlan
    from quill.core.assistant_ai import AssistantConnectionSettings


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AgentStep:
    """One completed step in an agent run."""

    label: str
    output: str


@dataclass
class AgentResult:
    """Outcome of a complete agent session run."""

    plan_id: str
    steps: list[AgentStep] = field(default_factory=list)
    final_output: str = ""
    cancelled: bool = False
    error: str = ""

    @property
    def succeeded(self) -> bool:
        return not self.cancelled and not self.error and bool(self.final_output)


# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------


class AgentSessionError(Exception):
    pass


class AgentSessionAuthError(AgentSessionError):
    pass


class AgentSessionCancelledError(AgentSessionError):
    pass


# ---------------------------------------------------------------------------
# AgentContext: holds state for one run
# ---------------------------------------------------------------------------


@dataclass
class AgentContext:
    """Mutable state for a single agent run.

    Attributes
    ----------
    plan:
        The resolved AgentPlan (profile + rendered prompt).
    connection:
        AssistantConnectionSettings for the AI provider.
    api_key:
        Key for the configured provider (may be empty for on-device).
    stop_event:
        Set externally to request cancellation; checked between steps.
    on_progress:
        Optional callable(step_label: str, step_index: int, total_steps: int)
        called before each step begins; intended for UI progress updates.
    """

    plan: AgentPlan
    connection: AssistantConnectionSettings
    api_key: str = ""
    stop_event: threading.Event = field(default_factory=threading.Event)
    on_progress: Callable[[str, int, int], None] | None = None

    def is_cancelled(self) -> bool:
        return self.stop_event.is_set()


# ---------------------------------------------------------------------------
# Step definitions
# ---------------------------------------------------------------------------

_REFINE_PROMPT = (
    "You previously produced the following output for the task below.\n"
    "Improve it: tighten the language, fix any inconsistencies, and ensure it "
    "fully addresses the user's goal. Return only the improved text.\n\n"
    "Original task:\n{task_prompt}\n\n"
    "Previous output:\n{previous_output}"
)


def _emit_progress(ctx: AgentContext, label: str, index: int, total: int) -> None:
    if ctx.on_progress is not None:
        try:
            ctx.on_progress(label, index, total)
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_agent(ctx: AgentContext, *, refine: bool = False) -> AgentResult:
    """Execute the agent plan and return an AgentResult.

    Parameters
    ----------
    ctx:
        Fully populated AgentContext.
    refine:
        If True, run a second "refine" step after the initial generation.
        The refinement asks the model to improve its own first draft.
    """
    result = AgentResult(plan_id=ctx.plan.profile.agent_id)
    total_steps = 2 if refine else 1

    # Step 1: initial generation
    _emit_progress(ctx, "Generating...", 0, total_steps)
    if ctx.is_cancelled():
        result.cancelled = True
        return result

    system_prompt, user_prompt = split_instruction(ctx.plan.profile.agent_id, ctx.plan.prompt)
    text, error = generate_assistant_response(
        ctx.connection,
        ctx.api_key,
        user_prompt,
        max_tokens=2048,
        timeout_seconds=90.0,
        system_prompt=system_prompt,
    )

    if ctx.is_cancelled():
        result.cancelled = True
        return result

    if error:
        if "401" in error or "auth" in error.lower() or "key" in error.lower():
            raise AgentSessionAuthError(error)
        raise AgentSessionError(error)

    step_output = (text or "").strip()
    result.steps.append(AgentStep(label="Initial generation", output=step_output))

    if not refine or not step_output:
        result.final_output = step_output
        return result

    # Step 2: optional refinement pass
    _emit_progress(ctx, "Refining...", 1, total_steps)
    if ctx.is_cancelled():
        result.cancelled = True
        result.final_output = step_output
        return result

    refine_prompt = _REFINE_PROMPT.format(
        task_prompt=ctx.plan.prompt,
        previous_output=step_output,
    )
    refined, refine_error = generate_assistant_response(
        ctx.connection,
        ctx.api_key,
        refine_prompt,
        max_tokens=2048,
        timeout_seconds=90.0,
    )

    if ctx.is_cancelled():
        result.cancelled = True
        result.final_output = step_output
        return result

    if refine_error:
        # Non-fatal: keep initial output rather than failing the whole run.
        result.final_output = step_output
        result.steps.append(
            AgentStep(label="Refinement (skipped)", output=f"Error: {refine_error}")
        )
    else:
        refined_text = (refined or "").strip() or step_output
        result.steps.append(AgentStep(label="Refinement", output=refined_text))
        result.final_output = refined_text

    return result
