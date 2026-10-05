"""What dictation does when something goes wrong mid-session, and the rescue keys.

Three behaviours from the 2026-09-28 reliability pass (dict.md 2.2, 2.3, 2.7),
kept out of :mod:`controller` because that module is at its size ceiling and
because each of these is a policy about *failure*, which the phrase pipeline
should not have to read past:

* **Escape cancels the phrase being heard.** While the engine is still
  listening to a phrase, Escape throws it away -- nothing is written -- and
  says "Cancelled". Ctrl+F11 still stops and keeps what was said. Escape does
  nothing to dictation while nothing is being heard, so the key falls through
  to whatever else answers it.
* **The microphone watchdog.** When the recogniser reports that the
  microphone stopped (unplugged, a headset that dropped, or digital silence
  for a few seconds), dictation pauses and says so, then resumes by itself
  when the device is back. Paused is still "on": the menu mark stays, and no
  phrase is written until the microphone is heard from again.
* **The self-healing engine.** The first time the engine stops answering,
  dictation restarts it once, silently. The second time, it reports the
  engine by name and names the one to try instead.

Mixed into :class:`~quill.core.windows_dictation.controller.DictationController`,
which supplies ``_state``, ``_set_state``, ``_recognizer``, ``_open``,
``_close_recognizer``, ``_preferences``, ``_feedback``, ``_say`` and
``_abandon``. wx-free; every method is safe to call from a test with a fake
recogniser.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from quill.core.windows_dictation.controller import DictationState
    from quill.core.windows_dictation.preferences import DictationPreferences

__all__ = ["ENGINE_NAMES", "ResilienceMixin", "engine_failure_message"]

#: The engines as Dictation Settings names them, and which one to suggest when
#: each stops working: the next one along that needs nothing installed.
ENGINE_NAMES: dict[str, str] = {
    "moonshine": "Moonshine",
    "whisper": "Whisper",
    "windows": "Windows speech recognition",
    "openai": "OpenAI dictation",
}
_TRY_INSTEAD: dict[str, str] = {
    "openai": "Moonshine",
    "moonshine": "Whisper",
    "whisper": "Windows speech recognition",
    "windows": "Moonshine",
}


def engine_failure_message(engine: str) -> str:
    """The second failure, with the engine's name and a next step."""
    name = ENGINE_NAMES.get(engine, "The speech engine")
    other = _TRY_INSTEAD.get(engine, "another engine")
    return f"{name} stopped working. Try {other} in Dictation Settings."


class ResilienceMixin:
    """Cancel, the microphone watchdog and the one silent restart."""

    _state: DictationState
    _recognizer: Any
    _feedback: Any
    _ignore_until_speech: bool
    _restarted: bool
    _preferences: Callable[[], DictationPreferences]

    # Provided by the controller; declared so the mixin type-checks on its own.
    def _set_state(self, state: DictationState) -> None:
        raise NotImplementedError

    def _say(self, message: str) -> None:
        raise NotImplementedError

    def _close_recognizer(self) -> None:
        raise NotImplementedError

    def _open(
        self, preferences: DictationPreferences, *, quiet: bool = False, report: bool = True
    ) -> bool:
        raise NotImplementedError

    # -- Escape ------------------------------------------------------------ #

    def cancel_phrase(self) -> bool:
        """Throw away the phrase being heard. ``False`` when nothing is."""
        from quill.core.windows_dictation.controller import DictationState

        if self._state is not DictationState.RECOGNIZING:
            return False
        discard = getattr(self._recognizer, "discard", None)
        if callable(discard):
            try:
                discard()
            except Exception:  # noqa: BLE001 - the guard below still drops it
                pass
        # Whatever the engine finalises from the audio it already had is not
        # wanted; the next real utterance clears this (on_speech_started).
        self._ignore_until_speech = True
        self._set_state(DictationState.LISTENING)
        self._say("Cancelled.")
        return True

    # -- the microphone ---------------------------------------------------- #

    def on_microphone_lost(self) -> None:
        """The recogniser lost the device or hears digital silence."""
        from quill.core.windows_dictation.controller import _LIVE, DictationState

        if self._state not in _LIVE:
            return
        self._set_state(DictationState.PAUSED)
        self._say("The microphone stopped. Dictation is paused and will resume when it comes back.")

    def on_microphone_back(self) -> None:
        from quill.core.windows_dictation.controller import DictationState

        if self._state is not DictationState.PAUSED:
            return
        self._ignore_until_speech = False
        self._set_state(DictationState.LISTENING)
        self._say("Microphone back. Listening.")

    # -- the engine -------------------------------------------------------- #

    def restart_once(self) -> bool:
        """Reopen the engine silently, the first time only. ``True`` if it is back."""
        from quill.core.windows_dictation.controller import DictationState

        if self._restarted:
            return False
        self._restarted = True
        was_live = self._state is not DictationState.STANDBY
        self._close_recognizer()
        preferences = self._preferences()
        if not self._open(preferences, quiet=True, report=False):
            return False
        self._set_state(DictationState.LISTENING if was_live else DictationState.STANDBY)
        self._feedback.show("Dictation restarted its speech engine.")
        return True
