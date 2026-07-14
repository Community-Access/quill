"""Shared base for optional SDK harness packs.

Every pack is the same shape: probe whether its SDK is installed, declare its
capabilities, and — when available — drive the Safe Editor Tool Gateway with the
SDK as transport, emitting the normalized event lifecycle. This base captures all
of that; a concrete pack supplies only its identity, the modules to probe, its
capabilities, and the SDK-specific ``invoke`` (built lazily).

Two design points keep this honest and testable:

- **Lazy probing.** :func:`modules_missing` uses ``importlib.util.find_spec`` and
  never imports the SDK, so importing a pack is free and safe in any environment.
- **Injectable transport.** :class:`SdkHarness` accepts an ``invoke`` override; a
  pack's real ``_make_invoke`` imports the SDK lazily, but tests (and advanced
  wiring) can inject a transport to exercise the gateway bridge without the SDK
  installed. Any error from ``invoke`` is contained as an error result, never a
  crash (PRD §21: version-checked adapters; Native always works).
"""

from __future__ import annotations

import importlib.util
import uuid
from collections.abc import Callable, Sequence

from quill.core.ai.context_builder import ContextScope
from quill.core.ai.events import AgentEvent, AgentEventKind
from quill.core.ai.harness import (
    AgentSpec,
    AIContext,
    HarnessCapabilities,
    HarnessResult,
    HarnessSession,
)
from quill.core.ai.permissions import PermissionBroker
from quill.core.ai.tool_gateway import Emit, SafeEditorToolGateway

__all__ = ["Invoke", "modules_missing", "SdkHarness"]

# The SDK transport: given the agent and built context, return proposed text.
Invoke = Callable[[AgentSpec, AIContext], str]


def modules_missing(names: Sequence[str]) -> list[str]:
    """Return the subset of ``names`` not importable, without importing them."""
    missing: list[str] = []
    for name in names:
        try:
            if importlib.util.find_spec(name) is None:
                missing.append(name)
        except (ImportError, ValueError):
            # find_spec raises if a parent package is itself missing/broken.
            missing.append(name)
    return missing


class _UnavailableSession:
    """Returned when a pack's SDK is not installed; explains how to enable it."""

    def __init__(self, reason: str, emit: Emit) -> None:
        self._id = uuid.uuid4().hex
        self._reason = reason
        self._emit = emit

    @property
    def session_id(self) -> str:
        return self._id

    def cancel(self) -> None:
        return None

    def run(self) -> HarnessResult:
        self._emit(AgentEvent(AgentEventKind.ERROR, self._reason))
        return HarnessResult(status="error", error=self._reason)


class _SdkSession:
    """Generate-and-apply pass for a pack, mirroring the Native session.

    The SDK runs via ``invoke``; the result is applied **only** through the
    gateway (replace for selection/section scopes, insert otherwise), so the
    permission, preview, undo, and audit guarantees hold for every pack exactly
    as they do for Native.
    """

    def __init__(
        self,
        display_name: str,
        agent: AgentSpec,
        ctx: AIContext,
        gateway: SafeEditorToolGateway,
        emit: Emit,
        invoke: Invoke,
    ) -> None:
        self._id = uuid.uuid4().hex
        self._name = display_name
        self._agent = agent
        self._ctx = ctx
        self._gateway = gateway
        self._emit = emit
        self._invoke = invoke
        self._cancelled = False

    @property
    def session_id(self) -> str:
        return self._id

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> HarnessResult:
        self._emit(AgentEvent(AgentEventKind.AGENT_STARTED, f"{self._name} started."))
        if self._cancelled:
            return self._cancelled_result()

        try:
            proposed = self._invoke(self._agent, self._ctx)
        except Exception as exc:  # SDK/transport failure stays contained
            self._emit(AgentEvent(AgentEventKind.ERROR, f"{self._name} could not complete."))
            return HarnessResult(status="error", error=str(exc))

        if self._cancelled:
            return self._cancelled_result()

        self._emit(AgentEvent(AgentEventKind.AGENT_TEXT_DELTA, f"{self._name} proposed a change."))
        if self._agent.default_scope in (ContextScope.SELECTION, ContextScope.CURRENT_SECTION):
            self._gateway.replace_selection(proposed, label=self._name)
        else:
            self._gateway.insert_at_cursor(proposed, label=self._name)

        self._emit(AgentEvent(AgentEventKind.AGENT_COMPLETED, f"{self._name} finished."))
        return HarnessResult(status="completed", final_text=proposed)

    def _cancelled_result(self) -> HarnessResult:
        self._emit(AgentEvent(AgentEventKind.AGENT_CANCELLED, f"{self._name} cancelled."))
        return HarnessResult(status="cancelled")


class SdkHarness:
    """Base class for optional SDK harness packs.

    Subclasses set the class attributes and override :meth:`capabilities` and
    :meth:`_make_invoke`. The default ``invoke`` override (constructor arg) lets
    tests and advanced wiring supply a transport without the SDK installed.
    """

    pack_id: str = ""
    pack_name: str = ""
    extra: str = ""
    sdk_modules: tuple[str, ...] = ()

    def __init__(self, invoke: Invoke | None = None) -> None:
        self._invoke_override = invoke

    @property
    def id(self) -> str:
        return self.pack_id

    @property
    def display_name(self) -> str:
        return self.pack_name

    def is_available(self) -> tuple[bool, str | None]:
        if self._invoke_override is not None:
            return True, None
        missing = modules_missing(self.sdk_modules)
        if missing:
            return False, (f'Install the {self.pack_name} pack: pip install "quill[{self.extra}]"')
        return True, None

    def capabilities(self) -> HarnessCapabilities:  # pragma: no cover - overridden
        raise NotImplementedError

    def responder(self) -> Invoke:
        """Return this pack's produce-text transport (override or SDK-backed).

        Same shape as the Native ``Responder`` (``(AgentSpec, AIContext) -> str``),
        so the agentic run path can swap engines without changing its threading:
        the call runs on a background thread and QUILL applies the text through its
        gateway exactly as for Native. Only call when :meth:`is_available` is True —
        for an uninstalled pack ``_make_invoke`` would fail to import the SDK.
        """
        if self._invoke_override is not None:
            return self._invoke_override
        return self._make_invoke()

    def start_session(
        self,
        agent: AgentSpec,
        ctx: AIContext,
        gateway: SafeEditorToolGateway,
        broker: PermissionBroker,
        emit: Emit,
    ) -> HarnessSession:
        invoke = self._invoke_override
        if invoke is None:
            available, reason = self.is_available()
            if not available:
                return _UnavailableSession(reason or "Harness unavailable.", emit)
            invoke = self._make_invoke()
        return _SdkSession(self.display_name, agent, ctx, gateway, emit, invoke)

    def _make_invoke(self) -> Invoke:  # pragma: no cover - requires the SDK installed
        """Build the SDK-backed transport (imports the SDK lazily).

        Overridden per pack. Only called when the SDK is actually installed, so it
        is never exercised in an environment without the extra; the gateway bridge
        itself is covered via the injectable ``invoke`` override.
        """
        raise NotImplementedError
