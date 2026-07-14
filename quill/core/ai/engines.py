"""Build the AI engine registry used for **selection** (Phase 6 UI).

The status-bar cell, the switch hotkey, and the AI Hub's Harnesses tab all need
the same list of engines: the always-present Native harness plus every optional
SDK pack (installed or not). This helper assembles that registry in one place so
those surfaces stay consistent.

It is a *selection* registry: it enumerates engines and reports readiness, but it
does not carry a live model ``Responder`` (running an agent builds its own gateway
in :mod:`quill.ui.agent_editor_host`). Native is therefore registered with a
placeholder responder that raises if anything tries to *run* through this
registry, making the selection-only contract explicit rather than silently wrong.

Building is cheap and import-safe: registering the packs only *probes* their SDKs
via ``importlib.util.find_spec`` (see :func:`quill.ai_packs._base.modules_missing`)
and never imports them.
"""

from __future__ import annotations

from quill.core.ai.harness import AgentSpec, AIContext, HarnessRegistry
from quill.core.ai.harness.native import NativeHarness

__all__ = ["build_engine_registry"]


def _selection_only(agent: AgentSpec, ctx: AIContext) -> str:
    raise RuntimeError(
        "This engine registry is for selection only; run agents via agent_editor_host."
    )


def build_engine_registry() -> HarnessRegistry:
    """Return a registry of Native plus every optional SDK pack, for selection."""
    registry = HarnessRegistry()
    registry.register(NativeHarness(_selection_only))
    # Imported here (not at module load) to keep the dependency direction clean:
    # ai_packs depends on the harness layer, not the other way around.
    from quill.ai_packs import register_all

    register_all(registry)
    return registry
