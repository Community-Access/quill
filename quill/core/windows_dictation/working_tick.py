"""A soft tick while a heard phrase is still being recognised (D-17, 2026-10-13).

With a large model the seconds between your pause and the text are silent, and
silence is indistinguishable from dictation having stopped hearing you. So,
when the setting is on:

* nothing for the first second (:data:`TICK_AFTER_S`): most phrases arrive
  inside it, and a tick for those would be a tick on every phrase;
* then a soft tick every second (:data:`TICK_EVERY_S`) until the text arrives,
  recognition fails, or dictation stops;
* after four seconds (:data:`SENTENCE_AFTER_S`), once in a dictation session,
  the words "Still working on that phrase." (:data:`STILL_WORKING`), so the
  first long wait explains the tick.

The clock starts when the recogniser hands a finished phrase to the engine
(``on_phrase_decoding``, posted by the worker), not when you start talking: a
long sentence is not a slow one. An engine that never says so -- Windows
speech recognition -- simply never ticks.

**The feedback rules.** The setting turns the tick on; *What you hear after
each phrase* (``phrase_feedback``) is the cap on it, because a person who chose
words only, or nothing, did not choose a sound once a second:

* ``silent``, or the setting off: no tick and no sentence. Silent stays silent.
* ``speech``: no tick. The sentence is said at four seconds, once per wait.
* ``sound`` and ``both``: the tick, and the sentence once a session. With no
  clip in the sound pack the tick falls through to words
  (:func:`quill.core.action_feedback.resolve`): the sentence at four seconds,
  once per wait, and never a word a second.

The sentence is only ever said from the timer's callback, which first checks
that the wait is still open, so a phrase that arrives first means it is never
said. The read-back that follows a phrase is spoken with interrupt, so a
sentence said a moment before is cut short by the words, never queued ahead
of them.

**The screen reader's gate** (``reader_gate.py``) hears QUILL's own process, so
the tick is never heard by the microphone as speech; the cost is the same as
for every other QUILL sound, a moment in which the microphone is not listened
to. The tick is the quietest and shortest dictation sound for that reason.

Timing is the host's: the feedback port's ``call_later`` (``wx.CallLater`` in
every host), whose handle is stopped the moment the wait ends. A host without
one gets no tick. A late callback for a wait that is already over does nothing,
so nothing outlives its owner.

Mixed into the controller, which supplies ``_state``, ``_clock``,
``_preferences`` and ``_feedback``. wx-free.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from quill.core.action_feedback import ActionFeedback, coerce, resolve

if TYPE_CHECKING:
    from quill.core.windows_dictation.ports import DictationState
    from quill.core.windows_dictation.preferences import DictationPreferences

__all__ = [
    "SENTENCE_AFTER_S",
    "STILL_WORKING",
    "TICK_AFTER_S",
    "TICK_EVERY_S",
    "WorkingTickMixin",
]

#: No tick for a phrase that arrives within this long.
TICK_AFTER_S = 1.0
#: Then one tick this often.
TICK_EVERY_S = 1.0
#: The sentence comes once a wait is this long.
SENTENCE_AFTER_S = 4.0
#: Said at four seconds: once a session with the tick, once a wait without it.
STILL_WORKING = "Still working on that phrase."


class WorkingTickMixin:
    """The working tick and its one sentence."""

    _state: DictationState
    _feedback: Any
    _clock: Callable[[], float]
    _preferences: Callable[[], DictationPreferences]

    def _init_working(self) -> None:
        self._working_since: float | None = None
        self._working_wait = 0  # which wait a scheduled callback belongs to
        self._working_handle: Any = None
        self._working_told = False  # the sentence, spent for this session

    def _working_new_session(self) -> None:
        self._working_done()
        self._working_told = False

    def on_phrase_decoding(self) -> None:
        """The recogniser: a heard phrase has gone to the engine."""
        from quill.core.windows_dictation.controller import _LIVE

        if self._state not in _LIVE or self._working_since is not None:
            return  # not dictating, or already counting this wait
        self._working_since = self._clock()
        self._working_schedule(TICK_AFTER_S)

    def _working_done(self) -> None:
        """The wait is over: the text arrived, it failed, or dictation stopped."""
        self._working_since = None
        self._working_wait += 1
        handle, self._working_handle = self._working_handle, None
        stop = getattr(handle, "Stop", None)
        if callable(stop):
            try:
                stop()
            except Exception:  # noqa: BLE001 - a timer that already fired is fine
                pass

    def _working_schedule(self, seconds: float) -> None:
        later = getattr(self._feedback, "call_later", None)
        if not callable(later):
            return
        wait = self._working_wait
        try:
            self._working_handle = later(seconds, lambda: self._working_tick(wait))
        except Exception:  # noqa: BLE001 - no event loop: no tick, never no dictation
            self._working_handle = None

    def _working_tick(self, wait: int) -> None:
        from quill.core.windows_dictation.controller import _LIVE
        from quill.core.windows_dictation.ports import Moment

        if wait != self._working_wait or self._working_since is None:
            return  # a late callback for a wait that is over
        self._working_handle = None
        if self._state not in _LIVE:
            self._working_done()
            return
        preferences = self._preferences()
        mode = coerce(getattr(preferences, "phrase_feedback", "sound"))
        if not getattr(preferences, "working_tick", False) or mode is ActionFeedback.SILENT:
            self._working_done()  # silent stays silent
            return
        # phrase_feedback is the cap: words only means no tick; a sound moment
        # with no clip in the pack falls through to words (resolve).
        play, _speak = resolve(
            "speech" if mode is ActionFeedback.SPEECH else "sound",
            has_sound=self._feedback.has_cue(Moment.WORKING),
        )
        waited = self._clock() - self._working_since
        if play:
            self._feedback.cue(Moment.WORKING)
            if not self._working_told and waited >= SENTENCE_AFTER_S:
                self._working_told = True  # with the tick: once a session explains it
                self._say_still_working()
            self._working_schedule(TICK_EVERY_S)
            return
        # Words instead of the tick: once per wait, at four seconds, and done.
        if waited >= SENTENCE_AFTER_S:
            self._say_still_working()
            self._working_since = None
            return
        self._working_schedule(SENTENCE_AFTER_S - waited)

    def _say_still_working(self) -> None:
        self._feedback.say(STILL_WORKING)
        self._feedback.show(STILL_WORKING)
