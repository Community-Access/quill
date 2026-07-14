"""Meeting Mode (verbosity §10).

Meeting Mode hard-mutes every earcon and routes speech through a reduced set,
while braille and the visual floor remain. It is a stronger, presentation-safe
sibling of Quiet Mode. The engine consults the ``meeting`` flag when routing
channels; this controller just owns the on/off state and phrasing.

Pure and wx-free.
"""

from __future__ import annotations

__all__ = ["MeetingMode"]


class MeetingMode:
    """The Meeting Mode on/off controller."""

    def __init__(self, *, active: bool = False) -> None:
        self._active = active

    @property
    def is_active(self) -> bool:
        return self._active

    def enter(self) -> str:
        """Turn Meeting Mode on; return the transition announcement."""
        self._active = True
        return "Meeting Mode on"

    def exit(self) -> str:
        """Turn Meeting Mode off; return the transition announcement."""
        self._active = False
        return "Meeting Mode off"

    def toggle(self) -> str:
        """Flip Meeting Mode and return the transition announcement."""
        return self.exit() if self._active else self.enter()
