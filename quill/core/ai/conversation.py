"""Multi-turn conversational agent session (Companion Phase 1).

:func:`~quill.core.ai.tool_loop.run_tool_loop` drives ONE task to completion. A
*companion* conversation is many such tasks in sequence that share memory: the
user asks a fact question about the open document and gets an answer (no edit),
then asks for a revision (a reviewed edit), then a follow-up that refers back to
"it". This wx-free session is that memory + dispatch layer.

Each :meth:`ConversationSession.ask` renders the running conversation into the
task prompt, drives the existing tool loop against the *same*
:class:`~quill.core.ai.tool_gateway.SafeEditorToolGateway` (so permission checks,
the diff preview, undo checkpoints, and the audit log all still apply to every
edit), records the assistant's final answer, and reports whether the turn
*answered a question* or *changed the document*. A ``final`` answer with no
mutating tool call is a Q&A response; a mutating tool call is a reviewed edit.

Provider-neutral and fully testable with a scripted planner: the session adds no
new transport, it only sequences and remembers turns over the loop that already
exists.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill.core.ai.agent_tools import MUTATING_TOOL_NAMES
from quill.core.ai.harness import AgentSpec, AIContext
from quill.core.ai.tool_gateway import Emit, SafeEditorToolGateway
from quill.core.ai.tool_loop import (
    MAX_STEPS,
    ToolPlanner,
    ToolResult,
    ToolStep,
    run_tool_loop,
)

__all__ = [
    "MUTATING_TOOLS",
    "ConversationTurn",
    "TurnResult",
    "ConversationSession",
]

# The tools that change the document/app (shared source of truth). A turn "edited"
# only when one of these ran AND the gateway reported it applied (transcript output
# ``"True"``); a previewed edit the user declined returns ``"False"`` and is not an
# edit.
MUTATING_TOOLS: frozenset[str] = MUTATING_TOOL_NAMES


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    """One remembered turn. ``role`` is ``"user"`` or ``"assistant"``."""

    role: str
    text: str


@dataclass(frozen=True, slots=True)
class TurnResult:
    """The outcome of one :meth:`ConversationSession.ask`.

    ``answer`` is what to show/speak. ``edited`` is True when the turn changed the
    document (an applied mutating tool), so the UI can announce "answered" vs
    "changed the document". ``tools_used`` lists the tool names the planner
    requested this turn (reads and mutations), in order.
    """

    answer: str
    status: str  # "completed" | "error"
    edited: bool = False
    error: str = ""
    tools_used: tuple[str, ...] = field(default_factory=tuple)


class _RecordingPlanner:
    """Wrap a planner to capture its steps and the fullest transcript it saw.

    Non-invasive: it forwards every ``next_step`` to the inner planner and records
    the returned step plus the transcript passed in. The transcript handed to the
    call that returns the ``final`` step contains every executed tool's result, so
    it is the authoritative record of what actually ran and whether it applied.
    """

    def __init__(self, inner: ToolPlanner) -> None:
        self._inner = inner
        self.steps: list[ToolStep] = []
        self.last_transcript: tuple[ToolResult, ...] = ()

    def next_step(
        self, agent: AgentSpec, ctx: AIContext, transcript: tuple[ToolResult, ...]
    ) -> ToolStep:
        if len(transcript) >= len(self.last_transcript):
            self.last_transcript = transcript
        step = self._inner.next_step(agent, ctx, transcript)
        self.steps.append(step)
        return step


class ConversationSession:
    """A remembered, multi-turn conversation driving the native tool loop.

    Construct once per chat with the agent, the live gateway, and a planner (a
    real :class:`~quill.core.ai.tool_planner.PromptToolPlanner` in the app, a
    scripted planner in tests). Call :meth:`ask` per user message.
    """

    def __init__(
        self,
        agent: AgentSpec,
        gateway: SafeEditorToolGateway,
        planner: ToolPlanner,
        *,
        emit: Emit | None = None,
        max_steps: int = MAX_STEPS,
    ) -> None:
        self._agent = agent
        self._gateway = gateway
        self._planner = planner
        self._emit: Emit = emit or (lambda _event: None)
        self._max_steps = max_steps
        self._turns: list[ConversationTurn] = []

    @property
    def turns(self) -> tuple[ConversationTurn, ...]:
        """The conversation so far, oldest first."""
        return tuple(self._turns)

    def ask(self, user_text: str, *, context_text: str = "", file_type: str = "") -> TurnResult:
        """Run one user turn through the loop; return the answer and what it did.

        ``context_text`` is the already-built editor context for this turn (a
        selection, section, or whole document — assembled and previewed upstream by
        the ContextBuilder once that is wired). The conversation memory is folded
        into the task prompt so follow-ups can refer back to earlier turns.
        """
        user_text = (user_text or "").strip()
        if not user_text:
            return TurnResult(answer="", status="error", error="Empty message.")

        self._turns.append(ConversationTurn("user", user_text))
        ctx = AIContext(
            prompt=self._render_prompt(), context_text=context_text, file_type=file_type
        )
        recorder = _RecordingPlanner(self._planner)
        result = run_tool_loop(
            recorder, self._agent, ctx, self._gateway, self._emit, max_steps=self._max_steps
        )

        answer = result.final_text
        self._turns.append(ConversationTurn("assistant", answer))

        tools_used = tuple(s.tool for s in recorder.steps if s.kind == "tool")
        edited = any(
            r.tool in MUTATING_TOOLS and r.ok and r.output == "True"
            for r in recorder.last_transcript
        )
        return TurnResult(
            answer=answer,
            status=result.status,
            edited=edited,
            error=result.error,
            tools_used=tools_used,
        )

    # -- internals ---------------------------------------------------------

    def _render_prompt(self) -> str:
        """Render the conversation memory + current ask into the task prompt.

        The agent's system prompt and the document context are added by the loop's
        planner; this is just the dialog so the model can resolve references like
        "it" / "the previous answer" across turns.
        """
        prior = self._turns[:-1]
        current = self._turns[-1].text
        if not prior:
            return current
        lines = [f"{'User' if t.role == 'user' else 'Assistant'}: {t.text}" for t in prior]
        return "Conversation so far:\n" + "\n".join(lines) + f"\n\nUser: {current}"
