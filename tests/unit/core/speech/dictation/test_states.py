from __future__ import annotations

from quill.core.speech.dictation.states import (
    ACTIVE_RECORDING_STATES,
    DictationState,
    is_valid_transition,
)


def test_only_two_recording_states_exist() -> None:
    # PRD §10.1 / §11: recording is never a bare boolean; exactly two states
    # represent an active microphone, and they are mutually exclusive.
    assert ACTIVE_RECORDING_STATES == {
        DictationState.HOLD_RECORDING,
        DictationState.LOCKED_RECORDING,
    }


def test_hold_happy_path_transitions_are_legal() -> None:
    chain = [
        DictationState.IDLE,
        DictationState.VALIDATING,
        DictationState.STARTING,
        DictationState.HOLD_RECORDING,
        DictationState.STOPPING,
        DictationState.SAVING_AUDIO,
        DictationState.TRANSCRIBING,
        DictationState.INSERTING,
        DictationState.COMPLETED,
        DictationState.IDLE,
    ]
    for current, target in zip(chain, chain[1:], strict=False):
        assert is_valid_transition(current, target), f"{current} -> {target}"


def test_locked_pause_resume_is_legal() -> None:
    assert is_valid_transition(DictationState.LOCKED_RECORDING, DictationState.PAUSED)
    assert is_valid_transition(DictationState.PAUSED, DictationState.LOCKED_RECORDING)


def test_failure_reachable_from_active_states_only() -> None:
    assert is_valid_transition(DictationState.TRANSCRIBING, DictationState.FAILED)
    assert is_valid_transition(DictationState.HOLD_RECORDING, DictationState.FAILED)
    # Terminal states cannot fall into FAILED.
    assert not is_valid_transition(DictationState.COMPLETED, DictationState.FAILED)
    assert not is_valid_transition(DictationState.CANCELLED, DictationState.FAILED)


def test_same_state_is_always_valid() -> None:
    for state in DictationState:
        assert is_valid_transition(state, state)


def test_idle_cannot_jump_straight_to_recording() -> None:
    assert not is_valid_transition(DictationState.IDLE, DictationState.HOLD_RECORDING)
    assert not is_valid_transition(DictationState.IDLE, DictationState.LOCKED_RECORDING)
