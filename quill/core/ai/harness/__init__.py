"""Harness layer (PRD §8.1, §8.2) — interchangeable agent engines above AIBackend.

A *harness* drives an agent session. The Native harness wraps QUILL's own loop;
optional SDK packs (Copilot, Claude, OpenAI Agents, Microsoft Agent Framework,
LangGraph, OpenHands) are lazily-imported extras. Every harness, native or pack,
drives the **same** :class:`~quill.core.ai.tool_gateway.SafeEditorToolGateway`
and :class:`~quill.core.ai.permissions.PermissionBroker`, and emits the **same**
normalized :class:`~quill.core.ai.events.AgentEvent`s. None edits the buffer
directly.

This package defines the protocol, the capability model, the lightweight
``AgentSpec`` / ``AIContext`` value types, and the :class:`HarnessRegistry`. The
Native harness lives in :mod:`quill.core.ai.harness.native`; SDK packs live under
``quill/ai_packs/`` and self-register only when their extra is installed.

Availability mirrors ``provider_backend.is_available``: an uninstalled pack
returns ``(False, "Install the X pack")`` and QUILL keeps working.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from quill.core.ai.context_builder import ContextScope
from quill.core.ai.permissions import Decision, PermissionBroker, PermissionCategory, RiskLevel
from quill.core.ai.tool_gateway import Emit, SafeEditorToolGateway

if TYPE_CHECKING:
    from quill.core.ai.approvals import Approver
    from quill.core.ai.family_tools import FamilyToolRegistry

__all__ = [
    "HarnessCapabilities",
    "AgentSpec",
    "AIContext",
    "HarnessResult",
    "HarnessSession",
    "Harness",
    "HarnessRegistry",
    "ToolSession",
    "ToolHarness",
    "TurnUsage",
    "supports_app_tools",
]


@dataclass(frozen=True, slots=True)
class HarnessCapabilities:
    """What a harness can do (PRD §8.2).

    QUILL must never assume a capability another harness has; the Hub hides or
    disables unsupported actions with a one-line reason. Defaults describe the
    minimal Native baseline (chat + streaming + tool calling + patches, local-
    capable, no key required by the harness itself — the provider may still need
    one).
    """

    chat: bool = True
    streaming: bool = True
    tool_calling: bool = True
    patch_generation: bool = True
    mcp: bool = False
    skills: bool = False
    subagents: bool = False
    local_only: bool = False
    requires_api_key: bool = False
    requires_oauth: bool = False
    images: bool = False
    audio: bool = False
    long_context: bool = False
    # Takes QUILL's family tools through ``start_tool_session`` (codex.md 5.1a):
    # a multi-turn session whose tool calls come back to the FamilyToolRegistry.
    app_tools: bool = False


@dataclass(frozen=True, slots=True)
class AgentSpec:
    """A declarative Agent Catalog entry a harness can run (PRD §13).

    Produced by the catalog loader (:mod:`quill.core.ai.agent_catalog`) from a
    validated JSON file, or constructed directly. ``default_harness = "auto"``
    lets the registry pick. ``permission_overrides`` are per-category defaults the
    UI feeds to a :class:`~quill.core.ai.permissions.PermissionBroker` for this
    agent (the broker's floor still wins). ``tools`` are the command ids the agent
    is expected to use (still constrained to ``SAFE_TOOL_IDS`` at call time).
    """

    id: str
    display_name: str
    system_prompt: str
    description: str = ""
    risk: RiskLevel = RiskLevel.LOW
    default_scope: ContextScope = ContextScope.SELECTION
    recommended_file_types: tuple[str, ...] = ()
    default_harness: str = "auto"
    tools: tuple[str, ...] = ()
    permission_overrides: tuple[tuple[PermissionCategory, Decision], ...] = ()
    # True for agents that depend on the multi-step tool loop (reading/editing via
    # tools across turns). Small/free models are unreliable at that loop, so the
    # UI can note "works best with a stronger model" while still offering the agent
    # (graceful degradation, never a hard block). Single-shot transform agents
    # leave this False. See quill.core.ai.free_models.supports_tool_use.
    needs_tool_use: bool = False

    def overrides_map(self) -> dict[PermissionCategory, Decision]:
        """Return the per-category permission overrides as a dict for the broker."""
        return dict(self.permission_overrides)


@dataclass(frozen=True, slots=True)
class AIContext:
    """The already-built, already-previewed context handed to a harness.

    Produced from a :class:`~quill.core.ai.context_builder.ContextPreview` after
    the user approves it, so a harness never assembles context itself.
    """

    prompt: str
    context_text: str = ""
    file_type: str = ""


@dataclass(frozen=True, slots=True)
class HarnessResult:
    """The terminal outcome of a session."""

    status: str  # "completed" | "cancelled" | "error"
    final_text: str = ""
    error: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "completed"


@runtime_checkable
class HarnessSession(Protocol):
    """A running (or runnable) agent session."""

    @property
    def session_id(self) -> str: ...
    def run(self) -> HarnessResult: ...
    def cancel(self) -> None: ...


@runtime_checkable
class Harness(Protocol):
    """An interchangeable agent engine (PRD §8.1)."""

    @property
    def id(self) -> str: ...
    @property
    def display_name(self) -> str: ...
    def is_available(self) -> tuple[bool, str | None]: ...
    def capabilities(self) -> HarnessCapabilities: ...
    def start_session(
        self,
        agent: AgentSpec,
        ctx: AIContext,
        gateway: SafeEditorToolGateway,
        broker: PermissionBroker,
        emit: Emit,
    ) -> HarnessSession: ...


@dataclass(frozen=True, slots=True)
class TurnUsage:
    """What one model call cost, as the engine reports it (feeds the usage line).

    Token counts only -- never converted to money (codex.md 8).
    """

    engine: str
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0


@runtime_checkable
class ToolSession(Protocol):
    """A multi-turn agent session over the family tools (codex.md 5.1a).

    Beside :class:`HarnessSession`, not instead of it: Native and the
    existing packs keep their one-shot sessions. Threading contract:

    - :meth:`run` blocks; call it on a worker thread (``QuillTaskManager``),
      never the UI thread. It runs the first prompt, then every follow-up
      given to :meth:`send`, and returns when the turn queue is empty --
      or, for a session started with ``keep_open=True``, when :meth:`end`
      or :meth:`cancel` is called. Every tool call and approval happens on
      worker threads; the approver marshals to the UI itself.
    - :meth:`send`, :meth:`cancel` and :meth:`end` are safe from any thread.
    - :meth:`cancel` (Stop) ends the turn within a second, unblocks any
      pending approval, and :meth:`run` returns ``status="cancelled"``.
    - "For this task" grants last exactly as long as one :meth:`run`.
    """

    @property
    def session_id(self) -> str: ...
    def run(self) -> HarnessResult: ...
    def cancel(self) -> None: ...
    def send(self, follow_up: str) -> None: ...
    def end(self) -> None: ...


@runtime_checkable
class ToolHarness(Protocol):
    """A harness that can run a :class:`ToolSession` (``app_tools`` is True)."""

    @property
    def id(self) -> str: ...
    def capabilities(self) -> HarnessCapabilities: ...
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
    ) -> ToolSession: ...


def supports_app_tools(harness: object) -> bool:
    """True when ``harness`` declares ``app_tools`` and has ``start_tool_session``."""
    caps = getattr(harness, "capabilities", None)
    if not callable(caps) or not callable(getattr(harness, "start_tool_session", None)):
        return False
    try:
        return bool(caps().app_tools)
    except Exception:  # noqa: BLE001 - a broken pack is simply not a tool harness
        return False


class HarnessRegistry:
    """In-process registry of harnesses, native plus any installed packs.

    Packs self-register on import; an uninstalled pack simply never registers (or
    registers and reports ``is_available() == (False, reason)``). ``available()``
    is what the AI Hub lists as runnable.
    """

    def __init__(self) -> None:
        self._harnesses: dict[str, Harness] = {}

    def register(self, harness: Harness) -> None:
        self._harnesses[harness.id] = harness

    def get(self, harness_id: str) -> Harness | None:
        return self._harnesses.get(harness_id)

    def all(self) -> list[Harness]:
        return list(self._harnesses.values())

    def available(self) -> list[Harness]:
        return [h for h in self._harnesses.values() if h.is_available()[0]]

    def resolve(self, preferred: str) -> Harness | None:
        """Pick a harness: the named one if available, else the first available.

        ``"auto"`` (or an unavailable/unknown id) falls back to the first
        available harness, which is always the Native one in a normal install.
        """
        if preferred != "auto":
            chosen = self.get(preferred)
            if chosen is not None and chosen.is_available()[0]:
                return chosen
        available = self.available()
        return available[0] if available else None
