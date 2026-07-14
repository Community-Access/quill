"""Normalized agent event types (Streaming Event Bridge — PRD §14).

Every harness (the native loop today; optional SDK packs later) produces wildly
different streams. This module defines the single, harness-neutral event
vocabulary they are normalized into, so the accessibility layer has exactly one
set of events to map to balanced screen-reader announcements.

This is the wx-free core. The UI subscribes to these events and decides how
loudly to speak them (honoring the verbosity setting); token deltas are
summarized, never spoken one by one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

__all__ = [
    "AgentEventKind",
    "AgentEvent",
]


class AgentEventKind(StrEnum):
    """The closed set of events a harness may emit through the bridge."""

    AGENT_STARTED = "agent_started"
    AGENT_THINKING_SUMMARY = "agent_thinking_summary"
    AGENT_TEXT_DELTA = "agent_text_delta"
    TOOL_CALL_REQUESTED = "tool_call_requested"
    TOOL_CALL_ALLOWED = "tool_call_allowed"
    TOOL_CALL_DENIED = "tool_call_denied"
    TOOL_CALL_COMPLETED = "tool_call_completed"
    PATCH_PROPOSED = "patch_proposed"
    PATCH_APPLIED = "patch_applied"
    PERMISSION_REQUIRED = "permission_required"
    WARNING = "warning"
    ERROR = "error"
    AGENT_COMPLETED = "agent_completed"
    AGENT_CANCELLED = "agent_cancelled"


@dataclass(frozen=True, slots=True)
class AgentEvent:
    """One normalized event from a running agent session.

    ``kind`` selects the vocabulary; ``summary`` is the already-balanced,
    screen-reader-friendly sentence (never raw token spam); ``detail`` carries
    structured, non-secret extras for the Activity log and richer views. Text
    deltas should arrive pre-summarized by the harness adapter, not per token.
    """

    kind: AgentEventKind
    summary: str = ""
    detail: dict[str, str] = field(default_factory=dict)

    def is_terminal(self) -> bool:
        """True when no further events follow in this session."""
        return self.kind in _TERMINAL_KINDS


_TERMINAL_KINDS: frozenset[AgentEventKind] = frozenset({
    AgentEventKind.AGENT_COMPLETED,
    AgentEventKind.AGENT_CANCELLED,
    AgentEventKind.ERROR,
})
