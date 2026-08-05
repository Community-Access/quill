"""Player events emitted by the controller for the UI to observe.

Core emits these synchronously; the UI subscribes and marshals to the main
thread with ``wx.CallAfter``. Core stays wx-free.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

#: A new item was loaded.
LOADED = "loaded"
#: The transport state changed (playing/paused/stopped/ended).
STATE_CHANGED = "state_changed"
#: The current chapter changed.
CHAPTER_CHANGED = "chapter_changed"
#: The item finished playing.
ENDED = "ended"
#: The position was set (seek/skip/timecode) -- carries the new ms in ``value``.
SEEKED = "seeked"


@dataclass(frozen=True, slots=True)
class PlayerEvent:
    """One player-state change."""

    kind: str
    value: object = None


PlayerListener = Callable[[PlayerEvent], None]

__all__ = [
    "CHAPTER_CHANGED",
    "ENDED",
    "LOADED",
    "SEEKED",
    "STATE_CHANGED",
    "PlayerEvent",
    "PlayerListener",
]
