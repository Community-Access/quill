"""Dictation state machine: modes, states, and legal transitions (PRD §11).

The PRD is emphatic that dictation must use an *explicit* state machine and that
"no two recording states may be active simultaneously" — a single boolean
``is_recording`` is forbidden (§10.1). This module holds the enums and the
transition table; :class:`~quill.core.speech.dictation.controller.DictationController`
enforces them. Keeping the legal-transition graph here (data, not control flow)
makes it directly unit-testable and keeps the controller readable.
"""

from __future__ import annotations

from enum import Enum, auto


class DictationMode(Enum):
    """Which activation style produced the active session."""

    HOLD = auto()
    LOCKED = auto()


class DictationState(Enum):
    """Lifecycle of a single dictation session (PRD §11)."""

    IDLE = auto()
    VALIDATING = auto()
    STARTING = auto()
    HOLD_RECORDING = auto()
    LOCKED_RECORDING = auto()
    PAUSED = auto()
    STOPPING = auto()
    SAVING_AUDIO = auto()
    TRANSCRIBING = auto()
    INSERTING = auto()
    REVIEW_REQUIRED = auto()
    COMPLETED = auto()
    CANCELLED = auto()
    FAILED = auto()
    RECOVERING = auto()


#: The states in which the microphone is actively capturing samples. Used by the
#: controller and UI to answer "is dictation recording right now?" without a bare
#: boolean, and to enforce the single-recorder invariant.
ACTIVE_RECORDING_STATES: frozenset[DictationState] = frozenset({
    DictationState.HOLD_RECORDING,
    DictationState.LOCKED_RECORDING,
})

#: States from which a session can still be safely stopped by the user (Escape,
#: focus loss, max-duration, shutdown). PAUSED is included: a paused locked
#: session still owns the audio device's buffered samples.
STOPPABLE_STATES: frozenset[DictationState] = frozenset(
    ACTIVE_RECORDING_STATES | {DictationState.PAUSED}
)

#: Terminal states — the controller returns to IDLE from any of these.
TERMINAL_STATES: frozenset[DictationState] = frozenset({
    DictationState.COMPLETED,
    DictationState.CANCELLED,
    DictationState.FAILED,
})


# The legal forward transitions. FAILED is reachable from any non-idle, non-
# terminal state (an exception can fire mid-flight), so it is handled separately
# in ``is_valid_transition`` rather than being listed under every key.
_VALID_TRANSITIONS: dict[DictationState, frozenset[DictationState]] = {
    DictationState.IDLE: frozenset({DictationState.VALIDATING, DictationState.RECOVERING}),
    DictationState.VALIDATING: frozenset({
        DictationState.STARTING,
        DictationState.IDLE,
        DictationState.CANCELLED,
    }),
    DictationState.STARTING: frozenset({
        DictationState.HOLD_RECORDING,
        DictationState.LOCKED_RECORDING,
        DictationState.IDLE,
        DictationState.CANCELLED,
    }),
    DictationState.HOLD_RECORDING: frozenset({DictationState.STOPPING, DictationState.CANCELLED}),
    DictationState.LOCKED_RECORDING: frozenset({
        DictationState.PAUSED,
        DictationState.STOPPING,
        DictationState.CANCELLED,
    }),
    DictationState.PAUSED: frozenset({
        DictationState.LOCKED_RECORDING,
        DictationState.STOPPING,
        DictationState.CANCELLED,
    }),
    DictationState.STOPPING: frozenset({DictationState.SAVING_AUDIO, DictationState.CANCELLED}),
    DictationState.SAVING_AUDIO: frozenset({DictationState.TRANSCRIBING, DictationState.CANCELLED}),
    DictationState.TRANSCRIBING: frozenset({
        DictationState.INSERTING,
        DictationState.REVIEW_REQUIRED,
        DictationState.CANCELLED,
    }),
    DictationState.INSERTING: frozenset({DictationState.COMPLETED, DictationState.REVIEW_REQUIRED}),
    DictationState.REVIEW_REQUIRED: frozenset({
        DictationState.INSERTING,
        DictationState.COMPLETED,
        DictationState.IDLE,
    }),
    DictationState.RECOVERING: frozenset({
        DictationState.TRANSCRIBING,
        DictationState.REVIEW_REQUIRED,
        DictationState.IDLE,
    }),
    DictationState.COMPLETED: frozenset({DictationState.IDLE}),
    DictationState.CANCELLED: frozenset({DictationState.IDLE}),
    DictationState.FAILED: frozenset({DictationState.RECOVERING, DictationState.IDLE}),
}


def is_valid_transition(current: DictationState, target: DictationState) -> bool:
    """Return True when ``current -> target`` is a legal state transition.

    A no-op transition to the same state is always allowed (idempotent setters).
    FAILED is reachable from any active, non-terminal state because an exception
    boundary can trip at any point during a live session (PRD §27).
    """
    if current is target:
        return True
    if target is DictationState.FAILED:
        return current not in TERMINAL_STATES
    return target in _VALID_TRANSITIONS.get(current, frozenset())
