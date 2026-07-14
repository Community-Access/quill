"""Wake-word detection policy for "Hey QUILL" (Phase 3).

Pure, wx-free, and audio-free: this decides *when* an always-listening session
should wake, from a stream of already-transcribed short audio windows. It does
not touch the microphone, the recognizer, wx, or the clock — the UI feeds it
transcribed windows and a periodic tick, and executes the :class:`WakeEffect`
objects it returns (arm the conversation, dispatch a trailing command, play a
cue, announce, keep listening, remind that the mic is live).

Keeping the policy here makes the whole always-listening contract testable with
plain strings: wake detection, an inline command after the wake phrase
("hey quill save file"), the cooldown that prevents a double-wake, and the
periodic "still listening" reminder that keeps a live microphone perceivable.

Safety: like every voice surface, the caller only reaches the safe-tool
allowlist for any command; the wake controller never *runs* anything — it emits
an ``arm`` or ``dispatch`` effect the UI validates and executes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill.core.speech.conversation import CUE_WAKE
from quill.core.speech.voice_commands import extract_transcript_body


class WakeState:
    OFF = "off"
    LISTENING = "listening"  # waiting for the wake phrase
    WOKEN = "woken"  # handed off to the conversation loop


@dataclass(frozen=True, slots=True)
class WakeEffect:
    """One side effect for the UI. Ordered; execute in sequence."""

    kind: str  # sound | announce | arm | dispatch | listen_again | reminder | stop_listen
    value: str = ""


def _sound(event_id: str) -> WakeEffect:
    return WakeEffect("sound", event_id)


def _say(text: str) -> WakeEffect:
    return WakeEffect("announce", text)


@dataclass(slots=True)
class WakeController:
    """Decides when an always-listening session wakes (pure; UI-driven).

    ``reminder_every`` is the number of idle windows between "still listening"
    reminders (0 disables them). ``cooldown_windows`` is how many windows to
    ignore right after a wake, so the tail of the wake utterance cannot
    immediately re-trigger.
    """

    reminder_every: int = 12
    cooldown_windows: int = 1
    state: str = WakeState.OFF
    _idle_windows: int = field(default=0, repr=False)
    _cooldown_left: int = field(default=0, repr=False)

    def start(self) -> list[WakeEffect]:
        """Begin always-listening for the wake phrase."""
        if self.state != WakeState.OFF:
            return []
        self.state = WakeState.LISTENING
        self._idle_windows = 0
        self._cooldown_left = 0
        return [
            _say('Listening for "Hey QUILL". Say "Hey QUILL" followed by a command.'),
            WakeEffect("listen_again"),
        ]

    def stop(self) -> list[WakeEffect]:
        """Stop always-listening from any state."""
        if self.state == WakeState.OFF:
            return []
        self.state = WakeState.OFF
        return [WakeEffect("stop_listen"), _say('Stopped listening for "Hey QUILL".')]

    def on_window(self, transcript: str) -> list[WakeEffect]:
        """A transcribed listening window arrived.

        Returns the effects for that window: wake (with an optional inline
        command), or keep listening (occasionally reminding that the mic is
        live). During the post-wake cooldown, windows are ignored.
        """
        if self.state != WakeState.LISTENING:
            return []
        if self._cooldown_left > 0:
            self._cooldown_left -= 1
            return [WakeEffect("listen_again")]

        body = extract_transcript_body(transcript or "")
        if body is None:
            # The wake phrase was not spoken — keep listening, remind now and then.
            self._idle_windows += 1
            effects: list[WakeEffect] = []
            if self.reminder_every > 0 and self._idle_windows % self.reminder_every == 0:
                effects.append(WakeEffect("reminder"))
            effects.append(WakeEffect("listen_again"))
            return effects

        # Woken.
        self._idle_windows = 0
        self._cooldown_left = self.cooldown_windows
        self.state = WakeState.WOKEN
        effects = [_sound(CUE_WAKE)]
        if body:
            # "hey quill save file" — pass the trailing command straight through.
            effects.append(WakeEffect("dispatch", body))
        else:
            # Bare "hey quill" — arm the conversation loop for the next utterance.
            effects.append(WakeEffect("arm"))
        return effects

    def resume_listening(self) -> list[WakeEffect]:
        """Return to LISTENING after the woken command/conversation finished."""
        if self.state == WakeState.OFF:
            return []
        self.state = WakeState.LISTENING
        return [WakeEffect("listen_again")]

    def status_text(self) -> str:
        return {
            WakeState.OFF: "Not listening",
            WakeState.LISTENING: 'Listening for "Hey QUILL"',
            WakeState.WOKEN: "Awake",
        }[self.state]


__all__ = ["WakeController", "WakeEffect", "WakeState"]
