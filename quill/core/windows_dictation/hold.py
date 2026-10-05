"""Hold-to-talk on the dictation key: a quick press toggles, a long press holds.

Learned from VS Code's editor dictation (``editorDictation.ts``, MIT), which
starts on the key going down and, if the key is still held half a second later,
stops when it comes up. QUILL's own words and code; credited in
``docs/design/2026-10-05-dictation-plan-and-status.md``.

* **Off, pressed and let go quickly** (under :data:`HOLD_SECONDS`): dictation
  starts and stays on. That is the toggle everybody already knows.
* **Off, pressed and held**: dictation starts at once -- nothing is lost
  waiting to decide -- and stops, keeping the last phrase, when the key comes up.
* **On, pressed**: dictation stops, however long the key is held.
* **Key repeat** while the key is down is ignored. Windows repeats a held
  accelerator about thirty times a second; without this, holding the key would
  start and stop dictation over and over.

The setting **Hold Ctrl+F11 to talk** (on by default) only decides whether
letting go of a long press stops dictation; with it off, the key is a pure
toggle for anybody for whom holding a key is hard, and repeats are still
ignored. A press that did not come from the key -- a menu, the Command
Palette, a test -- is always a plain toggle, because there is no key to hold.

Pure and wx-free: the host reports the key's state and the time, and does what
:class:`HoldToTalk` answers.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = ["HOLD_SECONDS", "HoldAction", "HoldToTalk"]

#: How long the key must stay down before letting go means "stop". VS Code's.
HOLD_SECONDS = 0.5


class HoldAction(StrEnum):
    """What the host does after a press or a poll."""

    START = "start"
    STOP = "stop"
    #: A repeat of a key already being watched: do nothing.
    IGNORE = "ignore"
    #: Keep polling the key.
    WATCH = "watch"
    #: Stop polling; dictation stays as it is.
    DONE = "done"
    #: The key came up after a hold: stop dictation, keeping the last phrase.
    RELEASE = "release"


class HoldToTalk:
    """One key's presses, as a tiny state machine."""

    def __init__(self, *, hold_enabled: bool = True) -> None:
        self.hold_enabled = hold_enabled
        self._down_at: float | None = None
        self._started = False
        self.holding = False

    @property
    def watching(self) -> bool:
        """Whether a press is being followed until the key comes up."""
        return self._down_at is not None

    def press(self, *, now: float, active: bool, key_down: bool) -> HoldAction:
        """The dictation command ran. *key_down*: the key is physically held."""
        if self.watching:
            return HoldAction.IGNORE
        if key_down:
            self._down_at = now
            self._started = not active
            self.holding = False
        return HoldAction.STOP if active else HoldAction.START

    def poll(self, *, now: float, key_down: bool) -> HoldAction:
        """The host's timer: is the key still down?"""
        if self._down_at is None:
            return HoldAction.DONE
        if key_down:
            if self._started and self.hold_enabled and now - self._down_at >= HOLD_SECONDS:
                self.holding = True
            return HoldAction.WATCH
        holding = self.holding or (
            self._started and self.hold_enabled and now - self._down_at >= HOLD_SECONDS
        )
        self.reset()
        return HoldAction.RELEASE if holding else HoldAction.DONE

    def reset(self) -> None:
        self._down_at = None
        self._started = False
        self.holding = False
