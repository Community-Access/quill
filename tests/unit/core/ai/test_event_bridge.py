"""Streaming Event Bridge: verbosity thresholds and anti-spam collapsing."""

from __future__ import annotations

from quill.core.ai.event_bridge import AnnouncementLevel, EventBridge, announce_for
from quill.core.ai.events import AgentEvent, AgentEventKind


def _ev(kind: AgentEventKind, summary: str = "") -> AgentEvent:
    return AgentEvent(kind, summary)


def test_quiet_speaks_only_outcomes() -> None:
    q = AnnouncementLevel.QUIET
    # Spoken even in Quiet:
    assert announce_for(_ev(AgentEventKind.ERROR, "boom"), q) == "boom"
    assert announce_for(_ev(AgentEventKind.PATCH_APPLIED, "done"), q) == "done"
    assert announce_for(_ev(AgentEventKind.PERMISSION_REQUIRED, "ok?"), q) == "ok?"
    assert announce_for(_ev(AgentEventKind.AGENT_COMPLETED, "fin"), q) == "fin"
    # Silent in Quiet:
    assert announce_for(_ev(AgentEventKind.AGENT_STARTED, "x"), q) is None
    assert announce_for(_ev(AgentEventKind.PATCH_PROPOSED, "x"), q) is None


def test_balanced_speaks_started_and_proposed_not_deltas() -> None:
    b = AnnouncementLevel.BALANCED
    assert announce_for(_ev(AgentEventKind.AGENT_STARTED, "go"), b) == "go"
    assert announce_for(_ev(AgentEventKind.PATCH_PROPOSED, "2 changes"), b) == "2 changes"
    # Internal chatter and deltas stay silent at Balanced.
    assert announce_for(_ev(AgentEventKind.TOOL_CALL_COMPLETED, "x"), b) is None
    assert announce_for(_ev(AgentEventKind.AGENT_TEXT_DELTA, "x"), b) is None


def test_detailed_adds_tool_chatter_but_not_deltas() -> None:
    d = AnnouncementLevel.DETAILED
    assert announce_for(_ev(AgentEventKind.TOOL_CALL_COMPLETED, "ran"), d) == "ran"
    assert announce_for(_ev(AgentEventKind.TOOL_CALL_REQUESTED, "req"), d) == "req"
    assert announce_for(_ev(AgentEventKind.AGENT_TEXT_DELTA, "x"), d) is None


def test_debug_speaks_text_deltas() -> None:
    assert (
        announce_for(_ev(AgentEventKind.AGENT_TEXT_DELTA, "tok"), AnnouncementLevel.DEBUG) == "tok"
    )


def test_empty_summary_falls_back_to_generic() -> None:
    msg = announce_for(_ev(AgentEventKind.PATCH_APPLIED), AnnouncementLevel.QUIET)
    assert msg is not None
    assert "undo" in msg.lower()


def test_bridge_speaks_only_permitted_levels() -> None:
    spoken: list[str] = []
    bridge = EventBridge(AnnouncementLevel.BALANCED, spoken.append)
    bridge.handle(_ev(AgentEventKind.AGENT_STARTED, "started"))
    bridge.handle(_ev(AgentEventKind.AGENT_TEXT_DELTA, "noise"))  # below threshold
    bridge.handle(_ev(AgentEventKind.AGENT_COMPLETED, "finished"))
    assert spoken == ["started", "finished"]


def test_bridge_collapses_consecutive_duplicates() -> None:
    spoken: list[str] = []
    bridge = EventBridge(AnnouncementLevel.BALANCED, spoken.append)
    bridge.handle(_ev(AgentEventKind.PATCH_PROPOSED, "1 change"))
    bridge.handle(_ev(AgentEventKind.PATCH_PROPOSED, "1 change"))  # duplicate, collapsed
    bridge.handle(_ev(AgentEventKind.PATCH_PROPOSED, "2 changes"))
    assert spoken == ["1 change", "2 changes"]


def test_bridge_set_level_changes_output() -> None:
    spoken: list[str] = []
    bridge = EventBridge(AnnouncementLevel.QUIET, spoken.append)
    bridge.handle(_ev(AgentEventKind.AGENT_STARTED, "started"))  # silent in Quiet
    assert spoken == []
    bridge.set_level(AnnouncementLevel.BALANCED)
    bridge.handle(_ev(AgentEventKind.AGENT_STARTED, "started2"))
    assert spoken == ["started2"]
