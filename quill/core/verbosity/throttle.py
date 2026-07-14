"""Announcement anti-spam: repetition collapse (#409) and budget (#408).

A screen-reader-first editor can produce the same announcement many times in a
row (holding a navigation key at a boundary, a repeated "no more results", a busy
status line) or a sudden flood of them. Speaking every one is exhausting. This
wx-free helper sits at the verbosity controller's single ``process`` choke-point
and decides whether a given piece of *speech* should actually be spoken:

- **Repetition collapse** — identical consecutive speech within a short window is
  dropped (the visual status bar still updates, so nothing is lost on screen).
- **Announcement budget** — at most ``max_per_window`` spoken announcements in a
  rolling window; beyond that, speech is dropped until the window drains.

Both are opt-out/opt-in via :class:`ThrottleConfig`. The clock is injectable so the
behaviour is deterministic under test. Visual output is never throttled here — only
the spoken channel — so this can never hide information from a sighted user.
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

# Internal windows (seconds). Kept as constants rather than settings to keep the
# user-facing surface small; the on/off knob and the budget count are the dials.
_REPEAT_WINDOW_S = 1.5
_BUDGET_WINDOW_S = 5.0


@dataclass(frozen=True, slots=True)
class ThrottleConfig:
    """How aggressively to suppress repeated / flooding spoken announcements."""

    collapse_repeats: bool = True
    # 0 disables the budget; a positive value caps spoken announcements per window.
    max_per_window: int = 0
    repeat_window_s: float = _REPEAT_WINDOW_S
    budget_window_s: float = _BUDGET_WINDOW_S


@dataclass(frozen=True, slots=True)
class ThrottleDecision:
    """Whether to speak, and why not when suppressed (``"repeat"`` / ``"budget"``)."""

    speak: bool
    reason: str = "ok"


class AnnouncementThrottle:
    """Stateful gate for the spoken channel at the announce choke-point."""

    def __init__(
        self, config: ThrottleConfig | None = None, *, time_fn: Callable[[], float] = time.monotonic
    ) -> None:
        self._config = config or ThrottleConfig()
        self._now = time_fn
        self._last_speech: str = ""
        self._last_speech_at: float = float("-inf")
        self._spoken_at: deque[float] = deque()

    @property
    def config(self) -> ThrottleConfig:
        return self._config

    def set_config(self, config: ThrottleConfig) -> None:
        """Adopt a new config (e.g. after a settings change). State is preserved."""
        self._config = config

    def reset(self) -> None:
        """Forget recent history (e.g. on a deliberate mode change)."""
        self._last_speech = ""
        self._last_speech_at = float("-inf")
        self._spoken_at.clear()

    def admit(self, speech: str) -> ThrottleDecision:
        """Decide whether *speech* should be spoken now, updating internal state.

        Empty speech is always admitted (there is nothing to suppress; upstream
        Quiet/Meeting/profile suppression is handled before this). A suppressed
        announcement does **not** count against the budget.
        """
        if not speech:
            return ThrottleDecision(True)
        now = self._now()

        if (
            self._config.collapse_repeats
            and speech == self._last_speech
            and (now - self._last_speech_at) <= self._config.repeat_window_s
        ):
            # Keep sliding the window so a held-down key stays collapsed.
            self._last_speech_at = now
            return ThrottleDecision(False, "repeat")

        if self._config.max_per_window > 0:
            cutoff = now - self._config.budget_window_s
            while self._spoken_at and self._spoken_at[0] < cutoff:
                self._spoken_at.popleft()
            if len(self._spoken_at) >= self._config.max_per_window:
                return ThrottleDecision(False, "budget")

        self._last_speech = speech
        self._last_speech_at = now
        self._spoken_at.append(now)
        return ThrottleDecision(True)


def config_from_settings(settings: object) -> ThrottleConfig:
    """Build a :class:`ThrottleConfig` from the app settings object (tolerant)."""
    collapse = bool(getattr(settings, "verbosity_collapse_repeats", True))
    try:
        budget = int(getattr(settings, "verbosity_max_announcements_per_window", 0) or 0)
    except (TypeError, ValueError):
        budget = 0
    return ThrottleConfig(collapse_repeats=collapse, max_per_window=max(0, budget))
