"""Thinking-indicator policy for the AI chat (Companion voice/text mode).

When the model takes a while, the user should be told it is working — first a
gentle "thinking" cue, then periodic "still thinking" reminders for a long wait.
This is the wx-free, clock-injected decision logic so it is unit-testable; the UI
drives it from a timer and turns each due cue into an earcon + announcement.
"""

from __future__ import annotations

__all__ = ["DEFAULT_PATIENCE_SECONDS", "DEFAULT_REPEAT_SECONDS", "ThinkingIndicator"]

# How long to wait before the first "thinking" cue, and how often to remind after
# that. Small enough to reassure, large enough not to chatter on fast replies.
DEFAULT_PATIENCE_SECONDS = 4.0
DEFAULT_REPEAT_SECONDS = 8.0


class ThinkingIndicator:
    """Decides when to emit "thinking" / "still thinking" cues during a wait.

    Construct once, call :meth:`start` when a turn begins, poll
    :meth:`due_for_cue` from a timer (passing the current monotonic time), and
    :meth:`stop` when the reply arrives. The first cue fires after
    ``patience_seconds``; further cues fire every ``repeat_seconds`` while the
    wait continues (set ``repeat_seconds`` to 0 for a single cue).
    """

    def __init__(
        self,
        patience_seconds: float = DEFAULT_PATIENCE_SECONDS,
        repeat_seconds: float = DEFAULT_REPEAT_SECONDS,
    ) -> None:
        self._patience = max(0.1, patience_seconds)
        self._repeat = max(0.0, repeat_seconds)
        self._start: float | None = None
        self._last_cue: float | None = None

    @property
    def active(self) -> bool:
        return self._start is not None

    def start(self, now: float) -> None:
        self._start = now
        self._last_cue = None

    def stop(self) -> None:
        self._start = None
        self._last_cue = None

    def elapsed(self, now: float) -> float:
        return 0.0 if self._start is None else max(0.0, now - self._start)

    def due_for_cue(self, now: float) -> bool:
        """Return True (once) each time a thinking cue is due at time ``now``."""
        if self._start is None:
            return False
        if self._last_cue is None:
            if now - self._start >= self._patience:
                self._last_cue = now
                return True
            return False
        if self._repeat > 0 and now - self._last_cue >= self._repeat:
            self._last_cue = now
            return True
        return False
