"""Selection registry builder (Phase 6 UI plumbing)."""

from __future__ import annotations

import pytest

from quill.core.ai.engines import build_engine_registry
from quill.core.ai.quick_switch import active_target, list_targets


def test_registry_has_native_plus_every_pack() -> None:
    reg = build_engine_registry()
    ids = {h.id for h in reg.all()}
    assert "native" in ids
    assert {"copilot", "claude_agent_sdk", "openai_agents"} <= ids


def test_native_is_always_available_and_default_active() -> None:
    reg = build_engine_registry()
    native = reg.get("native")
    assert native is not None and native.is_available()[0] is True
    # With no saved preference, Native is the running engine.
    active = active_target(reg)
    assert active is not None and active.harness_id == "native"


def test_targets_carry_install_reason_for_absent_packs() -> None:
    targets = {t.harness_id: t for t in list_targets(build_engine_registry())}
    # Whatever is/ isn't installed locally, an unavailable pack always names its extra.
    for pack_id in ("copilot", "claude_agent_sdk", "openai_agents"):
        target = targets[pack_id]
        if not target.available:
            assert target.reason and "pip install" in target.reason


def test_selection_registry_refuses_to_run() -> None:
    # The placeholder responder makes the selection-only contract explicit.
    from quill.core.ai.harness.native import build_prompt  # noqa: F401

    reg = build_engine_registry()
    native = reg.get("native")
    assert native is not None
    from quill.core.ai.harness import AgentSpec, AIContext

    agent = AgentSpec(id="x", display_name="X", system_prompt="y")
    # Reaching into the responder directly proves running is blocked.
    with pytest.raises(RuntimeError):
        native._responder(agent, AIContext(prompt="hi"))  # type: ignore[attr-defined]
