"""Voice conversation state machine (Hey QUILL Phase 2).

A pure, wx-free controller for the hands-free conversation loop, modeled on the
ADP Assistant's proven design (see
``docs/planning/quill-hey-quill-voice-interaction-plan.md`` §3). It owns the
five-state machine and the WCAG-grounded timing model; it does **not** touch the
microphone, the speech engine, wx, or the clock. The UI layer feeds it events
(the user armed it, a transcript arrived, a timer fired) and executes the
:class:`Effect` objects it returns (play an earcon, announce text, start a
timer, begin capture, dispatch a command).

That split keeps the whole conversation policy — every transition, every
timeout, cancel and barge-in handling — unit-testable with no audio at all.

States (ADP §3.1)::

    OFF  --start-->  IDLE
    IDLE --arm-->    ARMED  (listening for one utterance)
    ARMED --transcript--> REVIEW (brief cancel window) --> BUSY (dispatching)
    BUSY --done-->   ARMED (follow-up window) --or--> IDLE

Safety: the controller never *decides* what a command does — it only carries a
command id the UI already resolved against the safe-tool allowlist. Cancelling,
an empty transcript, or a no-match all return to a safe resting state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class State(Enum):
    """The five conversation states (ADP §3.1)."""

    OFF = "off"
    IDLE = "idle"
    ARMED = "armed"
    REVIEW = "review"
    BUSY = "busy"


#: The nine conversation sound-event ids (SoundEvent values), one per cue.
CUE_ON = "conversation_on"
CUE_OFF = "conversation_off"
CUE_WAKE = "conversation_wake"
CUE_LISTEN = "conversation_listen"
CUE_REVIEW = "conversation_review"
CUE_READY = "conversation_ready"
CUE_IDLE = "conversation_idle"
CUE_TICK = "conversation_thinking_tick"
CUE_ERROR = "conversation_error"


@dataclass(frozen=True, slots=True)
class Timing:
    """User-tunable windows, in milliseconds (ADP §3.2). 0 disables a window.

    * ``silence_ms`` — how long a pause ends an utterance (WCAG 2.2.1).
    * ``review_ms`` — the cancel beat before a matched command dispatches.
    * ``followup_ms`` — stay armed after acting so a follow-up needs no re-arm
      (0 = relax straight to idle).
    * ``thinking_ms`` — spacing of the "still working" tick (WCAG 2.2.2;
      0 = no tick).
    """

    silence_ms: int = 2000
    review_ms: int = 900
    followup_ms: int = 3000
    thinking_ms: int = 2000

    @classmethod
    def from_settings(cls, settings: object) -> Timing:
        def _read(name: str, default: int) -> int:
            try:
                value = int(getattr(settings, name, default))
            except (TypeError, ValueError):
                return default
            return value if value >= 0 else default

        return cls(
            silence_ms=_read("voice_conversation_silence_ms", 2000),
            review_ms=_read("voice_conversation_review_ms", 900),
            followup_ms=_read("voice_conversation_followup_ms", 3000),
            thinking_ms=_read("voice_conversation_thinking_ms", 2000),
        )


#: Timer channels the controller asks the UI to run. Each supersedes the prior
#: request on the same channel (the UI cancels an outstanding one before
#: starting the new one).
TIMER_REVIEW = "review"
TIMER_FOLLOWUP = "followup"
TIMER_THINKING = "thinking"


@dataclass(frozen=True, slots=True)
class Effect:
    """One side effect for the UI to perform. Ordered; execute in sequence."""

    kind: str  # sound | announce | start_capture | stop_capture | dispatch
    #             | start_timer | cancel_timer
    value: str = ""  # sound id / announcement text / command id / timer channel
    delay_ms: int = 0  # for start_timer


def _sound(event_id: str) -> Effect:
    return Effect("sound", event_id)


def _say(text: str) -> Effect:
    return Effect("announce", text)


@dataclass(slots=True)
class ConversationController:
    """The conversation policy engine (pure; drive it from the UI)."""

    timing: Timing = field(default_factory=Timing)
    state: State = State.OFF
    #: Optional name for warm prompts ("Listening, Jeff.").
    user_name: str = ""
    #: When True, prompts use the varied, time-aware voice-cue phrasing (ADP
    #: personality); when False, a plain "Listening." — deterministic for tests.
    varied_prompts: bool = False
    _armed_once: bool = field(default=False, repr=False)

    # -- lifecycle ------------------------------------------------------- #

    def start(self) -> list[Effect]:
        """Turn conversation mode on and arm the first listen."""
        if self.state is not State.OFF:
            return []
        self.state = State.IDLE
        self._armed_once = False
        return [_sound(CUE_ON), *self._arm()]

    def _listen_prompt(self) -> str:
        """The spoken 'go ahead' line — varied when enabled, plain otherwise."""
        if self.varied_prompts:
            from quill.core.speech import voice_cues

            if not self._armed_once:
                return voice_cues.welcome(self.user_name, first=True)
            return voice_cues.listening(self.user_name)
        return "Listening" + (f", {self.user_name}." if self.user_name else ".")

    def stop(self) -> list[Effect]:
        """Turn conversation mode off from any state."""
        if self.state is State.OFF:
            return []
        self.state = State.OFF
        return [
            Effect("cancel_timer", TIMER_REVIEW),
            Effect("cancel_timer", TIMER_FOLLOWUP),
            Effect("cancel_timer", TIMER_THINKING),
            Effect("stop_capture"),
            _sound(CUE_OFF),
            _say("Conversation mode off."),
        ]

    # -- listening ------------------------------------------------------- #

    def _arm(self) -> list[Effect]:
        """Enter ARMED and open the microphone for one utterance."""
        self.state = State.ARMED
        prompt = self._listen_prompt()
        self._armed_once = True
        return [
            Effect("cancel_timer", TIMER_FOLLOWUP),
            _sound(CUE_LISTEN),
            _say(prompt),
            Effect("start_capture"),
        ]

    def on_transcript(self, command_id: str | None, message: str) -> list[Effect]:
        """A transcript arrived and the UI resolved it (id or ``None``).

        ``command_id`` is a safe-tool id when a command matched, or ``None``
        for cancel / no-match / empty. ``message`` is the UI-supplied spoken
        line (e.g. "Running Save." or "No command matched.").
        """
        if self.state is not State.ARMED:
            return []
        if command_id is None:
            # No-match or empty: say why, then re-arm (still in conversation).
            return [_sound(CUE_ERROR), _say(message), *self._arm()]
        # Matched: brief review/cancel beat, then dispatch.
        self.state = State.REVIEW
        effects = [_sound(CUE_REVIEW), _say(message)]
        self._pending_command = command_id
        if self.timing.review_ms > 0:
            effects.append(Effect("start_timer", TIMER_REVIEW, self.timing.review_ms))
        else:
            effects.extend(self._dispatch())
        return effects

    def on_cancel(self) -> list[Effect]:
        """The user said a cancel phrase (or pressed Escape) mid-flight."""
        if self.state is State.OFF:
            return []
        self._pending_command = ""
        return [
            Effect("cancel_timer", TIMER_REVIEW),
            _say("Cancelled."),
            *self._arm(),
        ]

    def on_review_timer(self) -> list[Effect]:
        """The review/cancel window elapsed without a cancel — dispatch now."""
        if self.state is not State.REVIEW:
            return []
        return self._dispatch()

    def _dispatch(self) -> list[Effect]:
        command_id = self._pending_command
        self._pending_command = ""
        self.state = State.BUSY
        effects: list[Effect] = [Effect("dispatch", command_id)]
        if self.timing.thinking_ms > 0:
            effects.append(Effect("start_timer", TIMER_THINKING, self.timing.thinking_ms))
        return effects

    def on_thinking_timer(self) -> list[Effect]:
        """Emit a "still working" tick and re-arm the tick while still busy."""
        if self.state is not State.BUSY or self.timing.thinking_ms <= 0:
            return []
        return [
            _sound(CUE_TICK),
            Effect("start_timer", TIMER_THINKING, self.timing.thinking_ms),
        ]

    def on_action_done(self) -> list[Effect]:
        """The dispatched command finished; open the follow-up window."""
        if self.state is not State.BUSY:
            return []
        effects: list[Effect] = [
            Effect("cancel_timer", TIMER_THINKING),
            _sound(CUE_READY),
        ]
        if self.timing.followup_ms > 0:
            effects.extend(self._arm())
            effects.append(Effect("start_timer", TIMER_FOLLOWUP, self.timing.followup_ms))
        else:
            effects.extend(self._relax())
        return effects

    def on_followup_timer(self) -> list[Effect]:
        """No follow-up came within the window — relax to idle."""
        if self.state is not State.ARMED:
            return []
        return [Effect("stop_capture"), *self._relax()]

    def _relax(self) -> list[Effect]:
        self.state = State.IDLE
        return [_sound(CUE_IDLE)]

    # Set/cleared internally between transcript and dispatch.
    _pending_command: str = ""

    # -- introspection (for the UI status surface) ----------------------- #

    def status_text(self) -> str:
        return {
            State.OFF: "Conversation mode off",
            State.IDLE: "Conversation mode on"
            + (", say a command" if not self.user_name else f", {self.user_name}"),
            State.ARMED: "Listening",
            State.REVIEW: "Got it",
            State.BUSY: "Working",
        }[self.state]


__all__ = [
    "CUE_ERROR",
    "CUE_IDLE",
    "CUE_LISTEN",
    "CUE_OFF",
    "CUE_ON",
    "CUE_READY",
    "CUE_REVIEW",
    "CUE_TICK",
    "CUE_WAKE",
    "TIMER_FOLLOWUP",
    "TIMER_REVIEW",
    "TIMER_THINKING",
    "ConversationController",
    "Effect",
    "State",
    "Timing",
]
