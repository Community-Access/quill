"""Hear what a setting will do before you keep it (FUX-08, family M8).

A choice such as "a sound, words, both or neither" means little until it is
heard. This module plays a short preview of the choices a window *shows* --
never the saved ones -- so a person can try a choice, hear it, and still press
Cancel. Nothing here reads or writes a setting.

Three pieces, so every window that previews feedback does it the same way:

* :func:`feedback_step` -- what one moment does under the shared
  ``sound`` / ``speech`` / ``both`` / ``silent`` choice, resolved by
  :func:`quill.core.action_feedback.resolve`, the same function the real moment
  uses. A ``sound`` moment with no sound in the scheme speaks, as it does for
  real.
* :func:`edge_step` -- a start or stop moment that has a "play sounds" check
  box and a "say it" check box, the rule
  :meth:`quill.core.windows_dictation.controller.DictationController._announce_edge`
  follows.
* :class:`PreviewSequence` -- plays a few steps a moment apart, once. Pressing
  the button again, pressing Escape, or closing the window stops what is left.
  Escape stops the preview without closing the window, the way Scribe's Play
  Sample does; with nothing playing, Escape closes the window as usual.

What is said is only what the screen reader cannot know: the preview's own
words, and, when nothing could be heard, one sentence that says why (GATE-13).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from quill.core.action_feedback import resolve

__all__ = [
    "NOTHING_HEARD",
    "SOUNDS_OFF",
    "PreviewSequence",
    "PreviewStep",
    "edge_step",
    "feedback_step",
]

#: Said when every step of a preview is silent: the choice really is silence.
NOTHING_HEARD = "Nothing. With these choices, nothing plays and nothing is said."
#: Said when a step would play a sound and the app's sounds are off.
SOUNDS_OFF = "Sounds are turned off in this app, so its tones are not played."

#: How far apart the steps of one preview are, in milliseconds: long enough for
#: a tone and a few words to finish before the next one starts.
STEP_GAP_MS = 1800


@dataclass(frozen=True)
class PreviewStep:
    """One moment of a preview: a sound to play, words to say, or both."""

    sound: str = ""
    words: str = ""

    @property
    def silent(self) -> bool:
        return not self.sound and not self.words


def feedback_step(mode: object, *, event: str, words: str, has_sound: bool) -> PreviewStep:
    """What a moment does under the sound / speech / both / silent *mode*."""
    play, speak = resolve(mode, has_sound=has_sound)
    return PreviewStep(sound=event if play else "", words=words if speak else "")


def edge_step(
    *, cue_sounds: bool, announce: bool, event: str, words: str, has_sound: bool
) -> PreviewStep:
    """A start or stop moment with a sound check box and a words check box.

    With the sounds on and no sound in the scheme, the words step in, as they
    do for real: a choice never ends up as no feedback by accident.
    """
    played = bool(cue_sounds and has_sound)
    speak = bool(announce or (cue_sounds and not played))
    return PreviewStep(sound=event if played else "", words=words if speak else "")


def _post_cue(event: str) -> None:
    from quill.ui.companion_cues import post_cue

    post_cue(event)


def _sounds_on() -> bool:
    try:
        from quill.ui import sound_manager

        return bool(sound_manager.is_active())
    except Exception:  # noqa: BLE001 - no sound stack: nothing can play
        return False


class PreviewSequence:
    """Play a few :class:`PreviewStep` s a moment apart, and stop on request.

    *say* speaks through the app's announcement service, so the words are
    brailled too. *cue* plays an earcon (the app's sound scheme, volume and
    device). *call_later* is ``wx.CallLater``; tests pass their own.
    """

    def __init__(
        self,
        say: Callable[[str], None],
        *,
        cue: Callable[[str], None] | None = None,
        sounds_on: Callable[[], bool] | None = None,
        call_later: Callable[..., Any] | None = None,
        gap_ms: int = STEP_GAP_MS,
    ) -> None:
        self._say = say
        self._cue = cue or _post_cue
        self._sounds_on = sounds_on or _sounds_on
        self._call_later = call_later
        self._gap_ms = gap_ms
        self._pending: list[Any] = []
        self._muted_said = False

    @property
    def playing(self) -> bool:
        """True while steps of a preview are still waiting to be heard."""
        return any(_running(timer) for timer in self._pending)

    def play(self, steps: Sequence[PreviewStep]) -> None:
        """Start a preview of *steps*; one already playing is stopped first."""
        self.stop()
        heard = [step for step in steps if not step.silent]
        if not heard:
            self._say(NOTHING_HEARD)
            return
        self._muted_said = False
        self._run(heard[0])
        later = self._call_later or _wx_call_later()
        for index, step in enumerate(heard[1:], start=1):
            self._pending.append(later(self._gap_ms * index, self._run, step))

    def stop(self) -> bool:
        """Cancel the steps not yet heard. True when there were some."""
        pending, self._pending = self._pending, []
        stopped = False
        for timer in pending:
            if _running(timer):
                stopped = True
            try:
                timer.Stop()
            except Exception:  # noqa: BLE001 - a timer already gone is stopped
                pass
        return stopped

    def guard(self, window: Any) -> None:
        """Stop on Escape (without closing *window*) and when *window* closes."""
        from quill.ui.preview_guard import guard_preview

        guard_preview(window, self.stop, self._say)

    def _run(self, step: PreviewStep) -> None:
        if step.sound:
            if self._sounds_on():
                self._cue(step.sound)
            elif not self._muted_said:
                # Once per preview: the reason, not the same sentence each step.
                self._muted_said = True
                self._say(SOUNDS_OFF)
        if step.words:
            self._say(step.words)


def _running(timer: Any) -> bool:
    try:
        return bool(timer.IsRunning())
    except Exception:  # noqa: BLE001 - a destroyed timer is not running
        return False


def _wx_call_later() -> Callable[..., Any]:
    import wx

    return wx.CallLater
