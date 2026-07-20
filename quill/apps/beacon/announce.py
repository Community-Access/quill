"""Accessible announcement helpers (PRD sections 17.6, 18.4).

QuillBeacon announces through the status bar (always visible, screen-reader
reachable) and an optional wx bell, never through color or transient popups.
``Announcer`` wraps a wx frame's status bar so the rest of the UI calls one
method and stays consistent. verbosity controls how much is spoken.
"""

from __future__ import annotations

from typing import Literal

Verbosity = Literal["minimal", "normal", "verbose"]

_VERBOSITY_ORDER = {"minimal": 0, "normal": 1, "verbose": 2}


class Announcer:
    """Status-bar announcer with configurable verbosity (PRD 18.4, 29.2)."""

    def __init__(self, frame, *, verbosity: Verbosity = "normal") -> None:
        self.frame = frame
        self.verbosity = verbosity

    def set_verbosity(self, v: Verbosity) -> None:
        self.verbosity = v

    def say(self, message: str, level: Verbosity = "normal") -> None:
        """Post ``message`` to the status bar if verbosity permits.

        Falls back to the frame title if the frame has no status bar, so any
        wx.Frame (including the player) can host an Announcer.
        """
        if _VERBOSITY_ORDER[level] > _VERBOSITY_ORDER[self.verbosity]:
            return
        bar = self.frame.GetStatusBar() if hasattr(self.frame, "GetStatusBar") else None
        if bar is not None:
            self.frame.SetStatusText(message)
        else:
            self.frame.SetTitle(message)

    def announce_count(self, count: int, filtered: bool = False) -> None:
        word = "results" if count != 1 else "result"
        if filtered:
            self.say(f"{count} {word} (filtered)")
        else:
            self.say(f"{count} {word}")

    def announce_filters(self, filters: list[str]) -> None:
        if not filters:
            self.say("No filters active", "minimal")
            return
        self.say("Filters: " + ", ".join(filters))

    def where_am_i(self, context: dict) -> str:
        """Build the 'Where Am I?' announcement string (PRD 17.6)."""
        parts = []
        if context.get("area"):
            parts.append(context["area"])
        if context.get("collection"):
            parts.append(f"collection {context['collection']}")
        if context.get("search"):
            parts.append(f"search '{context['search']}'")
        if context.get("filters"):
            parts.append("filters " + ", ".join(context["filters"]))
        if context.get("sort"):
            parts.append(f"sort {context['sort']}")
        if context.get("selected"):
            parts.append(f"selected {context['selected']}")
        if context.get("position") and context.get("count"):
            parts.append(f"{context['position']} of {context['count']}")
        if context.get("sync"):
            parts.append(f"sync {context['sync']}")
        return ". ".join(parts) if parts else "QuillBeacon"
