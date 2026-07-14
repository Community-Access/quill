"""Streaming Event Bridge (PRD §2.4 gap 5, §6 item 7, §14).

Harnesses emit normalized :class:`~quill.core.ai.events.AgentEvent`s. The screen
reader must hear *balanced* announcements from that stream — never token spam,
never a flood of internal tool chatter — honoring the user's announcement
verbosity. This module is the wx-free decision layer: given an event and a level,
it returns the sentence to speak, or ``None`` to stay silent.

It is pure and testable. The UI subscribes to a harness's events, calls
:func:`announce_for` (or drives an :class:`EventBridge`), and speaks the non-empty
results through the existing status/Prism path (which applies the verbosity
engine's throttling / anti-spam on top).
"""

from __future__ import annotations

from collections.abc import Callable
from enum import IntEnum

from quill.core.ai.events import AgentEvent, AgentEventKind

__all__ = ["AnnouncementLevel", "SpeakFn", "announce_for", "EventBridge"]

# The UI's announce callback.
SpeakFn = Callable[[str], None]


class AnnouncementLevel(IntEnum):
    """How much of the event stream to speak (PRD §17). Ordered least -> most."""

    QUIET = 0
    BALANCED = 1  # default
    DETAILED = 2
    DEBUG = 3


# The minimum level at which each event kind is spoken. An event is announced
# when the active level is >= its threshold. Safety- and outcome-bearing events
# (errors, permission prompts, applied patches, completion) speak even in Quiet;
# internal chatter (tool allowed/completed, thinking) needs Detailed; raw text
# deltas need Debug.
_THRESHOLD: dict[AgentEventKind, AnnouncementLevel] = {
    AgentEventKind.AGENT_STARTED: AnnouncementLevel.BALANCED,
    AgentEventKind.AGENT_THINKING_SUMMARY: AnnouncementLevel.DETAILED,
    AgentEventKind.AGENT_TEXT_DELTA: AnnouncementLevel.DEBUG,
    AgentEventKind.TOOL_CALL_REQUESTED: AnnouncementLevel.DETAILED,
    AgentEventKind.TOOL_CALL_ALLOWED: AnnouncementLevel.DETAILED,
    AgentEventKind.TOOL_CALL_DENIED: AnnouncementLevel.BALANCED,
    AgentEventKind.TOOL_CALL_COMPLETED: AnnouncementLevel.DETAILED,
    AgentEventKind.PATCH_PROPOSED: AnnouncementLevel.BALANCED,
    AgentEventKind.PATCH_APPLIED: AnnouncementLevel.QUIET,
    AgentEventKind.PERMISSION_REQUIRED: AnnouncementLevel.QUIET,
    AgentEventKind.WARNING: AnnouncementLevel.BALANCED,
    AgentEventKind.ERROR: AnnouncementLevel.QUIET,
    AgentEventKind.AGENT_COMPLETED: AnnouncementLevel.QUIET,
    AgentEventKind.AGENT_CANCELLED: AnnouncementLevel.QUIET,
}


def announce_for(event: AgentEvent, level: AnnouncementLevel) -> str | None:
    """Return the sentence to speak for ``event`` at ``level``, or ``None``.

    Uses the event's already-balanced ``summary``; falls back to a generic phrase
    if a harness emitted an empty summary. Returns ``None`` when the event is
    below the active level's threshold (stay silent).
    """
    threshold = _THRESHOLD.get(event.kind, AnnouncementLevel.DETAILED)
    if level < threshold:
        return None
    return event.summary or _GENERIC[event.kind]


_GENERIC: dict[AgentEventKind, str] = {
    AgentEventKind.AGENT_STARTED: "Agent started.",
    AgentEventKind.AGENT_THINKING_SUMMARY: "Agent thinking.",
    AgentEventKind.AGENT_TEXT_DELTA: "Agent writing.",
    AgentEventKind.TOOL_CALL_REQUESTED: "Agent requested a tool.",
    AgentEventKind.TOOL_CALL_ALLOWED: "Tool allowed.",
    AgentEventKind.TOOL_CALL_DENIED: "Tool denied.",
    AgentEventKind.TOOL_CALL_COMPLETED: "Tool completed.",
    AgentEventKind.PATCH_PROPOSED: "Changes proposed.",
    AgentEventKind.PATCH_APPLIED: "Changes applied. Press Control Z to undo.",
    AgentEventKind.PERMISSION_REQUIRED: "The agent needs your permission.",
    AgentEventKind.WARNING: "Warning.",
    AgentEventKind.ERROR: "The agent encountered an error.",
    AgentEventKind.AGENT_COMPLETED: "Agent finished.",
    AgentEventKind.AGENT_CANCELLED: "Agent cancelled.",
}


class EventBridge:
    """Stateful adapter: feed events in, get balanced announcements out.

    Construct with the active level and a ``speak`` callback (the UI's announce
    path). :meth:`handle` is the ``emit`` a harness/gateway can be given directly;
    it speaks only what the level permits. Consecutive identical announcements are
    collapsed so a repeated cue is not spoken twice in a row (a light anti-spam
    guard; the verbosity engine still applies its own budget downstream).
    """

    def __init__(self, level: AnnouncementLevel, speak: SpeakFn) -> None:
        self._level = level
        self._speak = speak
        self._last: str | None = None

    @property
    def level(self) -> AnnouncementLevel:
        return self._level

    def set_level(self, level: AnnouncementLevel) -> None:
        self._level = level

    def handle(self, event: AgentEvent) -> None:
        message = announce_for(event, self._level)
        if message is None or message == self._last:
            return
        self._last = message
        self._speak(message)
