"""Agentic decision types and the safe tool allowlist for the assistant.

The assistant decides, per turn, whether to answer in chat, insert/replace
text, or RUN one Quill command. Only a curated, safe, automatable subset of
commands is offered for 'run' (no destructive or argument-heavy actions),
constrained via guided generation so the model can only pick a valid id.
"""

from __future__ import annotations

from dataclasses import dataclass

from quill.core.command_catalogue import agent_ok_ids

ACTIONS = ("answer", "insert", "replace", "run")

# Curated safe, automatable commands the agent may run. Ids must exist in the
# CommandRegistry; unknown/disabled ones are filtered at runtime. A view of the
# family command catalogue's ``agent_ok`` rows (docs/design/command-key.md 12):
# a row is agent-safe only when it is SAFE, which GATE-CATALOGUE checks.
SAFE_TOOL_IDS: tuple[str, ...] = agent_ok_ids("quill")


@dataclass(frozen=True, slots=True)
class AgentDecision:
    action: str  # one of ACTIONS
    text: str = ""  # for answer / insert / replace
    tool: str = ""  # command id when action == "run"


def allowed_tools(registry: object, feature_manager: object | None = None) -> list[tuple[str, str]]:
    """Return (id, title) for safe tools that actually exist in the registry."""
    available = {c.id: c.title for c in registry.list(feature_manager=feature_manager)}  # type: ignore[attr-defined]
    return [(tid, available[tid]) for tid in SAFE_TOOL_IDS if tid in available]
