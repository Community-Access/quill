"""Screen-reader announcements (PRD 6.3, 28.3, 28.5).

Important state is never hidden: every announcement reaches the user as text.
The announcer speaks through the most reliable channel available, in order:

1. ``accessible_output2`` (Tolk / SAPI) when installed -- direct speech that
   does not depend on where focus is.
2. The frame's status bar, which is always a text equivalent and is picked up
   by screen readers on review.

Verbosity gates chatter: ``minimal`` speaks only errors and explicit requests,
``normal`` speaks routine confirmations, ``verbose`` adds background detail.
Announcements are always marshaled onto the UI thread with ``wx.CallAfter`` so
background workers can announce safely (PRD 29.3).
"""

from __future__ import annotations

_LEVELS = {"minimal": 0, "normal": 1, "verbose": 2}


class Announcer:
    def __init__(self, frame, *, verbosity: str = "normal") -> None:
        self.frame = frame
        self.verbosity = verbosity
        self._speaker = self._make_speaker()

    def _make_speaker(self):
        try:
            import accessible_output2.outputs.auto  # type: ignore

            return accessible_output2.outputs.auto.Auto()
        except Exception:
            return None

    def set_verbosity(self, verbosity: str) -> None:
        if verbosity in _LEVELS:
            self.verbosity = verbosity

    def _allowed(self, level: str) -> bool:
        return _LEVELS.get(level, 1) <= _LEVELS.get(self.verbosity, 1)

    def say(self, text: str, level: str = "normal", *, interrupt: bool = False) -> None:
        """Announce ``text`` at ``level``; errors always speak (level 'error')."""
        if not text:
            return
        if level != "error" and not self._allowed(level):
            return
        import wx

        wx.CallAfter(self._emit, text, interrupt)

    def _emit(self, text: str, interrupt: bool) -> None:
        if self._speaker is not None:
            try:
                self._speaker.speak(text, interrupt=interrupt)
            except Exception:
                pass
        try:
            if self.frame and self.frame.GetStatusBar():
                self.frame.SetStatusText(text)
        except Exception:
            pass

    def error(self, text: str) -> None:
        self.say(text, "error", interrupt=True)
