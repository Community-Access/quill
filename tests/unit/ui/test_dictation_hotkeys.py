"""Coverage for the wx-free lookup tables in the dictation hotkeys mixin.

The live key routing needs wx and is exercised by hand; here we guard the static
feedback/status maps so a renamed or missing FeedbackEvent/DictationState mapping
is caught without a display.
"""

from __future__ import annotations

from quill.core.speech.dictation import DictationState
from quill.core.speech.dictation.controller import FeedbackEvent
from quill.ui.main_frame_dictation_hotkeys import (
    _DICTATION_COMMANDS,
    _DICTATION_FEEDBACK,
    _DICTATION_STATUS_TEXT,
)


def test_every_feedback_event_has_a_mapping() -> None:
    for event in FeedbackEvent:
        assert event in _DICTATION_FEEDBACK, f"missing feedback mapping for {event}"
        earcon, message, status = _DICTATION_FEEDBACK[event]
        assert isinstance(earcon, str) and isinstance(message, str) and isinstance(status, str)


def test_status_text_covers_the_user_visible_states() -> None:
    for state in (
        DictationState.IDLE,
        DictationState.HOLD_RECORDING,
        DictationState.LOCKED_RECORDING,
        DictationState.PAUSED,
        DictationState.TRANSCRIBING,
        DictationState.REVIEW_REQUIRED,
    ):
        assert state in _DICTATION_STATUS_TEXT


def test_all_hotkey_commands_are_declared() -> None:
    # Hold-to-Dictate (F9) was removed: holding a key repeats and announces
    # itself endlessly. Locked Dictation (Ctrl+F9) is the toggle now.
    ids = {command_id for command_id, _title in _DICTATION_COMMANDS}
    assert ids == {
        "tools.dictation_lock_toggle",
        "tools.dictation_pause",
        "tools.dictation_status",
        "tools.dictation_emergency_stop",
        "tools.dictation_cancel",
    }
