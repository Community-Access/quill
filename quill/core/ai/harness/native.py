"""Native harness (PRD §8.1) — QUILL's own loop, always present.

The Native harness is the default engine and the reference implementation of the
:class:`~quill.core.ai.harness.Harness` protocol. It takes a ``responder`` (the
model call — today's ``assistant_ai`` / ``ProviderChatBackend`` path) and drives
the :class:`~quill.core.ai.tool_gateway.SafeEditorToolGateway` to apply the
result, emitting the normalized event lifecycle so the accessibility layer can
announce it.

This first version is a single generate-and-apply pass (mirroring today's
``run_agent`` generate+refine shortcut), routed through the gateway so the
permission, preview, undo, and audit guarantees already hold. Phase 3 upgrades it
to a real multi-step, broker-gated tool-calling loop without changing this
public surface.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from quill.core.ai.backend import AIBackend
from quill.core.ai.context_builder import ContextScope
from quill.core.ai.events import AgentEvent, AgentEventKind
from quill.core.ai.harness import (
    AgentSpec,
    AIContext,
    Harness,
    HarnessCapabilities,
    HarnessResult,
    HarnessSession,
)
from quill.core.ai.permissions import PermissionBroker
from quill.core.ai.tool_gateway import Emit, SafeEditorToolGateway

__all__ = ["Responder", "NativeHarness", "register", "responder_from_backend", "build_prompt"]

# The model call: given the agent and its built context, return proposed text.
# Wrapping assistant_ai / ProviderChatBackend is the UI's job; the harness stays
# transport-agnostic and unit-testable with a plain function.
Responder = Callable[[AgentSpec, AIContext], str]


def build_prompt(agent: AgentSpec, ctx: AIContext) -> str:
    """Compose the single prompt sent to a backend from the agent + context.

    Stable, harness-neutral shape (system prompt, then the user's ask, then the
    already-built/previewed context); the SDK packs use the same composition.
    """
    return f"{agent.system_prompt}\n\n{ctx.prompt}\n\n{ctx.context_text}".strip()


def responder_from_backend(backend: AIBackend) -> Responder:
    """Adapt any :class:`~quill.core.ai.backend.AIBackend` into a ``Responder``.

    Lets the Native harness run on the existing provider stack
    (``ProviderChatBackend`` / ``SimpleChatBackend``) with no new transport: the
    agent + context become one prompt and ``backend.respond`` returns the text.
    Depends only on the core ABC, so it stays wx-free and dormant until wired.
    """

    def respond(agent: AgentSpec, ctx: AIContext) -> str:
        return backend.respond(build_prompt(agent, ctx))

    return respond


class _NativeSession:
    """One generate-and-apply pass, cancellable before the edit lands."""

    def __init__(
        self,
        agent: AgentSpec,
        ctx: AIContext,
        gateway: SafeEditorToolGateway,
        emit: Emit,
        responder: Responder,
    ) -> None:
        self._id = uuid.uuid4().hex
        self._agent = agent
        self._ctx = ctx
        self._gateway = gateway
        self._emit = emit
        self._responder = responder
        self._cancelled = False

    @property
    def session_id(self) -> str:
        return self._id

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> HarnessResult:
        self._emit(AgentEvent(AgentEventKind.AGENT_STARTED, f"{self._agent.display_name} started."))
        if self._cancelled:
            return self._cancel_result()

        try:
            proposed = self._responder(self._agent, self._ctx)
        except Exception as exc:  # responder/model failure must not crash the app
            self._emit(AgentEvent(AgentEventKind.ERROR, "The agent could not complete."))
            return HarnessResult(status="error", error=str(exc))

        if self._cancelled:
            return self._cancel_result()

        self._emit(
            AgentEvent(
                AgentEventKind.AGENT_TEXT_DELTA,
                f"{self._agent.display_name} proposed a change.",
            )
        )

        # Apply through the gateway: selection/section scopes replace the
        # selection; everything else inserts at the cursor. The gateway enforces
        # permission, preview, undo, and audit — the harness never edits directly.
        if self._agent.default_scope in (
            ContextScope.SELECTION,
            ContextScope.CURRENT_SECTION,
        ):
            self._gateway.replace_selection(proposed, label=self._agent.display_name)
        else:
            self._gateway.insert_at_cursor(proposed, label=self._agent.display_name)

        self._emit(
            AgentEvent(AgentEventKind.AGENT_COMPLETED, f"{self._agent.display_name} finished.")
        )
        return HarnessResult(status="completed", final_text=proposed)

    def _cancel_result(self) -> HarnessResult:
        self._emit(AgentEvent(AgentEventKind.AGENT_CANCELLED, "Agent cancelled."))
        return HarnessResult(status="cancelled")


class NativeHarness:
    """The default, always-available harness."""

    def __init__(self, responder: Responder) -> None:
        self._responder = responder

    @property
    def id(self) -> str:
        return "native"

    @property
    def display_name(self) -> str:
        return "Native (QUILL)"

    def is_available(self) -> tuple[bool, str | None]:
        return True, None

    def capabilities(self) -> HarnessCapabilities:
        return HarnessCapabilities(
            chat=True,
            streaming=True,
            tool_calling=True,
            patch_generation=True,
        )

    def start_session(
        self,
        agent: AgentSpec,
        ctx: AIContext,
        gateway: SafeEditorToolGateway,
        broker: PermissionBroker,
        emit: Emit,
    ) -> HarnessSession:
        return _NativeSession(agent, ctx, gateway, emit, self._responder)


def register(registry: object, responder: Responder) -> Harness:
    """Construct and register the Native harness; return it.

    Kept a free function so the UI wiring stays one line and tests can register
    into a throwaway registry.
    """
    harness = NativeHarness(responder)
    registry.register(harness)  # type: ignore[attr-defined]
    return harness
